from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.subscriptions.paywall import PaywallService
from app.subscriptions.plan_limits import read_plan_limit_settings
from app.subscriptions.plans import SubscriptionEntitlements


class EntitlementResolverService(Protocol):
    def resolve(
        self, subscription: Any | None, *, current_time: datetime
    ) -> SubscriptionEntitlements:
        ...


class UserEntitlementSubscriptionRepository(Protocol):
    def get_by_user_uuid(self, user_uuid: str | UUID) -> dict[str, Any] | None:
        ...


class UserEntitlementProfileRepository(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class UserEntitlementDatabasePort(Protocol):
    @property
    def subscriptions(self) -> UserEntitlementSubscriptionRepository | None:
        ...

    @property
    def user_profiles(self) -> UserEntitlementProfileRepository | None:
        ...


def read_user_uuid(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    raw_user_uuid = value.get("user_id") or value.get("user_uuid") or value.get("id")
    return str(raw_user_uuid) if raw_user_uuid else None


class UserEntitlementResolver:
    def __init__(
        self,
        db: UserEntitlementDatabasePort,
        entitlement_service: EntitlementResolverService | None = None,
    ) -> None:
        self.db = db
        self.entitlement_service = entitlement_service

    def resolve_for_user_uuid(
        self,
        user_uuid: str | UUID | None,
        *,
        current_time: datetime,
    ) -> SubscriptionEntitlements:
        subscription = self.subscription_for_user_uuid(user_uuid)
        return self.resolve_subscription(subscription, current_time=current_time)

    def resolve_subscription(self, subscription: Any | None, *, current_time: datetime) -> SubscriptionEntitlements:
        return self._entitlement_service().resolve(subscription, current_time=current_time)

    def subscription_for_user_uuid(self, user_uuid: str | UUID | None) -> Any | None:
        subscriptions = getattr(self.db, "subscriptions", None)
        if not user_uuid or subscriptions is None:
            return None
        return subscriptions.get_by_user_uuid(user_uuid)

    def resolve_for_telegram_user(self, telegram_user_id: int, *, current_time: datetime) -> SubscriptionEntitlements:
        return self.resolve_for_user_uuid(
            self.user_uuid_for_telegram_user(telegram_user_id),
            current_time=current_time,
        )

    def resolve_optional_for_telegram_user(
        self, telegram_user_id: int, *, current_time: datetime
    ) -> SubscriptionEntitlements | None:
        user_uuid = self.user_uuid_for_telegram_user(telegram_user_id)
        if not user_uuid or getattr(self.db, "subscriptions", None) is None:
            return None
        return self.resolve_for_user_uuid(user_uuid, current_time=current_time)

    def reminders_per_day_for_telegram_user(
        self, telegram_user_id: int, *, current_time: datetime
    ) -> int:
        entitlements = self.resolve_optional_for_telegram_user(
            telegram_user_id,
            current_time=current_time,
        )
        if entitlements is None:
            entitlements = self.resolve_subscription(None, current_time=current_time)
        return int(entitlements.reminders_per_day)

    def user_uuid_for_telegram_user(self, telegram_user_id: int) -> str | None:
        user_profiles = getattr(self.db, "user_profiles", None)
        if user_profiles is None:
            return None
        profile = user_profiles.get_profile(telegram_user_id)
        return read_user_uuid(profile)

    def _entitlement_service(self) -> EntitlementResolverService:
        if self.entitlement_service is not None:
            return self.entitlement_service
        return PaywallService(plan_limits=read_plan_limit_settings(self.db))
