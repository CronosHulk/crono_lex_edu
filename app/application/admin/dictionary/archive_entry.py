from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.dictionary.errors import (
    AdminDictionaryActionAccessDeniedError,
    AdminDictionaryActionEntityNotFoundError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.time_utils import TimeService


class ArchiveEntryAdminDictionaryPort(Protocol):
    def set_entry_archived(self, entry_id: int, *, is_archived: bool, current_time: datetime) -> bool: ...


class ArchiveDictionaryEntryDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_dictionary: ArchiveEntryAdminDictionaryPort


def archive_dictionary_entry(
    db: ArchiveDictionaryEntryDatabasePort,
    time_service: TimeService,
    *,
    actor: dict,
    entry_id: int,
) -> dict[str, str]:
    try:
        require_admin_access_allowed(db, actor, action="dictionary/archive_word", detail="Archive is not allowed")
    except AdminPermissionDeniedError as error:
        raise AdminDictionaryActionAccessDeniedError(error.detail) from error
    ok = db.admin_dictionary.set_entry_archived(entry_id, is_archived=True, current_time=time_service.now())
    if not ok:
        raise AdminDictionaryActionEntityNotFoundError()
    return {"status": "ok"}
