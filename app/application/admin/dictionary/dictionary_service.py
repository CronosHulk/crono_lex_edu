from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.dictionary.errors import (
    AdminDictionaryServiceAccessDeniedError,
    AdminDictionaryServiceAudioNotFoundError,
    AdminDictionaryServiceEntryNotFoundError,
    AdminDictionaryServiceValidationError,
)
from app.application.admin.dictionary.validators import (
    AdminExamplesValidationError,
    normalize_examples_json,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.reference.dictionary_entries import normalize_dictionary_entry_type
from app.storage.audio import AudioStorageProvider
from app.time_utils import TimeService

MAX_TEXT_FIELD_LENGTH = 500
MAX_EXAMPLES_COUNT = 20


class AdminDictionaryRepositoryPort(Protocol):
    def update_entry(
        self,
        entry_id: int,
        *,
        audio_storage_provider: AudioStorageProvider,
        word: str | None = None,
        transcription: str | None = None,
        translation_uk: str | None = None,
        translation_ru: str | None = None,
        translation_pl: str | None = None,
        examples_json: list[str] | None = None,
        entry_type: str | None = None,
        audio_roots: list[Path | str] | None = None,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

    def get_entry_audio(self, entry_id: int) -> dict[str, Any] | None: ...


class AdminDictionaryDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_dictionary: AdminDictionaryRepositoryPort
    settings: Any


class AdminDictionaryService:
    def __init__(
        self,
        db: AdminDictionaryDatabasePort,
        time_service: TimeService,
        *,
        audio_storage_provider: AudioStorageProvider,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.audio_storage_provider = audio_storage_provider

    def update_dictionary_entry(self, *, actor: dict[str, Any], entry_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="dictionary/update_word")
        normalized_payload = self.normalize_dictionary_entry_payload(payload)
        entry = self.db.admin_dictionary.update_entry(
            entry_id,
            word=normalized_payload.get("word"),
            transcription=normalized_payload.get("transcription"),
            translation_uk=normalized_payload.get("translation_uk"),
            translation_ru=normalized_payload.get("translation_ru"),
            translation_pl=normalized_payload.get("translation_pl"),
            examples_json=normalized_payload.get("examples_json"),
            entry_type=normalized_payload.get("entry_type"),
            audio_storage_provider=self.audio_storage_provider,
            audio_roots=[Path(str(getattr(self.db.settings, "app_dictionary_audio_dir", "word_base/base")))],
            current_time=self.time_service.now(),
        )
        if entry is None:
            raise AdminDictionaryServiceEntryNotFoundError()
        return entry

    def get_audio_path(self, *, actor: dict[str, Any], entry_id: int) -> str | None:
        self._require_admin_access(actor, action="dictionary/play_audio")
        entry = self.db.admin_dictionary.get_entry_audio(entry_id)
        if entry is None:
            raise AdminDictionaryServiceAudioNotFoundError()
        return entry.get("audio_path")

    def normalize_dictionary_entry_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        allowed_fields = {
            "word",
            "transcription",
            "phonetic_us",
            "translation_uk",
            "translation_ru",
            "translation_pl",
            "examples_json",
            "entry_type",
        }
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in allowed_fields:
                continue
            if key == "phonetic_us":
                key = "transcription"
            if key in {"word", "transcription", "translation_uk", "translation_ru", "translation_pl"}:
                text = str(value or "").strip()
                if key in {"word", "translation_uk"} and not text:
                    raise AdminDictionaryServiceValidationError(f"{key} is required")
                if len(text) > MAX_TEXT_FIELD_LENGTH:
                    raise AdminDictionaryServiceValidationError(f"{key} is too long")
                normalized[key] = text
            elif key == "examples_json":
                try:
                    normalized[key] = normalize_examples_json(value, max_count=MAX_EXAMPLES_COUNT)
                except AdminExamplesValidationError as error:
                    raise AdminDictionaryServiceValidationError(error.detail) from error
            elif key == "entry_type":
                try:
                    normalized[key] = normalize_dictionary_entry_type(str(value or "").strip())
                except ValueError as error:
                    raise AdminDictionaryServiceValidationError(str(error)) from error
        return normalized

    def _require_admin_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminDictionaryServiceAccessDeniedError(error.detail) from error
