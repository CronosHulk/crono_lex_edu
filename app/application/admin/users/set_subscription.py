from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    ensure_super_admin_actor_allowed,
    require_admin_access_allowed,
)
from app.application.admin.users.errors import (
    AdminUserActionAccessDeniedError,
    AdminUserActionNotFoundError,
    AdminUserActionValidationError,
)
from app.subscriptions.plans import get_subscription_plan
from app.time_utils import TimeService


class SetUserSubscriptionAdminUsersPort(Protocol):
    def get_by_id(self, user_id: str) -> dict[str, Any] | None: ...


class SetUserSubscriptionSubscriptionsPort(Protocol):
    def set_plan_for_user(
        self,
        user_id: str,
        *,
        plan_key: str,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...


class SetUserSubscriptionDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_users: SetUserSubscriptionAdminUsersPort
    subscriptions: SetUserSubscriptionSubscriptionsPort


def set_user_subscription(
    db: SetUserSubscriptionDatabasePort,
    time_service: TimeService,
    *,
    actor: dict[str, Any],
    target_user_id: str,
    plan_key: str,
) -> dict[str, Any]:
    normalized_plan = plan_key.strip()
    try:
        get_subscription_plan(normalized_plan)
    except ValueError as error:
        raise AdminUserActionValidationError(str(error)) from error
    try:
        require_admin_access_allowed(
            db,
            actor,
            action="users/update_subscription",
            detail="Subscription change is not allowed",
        )
        ensure_super_admin_actor_allowed(actor)
    except AdminPermissionDeniedError as error:
        raise AdminUserActionAccessDeniedError(error.detail) from error
    target = db.admin_users.get_by_id(target_user_id)
    if target is None:
        raise AdminUserActionNotFoundError("User not found")
    subscription = db.subscriptions.set_plan_for_user(
        str(target["user_id"]),
        plan_key=normalized_plan,
        current_time=time_service.now(),
    )
    if subscription is None:
        raise AdminUserActionNotFoundError("User not found")
    updated = db.admin_users.get_by_id(target_user_id)
    return updated or {**target, "subscription": subscription}
