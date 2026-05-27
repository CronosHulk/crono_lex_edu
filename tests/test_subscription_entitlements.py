from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.subscriptions.entitlements import SubscriptionEntitlementService
from app.subscriptions.paywall import (
    CAPABILITY_CORE_LEVEL,
    CAPABILITY_LISTENING_TRAINING,
    CAPABILITY_SMART_IMPORT,
    CAPABILITY_WORDS_PER_SESSION,
    CHECKOUT_PROVIDER_BILLING,
    PaywallAccessError,
    PaywallService,
)
from app.subscriptions.plan_limits import DEFAULT_PLAN_LIMITS, normalize_plan_limit_settings
from app.subscriptions.plans import PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS
from app.subscriptions.user_entitlements import UserEntitlementResolver, read_user_uuid


def test_free_plan_caps_levels_reminders_words_and_import_mode() -> None:
    service = SubscriptionEntitlementService()
    subscription = SimpleNamespace(plan_key=PLAN_FREE, trial_start=None, trial_end=None)

    entitlements = service.resolve(subscription, current_time=datetime(2026, 5, 3, tzinfo=UTC))

    assert entitlements.level_titles == ("A1", "A2")
    assert entitlements.words_per_session_options == (5, 10, 15)
    assert entitlements.reminders_per_day == 1
    assert entitlements.import_mode == "lookup_only"
    assert entitlements.new_import_words_per_week == 0


def test_active_trial_keeps_free_reminder_limit_without_ai_import() -> None:
    service = SubscriptionEntitlementService()
    current_time = datetime(2026, 5, 3, tzinfo=UTC)
    subscription = SimpleNamespace(
        plan_key=PLAN_FREE,
        trial_start=current_time - timedelta(days=1),
        trial_end=current_time + timedelta(days=6),
    )

    entitlements = service.resolve(subscription, current_time=current_time)

    assert entitlements.level_titles is None
    assert entitlements.words_per_session_options is None
    assert entitlements.reminders_per_day == 1
    assert entitlements.import_mode == "lookup_only"
    assert entitlements.new_import_words_per_week == 0


def test_entitlement_service_accepts_repository_dict_rows() -> None:
    service = SubscriptionEntitlementService()
    current_time = datetime(2026, 5, 3, tzinfo=UTC)
    subscription = {
        "plan_key": PLAN_FREE,
        "trial_start": current_time - timedelta(days=1),
        "trial_end": current_time + timedelta(days=6),
    }

    entitlements = service.resolve(subscription, current_time=current_time)

    assert entitlements.import_mode == "lookup_only"
    assert service.is_trial_active(subscription, current_time=current_time) is True


def test_premium_plan_does_not_cap_new_import_words() -> None:
    service = SubscriptionEntitlementService()
    subscription = SimpleNamespace(plan_key=PLAN_PREMIUM, trial_start=None, trial_end=None)

    entitlements = service.resolve(subscription, current_time=datetime(2026, 5, 3, tzinfo=UTC))

    assert entitlements.new_import_words_per_week is None


def test_premium_plus_enables_planned_training_caps() -> None:
    service = PaywallService()
    subscription = SimpleNamespace(plan_key=PLAN_PREMIUM_PLUS, trial_start=None, trial_end=None)

    entitlements = service.resolve(subscription, current_time=datetime(2026, 5, 3, tzinfo=UTC))

    assert service.can_use(entitlements, CAPABILITY_CORE_LEVEL, "C2") is True
    assert service.can_use(entitlements, CAPABILITY_WORDS_PER_SESSION, 30) is True
    assert service.can_use(entitlements, CAPABILITY_SMART_IMPORT) is True
    assert service.can_use(entitlements, CAPABILITY_LISTENING_TRAINING) is True
    assert entitlements.reading_training is True
    assert entitlements.new_import_words_per_week is None


def test_paywall_builds_customer_plan_cards_for_instant_billing_checkout() -> None:
    service = PaywallService()

    cards = service.list_customer_plans(PLAN_PREMIUM)

    assert [card["key"] for card in cards] == [PLAN_FREE, PLAN_PREMIUM, PLAN_PREMIUM_PLUS]
    assert "words_per_session_5_10_15" in cards[0]["feature_keys"]
    assert cards[1]["is_current"] is True
    assert cards[1]["checkout"]["mode"] == "instant"
    assert cards[1]["checkout"]["provider"] == CHECKOUT_PROVIDER_BILLING
    assert cards[2]["feature_keys"][-2:] == ["planned_listening_training", "planned_reading_training"]


def test_paywall_builds_customer_plan_cards_for_selected_plan_keys() -> None:
    service = PaywallService()

    cards = service.list_customer_plans(PLAN_PREMIUM, plan_keys=(PLAN_FREE, PLAN_PREMIUM))

    assert [card["key"] for card in cards] == [PLAN_FREE, PLAN_PREMIUM]
    assert cards[1]["is_current"] is True


def test_paywall_uses_normalized_db_backed_plan_limits() -> None:
    limits = normalize_plan_limit_settings(
        {
            PLAN_PREMIUM: {
                **DEFAULT_PLAN_LIMITS[PLAN_PREMIUM],
                "words_per_session_options": [10, 20],
                "listening_training": True,
            }
        },
        partial=True,
    )
    service = PaywallService(plan_limits=limits)
    subscription = SimpleNamespace(plan_key=PLAN_PREMIUM, trial_start=None, trial_end=None)

    entitlements = service.resolve(subscription, current_time=datetime(2026, 5, 3, tzinfo=UTC))

    assert service.can_use(entitlements, CAPABILITY_WORDS_PER_SESSION, 20) is True
    assert service.can_use(entitlements, CAPABILITY_WORDS_PER_SESSION, 30) is False
    assert service.can_use(entitlements, CAPABILITY_LISTENING_TRAINING) is True


def test_paywall_require_raises_non_http_access_error() -> None:
    service = PaywallService()
    subscription = SimpleNamespace(plan_key=PLAN_FREE, trial_start=None, trial_end=None)
    entitlements = service.resolve(subscription, current_time=datetime(2026, 5, 3, tzinfo=UTC))

    try:
        service.require(entitlements, CAPABILITY_WORDS_PER_SESSION, 30, detail="Upgrade required")
    except PaywallAccessError as error:
        assert error.detail == "Upgrade required"
        assert str(error) == "Upgrade required"
    else:  # pragma: no cover
        raise AssertionError("PaywallAccessError was expected")


class FakeSubscriptionRepository:
    def __init__(self) -> None:
        self.rows = {
            "user-1": {
                "plan_key": PLAN_PREMIUM,
                "trial_start": None,
                "trial_end": None,
            }
        }

    def get_by_user_uuid(self, user_uuid: str) -> dict[str, object] | None:
        return self.rows.get(str(user_uuid))


class FakeUserProfiles:
    def get_profile(self, telegram_user_id: int) -> dict[str, object] | None:
        if telegram_user_id != 42:
            return None
        return {"user_id": "user-1", "telegram_user_id": telegram_user_id}


class FakeEntitlementDb:
    subscriptions = FakeSubscriptionRepository()
    user_profiles = FakeUserProfiles()


def test_user_entitlement_resolver_reads_subscription_by_user_uuid() -> None:
    resolver = UserEntitlementResolver(FakeEntitlementDb())

    entitlements = resolver.resolve_for_user_uuid("user-1", current_time=datetime(2026, 5, 3, tzinfo=UTC))

    assert entitlements.import_mode == "ai_new_words"


def test_user_entitlement_resolver_reads_user_uuid_from_telegram_profile() -> None:
    resolver = UserEntitlementResolver(FakeEntitlementDb())

    entitlements = resolver.resolve_for_telegram_user(42, current_time=datetime(2026, 5, 3, tzinfo=UTC))

    assert entitlements.import_mode == "ai_new_words"


def test_user_entitlement_resolver_returns_optional_telegram_entitlements() -> None:
    resolver = UserEntitlementResolver(FakeEntitlementDb())

    entitlements = resolver.resolve_optional_for_telegram_user(
        42,
        current_time=datetime(2026, 5, 3, tzinfo=UTC),
    )

    assert entitlements is not None
    assert entitlements.import_mode == "ai_new_words"
    assert (
        resolver.resolve_optional_for_telegram_user(
            41,
            current_time=datetime(2026, 5, 3, tzinfo=UTC),
        )
        is None
    )


def test_user_entitlement_resolver_reads_telegram_reminders_per_day_with_free_fallback() -> None:
    resolver = UserEntitlementResolver(FakeEntitlementDb())

    assert (
        resolver.reminders_per_day_for_telegram_user(
            42,
            current_time=datetime(2026, 5, 3, tzinfo=UTC),
        )
        == 4
    )
    assert (
        resolver.reminders_per_day_for_telegram_user(
            41,
            current_time=datetime(2026, 5, 3, tzinfo=UTC),
        )
        == 1
    )


def test_read_user_uuid_accepts_common_profile_keys() -> None:
    assert read_user_uuid({"user_id": "user-1"}) == "user-1"
    assert read_user_uuid({"user_uuid": "user-2"}) == "user-2"
    assert read_user_uuid({"id": "user-3"}) == "user-3"
