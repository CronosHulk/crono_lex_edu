from __future__ import annotations

from datetime import datetime
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
from app.application.admin.user_dictionary.promote import AdminUserDictionaryPromoteAction
from app.domain.user_dictionary.constants import (
    USER_DICTIONARY_DETAILS_FAILED,
    USER_DICTIONARY_EMBEDDING_FAILED,
    USER_DICTIONARY_QUEUED_EMBEDDING,
    USER_DICTIONARY_REJECTED,
)
from app.time_utils import TimeService

USER_DICTIONARY_BULK_PROMOTE_TO_BASE = "promote_to_base"
USER_DICTIONARY_BULK_REJECT = "reject"
USER_DICTIONARY_BULK_REBUILD_DETAILS = "rebuild_details"
USER_DICTIONARY_BULK_REBUILD_EMBEDDING = "rebuild_embedding"
USER_DICTIONARY_BULK_ACTIONS = {
    USER_DICTIONARY_BULK_PROMOTE_TO_BASE,
    USER_DICTIONARY_BULK_REJECT,
    USER_DICTIONARY_BULK_REBUILD_DETAILS,
    USER_DICTIONARY_BULK_REBUILD_EMBEDDING,
}


class AdminUserDictionaryBulkUserDictionaryPort(Protocol):
    def get_entry(self, entry_id: int) -> dict[str, Any] | None: ...

    def requeue_entry_details_build(
        self,
        entry_id: int,
        *,
        actor_label: str,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

    def requeue_entry_embedding_build(
        self,
        entry_id: int,
        *,
        actor_label: str,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

    def update_entry_status(
        self,
        entry_id: int,
        *,
        status: str,
        current_time: datetime,
        source_provider_status_json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...

    def archive_assignments_for_entry(self, entry_id: int, *, current_time: datetime) -> int: ...


class AdminUserDictionaryBulkUserImportItemsPort(Protocol):
    def sync_for_user_dictionary_entry(
        self,
        user_dictionary_entry_id: int,
        *,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None: ...


class AdminUserDictionaryBulkDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    user_dictionary: AdminUserDictionaryBulkUserDictionaryPort
    user_import_items: AdminUserDictionaryBulkUserImportItemsPort


class AdminUserDictionaryBulkAction:
    def __init__(
        self,
        db: AdminUserDictionaryBulkDatabasePort,
        time_service: TimeService,
        promote_action: AdminUserDictionaryPromoteAction,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.promote_action = promote_action

    def execute(self, *, actor: dict[str, Any], action: str, entry_ids: list[int]) -> dict[str, Any]:
        if action == USER_DICTIONARY_BULK_PROMOTE_TO_BASE:
            result = self.promote_action.promote_entries(actor=actor, entry_ids=entry_ids)
            return {**result, "action": action, "updated_count": int(result["promoted_count"])}
        self._require_rebuild_access(actor)
        if action == USER_DICTIONARY_BULK_REJECT:
            return self._reject(actor=actor, entry_ids=entry_ids)
        if action == USER_DICTIONARY_BULK_REBUILD_DETAILS:
            return self._rebuild_details(actor=actor, entry_ids=entry_ids)
        if action == USER_DICTIONARY_BULK_REBUILD_EMBEDDING:
            return self._rebuild_embedding(actor=actor, entry_ids=entry_ids)
        raise AdminUserDictionaryActionValidationError("Unsupported user dictionary bulk action")

    def _require_rebuild_access(self, actor: dict[str, Any]) -> None:
        try:
            require_admin_access_allowed(
                self.db,
                actor,
                action="dictionary/update_word",
                detail="User dictionary rebuild is not allowed",
            )
        except AdminPermissionDeniedError as error:
            raise AdminUserDictionaryActionAccessDeniedError(error.detail) from error

    def _rebuild_details(self, *, actor: dict[str, Any], entry_ids: list[int]) -> dict[str, Any]:
        entries = [self._require_entry(entry_id) for entry_id in entry_ids]
        for entry in entries:
            if entry.get("status") != USER_DICTIONARY_DETAILS_FAILED:
                raise AdminUserDictionaryActionValidationError("Only details_failed entries can be rebuilt")
        current_time = self.time_service.now()
        actor_label = self._actor_label(actor)
        items = []
        for entry in entries:
            updated = self.db.user_dictionary.requeue_entry_details_build(
                int(entry["id"]),
                actor_label=actor_label,
                current_time=current_time,
            )
            if updated is None:
                raise AdminUserDictionaryActionNotFoundError("User dictionary entry not found")
            self.db.user_import_items.sync_for_user_dictionary_entry(
                int(entry["id"]),
                status="queued_for_details",
                error_text=None,
                current_time=current_time,
            )
            items.append(updated)
        return {"action": USER_DICTIONARY_BULK_REBUILD_DETAILS, "items": items, "entry_ids": entry_ids, "updated_count": len(items)}

    def _rebuild_embedding(self, *, actor: dict[str, Any], entry_ids: list[int]) -> dict[str, Any]:
        entries = [self._require_entry(entry_id) for entry_id in entry_ids]
        for entry in entries:
            if not _can_rebuild_embedding(entry):
                raise AdminUserDictionaryActionValidationError(
                    "Only detailed entries without ready embedding can be rebuilt"
                )
        current_time = self.time_service.now()
        actor_label = self._actor_label(actor)
        items = []
        for entry in entries:
            updated = self.db.user_dictionary.requeue_entry_embedding_build(
                int(entry["id"]),
                actor_label=actor_label,
                current_time=current_time,
            )
            if updated is None:
                raise AdminUserDictionaryActionNotFoundError("User dictionary entry not found")
            self.db.user_import_items.sync_for_user_dictionary_entry(
                int(entry["id"]),
                status="queued_for_embedding",
                error_text=None,
                current_time=current_time,
            )
            items.append(updated)
        return {"action": USER_DICTIONARY_BULK_REBUILD_EMBEDDING, "items": items, "entry_ids": entry_ids, "updated_count": len(items)}

    def _reject(self, *, actor: dict[str, Any], entry_ids: list[int]) -> dict[str, Any]:
        entries = [self._require_entry(entry_id) for entry_id in entry_ids]
        for entry in entries:
            if entry.get("status") == USER_DICTIONARY_REJECTED:
                raise AdminUserDictionaryActionValidationError("Only non-rejected entries can be rejected")
            if entry.get("promoted_dictionary_entry_id"):
                raise AdminUserDictionaryActionValidationError("Promoted user dictionary entries cannot be rejected")
        current_time = self.time_service.now()
        actor_label = self._actor_label(actor)
        items = []
        for entry in entries:
            provider_status = dict(entry.get("source_provider_status_json") or {})
            provider_status["admin_reject"] = {
                "actor": actor_label,
                "rejected_at": current_time.isoformat(),
            }
            updated = self.db.user_dictionary.update_entry_status(
                int(entry["id"]),
                status=USER_DICTIONARY_REJECTED,
                source_provider_status_json=provider_status,
                current_time=current_time,
            )
            if updated is None:
                raise AdminUserDictionaryActionNotFoundError("User dictionary entry not found")
            self.db.user_dictionary.archive_assignments_for_entry(int(entry["id"]), current_time=current_time)
            self.db.user_import_items.sync_for_user_dictionary_entry(
                int(entry["id"]),
                status=USER_DICTIONARY_REJECTED,
                error_text=f"Rejected by admin: {actor_label}",
                current_time=current_time,
            )
            items.append(updated)
        return {"action": USER_DICTIONARY_BULK_REJECT, "items": items, "entry_ids": entry_ids, "updated_count": len(items)}

    def _require_entry(self, entry_id: int) -> dict[str, Any]:
        entry = self.db.user_dictionary.get_entry(entry_id)
        if entry is None:
            raise AdminUserDictionaryActionNotFoundError("User dictionary entry not found")
        return entry

    def _actor_label(self, actor: dict[str, Any]) -> str:
        return str(actor.get("username") or actor.get("telegram_user_id") or actor.get("id") or "admin")


def _can_rebuild_embedding(entry: dict[str, Any]) -> bool:
    if bool(entry.get("is_embedding_ready")):
        return False
    status = str(entry.get("status") or "")
    if status not in {USER_DICTIONARY_QUEUED_EMBEDDING, USER_DICTIONARY_EMBEDDING_FAILED}:
        return False
    if not str(entry.get("translation_uk") or "").strip():
        return False
    if not str(entry.get("part_of_speech") or "").strip():
        return False
    if not list(entry.get("examples_json") or []):
        return False
    return True
