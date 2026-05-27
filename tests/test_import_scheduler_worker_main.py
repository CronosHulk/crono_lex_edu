from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import import_scheduler_worker_main


class FakeSchedulerService:
    def __init__(self) -> None:
        self.calls = 0

    def process_due_import_scheduler_tick(self) -> list[object]:
        self.calls += 1
        return [object(), object()]


class FakeAppSettings:
    def __init__(self, value) -> None:
        self.value = value

    def get_value(self, key: str):
        assert key == "user_import.runtime_settings"
        return self.value


def test_run_scheduler_tick_delegates_to_runtime_service() -> None:
    service = FakeSchedulerService()

    result = import_scheduler_worker_main.run_scheduler_tick(service)

    assert result == {"notification_count": 2}
    assert service.calls == 1


def test_build_import_scheduler_runtime_uses_composed_scheduled_runtime_service() -> None:
    runtime = FakeSchedulerService()
    service = SimpleNamespace(user_import_scheduled_runtime_service=runtime)

    assert import_scheduler_worker_main.build_import_scheduler_runtime(service) is runtime


def test_import_scheduler_worker_uses_composed_runtime_and_closes_db(monkeypatch) -> None:
    calls: list[str] = []
    settings = SimpleNamespace(app_timezone="Europe/Kyiv")
    runtime_service = FakeSchedulerService()
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
        return SimpleNamespace(user_import_scheduled_runtime_service=runtime_service)

    def fake_run_scheduler_tick(service) -> dict[str, int]:
        assert service is runtime_service
        calls.append("process")
        raise SystemExit

    monkeypatch.setattr(import_scheduler_worker_main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        import_scheduler_worker_main,
        "build_database",
        lambda settings: FakeDatabase(settings),
    )
    monkeypatch.setattr(import_scheduler_worker_main, "TimeService", FakeTimeService)
    monkeypatch.setattr(
        import_scheduler_worker_main,
        "build_learning_runtime",
        fake_build_learning_runtime,
    )
    monkeypatch.setattr(import_scheduler_worker_main, "resolve_tick_seconds", lambda db: 30)
    monkeypatch.setattr(import_scheduler_worker_main.time, "time", lambda: 0)
    monkeypatch.setattr(import_scheduler_worker_main, "run_scheduler_tick", fake_run_scheduler_tick)

    with pytest.raises(SystemExit):
        import_scheduler_worker_main.main()

    assert calls == ["compose", "connect", "migrate", "process", "close"]
    assert built_db is not None
    assert built_db.settings is settings
    assert built_time_service is not None
    assert built_time_service.timezone_name == "Europe/Kyiv"


def test_resolve_tick_seconds_reads_runtime_setting() -> None:
    db = SimpleNamespace(app_settings=FakeAppSettings({"scheduler_tick_minutes": 5}))

    assert import_scheduler_worker_main.resolve_tick_seconds(db) == 300


def test_resolve_sleep_until_next_tick_seconds_uses_wall_clock_grid() -> None:
    assert (
        import_scheduler_worker_main.resolve_sleep_until_next_tick_seconds(2 * 3600 + 7 * 60, 600)
        == 180
    )
    assert (
        import_scheduler_worker_main.resolve_sleep_until_next_tick_seconds(
            11 * 3600 + 17 * 60, 1800
        )
        == 780
    )
    assert (
        import_scheduler_worker_main.resolve_sleep_until_next_tick_seconds(11 * 3600 + 1, 3600)
        == 3599
    )


def test_resolve_sleep_until_next_tick_seconds_returns_zero_on_exact_boundary() -> None:
    assert (
        import_scheduler_worker_main.resolve_sleep_until_next_tick_seconds(
            11 * 3600 + 30 * 60, 1800
        )
        == 0
    )
    assert import_scheduler_worker_main.resolve_sleep_until_next_tick_seconds(12 * 3600, 3600) == 0
