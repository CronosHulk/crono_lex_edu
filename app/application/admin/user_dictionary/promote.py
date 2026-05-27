from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.application.admin.user_dictionary.errors import (
    AdminUserDictionaryActionAccessDeniedError,
    AdminUserDictionaryActionNotFoundError,
    AdminUserDictionaryActionValidationError,
)
from app.domain.user_dictionary.constants import USER_DICTIONARY_READY
from app.reference.dictionary_entries import normalize_dictionary_part_of_speech
from app.storage.audio import AudioStorageProvider
from app.time_utils import TimeService
from app.user_import.services.audio_paths import build_pos_audio_path


class AdminUserDictionaryPromoteUserDictionaryPort(Protocol):
    def get_entry(self, entry_id: int) -> dict[str, Any] | None: ...

    def promote_entry_to_core(
        self,
        entry_id: int,
        *,
        audio_path: str,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...


class AdminUserDictionaryPromoteAdminDictionaryPort(Protocol):
    def get_entry(self, entry_id: int) -> dict[str, Any] | None: ...


class AdminUserDictionaryPromoteSettingsPort(Protocol):
    app_dictionary_audio_dir: str
    app_user_import_audio_dir: str


class AdminUserDictionaryPromoteDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_dictionary: AdminUserDictionaryPromoteAdminDictionaryPort
    settings: AdminUserDictionaryPromoteSettingsPort
    user_dictionary: AdminUserDictionaryPromoteUserDictionaryPort


class AdminUserDictionaryPromoteAction:
    def __init__(
        self,
        db: AdminUserDictionaryPromoteDatabasePort,
        time_service: TimeService,
        *,
        audio_storage_provider: AudioStorageProvider,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.audio_storage_provider = audio_storage_provider

    def promote_entry(self, *, actor: dict[str, Any], entry_id: int) -> dict[str, Any]:
        self._require_promote_access(actor)
        return self._promote_entry(entry_id)

    def promote_entries(self, *, actor: dict[str, Any], entry_ids: list[int]) -> dict[str, Any]:
        self._require_promote_access(actor)
        for entry_id in entry_ids:
            self._validate_promotable_entry(entry_id)
        results = [self._promote_entry(entry_id) for entry_id in entry_ids]
        return {
            "items": results,
            "entry_ids": entry_ids,
            "promoted_count": len(results),
        }

    def _require_promote_access(self, actor: dict[str, Any]) -> None:
        try:
            require_admin_access_allowed(
                self.db,
                actor,
                action="dictionary/update_word",
                detail="User dictionary promotion is not allowed",
            )
        except AdminPermissionDeniedError as error:
            raise AdminUserDictionaryActionAccessDeniedError(error.detail) from error

    def _promote_entry(self, entry_id: int) -> dict[str, Any]:
        current_time = self.time_service.now()
        entry = self.db.user_dictionary.get_entry(entry_id)
        entry = self._validate_promotable_entry(entry_id, entry=entry)
        if entry.get("promoted_dictionary_entry_id"):
            promoted = self.db.admin_dictionary.get_entry(int(entry["promoted_dictionary_entry_id"]))
            if promoted is None:
                raise AdminUserDictionaryActionNotFoundError("Promoted dictionary entry not found")
            return {"entry": entry, "dictionary_entry": promoted, "created": False}

        audio_path, source_path = self._prepare_audio_at_core_path(entry)
        dictionary_entry = self.db.user_dictionary.promote_entry_to_core(
            entry_id,
            audio_path=audio_path,
            current_time=current_time,
        )
        if dictionary_entry is None:
            raise AdminUserDictionaryActionNotFoundError("User dictionary entry not found")
        self._remove_user_audio_source(source_path)
        promoted_entry = {
            **entry,
            "status": "promoted",
            "promoted_dictionary_entry_id": int(dictionary_entry["id"]),
            "audio_path": audio_path,
        }
        return {"entry": promoted_entry, "dictionary_entry": dictionary_entry, "created": True}

    def _validate_promotable_entry(self, entry_id: int, *, entry: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = entry if entry is not None else self.db.user_dictionary.get_entry(entry_id)
        if entry is None:
            raise AdminUserDictionaryActionNotFoundError("User dictionary entry not found")
        if entry.get("status") != USER_DICTIONARY_READY:
            raise AdminUserDictionaryActionValidationError("Only ready user dictionary entries can be promoted")
        if not entry.get("promoted_dictionary_entry_id"):
            try:
                normalize_dictionary_part_of_speech(entry.get("part_of_speech"))
            except ValueError as error:
                raise AdminUserDictionaryActionValidationError(str(error)) from error
            self._validate_audio_available(entry)
        return entry

    def _validate_audio_available(self, entry: dict[str, Any]) -> None:
        source_audio_path = str(entry.get("audio_path") or "").strip()
        if not source_audio_path:
            raise AdminUserDictionaryActionValidationError("User dictionary entry has no audio")
        target_audio_path = self._canonical_core_audio_path(entry)
        if self.audio_storage_provider.exists(target_audio_path):
            return
        if not self.audio_storage_provider.exists(source_audio_path):
            raise AdminUserDictionaryActionValidationError("User dictionary audio file is missing")

    def _prepare_audio_at_core_path(self, entry: dict[str, Any]) -> tuple[str, str]:
        source_audio_path = str(entry.get("audio_path") or "").strip()
        if not source_audio_path:
            raise AdminUserDictionaryActionValidationError("User dictionary entry has no audio")
        target_audio_path = self._canonical_core_audio_path(entry)
        if self.audio_storage_provider.exists(target_audio_path):
            return target_audio_path, source_audio_path
        if not self.audio_storage_provider.exists(source_audio_path):
            raise AdminUserDictionaryActionValidationError("User dictionary audio file is missing")
        self.audio_storage_provider.copy(source_audio_path, target_audio_path)
        return target_audio_path, source_audio_path

    def _canonical_core_audio_path(self, entry: dict[str, Any]) -> str:
        audio_dir = Path(str(getattr(self.db.settings, "app_dictionary_audio_dir", "word_base/base")))
        return build_pos_audio_path(audio_dir, entry)

    def _remove_user_audio_source(self, source_audio_path: str) -> None:
        user_audio_root = str(getattr(self.db.settings, "app_user_import_audio_dir", "word_base/user"))
        self.audio_storage_provider.delete_if_under_roots(source_audio_path, [user_audio_root])
