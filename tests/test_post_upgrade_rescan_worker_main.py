from __future__ import annotations

from types import SimpleNamespace

from app import post_upgrade_rescan_worker_main


class FakePostUpgradeRescanService:
    def __init__(self) -> None:
        self.calls = 0

    def process_due_post_upgrade_rescans(self) -> list[object]:
        self.calls += 1
        return []


def test_run_post_upgrade_rescan_delegates_to_runtime_service() -> None:
    service = FakePostUpgradeRescanService()

    result = post_upgrade_rescan_worker_main.run_post_upgrade_rescan(service)

    assert result == {"status": "ok"}
    assert service.calls == 1


def test_build_post_upgrade_rescan_runtime_uses_composed_scheduled_runtime_service() -> None:
    runtime = FakePostUpgradeRescanService()
    service = SimpleNamespace(user_import_scheduled_runtime_service=runtime)

    assert post_upgrade_rescan_worker_main.build_post_upgrade_rescan_runtime(service) is runtime


def test_post_upgrade_rescan_worker_processes_queue_and_closes_db(monkeypatch, capsys) -> None:
    calls: list[str] = []
    settings = SimpleNamespace(app_timezone="Europe/Kyiv")
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

    class CapturingPostUpgradeRescanService(FakePostUpgradeRescanService):
        def process_due_post_upgrade_rescans(self) -> list[object]:
            calls.append("process")
            return []

    def fake_build_learning_runtime(db, time_service):
        nonlocal built_db, built_time_service
        calls.append("compose")
        built_db = db
        built_time_service = time_service
        return SimpleNamespace(
            user_import_scheduled_runtime_service=CapturingPostUpgradeRescanService()
        )

    monkeypatch.setattr(post_upgrade_rescan_worker_main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        post_upgrade_rescan_worker_main,
        "build_database",
        lambda settings: FakeDatabase(settings),
    )
    monkeypatch.setattr(
        post_upgrade_rescan_worker_main,
        "build_learning_runtime",
        fake_build_learning_runtime,
    )

    post_upgrade_rescan_worker_main.main()

    assert calls == ["compose", "connect", "migrate", "process", "close"]
    assert built_db is not None
    assert built_db.settings is settings
    assert built_time_service is not None
    assert built_time_service.timezone_name == "Europe/Kyiv"
    assert capsys.readouterr().out.strip() == '{"status": "ok"}'
