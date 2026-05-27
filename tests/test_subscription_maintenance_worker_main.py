from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app import subscription_maintenance_worker_main


class FakeSubscriptionMaintenanceService:
    def __init__(self) -> None:
        self.calls = 0

    def process_due_subscription_maintenance(self) -> dict[str, object]:
        self.calls += 1
        return {"status": "ok"}


class FakeAppSettings:
    def __init__(self, value) -> None:
        self.value = value

    def get_value(self, key: str):
        if key == "billing.runtime_settings":
            return self.value
        return None


def test_run_subscription_maintenance_tick_delegates_to_runtime_service() -> None:
    service = FakeSubscriptionMaintenanceService()

    result = subscription_maintenance_worker_main.run_subscription_maintenance_tick(service)

    assert result == {"status": "ok"}
    assert service.calls == 1


def test_build_subscription_maintenance_runtime_uses_composed_runtime_service() -> None:
    runtime_service = FakeSubscriptionMaintenanceService()
    service = SimpleNamespace(subscription_maintenance_runtime_service=runtime_service)

    assert subscription_maintenance_worker_main.build_subscription_maintenance_runtime(service) is runtime_service


def test_subscription_maintenance_worker_uses_composed_runtime_and_closes_db(monkeypatch) -> None:
    calls: list[str] = []
    settings = SimpleNamespace(app_timezone="Europe/Kyiv")
    runtime_service = FakeSubscriptionMaintenanceService()
    built_db = None
    built_time_service = None

    class FakeDatabase:
        def __init__(self, settings) -> None:
            self.settings = settings

        def connect(self) -> None:
            calls.append("connect")

        def run_migrations(self) -> None:
            calls.append("migrate")

        def close(self) -> None:
            calls.append("close")

    class FakeTimeService:
        def __init__(self, timezone_name: str) -> None:
            self.timezone_name = timezone_name

        def now(self) -> datetime:
            return datetime(2026, 6, 1, 0, 0, tzinfo=UTC)

    def fake_build_learning_runtime(db, time_service):
        nonlocal built_db, built_time_service
        calls.append("compose")
        built_db = db
        built_time_service = time_service
        return SimpleNamespace(subscription_maintenance_runtime_service=runtime_service)

    def fake_run_subscription_maintenance_tick(service) -> dict[str, object]:
        assert service is runtime_service
        calls.append("process")
        raise SystemExit

    def fake_build_database(settings):
        return FakeDatabase(settings)

    monkeypatch.setattr(subscription_maintenance_worker_main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        subscription_maintenance_worker_main,
        "build_database",
        fake_build_database,
    )
    monkeypatch.setattr(subscription_maintenance_worker_main, "TimeService", FakeTimeService)
    monkeypatch.setattr(
        subscription_maintenance_worker_main,
        "build_learning_runtime",
        fake_build_learning_runtime,
    )
    monkeypatch.setattr(subscription_maintenance_worker_main, "resolve_run_hour", lambda db: 0)
    monkeypatch.setattr(
        subscription_maintenance_worker_main,
        "run_subscription_maintenance_tick",
        fake_run_subscription_maintenance_tick,
    )

    with pytest.raises(SystemExit):
        subscription_maintenance_worker_main.main()

    assert calls == ["compose", "connect", "migrate", "process", "close"]
    assert built_db is not None
    assert built_db.settings is settings
    assert built_time_service is not None
    assert built_time_service.timezone_name == "Europe/Kyiv"


def test_resolve_run_hour_reads_billing_runtime_setting() -> None:
    db = SimpleNamespace(app_settings=FakeAppSettings({"subscription_expiration_hour": 3}))

    assert subscription_maintenance_worker_main.resolve_run_hour(db) == 3


def test_resolve_sleep_until_next_daily_run_seconds_uses_configured_hour() -> None:
    current_time = datetime(2026, 6, 1, 22, 30, tzinfo=UTC)

    assert (
        subscription_maintenance_worker_main.resolve_sleep_until_next_daily_run_seconds(
            current_time,
            0,
        )
        == 5400
    )
    assert (
        subscription_maintenance_worker_main.resolve_sleep_until_next_daily_run_seconds(
            datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
            0,
        )
        == 0
    )
