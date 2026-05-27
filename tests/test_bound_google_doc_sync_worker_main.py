from __future__ import annotations

from types import SimpleNamespace

from app import bound_google_doc_sync_worker_main


class FakeBoundGoogleDocSyncService:
    def __init__(self) -> None:
        self.calls = 0

    def process_due_bound_google_doc_syncs(self) -> list[object]:
        self.calls += 1
        return []


def test_run_bound_google_doc_sync_delegates_to_runtime_service() -> None:
    service = FakeBoundGoogleDocSyncService()

    result = bound_google_doc_sync_worker_main.run_bound_google_doc_sync(service)

    assert result == {"status": "ok"}
    assert service.calls == 1


def test_build_bound_google_doc_sync_runtime_uses_composed_scheduled_runtime_service() -> None:
    runtime_service = FakeBoundGoogleDocSyncService()
    service = SimpleNamespace(user_import_scheduled_runtime_service=runtime_service)

    assert bound_google_doc_sync_worker_main.build_bound_google_doc_sync_runtime(service) is runtime_service


def test_bound_google_doc_sync_worker_processes_due_docs_and_closes_db(monkeypatch, capsys) -> None:
    calls: list[str] = []
    settings = SimpleNamespace(app_timezone="Europe/Kyiv")

    class FakeDatabase:
        def __init__(self, settings) -> None:
            self.settings = settings

        def connect(self) -> None:
            calls.append("connect")

        def run_migrations(self) -> None:
            calls.append("migrate")

        def close(self) -> None:
            calls.append("close")

    class CapturingBoundGoogleDocSyncService(FakeBoundGoogleDocSyncService):
        def process_due_bound_google_doc_syncs(self) -> list[object]:
            calls.append("process")
            return []

    def fake_build_learning_runtime(db, time_service):
        assert isinstance(db, FakeDatabase)
        assert db.settings is settings
        assert time_service.timezone_name == settings.app_timezone
        calls.append("compose")
        return SimpleNamespace(
            user_import_scheduled_runtime_service=CapturingBoundGoogleDocSyncService()
        )

    monkeypatch.setattr(bound_google_doc_sync_worker_main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        bound_google_doc_sync_worker_main,
        "build_database",
        lambda worker_settings: FakeDatabase(worker_settings),
    )
    monkeypatch.setattr(
        bound_google_doc_sync_worker_main,
        "build_learning_runtime",
        fake_build_learning_runtime,
    )

    bound_google_doc_sync_worker_main.main()

    assert calls == ["compose", "connect", "migrate", "process", "close"]
    assert capsys.readouterr().out.strip() == '{"status": "ok"}'
