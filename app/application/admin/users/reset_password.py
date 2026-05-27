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
)
from app.time_utils import TimeService


class ResetUserPasswordAdminUsersPort(Protocol):
    def get_by_id(self, user_id: str) -> dict[str, Any] | None: ...


class ResetUserPasswordClientWebAuthPort(Protocol):
    def clear_password_hash(self, telegram_user_id: int, *, current_time: datetime) -> None: ...

    def revoke_sessions_for_user(self, telegram_user_id: int, *, current_time: datetime) -> int: ...


class ResetUserPasswordDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_users: ResetUserPasswordAdminUsersPort
    client_web_auth: ResetUserPasswordClientWebAuthPort


def reset_user_password(
    db: ResetUserPasswordDatabasePort,
    time_service: TimeService,
    *,
    actor: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    try:
        require_admin_access_allowed(db, actor, action="users/reset_password", detail="Password reset is not allowed")
    except AdminPermissionDeniedError as error:
        raise AdminUserActionAccessDeniedError(error.detail) from error
    target = db.admin_users.get_by_id(user_id)
    if target is None:
        raise AdminUserActionNotFoundError("User not found")
    current_time = time_service.now()
    telegram_user_id = int(target["telegram_user_id"])
    db.client_web_auth.clear_password_hash(telegram_user_id, current_time=current_time)
    revoked_sessions = db.client_web_auth.revoke_sessions_for_user(telegram_user_id, current_time=current_time)
    return {"status": "ok", "revoked_sessions": revoked_sessions}
