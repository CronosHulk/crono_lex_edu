from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

import app.billing.services.checkout_provider_config as provider_config_module
from app.application.client_web.plan_service import (
    ClientWebPlanProfileNotFoundError,
    ClientWebPlanService,
    ClientWebPlanValidationError,
)
from app.billing.runtime_settings import BILLING_RUNTIME_SETTINGS_KEY
from app.data_access.subscriptions import subscription_to_dict
from app.models import UserSubscription
from app.subscriptions.plan_limits import PLAN_LIMITS_SETTINGS_KEY
from app.subscriptions.plans import PLAN_PERMANENT_PREMIUM


class FakeTimeService:
    def __init__(self, current_time: datetime | None = None) -> None:
        self.current_time = current_time or datetime(2026, 5, 4, 12, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current_time


class FakeProfiles:
    def get_profile(self, telegram_user_id: int) -> dict[str, object] | None:
        if telegram_user_id != 42:
            return None
        return {"telegram_user_id": 42, "user_uuid": "11111111-1111-4111-8111-111111111111"}


class FakeAppSettings:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def get_value(self, key: str) -> dict[str, object] | None:
        return self.rows.get(key)


class FakeSubscriptions:
    def __init__(self) -> None:
        self.rows = {
            "11111111-1111-4111-8111-111111111111": _subscription("free"),
        }
        self.set_calls: list[tuple[str, str]] = []

    def get_by_user_uuid(self, user_uuid: str) -> dict[str, object] | None:
        return self.rows.get(str(user_uuid))

    def set_plan_for_user(self, user_uuid: str, *, plan_key: str, current_time: datetime) -> dict[str, object]:
        self.set_calls.append((str(user_uuid), plan_key))
        payload = _subscription(plan_key, current_time=current_time)
        self.rows[str(user_uuid)] = payload
        return payload


class FakeBilling:
    def __init__(self) -> None:
        self.subscription_projection: dict[str, object] | None = None

    def get_subscription_projection_for_user(
        self,
        user_uuid: str,
        *,
        current_time: datetime,
    ) -> dict[str, object] | None:
        _ = user_uuid, current_time
        return self.subscription_projection


class FakeDatabase:
    def __init__(self) -> None:
        self.user_profiles = FakeProfiles()
        self.subscriptions = FakeSubscriptions()
        self.app_settings = FakeAppSettings()
        self.billing = FakeBilling()


class FakeAccountProvider:
    def __init__(self, db: FakeDatabase) -> None:
        self.db = db

    def user_uuid_for_user(self, user: dict[str, object]) -> str | None:
        user_uuid = user.get("user_uuid") or user.get("user_id")
        if not user_uuid:
            profile = self.db.user_profiles.get_profile(int(user["telegram_user_id"]))
            user_uuid = profile.get("user_uuid") if profile else None
        return str(user_uuid) if user_uuid else None

    def subscription_for_user_uuid(self, user_uuid: str) -> dict[str, object] | None:
        return self.db.subscriptions.get_by_user_uuid(user_uuid)

    def set_plan_for_user(self, user_uuid: str, *, plan_key: str, current_time: datetime) -> dict[str, object]:
        return self.db.subscriptions.set_plan_for_user(
            user_uuid,
            plan_key=plan_key,
            current_time=current_time,
        )

    def billing_subscription_projection(
        self,
        user_uuid: str | None,
        *,
        fallback_subscription: dict[str, object] | None,
        current_time: datetime,
    ) -> dict[str, object] | None:
        billing = getattr(self.db, "billing", None)
        if user_uuid is None or billing is None:
            return fallback_subscription
        projection = billing.get_subscription_projection_for_user(
            user_uuid,
            current_time=current_time,
        )
        if projection is None:
            return fallback_subscription
        return {
            "plan_key": projection.get("plan_key"),
            "start": projection.get("start"),
            "end": projection.get("end"),
            "status": "active",
        }


def _service(
    db: FakeDatabase | None = None,
    time_service: FakeTimeService | None = None,
    *,
    post_upgrade_rescan=None,
) -> ClientWebPlanService:
    db = db or FakeDatabase()
    return ClientWebPlanService(
        db,
        time_service or FakeTimeService(),
        account_provider=FakeAccountProvider(db),
        post_upgrade_rescan=post_upgrade_rescan,
    )


def _subscription(
    plan_key: str,
    *,
    current_time: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, object]:
    return subscription_to_dict(
        UserSubscription(
            user_uuid=UUID("11111111-1111-4111-8111-111111111111"),
            plan_key=plan_key,
            start=current_time or datetime(2026, 5, 3, tzinfo=UTC),
            end=end,
            trial_start=None,
            trial_end=None,
            status="active",
        )
    )


def test_client_web_plan_service_lists_current_plan_and_checkout_metadata() -> None:
    service = _service()

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["current_plan_key"] == "free"
    assert [plan["key"] for plan in payload["plans"]] == ["free", "premium", "premium_plus"]
    assert payload["plans"][0]["is_current"] is True
    assert payload["subscription"]["plan_key"] == "free"
    assert payload["subscription"]["remaining_days"] == 0
    assert payload["plans"][1]["checkout"] == {"mode": "instant", "provider": "billing", "redirect_url": None}
    assert payload["plans"][1]["availability"] == {"can_checkout": True, "reason": None}
    assert payload["plans"][1]["order_previews"]["1"]["amount_minor"] == 1000
    assert payload["billing"]["double_time_for_project_support_enabled"] is False
    assert payload["billing"]["premium_plus_checkout_enabled"] is True
    assert "monobank_mode" not in payload["billing"]


def test_client_web_plan_service_filters_enabled_periods_by_provider_supported_periods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_config_module,
        "MONOBANK_SUPPORTED_PERIOD_MONTHS",
        (1, 3),
    )
    db = FakeDatabase()
    db.settings = SimpleNamespace(monobank_token_test="", monobank_token="")
    db.app_settings.rows[BILLING_RUNTIME_SETTINGS_KEY] = {
        "enabled_period_months": [6, 1],
        "monobank_mode": "test",
    }
    service = _service(db)

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["billing"]["enabled_period_months"] == [1]
    premium = next(plan for plan in payload["plans"] if plan["key"] == "premium")
    assert set(premium["order_previews"]) == {"1"}


def test_client_web_plan_service_keeps_enabled_periods_without_provider_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_config_module,
        "MONOBANK_SUPPORTED_PERIOD_MONTHS",
        (1,),
    )
    db = FakeDatabase()
    db.app_settings.rows[BILLING_RUNTIME_SETTINGS_KEY] = {
        "enabled_period_months": [1, 6],
        "monobank_mode": "test",
    }
    service = _service(db)

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["billing"]["enabled_period_months"] == [1, 6]
    premium = next(plan for plan in payload["plans"] if plan["key"] == "premium")
    assert set(premium["order_previews"]) == {"1", "6"}


def test_client_web_plan_service_keeps_enabled_periods_when_monobank_disabled() -> None:
    db = FakeDatabase()
    db.settings = SimpleNamespace(monobank_token_test="", monobank_token="")
    db.app_settings.rows[BILLING_RUNTIME_SETTINGS_KEY] = {
        "enabled_period_months": [1, 6],
        "monobank_mode": "disabled",
    }
    service = _service(db)

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["billing"]["enabled_period_months"] == [1, 6]
    premium = next(plan for plan in payload["plans"] if plan["key"] == "premium")
    assert set(premium["order_previews"]) == {"1", "6"}


def test_client_web_plan_service_hides_premium_plus_when_checkout_disabled() -> None:
    db = FakeDatabase()
    db.app_settings.rows["billing.runtime_settings"] = {
        "premium_plus_checkout_enabled": False,
    }
    service = _service(db)

    payload = service.list_plans({"telegram_user_id": 42})

    assert [plan["key"] for plan in payload["plans"]] == ["free", "premium"]
    assert payload["billing"]["premium_plus_checkout_enabled"] is False


def test_client_web_plan_service_exposes_double_time_support_offer() -> None:
    db = FakeDatabase()
    db.app_settings.rows["billing.runtime_settings"] = {
        "double_time_for_project_support_enabled": True,
    }
    service = _service(db)

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["billing"]["double_time_for_project_support_enabled"] is True
    assert "подвоєний час підписки" in payload["billing"]["double_time_for_project_support_text"]
    premium = next(plan for plan in payload["plans"] if plan["key"] == "premium")
    assert premium["order_previews"]["1"]["period_months"] == 1
    assert premium["order_previews"]["1"]["granted_period_months"] == 2
    assert premium["order_previews"]["1"]["promotion"]["label"] == "Двойное время за поддержку проекта"


def test_client_web_plan_service_hides_permanent_premium_from_customer_plan_list() -> None:
    db = FakeDatabase()
    db.subscriptions.rows["11111111-1111-4111-8111-111111111111"] = _subscription(PLAN_PERMANENT_PREMIUM)
    service = _service(db)

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["current_plan_key"] == PLAN_PERMANENT_PREMIUM
    assert [plan["key"] for plan in payload["plans"]] == ["free", "premium", "premium_plus"]


def test_client_web_plan_service_rejects_paid_plan_without_checkout() -> None:
    db = FakeDatabase()
    service = _service(db)

    with pytest.raises(ClientWebPlanValidationError) as error:
        service.select_plan({"telegram_user_id": 42}, plan_key="premium_plus")

    assert "checkout" in str(error.value.detail)
    assert db.subscriptions.set_calls == []


def test_client_web_plan_service_keeps_free_plan_free_without_checkout() -> None:
    db = FakeDatabase()
    service = _service(db)

    payload = service.select_plan({"telegram_user_id": 42}, plan_key="free")

    assert db.subscriptions.set_calls == [("11111111-1111-4111-8111-111111111111", "free")]
    assert payload["current_plan_key"] == "free"
    assert payload["checkout"] == {
        "mode": "instant",
        "provider": "billing",
        "redirect_url": None,
    }


def test_client_web_plan_service_queues_post_upgrade_rescan_when_ai_import_becomes_available() -> None:
    db = FakeDatabase()
    rescan_calls: list[dict[str, object]] = []

    def post_upgrade_rescan(**kwargs: object) -> dict[str, object]:
        rescan_calls.append(dict(kwargs))
        return {"status": "queued", "task_log_id": 10}

    service = _service(db, post_upgrade_rescan=post_upgrade_rescan)

    with pytest.raises(ClientWebPlanValidationError):
        service.select_plan({"telegram_user_id": 42}, plan_key="premium")

    assert rescan_calls == []


def test_client_web_plan_service_rejects_manual_downgrade_from_paid() -> None:
    db = FakeDatabase()
    db.subscriptions.rows["11111111-1111-4111-8111-111111111111"] = _subscription("premium")
    service = _service(db)

    with pytest.raises(ClientWebPlanValidationError) as error:
        service.select_plan({"telegram_user_id": 42}, plan_key="free")

    assert "downgraded manually" in str(error.value.detail)


def test_client_web_plan_service_marks_paid_downgrade_unavailable_until_period_end() -> None:
    db = FakeDatabase()
    db.subscriptions.rows["11111111-1111-4111-8111-111111111111"] = _subscription(
        "premium_plus",
        end=datetime(2026, 5, 14, 12, tzinfo=UTC),
    )
    service = _service(db)

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["subscription"]["remaining_days"] == 10
    premium = next(plan for plan in payload["plans"] if plan["key"] == "premium")
    assert premium["availability"] == {
        "can_checkout": False,
        "reason": "downgrade_after_current_period",
    }
    premium_plus = next(plan for plan in payload["plans"] if plan["key"] == "premium_plus")
    assert premium_plus["availability"] == {"can_checkout": True, "reason": None}
    assert premium_plus["order_previews"]["1"]["kind"] == "renewal"


def test_client_web_plan_service_uses_billing_projection_for_paid_horizon() -> None:
    db = FakeDatabase()
    db.subscriptions.rows["11111111-1111-4111-8111-111111111111"] = _subscription(
        "premium_plus",
        current_time=datetime(2026, 5, 8, 18, 13, tzinfo=UTC),
        end=datetime(2026, 6, 8, 18, 13, tzinfo=UTC),
    )
    db.billing.subscription_projection = {
        "user_uuid": "11111111-1111-4111-8111-111111111111",
        "plan_key": "premium_plus",
        "start": datetime(2026, 5, 8, 18, 13, tzinfo=UTC),
        "end": datetime(2026, 12, 8, 18, 13, tzinfo=UTC),
        "purchase_ids": [1, 2],
    }
    service = _service(db, FakeTimeService(datetime(2026, 5, 11, 12, tzinfo=UTC)))

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["current_plan_key"] == "premium_plus"
    assert payload["subscription"]["end"] == datetime(2026, 12, 8, 18, 13, tzinfo=UTC)
    assert payload["subscription"]["remaining_days"] == 212
    premium_plus = next(plan for plan in payload["plans"] if plan["key"] == "premium_plus")
    assert premium_plus["order_previews"]["1"]["kind"] == "renewal"
    assert premium_plus["order_previews"]["1"]["period_start"] == "2026-12-08T18:13:00+00:00"


def test_client_web_plan_service_falls_back_to_subscription_without_billing_repository() -> None:
    db = FakeDatabase()
    delattr(db, "billing")
    db.subscriptions.rows["11111111-1111-4111-8111-111111111111"] = _subscription(
        "premium",
        current_time=datetime(2026, 5, 8, 18, 13, tzinfo=UTC),
        end=datetime(2026, 6, 8, 18, 13, tzinfo=UTC),
    )
    service = _service(db, FakeTimeService(datetime(2026, 5, 11, 12, tzinfo=UTC)))

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["current_plan_key"] == "premium"
    assert payload["subscription"]["plan_key"] == "premium"
    assert payload["subscription"]["end"] == datetime(2026, 6, 8, 18, 13, tzinfo=UTC)
    assert payload["subscription"]["remaining_days"] == 29


def test_client_web_plan_service_returns_prorated_upgrade_previews() -> None:
    db = FakeDatabase()
    db.subscriptions.rows["11111111-1111-4111-8111-111111111111"] = _subscription(
        "premium",
        current_time=datetime(2026, 5, 1, 12, tzinfo=UTC),
        end=datetime(2026, 5, 11, 12, tzinfo=UTC),
    )
    service = _service(db, FakeTimeService(datetime(2026, 5, 6, 12, tzinfo=UTC)))

    payload = service.list_plans({"telegram_user_id": 42})

    premium_plus = next(plan for plan in payload["plans"] if plan["key"] == "premium_plus")
    assert premium_plus["order_previews"]["1"]["kind"] == "upgrade"
    assert premium_plus["order_previews"]["1"]["amount_minor"] == 500
    assert premium_plus["order_previews"]["3"]["amount_minor"] == 4500


def test_client_web_plan_service_keeps_discounted_period_price_for_upgrade_preview() -> None:
    db = FakeDatabase()
    db.app_settings.rows["billing.runtime_settings"] = {
        "plan_prices_uah": {
            "premium_plus": {"12": 180},
        }
    }
    db.subscriptions.rows["11111111-1111-4111-8111-111111111111"] = _subscription(
        "premium",
        current_time=datetime(2026, 5, 1, 12, tzinfo=UTC),
        end=datetime(2026, 5, 11, 12, tzinfo=UTC),
    )
    service = _service(db, FakeTimeService(datetime(2026, 5, 6, 12, tzinfo=UTC)))

    payload = service.list_plans({"telegram_user_id": 42})

    premium_plus = next(plan for plan in payload["plans"] if plan["key"] == "premium_plus")
    assert premium_plus["order_previews"]["12"]["kind"] == "upgrade"
    assert premium_plus["order_previews"]["12"]["remainder_amount_minor"] == 500
    assert premium_plus["order_previews"]["12"]["extension_amount_minor"] == 16000
    assert premium_plus["order_previews"]["12"]["amount_minor"] == 16500


def test_client_web_plan_service_uses_admin_configured_plan_limits() -> None:
    db = FakeDatabase()
    db.app_settings.rows[PLAN_LIMITS_SETTINGS_KEY] = {
        "free": {
            "level_titles": ["A1"],
            "words_per_session_options": [10],
            "reminders_per_day": 1,
            "import_mode": "lookup_only",
            "new_import_words_per_week": 0,
            "listening_training": False,
            "reading_training": False,
        }
    }
    service = _service(db)

    payload = service.list_plans({"telegram_user_id": 42})

    assert payload["plans"][0]["entitlements"]["level_titles"] == ["A1"]
    assert payload["plans"][0]["entitlements"]["words_per_session_options"] == [10]


def test_client_web_plan_service_rejects_unknown_customer_plan() -> None:
    service = _service()

    with pytest.raises(ClientWebPlanValidationError) as error:
        service.select_plan({"telegram_user_id": 42}, plan_key="teacher_premium")

    assert "plan_key" in str(error.value.detail)


def test_client_web_plan_service_rejects_missing_profile_for_free_plan_select() -> None:
    service = _service()

    with pytest.raises(ClientWebPlanProfileNotFoundError) as error:
        service.select_plan({"telegram_user_id": 7}, plan_key="free")

    assert error.value.detail == "User profile not found"
