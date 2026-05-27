from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import billing_reconciliation_worker_main


class FakeReconciliationService:
    def __init__(self) -> None:
        self.calls = 0

    def process_due_billing_reconciliation(self) -> dict[str, object]:
        self.calls += 1
        return {"checked_count": 2}


class FakeAppSettings:
    def __init__(self, value) -> None:
        self.value = value

    def get_value(self, key: str):
        if key == "billing.runtime_settings":
            return self.value
        return None


def test_run_reconciliation_tick_delegates_to_runtime_service() -> None:
    service = FakeReconciliationService()

    result = billing_reconciliation_worker_main.run_reconciliation_tick(service)

    assert result == {"checked_count": 2}
    assert service.calls == 1


def test_build_billing_reconciliation_runtime_uses_composed_runtime_service() -> None:
    runtime_service = FakeReconciliationService()
    service = SimpleNamespace(billing_reconciliation_runtime_service=runtime_service)

    assert billing_reconciliation_worker_main.build_billing_reconciliation_runtime(service) is runtime_service


def test_billing_reconciliation_worker_uses_composed_runtime_and_closes_db(monkeypatch) -> None:
    calls: list[str] = []
    settings = SimpleNamespace(app_timezone="Europe/Kyiv")
    runtime_service = FakeReconciliationService()
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

    def fake_build_learning_runtime(db, time_service):
        nonlocal built_db, built_time_service
        calls.append("compose")
        built_db = db
        built_time_service = time_service
        return SimpleNamespace(billing_reconciliation_runtime_service=runtime_service)

    def fake_run_reconciliation_tick(service) -> dict[str, object]:
        assert service is runtime_service
        calls.append("process")
        raise SystemExit

    monkeypatch.setattr(billing_reconciliation_worker_main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        billing_reconciliation_worker_main,
        "build_database",
        lambda settings: FakeDatabase(settings),
    )
    monkeypatch.setattr(billing_reconciliation_worker_main, "TimeService", FakeTimeService)
    monkeypatch.setattr(
        billing_reconciliation_worker_main,
        "build_learning_runtime",
        fake_build_learning_runtime,
    )
    monkeypatch.setattr(billing_reconciliation_worker_main, "resolve_tick_seconds", lambda db: 30)
    monkeypatch.setattr(billing_reconciliation_worker_main.time, "time", lambda: 0)
    monkeypatch.setattr(
        billing_reconciliation_worker_main,
        "run_reconciliation_tick",
        fake_run_reconciliation_tick,
    )

    with pytest.raises(SystemExit):
        billing_reconciliation_worker_main.main()

    assert calls == ["compose", "connect", "migrate", "process", "close"]
    assert built_db is not None
    assert built_db.settings is settings
    assert built_time_service is not None
    assert built_time_service.timezone_name == "Europe/Kyiv"


def test_resolve_tick_seconds_reads_billing_runtime_setting() -> None:
    db = SimpleNamespace(app_settings=FakeAppSettings({"reconciliation_interval_seconds": 90}))

    assert billing_reconciliation_worker_main.resolve_tick_seconds(db) == 90


def test_resolve_tick_seconds_uses_default_when_setting_is_missing() -> None:
    db = SimpleNamespace(app_settings=FakeAppSettings({}))

    assert billing_reconciliation_worker_main.resolve_tick_seconds(db) == 3600
