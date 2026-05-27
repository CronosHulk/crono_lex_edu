from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app import embedding_worker_main


class FakeTaskLogs:
    def __init__(self) -> None:
        self.created: list[dict] = []
        self.updated: list[tuple[int, dict]] = []
        self.stale_mark_count = 0
        self.stale_kwargs: dict | None = None

    def create(self, **kwargs):
        self.created.append(kwargs)
        return {"id": 10, **kwargs}

    def update(self, task_log_id: int, **kwargs):
        self.updated.append((task_log_id, kwargs))
        return {"id": task_log_id, **kwargs}

    def mark_stale_processing_fatal(self, **kwargs):
        self.stale_kwargs = kwargs
        return self.stale_mark_count


class FakeDb:
    def __init__(self) -> None:
        self.task_logs = FakeTaskLogs()


class FakeTimeService:
    def __init__(self, timezone: str = "UTC") -> None:
        self.timezone = timezone

    def now(self) -> datetime:
        return datetime(2026, 5, 6, 12, 0, 0)


class FakeEmbeddingService:
    def __init__(self, *, should_fail: bool = False, embedding_failed_count: int = 0) -> None:
        self.should_fail = should_fail
        self.embedding_failed_count = embedding_failed_count

    def process_due_user_import_embeddings_now(self) -> dict[str, int]:
        if self.should_fail:
            raise RuntimeError("CUDA out of memory")
        return {
            "ready_for_rotation_count": 2,
            "retry_scheduled_count": 0,
            "embedding_failed_count": self.embedding_failed_count,
        }


def test_build_user_import_embedding_runtime_uses_composed_runtime_service() -> None:
    runtime_service = FakeEmbeddingService()
    service = SimpleNamespace(user_import_runtime_service=runtime_service)

    assert embedding_worker_main.build_user_import_embedding_runtime(service) is runtime_service


def test_run_embedding_tick_records_success_task_log() -> None:
    db = FakeDb()

    result = embedding_worker_main.run_embedding_tick(db, FakeEmbeddingService(), FakeTimeService())

    assert result["ready_for_rotation_count"] == 2
    assert db.task_logs.created[0]["task_type"] == embedding_worker_main.USER_IMPORT_EMBEDDING_TASK_TYPE
    assert db.task_logs.stale_kwargs["task_type"] == embedding_worker_main.USER_IMPORT_EMBEDDING_TASK_TYPE
    assert db.task_logs.updated[0][1]["status"] == "success"
    assert db.task_logs.updated[0][1]["result_json"] == result


def test_run_embedding_tick_marks_stale_processing_task_logs() -> None:
    db = FakeDb()
    db.task_logs.stale_mark_count = 1

    embedding_worker_main.run_embedding_tick(db, FakeEmbeddingService(), FakeTimeService())

    assert db.task_logs.stale_kwargs["result_json"]["error_type"] == "StaleProcessingTask"
    assert "likely crashed" in db.task_logs.stale_kwargs["description"]


def test_run_embedding_tick_records_error_task_log_when_rows_fail() -> None:
    db = FakeDb()

    result = embedding_worker_main.run_embedding_tick(
        db, FakeEmbeddingService(embedding_failed_count=2), FakeTimeService()
    )

    assert result["embedding_failed_count"] == 2
    assert db.task_logs.updated[0][1]["status"] == "error"
    assert "2 user dictionary row" in db.task_logs.updated[0][1]["error_text"]
    assert db.task_logs.updated[0][1]["result_json"] == result


def test_run_embedding_tick_records_fatal_task_log_on_crash() -> None:
    db = FakeDb()

    with pytest.raises(RuntimeError):
        embedding_worker_main.run_embedding_tick(db, FakeEmbeddingService(should_fail=True), FakeTimeService())

    assert db.task_logs.updated[0][1]["status"] == "fatal"
    assert "CUDA out of memory" in db.task_logs.updated[0][1]["error_text"]
    assert db.task_logs.updated[0][1]["result_json"] == {"error_type": "RuntimeError"}


def test_run_embedding_worker_once_uses_composed_runtime_and_closes_db(monkeypatch) -> None:
    calls: list[str] = []
    settings = SimpleNamespace(app_timezone="Europe/Kyiv")
    captured: dict[str, object] = {}

    class FakeDatabase(FakeDb):
        def __init__(self, settings) -> None:
            super().__init__()
            self.settings = settings

        def connect(self) -> None:
            calls.append("connect")

        def run_migrations(self) -> None:
            calls.append("migrate")

        def close(self) -> None:
            calls.append("close")

    class CapturingEmbeddingService(FakeEmbeddingService):
        def process_due_user_import_embeddings_now(self) -> dict[str, int]:
            calls.append("process")
            return super().process_due_user_import_embeddings_now()

    def fake_build_learning_runtime(db, time_service):
        calls.append("factory")
        captured["db"] = db
        captured["time_service"] = time_service
        return SimpleNamespace(user_import_runtime_service=CapturingEmbeddingService())

    monkeypatch.setattr(
        embedding_worker_main,
        "build_database",
        lambda settings: FakeDatabase(settings),
    )
    monkeypatch.setattr(embedding_worker_main, "TimeService", FakeTimeService)
    monkeypatch.setattr(embedding_worker_main, "build_learning_runtime", fake_build_learning_runtime)

    result = embedding_worker_main.run_embedding_worker_once(settings)

    assert calls == ["factory", "connect", "migrate", "process", "close"]
    assert isinstance(captured["db"], FakeDatabase)
    assert captured["db"].settings is settings
    assert isinstance(captured["time_service"], FakeTimeService)
    assert captured["time_service"].timezone == "Europe/Kyiv"
    assert result["ready_for_rotation_count"] == 2


def test_run_embedding_worker_loop_uses_composed_runtime_and_cleans_up(monkeypatch) -> None:
    calls: list[str] = []
    settings = SimpleNamespace(app_timezone="Europe/Kyiv", app_user_import_embedding_build_hour=3)
    captured: dict[str, object] = {}

    class FakeDatabase(FakeDb):
        def __init__(self, settings) -> None:
            super().__init__()
            self.settings = settings

        def connect(self) -> None:
            calls.append("connect")

        def run_migrations(self) -> None:
            calls.append("migrate")

        def close(self) -> None:
            calls.append("close")

    class ExitingEmbeddingService(FakeEmbeddingService):
        def process_due_user_import_embeddings_now(self) -> dict[str, int]:
            calls.append("process")
            raise SystemExit

    def fake_build_learning_runtime(db, time_service):
        calls.append("factory")
        captured["db"] = db
        captured["time_service"] = time_service
        return SimpleNamespace(user_import_runtime_service=ExitingEmbeddingService())

    def fake_resolve_sleep_until_next_daily_run_seconds(current_time, run_hour):
        captured["sleep_current_time"] = current_time
        captured["sleep_run_hour"] = run_hour
        return 0

    monkeypatch.setattr(
        embedding_worker_main,
        "build_database",
        lambda settings: FakeDatabase(settings),
    )
    monkeypatch.setattr(embedding_worker_main, "TimeService", FakeTimeService)
    monkeypatch.setattr(embedding_worker_main, "build_learning_runtime", fake_build_learning_runtime)
    monkeypatch.setattr(
        embedding_worker_main,
        "resolve_sleep_until_next_daily_run_seconds",
        fake_resolve_sleep_until_next_daily_run_seconds,
    )
    monkeypatch.setattr(embedding_worker_main, "clear_encoder_cache", lambda: calls.append("clear-cache"))
    monkeypatch.setattr(embedding_worker_main.gc, "collect", lambda: calls.append("gc"))

    with pytest.raises(SystemExit):
        embedding_worker_main.run_embedding_worker_loop(settings)

    assert calls == ["factory", "connect", "migrate", "process", "clear-cache", "gc", "close"]
    assert isinstance(captured["db"], FakeDatabase)
    assert captured["db"].settings is settings
    assert isinstance(captured["time_service"], FakeTimeService)
    assert captured["time_service"].timezone == "Europe/Kyiv"
    assert captured["sleep_current_time"] == datetime(2026, 5, 6, 12, 0, 0)
    assert captured["sleep_run_hour"] == 3


def test_resolve_sleep_until_next_daily_run_seconds_uses_configured_hour() -> None:
    assert (
        embedding_worker_main.resolve_sleep_until_next_daily_run_seconds(
            datetime(2026, 5, 7, 2, 30, tzinfo=UTC),
            3,
        )
        == 1800
    )
    assert (
        embedding_worker_main.resolve_sleep_until_next_daily_run_seconds(
            datetime(2026, 5, 7, 3, 0, tzinfo=UTC),
            3,
        )
        == 0
    )
    assert (
        embedding_worker_main.resolve_sleep_until_next_daily_run_seconds(
            datetime(2026, 5, 7, 4, 0, tzinfo=UTC),
            3,
        )
        == 82800
    )
