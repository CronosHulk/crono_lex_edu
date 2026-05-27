from __future__ import annotations

from typing import Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.dictionary.errors import (
    AdminDictionaryActionAccessDeniedError,
    AdminDictionaryActionAssignedEntryError,
    AdminDictionaryActionEntityNotFoundError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.domain.user_dictionary.constants import USER_WORD_SOURCE_CORE


class DeleteEntryUserDictionaryPort(Protocol):
    def count_assignments_for_word(self, *, word_source: str, word_id: int) -> int: ...


class DeleteEntryAdminDictionaryPort(Protocol):
    def delete_entry(self, entry_id: int) -> bool: ...


class DeleteDictionaryEntryDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    user_dictionary: DeleteEntryUserDictionaryPort
    admin_dictionary: DeleteEntryAdminDictionaryPort


def delete_dictionary_entry(db: DeleteDictionaryEntryDatabasePort, *, actor: dict, entry_id: int) -> dict[str, str]:
    try:
        require_admin_access_allowed(db, actor, action="dictionary/delete_word", detail="Delete is not allowed")
    except AdminPermissionDeniedError as error:
        raise AdminDictionaryActionAccessDeniedError(error.detail) from error
    assigned_count = db.user_dictionary.count_assignments_for_word(word_source=USER_WORD_SOURCE_CORE, word_id=entry_id)
    if assigned_count > 0:
        raise AdminDictionaryActionAssignedEntryError()
    ok = db.admin_dictionary.delete_entry(entry_id)
    if not ok:
        raise AdminDictionaryActionEntityNotFoundError()
    return {"status": "ok"}
