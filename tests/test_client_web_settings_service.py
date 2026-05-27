from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.application.client_web.settings_service import (
    ClientWebSettingsService,
    ClientWebSettingsValidationError,
)
from app.data_access.subscriptions import subscription_to_dict
from app.models import UserSubscription
from app.subscriptions.paywall import PaywallService


class FakeReference:
    def language_levels(self) -> list[dict[str, object]]:
        return [{"title": "A1"}, {"title": "A2"}, {"title": "B1"}]

    def get_level_by_title(self, title: str) -> dict[str, object] | None:
        return next((row for row in self.language_levels() if row["title"] == title), None)

    def words_per_session_options(self) -> tuple[int, ...]:
        return (5, 10, 15, 20)


class FakeProfiles:
    def __init__(self) -> None:
        self.profile = {
            "telegram_user_id": 42,
            "user_id": "11111111-1111-4111-8111-111111111111",
            "user_uuid": "11111111-1111-4111-8111-111111111111",
        }

    def get_profile(self, telegram_user_id: int) -> dict[str, object]:
        return self.profile

    def set_interface_locale(self, telegram_user_id: int, locale: str) -> None:
        self.profile["interface_locale"] = locale


class FakeLearningLevels:
    def __init__(self) -> None:
        self.saved_levels: list[tuple[int, str]] = []

    def save_language_level(self, telegram_user_id: int, level: str) -> None:
        self.saved_levels.append((telegram_user_id, level))


class FakeLearningSettings:
    def __init__(self) -> None:
        self.saved_counts: list[tuple[int, int]] = []
        self.saved_reminder_schedule: list[dict[str, object]] | None = None
        self.current_app_version = "0.2.2"

    def get_current_app_version(self) -> str | None:
        return self.current_app_version

    def set_words_per_session(self, telegram_user_id: int, count: int) -> None:
        self.saved_counts.append((telegram_user_id, count))

    def replace_reminder_schedule(self, telegram_user_id: int, schedule_rows: list[dict[str, object]]) -> None:
        self.saved_reminder_schedule = list(schedule_rows)

    def set_daily_reminder_hour(self, telegram_user_id: int, hour: int) -> None:
        pass

    def set_reminder_weekdays(self, telegram_user_id: int, weekdays: list[int]) -> None:
        pass


class FakeSubscriptions:
    def __init__(self, subscription: dict[str, object]) -> None:
        self.subscription = subscription

    def get_by_user_uuid(self, user_uuid: str) -> dict[str, object]:
        return self.subscription


class FakeSettings:
    app_bot_username = ""


class FakeSettingsWithoutBotUsername:
    pass


class FakeAppSettings:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def get_value(self, key: str) -> dict[str, object] | None:
        return self.rows.get(key)


class FakeDatabase:
    def __init__(self, subscription: dict[str, object]) -> None:
        self.user_profiles = FakeProfiles()
        self.learning_levels = FakeLearningLevels()
        self.user_learning_settings = FakeLearningSettings()
        self.subscriptions = FakeSubscriptions(subscription)
        self.settings = FakeSettings()
        self.app_settings = FakeAppSettings()
        self.task_logs = FakeTaskLogs()


class FakeTaskLogs:
    def __init__(self) -> None:
        self.has_active = False
        self.has_active_calls: list[dict[str, object]] = []

    def has_active_for_user(self, **kwargs: object) -> bool:
        self.has_active_calls.append(dict(kwargs))
        return self.has_active


class FakeEntitlementProvider:
    def __init__(self, subscription: dict[str, object], *, user_uuid: str | None | object = None) -> None:
        self.subscription = subscription
        self.user_uuid = user_uuid
        self.paywall = PaywallService()
        self.resolve_calls: list[dict[str, object]] = []

    def resolve_for_profile(self, profile: dict[str, object] | None, *, current_time: object) -> object:
        self.resolve_calls.append({"profile": profile, "current_time": current_time})
        return self.paywall.resolve(self.subscription, current_time=current_time)

    def user_uuid_from_profile(self, profile: dict[str, object] | None) -> str | None:
        if self.user_uuid is not None:
            return self.user_uuid if isinstance(self.user_uuid, str) else None
        if profile is None:
            return None
        raw_user_uuid = profile.get("user_id") or profile.get("user_uuid") or profile.get("id")
        return str(raw_user_uuid) if raw_user_uuid else None


def make_subscription(plan_key: str) -> dict[str, object]:
    return subscription_to_dict(
        UserSubscription(
            user_uuid=UUID("11111111-1111-4111-8111-111111111111"),
            plan_key=plan_key,
            start=datetime(2026, 5, 3, tzinfo=UTC),
            end=None,
            trial_start=None,
            trial_end=None,
            status="active",
        )
    )


def make_service(db: FakeDatabase, reference: FakeReference | None = None) -> ClientWebSettingsService:
    return ClientWebSettingsService(
        db,
        reference or FakeReference(),
        entitlement_provider=FakeEntitlementProvider(db.subscriptions.subscription),
    )


def test_client_web_settings_filters_free_level_and_word_options() -> None:
    service = make_service(FakeDatabase(make_subscription("free")))

    settings = service.get_settings({"telegram_user_id": 42})

    assert settings["levels"] == ["A1", "A2"]
    assert settings["words_per_session_options"] == [5, 10, 15]
    assert settings["subscription"] == {
        "import_mode": "lookup_only",
        "reminders_per_day": 1,
    }
    assert settings["app_version"] == "0.2.2"
    assert settings["support_settings"] == {
        "is_enabled": True,
        "support_url": "https://send.monobank.ua/jar/7E7wGkzHJr",
    }
    assert settings["google_doc_rescan_schedule"] == {
        "hour": 0,
        "weekdays": None,
        "interval_days": 3,
    }
    assert settings["google_doc_post_upgrade_rescan_pending"] is False


def test_client_web_settings_returns_configured_support_settings() -> None:
    db = FakeDatabase(make_subscription("free"))
    db.app_settings.rows["project.support_settings"] = {
        "is_enabled": False,
        "support_url": "https://send.monobank.ua/jar/custom",
    }
    service = make_service(db)

    settings = service.get_settings({"telegram_user_id": 42})

    assert settings["support_settings"] == {
        "is_enabled": False,
        "support_url": "https://send.monobank.ua/jar/custom",
    }


def test_client_web_settings_returns_admin_configured_google_doc_rescan_schedule() -> None:
    db = FakeDatabase(make_subscription("free"))
    db.app_settings.rows["user_import.runtime_settings"] = {
        "google_doc_sync_hour": 9,
        "google_doc_sync_weekdays": [0, 2, 4],
        "google_doc_sync_interval_days": 7,
    }
    service = make_service(db)

    settings = service.get_settings({"telegram_user_id": 42})

    assert settings["google_doc_rescan_schedule"] == {
        "hour": 9,
        "weekdays": [0, 2, 4],
        "interval_days": 7,
    }


def test_client_web_settings_returns_pending_post_upgrade_rescan_flag() -> None:
    db = FakeDatabase(make_subscription("premium"))
    db.task_logs.has_active = True
    service = make_service(db)

    settings = service.get_settings({"telegram_user_id": 42})

    assert settings["google_doc_post_upgrade_rescan_pending"] is True
    assert db.task_logs.has_active_calls[0]["task_type"] == "post_upgrade_google_doc_rescan"
    assert db.task_logs.has_active_calls[0]["user_uuid"] == "11111111-1111-4111-8111-111111111111"
    assert db.task_logs.has_active_calls[0]["statuses"] == {"queued", "processing"}


def test_client_web_settings_rejects_subscription_blocked_values() -> None:
    db = FakeDatabase(make_subscription("free"))
    service = make_service(db)

    with pytest.raises(ClientWebSettingsValidationError):
        service.update_settings(
            {"telegram_user_id": 42},
            interface_locale=None,
            language_level="B1",
            words_per_session=None,
            daily_reminder_hour=None,
            reminder_weekdays=None,
            reminder_schedule=None,
        )
    with pytest.raises(ClientWebSettingsValidationError):
        service.update_settings(
            {"telegram_user_id": 42},
            interface_locale=None,
            language_level=None,
            words_per_session=20,
            daily_reminder_hour=None,
            reminder_weekdays=None,
            reminder_schedule=None,
        )

    assert db.learning_levels.saved_levels == []
    assert db.user_learning_settings.saved_counts == []


def test_client_web_settings_rejects_reminder_schedule_over_subscription_cap() -> None:
    db = FakeDatabase(make_subscription("free"))
    service = make_service(db)

    with pytest.raises(ClientWebSettingsValidationError) as error:
        service.update_settings(
            {"telegram_user_id": 42},
            interface_locale=None,
            language_level=None,
            words_per_session=None,
            daily_reminder_hour=None,
            reminder_weekdays=None,
            reminder_schedule=[
                {"weekday": 0, "hour": 9, "status": "enabled"},
                {"weekday": 0, "hour": 12, "status": "enabled"},
            ],
        )

    assert "reminders_per_day" in str(error.value.detail)
    assert db.user_learning_settings.saved_reminder_schedule is None


def test_client_web_settings_allows_disabled_rows_over_enabled_reminder_cap() -> None:
    db = FakeDatabase(make_subscription("free"))
    service = make_service(db)
    schedule = [
        {"weekday": 0, "hour": 9, "status": "enabled"},
        {"weekday": 0, "hour": 12, "minute": 30, "status": "disabled"},
    ]

    service.update_settings(
        {"telegram_user_id": 42},
        interface_locale=None,
        language_level=None,
        words_per_session=None,
        daily_reminder_hour=None,
        reminder_weekdays=None,
        reminder_schedule=schedule,
    )

    assert db.user_learning_settings.saved_reminder_schedule == [
        {"weekday": 0, "hour": 9, "minute": 0, "status": "enabled"},
        {"weekday": 0, "hour": 12, "minute": 30, "status": "disabled"},
    ]


def test_client_web_settings_rejects_duplicate_reminder_schedule_rows_before_cap_check() -> None:
    db = FakeDatabase(make_subscription("free"))
    service = make_service(db)

    with pytest.raises(ClientWebSettingsValidationError) as error:
        service.update_settings(
            {"telegram_user_id": 42},
            interface_locale=None,
            language_level=None,
            words_per_session=None,
            daily_reminder_hour=None,
            reminder_weekdays=None,
            reminder_schedule=[
                {"weekday": 0, "hour": 9, "status": "enabled"},
                {"weekday": 0, "hour": 9, "status": "enabled"},
            ],
        )

    assert "duplicate reminder schedule row" in str(error.value.detail)
    assert db.user_learning_settings.saved_reminder_schedule is None


def test_client_web_settings_rejects_unsupported_reminder_minute() -> None:
    db = FakeDatabase(make_subscription("premium"))
    service = make_service(db)

    with pytest.raises(ClientWebSettingsValidationError) as error:
        service.update_settings(
            {"telegram_user_id": 42},
            interface_locale=None,
            language_level=None,
            words_per_session=None,
            daily_reminder_hour=None,
            reminder_weekdays=None,
            reminder_schedule=[
                {"weekday": 0, "hour": 20, "minute": 31, "status": "enabled"},
            ],
        )

    assert "minute must be 0 or 30" in str(error.value.detail)
    assert db.user_learning_settings.saved_reminder_schedule is None


def test_client_web_settings_saves_normalized_reminder_schedule() -> None:
    db = FakeDatabase(make_subscription("premium"))
    service = make_service(db)

    service.update_settings(
        {"telegram_user_id": 42},
        interface_locale=None,
        language_level=None,
        words_per_session=None,
        daily_reminder_hour=None,
        reminder_weekdays=None,
        reminder_schedule=[
            {"weekday": 2, "hour": 12, "minute": 30, "status": "enabled"},
            {"weekday": 0, "hour": 9, "status": "enabled"},
        ],
    )

    assert db.user_learning_settings.saved_reminder_schedule == [
        {"weekday": 0, "hour": 9, "minute": 0, "status": "enabled"},
        {"weekday": 2, "hour": 12, "minute": 30, "status": "enabled"},
    ]


def test_client_web_settings_teacher_update_handles_missing_app_bot_username() -> None:
    db = FakeDatabase(make_subscription("premium"))
    db.settings = FakeSettingsWithoutBotUsername()
    service = make_service(db)

    payload = service.update_settings(
        {
            "telegram_user_id": 42,
            "learning_role": "teacher",
        },
        interface_locale=None,
        language_level=None,
        words_per_session=None,
        daily_reminder_hour=None,
        reminder_weekdays=None,
        reminder_schedule=None,
    )

    assert payload["user"]["teacher_referral_url"] is None
