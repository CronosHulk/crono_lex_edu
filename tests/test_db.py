from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from app.config import Settings
from app.data_access.bot_message_logs import BotMessageLogRepository
from app.data_access.error_logs import ErrorLogRepository
from app.data_access.task_logs import TaskLogRepository
from app.data_access.training_schedules import TrainingScheduleRepository
from app.data_access.user_profiles import UserProfileRepository
from app.models import (
    BotMessageLog,
    ErrorLog,
    TaskLog,
    User,
)
from app.orm import SessionManager


class Database(SessionManager):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._session_manager = self
        self.error_logs = ErrorLogRepository(self)
        self.task_logs = TaskLogRepository(self)
        self.bot_message_logs = BotMessageLogRepository(self)
        self.user_profiles = UserProfileRepository(self)
        self.training_schedules = TrainingScheduleRepository(self)

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def engine(self):
        if self._session_manager is self:
            return super().engine
        return self._session_manager.engine

    @contextmanager
    def session(self):
        if self._session_manager is self:
            with super().session() as s:
                yield s
        else:
            with self._session_manager.session() as s:
                yield s



USER_UUID = UUID("00000000-0000-0000-0000-000000000001")


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    def dispose(self) -> None:
        self.disposed = True


class FakeMigrationScalarsResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalars(self):
        return self


class FakeMigrationConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict | None]] = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params))
        if "SELECT version FROM schema_migrations" in sql:
            return FakeMigrationScalarsResult([])
        return FakeMigrationScalarsResult([])


class FakeMigrationBeginContext:
    def __init__(self, connection: FakeMigrationConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeMigrationConnection:
        return self.connection

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FakeMigrationEngine:
    def __init__(self, connection: FakeMigrationConnection) -> None:
        self.connection = connection

    def begin(self) -> FakeMigrationBeginContext:
        return FakeMigrationBeginContext(self.connection)


class FakeMigrationSessionManager:
    def __init__(self, engine: FakeMigrationEngine) -> None:
        self.engine = engine


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_id=None, scalars_rows=None, execute_rows=None, scalar_values=None) -> None:
        self.row_by_id = row_by_id or {}
        self.scalars_rows = list(scalars_rows or [])
        self.execute_rows = list(execute_rows or [])
        self.scalar_values = list(scalar_values or [])
        self.added = []

    def get(self, model, primary_key):
        return self.row_by_id.get(primary_key)

    def execute(self, statement):
        return FakeScalarsResult(self.execute_rows.pop(0) if self.execute_rows else [])

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        return FakeScalarsResult(self.scalars_rows)

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        return None


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def build_settings() -> Settings:
    return Settings(
        bot_token="token",
        db_host="localhost",
        db_port=5432,
        db_name="cronolex",
        db_user="user",
        db_password="password",
        app_env="test",
        app_timezone="Europe/Kyiv",
        app_host="127.0.0.1",
        app_port=8000,
        app_api_base_url="http://127.0.0.1:8000",
        app_bot_enabled=False,
        app_bot_reminder_poll_minutes=5,
        app_bot_message_cleanup_poll_minutes=60,
        app_bot_message_retention_days=30,
        app_db_pool_min_size=4,
        app_db_pool_max_size=20,
        app_api_workers=2,
        app_word_cooldown_days=2,
        app_review_mix_percent=30,
    )


def test_connect_initializes_session_manager(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("app.orm.create_engine", lambda *args, **kwargs: calls.append("engine") or FakeEngine())

    database = Database(build_settings())
    database.connect()

    assert calls == ["engine"]
    assert database.session_manager.engine is not None


def test_close_disposes_engine(monkeypatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("app.orm.create_engine", lambda *args, **kwargs: engine)

    database = Database(build_settings())
    database.connect()
    database.close()

    assert engine.disposed is True


def test_run_migrations_delegates_to_schema_migration_runner(monkeypatch) -> None:
    connection = FakeMigrationConnection()
    engine = FakeMigrationEngine(connection)
    calls = []

    def fake_run_schema_migrations(received_engine, *, app_timezone: str):
        calls.append((received_engine, app_timezone))

    database = Database(build_settings())
    database._session_manager = FakeMigrationSessionManager(engine)
    monkeypatch.setattr("app.data_access.schema_migrations.run_schema_migrations", fake_run_schema_migrations)

    database.run_migrations()

    assert calls == [(engine, "Europe/Kyiv")]


def test_error_logs_create_rejects_unknown_level() -> None:
    database = Database(build_settings())

    try:
        database.error_logs.create("info", "text")
    except ValueError as error:
        assert "Unsupported error level" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_error_logs_create_persists_context_json() -> None:
    database = Database(build_settings())
    session = FakeSession(row_by_id={1: User(uuid=USER_UUID, telegram_user_id=1)})
    database._session_manager = FakeSessionManager(session)

    database.error_logs.create("warn", "task failed", context_json={"task_log_id": 7, "telegram_user_id": 1})

    assert len(session.added) == 1
    assert session.added[0].context_json == {"task_log_id": 7, "telegram_user_id": 1}


def test_create_task_log_returns_serialized_payload() -> None:
    database = Database(build_settings())
    session = FakeSession(row_by_id={1: User(uuid=USER_UUID, telegram_user_id=1)})
    database._session_manager = FakeSessionManager(session)
    current_time = datetime(2026, 5, 6, 10, 0, 0)

    payload = database.task_logs.create(
        task_type="bound_google_doc_sync",
        status="processing",
        current_time=current_time,
        telegram_user_id=1,
        source_type="google_doc",
        source_identifier="demo",
        description="started",
    )

    assert len(session.added) == 1
    row = session.added[0]
    assert isinstance(row, TaskLog)
    assert payload["task_type"] == "bound_google_doc_sync"
    assert payload["status"] == "processing"
    assert payload["user_id"] == str(USER_UUID)
    assert payload["user_uuid"] == str(USER_UUID)


def test_get_latest_task_log_for_import_job_returns_most_recent_match() -> None:
    database = Database(build_settings())
    third = TaskLog(
        id=13,
        task_type="user_vocabulary_import_job_process",
        status="success",
        import_job_id=7,
        created=datetime(2026, 5, 6, 10, 2, 0),
    )
    database._session_manager = FakeSessionManager(FakeSession(scalar_values=[third]))

    payload = database.task_logs.get_latest_for_import_job(7, task_type="user_vocabulary_import_job_process")

    assert payload is not None
    assert payload["id"] == 13


def test_error_logs_list_admin_returns_paginated_rows() -> None:
    database = Database(build_settings())
    row = ErrorLog(
        id=5,
        level="warn",
        text="task failed",
        context_json={"task_log_id": 13},
        created=datetime(2026, 5, 6, 10, 2, 0),
    )
    database._session_manager = FakeSessionManager(FakeSession(scalars_rows=[row], scalar_values=[1]))

    payload = database.error_logs.list_admin(page=1, page_size=50, level=["warn"], search="task")

    assert payload["total"] == 1
    assert payload["items"][0]["id"] == 5
    assert payload["items"][0]["context_json"] == {"task_log_id": 13}


def test_save_bot_message_cleanup_result_keeps_deleted_row_on_late_failure() -> None:
    database = Database(build_settings())
    row = BotMessageLog(
        id=77,
        telegram_user_id=1,
        chat_id=10,
        message_id=20,
        screen_id="menu",
        status="deleted",
        delete_after=datetime(2026, 5, 6, 10, 0, 0),
        deleted=datetime(2026, 5, 6, 9, 0, 0),
    )
    database._session_manager = FakeSessionManager(FakeSession(row_by_id={77: row}))

    database.bot_message_logs.save_cleanup_result(
        77,
        is_deleted=False,
        current_time=datetime(2026, 5, 6, 10, 30, 0),
        error_text="late failure",
    )

    assert row.status == "deleted"
    assert row.deleted == datetime(2026, 5, 6, 9, 0, 0)
    assert row.error_text is None


def test_upsert_user_defaults_to_student_acl_when_no_explicit_group_is_provided() -> None:
    database = Database(build_settings())
    existing_user = User(uuid=USER_UUID, telegram_user_id=7, status="active", acl_group_id=1)
    session = FakeSession(row_by_id={7: existing_user}, scalar_values=[1])
    database._session_manager = FakeSessionManager(session)

    database.user_profiles.upsert_user(
        {
            "telegram_user_id": 7,
            "username": "CronosHulk",
            "first_name": "Cronos",
            "raw_telegram_json": "{}",
        }
    )

    assert existing_user.acl_group_id == 1
    assert existing_user.username == "CronosHulk"


def test_get_due_bot_message_cleanup_requeues_cleanup_failed_after_retry_window() -> None:
    database = Database(build_settings())
    row = BotMessageLog(
        id=88,
        telegram_user_id=1,
        chat_id=10,
        message_id=21,
        screen_id="menu",
        status="cleanup_failed",
        error_text="temporary error",
        delete_after=datetime(2026, 5, 5, 10, 0, 0),
        updated=datetime(2026, 5, 6, 8, 0, 0),
    )
    database._session_manager = FakeSessionManager(FakeSession(scalars_rows=[row]))

    payload = database.bot_message_logs.claim_due_cleanup(
        current_time=datetime(2026, 5, 6, 10, 0, 0),
        retry_before=datetime(2026, 5, 6, 9, 0, 0),
    )

    assert payload[0]["id"] == 88
    assert payload[0]["status"] == "cleanup_in_progress"
    assert row.status == "cleanup_in_progress"
    assert row.error_text is None


def test_get_bot_message_log_returns_latest_row_for_message() -> None:
    database = Database(build_settings())
    row = BotMessageLog(
        id=88,
        telegram_user_id=1,
        chat_id=10,
        message_id=21,
        screen_id="reminder:21",
        status="active",
        delete_after=datetime(2026, 5, 6, 10, 0, 0),
    )
    database._session_manager = FakeSessionManager(FakeSession(scalar_values=[row]))

    payload = database.bot_message_logs.get_latest_for_message(
        telegram_user_id=1,
        chat_id=10,
        message_id=21,
    )

    assert payload is not None
    assert payload["id"] == 88
    assert payload["screen_id"] == "reminder:21"


def test_list_active_bot_messages_returns_undeleted_rows_for_chat() -> None:
    database = Database(build_settings())
    rows = [
        BotMessageLog(
            id=88,
            telegram_user_id=1,
            chat_id=10,
            message_id=21,
            screen_id="reminder:21",
            status="active",
            delete_after=datetime(2026, 5, 6, 10, 0, 0),
        ),
        BotMessageLog(
            id=89,
            telegram_user_id=1,
            chat_id=10,
            message_id=22,
            screen_id="menu",
            status="cleanup_failed",
            delete_after=datetime(2026, 5, 6, 10, 0, 0),
        ),
    ]
    database._session_manager = FakeSessionManager(FakeSession(scalars_rows=rows))

    payload = database.bot_message_logs.list_active(
        telegram_user_id=1,
        chat_id=10,
    )

    assert [row["id"] for row in payload] == [88, 89]
    assert [row["message_id"] for row in payload] == [21, 22]


def test_ensure_daily_schedules_skips_past_due_reminder_time() -> None:
    database = Database(build_settings())
    fake_session = FakeSession(
        execute_rows=[[(USER_UUID, 11, 0)]],
        scalar_values=[1],
    )
    database._session_manager = FakeSessionManager(fake_session)

    database.training_schedules.ensure_daily(datetime(2026, 4, 6, 19, 25, 0))

    assert fake_session.added == []


def test_ensure_daily_schedules_creates_schedule_for_upcoming_reminder_time() -> None:
    database = Database(build_settings())
    fake_session = FakeSession(
        execute_rows=[[(USER_UUID, 20, 0)]],
        scalar_values=[0],
    )
    database._session_manager = FakeSessionManager(fake_session)

    database.training_schedules.ensure_daily(datetime(2026, 4, 6, 19, 25, 0))

    assert len(fake_session.added) == 1
    created_schedule = fake_session.added[0]
    assert created_schedule.schedule_type == "daily"
    assert created_schedule.scheduled_for == datetime(2026, 4, 6, 20, 0, 0)


def test_ensure_daily_schedules_creates_half_hour_schedule() -> None:
    database = Database(build_settings())
    fake_session = FakeSession(
        execute_rows=[[(USER_UUID, 20, 30)]],
        scalar_values=[0],
    )
    database._session_manager = FakeSessionManager(fake_session)

    database.training_schedules.ensure_daily(datetime(2026, 4, 6, 19, 25, 0))

    assert len(fake_session.added) == 1
    created_schedule = fake_session.added[0]
    assert created_schedule.schedule_type == "daily"
    assert created_schedule.scheduled_for == datetime(2026, 4, 6, 20, 30, 0)
