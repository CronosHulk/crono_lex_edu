from __future__ import annotations

from datetime import datetime
from typing import Any

from app.subscriptions.plans import (
    PLAN_FREE,
    TRIAL_ENTITLEMENTS,
    SubscriptionEntitlements,
    get_subscription_plan,
)


class SubscriptionEntitlementService:
    def resolve(self, subscription: Any | None, *, current_time: datetime) -> SubscriptionEntitlements:
        if subscription is not None and self.is_trial_active(subscription, current_time=current_time):
            return TRIAL_ENTITLEMENTS
        plan_key = str(_read_subscription_value(subscription, "plan_key") or PLAN_FREE)
        return get_subscription_plan(plan_key).entitlements

    def is_trial_active(self, subscription: Any | None, *, current_time: datetime) -> bool:
        if subscription is None:
            return False
        trial_start = _read_subscription_value(subscription, "trial_start")
        trial_end = _read_subscription_value(subscription, "trial_end")
        return trial_start is not None and trial_end is not None and trial_start <= current_time < trial_end


def _read_subscription_value(subscription: Any, key: str) -> Any:
    if isinstance(subscription, dict):
        return subscription.get(key)
    return getattr(subscription, key, None)
