from __future__ import annotations

from typing import Any, Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.application.admin.users.errors import (
    AdminUserActionAccessDeniedError,
    AdminUserActionNotFoundError,
    AdminUserActionValidationError,
)


class DeleteUserAdminUsersPort(Protocol):
    def delete(self, user_id: str) -> bool: ...


class DeleteUserDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_users: DeleteUserAdminUsersPort


def delete_user(db: DeleteUserDatabasePort, *, actor: dict[str, Any], user_id: str) -> dict[str, str]:
    try:
        require_admin_access_allowed(db, actor, action="users/delete", detail="Delete is not allowed")
    except AdminPermissionDeniedError as error:
        raise AdminUserActionAccessDeniedError(error.detail) from error
    if str(actor.get("user_id") or actor.get("id") or "") == user_id:
        raise AdminUserActionValidationError("You cannot delete your own user")
    ok = db.admin_users.delete(user_id)
    if not ok:
        raise AdminUserActionNotFoundError("Entity not found")
    return {"status": "ok"}
