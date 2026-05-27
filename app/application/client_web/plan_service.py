from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.billing.runtime_settings import (
    DOUBLE_TIME_FOR_PROJECT_SUPPORT_TEXT,
    BillingRuntimeSettingsValidationError,
    read_billing_runtime_settings,
)
from app.billing.services.checkout_provider_config import (
    resolve_checkout_provider_config,
    supported_checkout_period_months,
)
from app.billing.services.checkout_service import build_checkout_quote
from app.subscriptions.paywall import (
    CHECKOUT_MODE_INSTANT,
    CHECKOUT_PROVIDER_BILLING,
    PaywallService,
)
from app.subscriptions.plan_limits import (
    CUSTOMER_PLAN_KEYS,
    PlanLimitSettingsValidationError,
    read_plan_limit_settings,
)
from app.subscriptions.plans import (
    PLAN_FREE,
    PLAN_PREMIUM,
    PLAN_PREMIUM_PLUS,
    get_subscription_plan,
)
from app.time_utils import TimeService

CUSTOMER_PLAN_RANKS = {
    PLAN_FREE: 0,
    PLAN_PREMIUM: 1,
    PLAN_PREMIUM_PLUS: 2,
}


class ClientWebPlanError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ClientWebPlanValidationError(ClientWebPlanError):
    pass


class ClientWebPlanProfileNotFoundError(ClientWebPlanError):
    pass


class ClientWebPlanAppSettingsPort(Protocol):
    def get_value(self, key: str) -> Any | None: ...


class ClientWebPlanDatabasePort(Protocol):
    settings: Any
    app_settings: ClientWebPlanAppSettingsPort


class ClientWebPlanAccountProvider(Protocol):
    def user_uuid_for_user(self, user: dict[str, Any]) -> str | None: ...

    def subscription_for_user_uuid(self, user_uuid: str) -> Any | None: ...

    def set_plan_for_user(self, user_uuid: str, *, plan_key: str, current_time: datetime) -> Any: ...

    def billing_subscription_projection(
        self,
        user_uuid: str | None,
        *,
        fallback_subscription: Any | None,
        current_time: datetime,
    ) -> Any | None: ...


class ClientWebPlanService:
    def __init__(
        self,
        db: ClientWebPlanDatabasePort,
        time_service: TimeService,
        *,
        account_provider: ClientWebPlanAccountProvider,
        post_upgrade_rescan: Callable[..., dict[str, Any] | None] | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.account_provider = account_provider
        self.post_upgrade_rescan = post_upgrade_rescan

    def list_plans(self, user: dict[str, Any]) -> dict[str, Any]:
        user_uuid = self.account_provider.user_uuid_for_user(user)
        subscription = self.account_provider.subscription_for_user_uuid(user_uuid) if user_uuid else None
        paywall = self._paywall()
        current_time = self.time_service.now()
        billing_subscription = self.account_provider.billing_subscription_projection(
            user_uuid,
            fallback_subscription=subscription,
            current_time=current_time,
        )
        current_plan_key = paywall.read_plan_key(billing_subscription)
        billing_settings = self._client_billing_settings(self._billing_settings())
        customer_plan_keys = build_customer_plan_keys(billing_settings)
        return {
            "current_plan_key": current_plan_key,
            "subscription": build_client_subscription_payload(billing_subscription, current_time=current_time),
            "billing": build_client_billing_settings(billing_settings),
            "plans": [
                enrich_plan_card_for_billing(
                    plan,
                    subscription=billing_subscription,
                    billing_settings=billing_settings,
                    current_time=current_time,
                )
                for plan in paywall.list_customer_plans(current_plan_key, plan_keys=customer_plan_keys)
            ],
        }

    def select_plan(self, user: dict[str, Any], *, plan_key: str) -> dict[str, Any]:
        normalized_plan = str(plan_key or "").strip()
        if normalized_plan not in CUSTOMER_PLAN_KEYS:
            raise ClientWebPlanValidationError("plan_key must be one of: free, premium, premium_plus")
        get_subscription_plan(normalized_plan)
        user_uuid = self.account_provider.user_uuid_for_user(user)
        if not user_uuid:
            raise ClientWebPlanProfileNotFoundError("User profile not found")
        current_time = self.time_service.now()
        paywall = self._paywall()
        subscription = self.account_provider.subscription_for_user_uuid(user_uuid)
        current_plan_key = paywall.read_plan_key(subscription)
        if normalized_plan != PLAN_FREE:
            raise ClientWebPlanValidationError("Paid plans require billing checkout")
        if current_plan_key != PLAN_FREE:
            raise ClientWebPlanValidationError("Paid subscription cannot be downgraded manually")
        previous_import_mode = paywall.resolve(subscription, current_time=current_time).import_mode if subscription else None
        subscription = self.account_provider.set_plan_for_user(
            user_uuid,
            plan_key=normalized_plan,
            current_time=current_time,
        )
        new_import_mode = paywall.resolve(subscription, current_time=current_time).import_mode
        rescan_result = None
        if previous_import_mode != new_import_mode and new_import_mode == "ai_new_words":
            rescan_result = self._queue_post_upgrade_rescan(
                telegram_user_id=int(user["telegram_user_id"]),
                user_uuid=str(user_uuid),
                current_time=current_time,
            )
        result = self.list_plans({**user, "user_id": user_uuid, "user_uuid": user_uuid})
        return {
            **result,
            "subscription": subscription,
            "post_upgrade_rescan": rescan_result,
            "checkout": {
                "mode": CHECKOUT_MODE_INSTANT,
                "provider": CHECKOUT_PROVIDER_BILLING,
                "redirect_url": None,
            },
        }

    def _paywall(self) -> PaywallService:
        try:
            plan_limits = read_plan_limit_settings(self.db)
        except PlanLimitSettingsValidationError as error:
            raise ClientWebPlanValidationError(str(error)) from error
        return PaywallService(plan_limits=plan_limits)

    def _billing_settings(self) -> dict[str, Any]:
        try:
            return read_billing_runtime_settings(self.db)
        except BillingRuntimeSettingsValidationError as error:
            raise ClientWebPlanValidationError(str(error)) from error

    def _client_billing_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        client_settings = {
            **settings,
            "enabled_period_months": list(settings["enabled_period_months"]),
        }
        provider_settings = getattr(self.db, "settings", None)
        if provider_settings is None:
            return client_settings
        try:
            provider_config = resolve_checkout_provider_config(
                settings,
                provider_settings,
                validate_credentials=False,
            )
        except (AttributeError, BillingRuntimeSettingsValidationError):
            return client_settings
        client_settings["enabled_period_months"] = supported_checkout_period_months(
            provider_config,
            client_settings["enabled_period_months"],
        )
        return client_settings

    def _queue_post_upgrade_rescan(
        self,
        *,
        telegram_user_id: int,
        user_uuid: str,
        current_time: Any,
    ) -> dict[str, Any] | None:
        if self.post_upgrade_rescan is None:
            return None
        return self.post_upgrade_rescan(
            telegram_user_id=telegram_user_id,
            user_uuid=user_uuid,
            current_time=current_time,
        )


def build_client_billing_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "billing_provider": settings["billing_provider"],
        "enabled_period_months": settings["enabled_period_months"],
        "plan_prices_uah": settings["plan_prices_uah"],
        "premium_plus_checkout_enabled": bool(settings["premium_plus_checkout_enabled"]),
        "double_time_for_project_support_enabled": bool(settings["double_time_for_project_support_enabled"]),
        "double_time_for_project_support_text": DOUBLE_TIME_FOR_PROJECT_SUPPORT_TEXT,
        "frontend_poll_interval_seconds": settings["frontend_poll_interval_seconds"],
        "frontend_poll_timeout_seconds": settings["frontend_poll_timeout_seconds"],
        "long_processing_seconds": settings["long_processing_seconds"],
    }


def build_customer_plan_keys(settings: dict[str, Any]) -> tuple[str, ...]:
    if settings.get("premium_plus_checkout_enabled", True):
        return CUSTOMER_PLAN_KEYS
    return tuple(plan_key for plan_key in CUSTOMER_PLAN_KEYS if plan_key != PLAN_PREMIUM_PLUS)


def build_client_subscription_payload(subscription: Any | None, *, current_time: datetime) -> dict[str, Any] | None:
    if subscription is None:
        return None
    end = _read_subscription_value(subscription, "end")
    remaining_seconds = remaining_subscription_seconds(end, current_time=current_time)
    return {
        "plan_key": _read_subscription_value(subscription, "plan_key"),
        "start": _read_subscription_value(subscription, "start"),
        "end": end,
        "status": _read_subscription_value(subscription, "status"),
        "remaining_seconds": remaining_seconds,
        "remaining_days": (remaining_seconds + 86_399) // 86_400 if remaining_seconds > 0 else 0,
    }


def enrich_plan_card_for_billing(
    plan: dict[str, Any],
    *,
    subscription: Any | None,
    billing_settings: dict[str, Any],
    current_time: datetime,
) -> dict[str, Any]:
    plan_key = str(plan["key"])
    availability = {
        "can_checkout": True,
        "reason": None,
    }
    if plan_key != PLAN_FREE and target_is_paid_downgrade(plan_key, subscription, current_time=current_time):
        availability = {
            "can_checkout": False,
            "reason": "downgrade_after_current_period",
        }
    order_previews = {}
    if plan_key != PLAN_FREE:
        order_previews = {
            str(period): build_checkout_quote(
                billing_settings,
                subscription,
                target_plan_key=plan_key,
                period_months=int(period),
                current_time=current_time,
            )
            for period in billing_settings["enabled_period_months"]
        }
    return {
        **plan,
        "availability": availability,
        "order_previews": order_previews,
    }


def target_is_paid_downgrade(target_plan_key: str, subscription: Any | None, *, current_time: datetime) -> bool:
    current_plan_key = str(_read_subscription_value(subscription, "plan_key") or PLAN_FREE)
    if CUSTOMER_PLAN_RANKS.get(current_plan_key, 0) <= CUSTOMER_PLAN_RANKS.get(target_plan_key, 0):
        return False
    return remaining_subscription_seconds(_read_subscription_value(subscription, "end"), current_time=current_time) > 0


def remaining_subscription_seconds(end: Any, *, current_time: datetime) -> int:
    if not isinstance(end, datetime):
        return 0
    current = current_time
    normalized_end = end
    if normalized_end.tzinfo is None and current.tzinfo is not None:
        normalized_end = normalized_end.replace(tzinfo=current.tzinfo)
    if current.tzinfo is None and normalized_end.tzinfo is not None:
        current = current.replace(tzinfo=normalized_end.tzinfo)
    return max(int((normalized_end - current).total_seconds()), 0)


def _read_subscription_value(subscription: Any | None, key: str) -> Any:
    if subscription is None:
        return None
    if isinstance(subscription, dict):
        return subscription.get(key)
    return getattr(subscription, key, None)
