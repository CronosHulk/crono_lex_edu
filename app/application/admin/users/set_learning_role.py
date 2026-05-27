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
)
from app.time_utils import TimeService


class SetUserLearningRoleAdminUsersPort(Protocol):
    def set_learning_role(
        self,
        user_id: str,
        learning_role: str,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...


class SetUserLearningRoleDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_users: SetUserLearningRoleAdminUsersPort


def set_user_learning_role(
    db: SetUserLearningRoleDatabasePort,
    time_service: TimeService,
    *,
    actor: dict[str, Any],
    target_user_id: str,
    learning_role: str,
) -> dict[str, Any]:
    normalized_role = learning_role.strip()
    try:
        require_admin_access_allowed(
            db,
            actor,
            action="users/update_learning_role",
            detail="Learning role change is not allowed",
        )
    except AdminPermissionDeniedError as error:
        raise AdminUserActionAccessDeniedError(error.detail) from error
    if normalized_role not in {"student", "teacher"}:
        raise AdminUserActionForbiddenError("Learning role change is not allowed")
    updated = db.admin_users.set_learning_role(target_user_id, normalized_role, current_time=time_service.now())
    if updated is None:
        raise AdminUserActionNotFoundError("User not found")
    return updated
