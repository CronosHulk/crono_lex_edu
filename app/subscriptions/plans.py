from __future__ import annotations

from dataclasses import dataclass

PLAN_FREE = "free"
PLAN_PREMIUM = "premium"
PLAN_PREMIUM_PLUS = "premium_plus"
PLAN_PERMANENT_PREMIUM = "permanent_premium"
PLAN_TEACHER_FREE = "teacher_free"
PLAN_TEACHER_PREMIUM = "teacher_premium"

IMPORT_MODE_LOOKUP_ONLY = "lookup_only"
IMPORT_MODE_AI_NEW_WORDS = "ai_new_words"


@dataclass(frozen=True)
class SubscriptionEntitlements:
    level_titles: tuple[str, ...] | None
    words_per_session_options: tuple[int, ...] | None
    reminders_per_day: int
    import_mode: str
    new_import_words_per_week: int | None
    homework_access: bool
    listening_training: bool = False
    reading_training: bool = False


@dataclass(frozen=True)
class SubscriptionPlan:
    key: str
    title: str
    entitlements: SubscriptionEntitlements


FREE_ENTITLEMENTS = SubscriptionEntitlements(
    level_titles=("A1", "A2"),
    words_per_session_options=(5, 10, 15),
    reminders_per_day=1,
    import_mode=IMPORT_MODE_LOOKUP_ONLY,
    new_import_words_per_week=0,
    homework_access=False,
)
PREMIUM_ENTITLEMENTS = SubscriptionEntitlements(
    level_titles=None,
    words_per_session_options=None,
    reminders_per_day=4,
    import_mode=IMPORT_MODE_AI_NEW_WORDS,
    new_import_words_per_week=None,
    homework_access=False,
)
PREMIUM_PLUS_ENTITLEMENTS = SubscriptionEntitlements(
    level_titles=None,
    words_per_session_options=None,
    reminders_per_day=4,
    import_mode=IMPORT_MODE_AI_NEW_WORDS,
    new_import_words_per_week=None,
    homework_access=False,
    listening_training=True,
    reading_training=True,
)
TRIAL_ENTITLEMENTS = SubscriptionEntitlements(
    level_titles=None,
    words_per_session_options=None,
    reminders_per_day=1,
    import_mode=IMPORT_MODE_LOOKUP_ONLY,
    new_import_words_per_week=0,
    homework_access=False,
)
TEACHER_ENTITLEMENTS = SubscriptionEntitlements(
    level_titles=None,
    words_per_session_options=None,
    reminders_per_day=4,
    import_mode=IMPORT_MODE_AI_NEW_WORDS,
    new_import_words_per_week=None,
    homework_access=True,
)

_PLANS = {
    PLAN_FREE: SubscriptionPlan(PLAN_FREE, "Free", FREE_ENTITLEMENTS),
    PLAN_PREMIUM: SubscriptionPlan(PLAN_PREMIUM, "Premium", PREMIUM_ENTITLEMENTS),
    PLAN_PREMIUM_PLUS: SubscriptionPlan(PLAN_PREMIUM_PLUS, "Premium +", PREMIUM_PLUS_ENTITLEMENTS),
    PLAN_PERMANENT_PREMIUM: SubscriptionPlan(PLAN_PERMANENT_PREMIUM, "Permanent premium", TEACHER_ENTITLEMENTS),
    PLAN_TEACHER_FREE: SubscriptionPlan(PLAN_TEACHER_FREE, "Teacher free", TEACHER_ENTITLEMENTS),
    PLAN_TEACHER_PREMIUM: SubscriptionPlan(PLAN_TEACHER_PREMIUM, "Teacher premium", TEACHER_ENTITLEMENTS),
}


def get_subscription_plan(plan_key: str) -> SubscriptionPlan:
    try:
        return _PLANS[plan_key]
    except KeyError as error:
        raise ValueError(f"Unknown subscription plan: {plan_key}") from error


def list_subscription_plans() -> list[SubscriptionPlan]:
    return list(_PLANS.values())
