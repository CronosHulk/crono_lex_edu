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
    AdminUserActionForbiddenError,
    AdminUserActionNotFoundError,
    AdminUserActionValidationError,
)
from app.time_utils import TimeService


class SetUserRoleAdminUsersPort(Protocol):
    def set_acl_group_by_title(
        self,
        user_id: str,
        group_title: str,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...


class SetUserRoleDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_users: SetUserRoleAdminUsersPort


def set_user_role(
    db: SetUserRoleDatabasePort,
    time_service: TimeService,
    *,
    actor: dict[str, Any],
    target_user_id: str,
    role: str,
) -> dict[str, Any]:
    actor_role = str(actor.get("acl_group_title") or "")
    normalized_role = role.strip()
    try:
        require_admin_access_allowed(
            db,
            actor,
            action=f"users/update_role_to_{normalized_role}",
            detail="Role change is not allowed",
        )
    except AdminPermissionDeniedError as error:
        raise AdminUserActionAccessDeniedError(error.detail) from error
    if str(actor.get("user_id") or actor.get("id") or "") == target_user_id and normalized_role != actor_role:
        raise AdminUserActionValidationError("You cannot change your own role")
    if actor_role == "super_admin":
        if normalized_role not in {"student", "admin", "admin_editor"}:
            raise AdminUserActionForbiddenError("Role change is not allowed")
    else:
        raise AdminUserActionForbiddenError("Role change is not allowed")
    updated = db.admin_users.set_acl_group_by_title(target_user_id, normalized_role, current_time=time_service.now())
    if updated is None:
        raise AdminUserActionNotFoundError("User not found")
    return updated
