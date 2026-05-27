from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta

from app.data_access.bot_message_logs import BotMessageLogRepository
from app.models import BotMessageLog


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_id=None, scalars_rows=None, scalar_values=None) -> None:
        self.row_by_id = row_by_id or {}
        self.scalars_rows = list(scalars_rows or [])
        self.scalar_values = list(scalar_values or [])
        self.added = []
        self.flushed = False

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True

    def get(self, model, primary_key):
        return self.row_by_id.get(primary_key)

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        return FakeScalarsResult(self.scalars_rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_message(**overrides) -> BotMessageLog:
    now = datetime(2026, 5, 6, 10, 0, 0)
    values = {
        "id": 901,
        "telegram_user_id": 42,
        "chat_id": 99,
        "message_id": 501,
        "screen_id": "learn:card",
        "status": "active",
        "error_text": None,
        "delete_after": now + timedelta(minutes=10),
        "created": now,
        "updated": now,
        "deleted": None,
    }
    values.update(overrides)
    return BotMessageLog(**values)


def test_create_persists_active_message() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    delete_after = current_time + timedelta(minutes=30)
    session = FakeSession()
    repository = BotMessageLogRepository(FakeSessionManager(session))

    payload = repository.create(42, 99, 501, "learn:card", delete_after, current_time)

    assert session.flushed is True
    assert session.added[0].status == "active"
    assert session.added[0].delete_after == delete_after
    assert payload["message_id"] == 501


def test_get_latest_for_message_returns_payload_or_none() -> None:
    repository = BotMessageLogRepository(FakeSessionManager(FakeSession(scalar_values=[make_message(), None])))

    assert repository.get_latest_for_message(42, 99, 501)["id"] == 901
    assert repository.get_latest_for_message(42, 99, 404) is None


def test_get_latest_active_screen_returns_payload_or_none() -> None:
    repository = BotMessageLogRepository(FakeSessionManager(FakeSession(scalar_values=[make_message(), None])))

    assert repository.get_latest_active_screen(42)["screen_id"] == "learn:card"
    assert repository.get_latest_active_screen(404) is None


def test_list_active_returns_payloads() -> None:
    repository = BotMessageLogRepository(FakeSessionManager(FakeSession(scalars_rows=[make_message()])))

    assert repository.list_active(42, 99)[0]["screen_id"] == "learn:card"


def test_claim_due_cleanup_marks_rows_in_progress() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    row = make_message(status="cleanup_failed", error_text="old")
    repository = BotMessageLogRepository(FakeSessionManager(FakeSession(scalars_rows=[row])))

    payload = repository.claim_due_cleanup(current_time, current_time - timedelta(minutes=5))

    assert payload[0]["status"] == "cleanup_in_progress"
    assert row.status == "cleanup_in_progress"
    assert row.updated == current_time
    assert row.error_text is None


def test_save_cleanup_result_handles_missing_late_failure_success_and_failure() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    deleted_row = make_message(id=1, deleted=current_time, status="deleted")
    success_row = make_message(id=2, status="cleanup_in_progress")
    failure_row = make_message(id=3, status="cleanup_in_progress")
    repository = BotMessageLogRepository(
        FakeSessionManager(FakeSession(row_by_id={1: deleted_row, 2: success_row, 3: failure_row}))
    )

    repository.save_cleanup_result(404, is_deleted=True, current_time=current_time)
    repository.save_cleanup_result(1, is_deleted=False, current_time=current_time, error_text="late")
    repository.save_cleanup_result(2, is_deleted=True, current_time=current_time)
    repository.save_cleanup_result(3, is_deleted=False, current_time=current_time, error_text="boom")

    assert deleted_row.error_text is None
    assert success_row.status == "deleted"
    assert success_row.deleted == current_time
    assert failure_row.status == "cleanup_failed"
    assert failure_row.error_text == "boom"
