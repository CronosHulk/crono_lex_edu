from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.dictionary.errors import AdminDictionaryActionAccessDeniedError
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.time_utils import TimeService


class VerifyEntriesAdminDictionaryPort(Protocol):
    def mark_entries_teacher_verified(
        self,
        entry_ids: list[int],
        *,
        verified_by_user_uuid: str,
        current_time: datetime,
    ) -> int: ...


class VerifyDictionaryEntriesDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_dictionary: VerifyEntriesAdminDictionaryPort


def verify_dictionary_entries(
    db: VerifyDictionaryEntriesDatabasePort,
    time_service: TimeService,
    *,
    actor: dict[str, Any],
    entry_ids: list[int],
) -> dict[str, Any]:
    try:
        require_admin_access_allowed(
            db,
            actor,
            action="dictionary/verify_word",
            detail="Dictionary verification is not allowed",
        )
    except AdminPermissionDeniedError as error:
        raise AdminDictionaryActionAccessDeniedError(error.detail) from error
    verified_count = db.admin_dictionary.mark_entries_teacher_verified(
        entry_ids,
        verified_by_user_uuid=str(actor["user_id"]),
        current_time=time_service.now(),
    )
    return {"status": "ok", "verified_count": verified_count}
