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
from app.subscriptions.runtime_settings import (
    SubscriptionSettingsValidationError,
    read_subscription_runtime_settings,
)
from app.time_utils import TimeService


class SetUserSubscriptionTrialAdminUsersPort(Protocol):
    def get_by_id(self, user_id: str) -> dict[str, Any] | None: ...


class SetUserSubscriptionTrialSubscriptionsPort(Protocol):
    def set_trial_for_user(
        self,
        user_id: str,
        *,
        trial_duration_days: int,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

    def clear_trial_for_user(self, user_id: str, *, current_time: datetime) -> dict[str, Any] | None: ...


class SetUserSubscriptionTrialAppSettingsPort(Protocol):
    def get_value(self, key: str) -> Any | None: ...


class SetUserSubscriptionTrialDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    admin_users: SetUserSubscriptionTrialAdminUsersPort
    subscriptions: SetUserSubscriptionTrialSubscriptionsPort
    app_settings: SetUserSubscriptionTrialAppSettingsPort


def set_user_subscription_trial(
    db: SetUserSubscriptionTrialDatabasePort,
    time_service: TimeService,
    *,
    actor: dict[str, Any],
    target_user_id: str,
    is_trial_enabled: bool,
) -> dict[str, Any]:
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
    current_time = time_service.now()
    if is_trial_enabled:
        try:
            trial_duration_days = int(read_subscription_runtime_settings(db)["trial_duration_days"])
        except SubscriptionSettingsValidationError as error:
            raise AdminUserActionValidationError(str(error)) from error
        if trial_duration_days <= 0:
            raise AdminUserActionValidationError("Trial duration is disabled in subscription settings")
        subscription = db.subscriptions.set_trial_for_user(
            str(target["user_id"]),
            trial_duration_days=trial_duration_days,
            current_time=current_time,
        )
        if subscription is None:
            raise AdminUserActionValidationError("Trial can be enabled only for free plan users")
    else:
        subscription = db.subscriptions.clear_trial_for_user(
            str(target["user_id"]),
            current_time=current_time,
        )
    if subscription is None:
        raise AdminUserActionNotFoundError("User subscription not found")
    updated = db.admin_users.get_by_id(target_user_id)
    return updated or {**target, "subscription": subscription}
