from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.subscriptions.entitlements import SubscriptionEntitlementService
from app.subscriptions.plan_limits import CUSTOMER_PLAN_KEYS, DEFAULT_PLAN_LIMITS
from app.subscriptions.plans import (
    PLAN_FREE,
    PLAN_PREMIUM,
    PLAN_PREMIUM_PLUS,
    SubscriptionEntitlements,
    get_subscription_plan,
)

CAPABILITY_CORE_LEVEL = "core_level"
CAPABILITY_WORDS_PER_SESSION = "words_per_session"
CAPABILITY_REMINDERS_PER_DAY = "reminders_per_day"
CAPABILITY_SMART_IMPORT = "smart_import"
CAPABILITY_LISTENING_TRAINING = "listening_training"
CAPABILITY_READING_TRAINING = "reading_training"

CHECKOUT_PROVIDER_BILLING = "billing"
CHECKOUT_MODE_INSTANT = "instant"

CUSTOMER_PLAN_FEATURE_KEYS = {
    PLAN_FREE: [
        "unlimited_trainings",
        "core_levels_a1_a2",
        "cronolex_existing_import",
        "words_per_session_5_10_15",
        "one_reminder_per_day",
    ],
    PLAN_PREMIUM: [
        "unlimited_trainings",
        "all_core_levels",
        "collective_cronolex_import",
        "smart_missing_word_import",
        "all_words_per_session",
        "four_reminders_per_day",
    ],
    PLAN_PREMIUM_PLUS: [
        "unlimited_trainings",
        "all_core_levels",
        "collective_cronolex_import",
        "smart_missing_word_import",
        "all_words_per_session",
        "four_reminders_per_day",
        "planned_listening_training",
        "planned_reading_training",
    ],
}


class PaywallAccessError(PermissionError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PaywallService:
    def __init__(
        self,
        *,
        plan_limits: dict[str, dict[str, Any]] | None = None,
        checkout_mode: str = CHECKOUT_MODE_INSTANT,
        checkout_provider: str = CHECKOUT_PROVIDER_BILLING,
    ) -> None:
        self.plan_limits = plan_limits or DEFAULT_PLAN_LIMITS
        self.checkout_mode = checkout_mode
        self.checkout_provider = checkout_provider
        self.fallback_entitlements = SubscriptionEntitlementService()

    def resolve(self, subscription: Any | None, *, current_time: datetime) -> SubscriptionEntitlements:
        if self.fallback_entitlements.is_trial_active(subscription, current_time=current_time):
            return self.fallback_entitlements.resolve(subscription, current_time=current_time)
        plan_key = self.read_plan_key(subscription)
        limits = self.plan_limits.get(plan_key)
        if limits is None:
            return self.fallback_entitlements.resolve(subscription, current_time=current_time)
        return entitlements_from_limits(limits)

    def read_plan_key(self, subscription: Any | None) -> str:
        value = _read_subscription_value(subscription, "plan_key") or PLAN_FREE
        get_subscription_plan(str(value))
        return str(value)

    def can_use(self, entitlements: SubscriptionEntitlements, capability: str, value: Any = None) -> bool:
        if capability == CAPABILITY_CORE_LEVEL:
            return entitlements.level_titles is None or str(value) in set(entitlements.level_titles)
        if capability == CAPABILITY_WORDS_PER_SESSION:
            return entitlements.words_per_session_options is None or int(value) in set(entitlements.words_per_session_options)
        if capability == CAPABILITY_REMINDERS_PER_DAY:
            return int(value) <= int(entitlements.reminders_per_day)
        if capability == CAPABILITY_SMART_IMPORT:
            return entitlements.import_mode == "ai_new_words"
        if capability == CAPABILITY_LISTENING_TRAINING:
            return entitlements.listening_training
        if capability == CAPABILITY_READING_TRAINING:
            return entitlements.reading_training
        raise ValueError(f"Unknown paywall capability: {capability}")

    def require(self, entitlements: SubscriptionEntitlements, capability: str, value: Any = None, *, detail: str) -> None:
        if not self.can_use(entitlements, capability, value):
            raise PaywallAccessError(detail)

    def list_customer_plans(self, current_plan_key: str, *, plan_keys: tuple[str, ...] = CUSTOMER_PLAN_KEYS) -> list[dict[str, Any]]:
        return [
            self.plan_card(plan_key, is_current=plan_key == current_plan_key)
            for plan_key in plan_keys
        ]

    def plan_card(self, plan_key: str, *, is_current: bool) -> dict[str, Any]:
        plan = get_subscription_plan(plan_key)
        entitlements = entitlements_from_limits(self.plan_limits.get(plan_key, DEFAULT_PLAN_LIMITS[plan_key]))
        entitlements_payload = asdict(entitlements)
        for key in ("level_titles", "words_per_session_options"):
            if entitlements_payload[key] is not None:
                entitlements_payload[key] = list(entitlements_payload[key])
        return {
            "key": plan.key,
            "title": plan.title,
            "feature_keys": CUSTOMER_PLAN_FEATURE_KEYS[plan.key],
            "entitlements": entitlements_payload,
            "is_current": is_current,
            "checkout": {
                "mode": self.checkout_mode,
                "provider": self.checkout_provider,
                "redirect_url": None,
            },
        }


def entitlements_from_limits(limits: dict[str, Any]) -> SubscriptionEntitlements:
    level_titles = limits.get("level_titles")
    words_per_session_options = limits.get("words_per_session_options")
    return SubscriptionEntitlements(
        level_titles=tuple(level_titles) if level_titles is not None else None,
        words_per_session_options=tuple(int(item) for item in words_per_session_options) if words_per_session_options is not None else None,
        reminders_per_day=int(limits["reminders_per_day"]),
        import_mode=str(limits["import_mode"]),
        new_import_words_per_week=(
            int(limits["new_import_words_per_week"]) if limits.get("new_import_words_per_week") is not None else None
        ),
        homework_access=bool(limits.get("homework_access", False)),
        listening_training=bool(limits.get("listening_training", False)),
        reading_training=bool(limits.get("reading_training", False)),
    )


def _read_subscription_value(subscription: Any, key: str) -> Any:
    if subscription is None:
        return None
    if isinstance(subscription, dict):
        return subscription.get(key)
    return getattr(subscription, key, None)
