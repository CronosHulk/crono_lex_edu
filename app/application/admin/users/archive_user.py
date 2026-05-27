from __future__ import annotations

from datetime import datetime
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
from app.time_utils import TimeService


class ArchiveUserAdminUsersPort(Protocol):
    def set_status(self, user_id: str, status: str, *, current_time: datetime) -> bool: ...


class ArchiveUserDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_users: ArchiveUserAdminUsersPort


def archive_user(
    db: ArchiveUserDatabasePort,
    time_service: TimeService,
    *,
    actor: dict[str, Any],
    user_id: str,
) -> dict[str, str]:
    try:
        require_admin_access_allowed(db, actor, action="users/archive", detail="Archive is not allowed")
    except AdminPermissionDeniedError as error:
        raise AdminUserActionAccessDeniedError(error.detail) from error
    if str(actor.get("user_id") or actor.get("id") or "") == user_id:
        raise AdminUserActionValidationError("You cannot archive your own user")
    ok = db.admin_users.set_status(user_id, "archived", current_time=time_service.now())
    if not ok:
        raise AdminUserActionNotFoundError("Entity not found")
    return {"status": "ok"}
