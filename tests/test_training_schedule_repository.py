from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from app.data_access.training_schedules import (
    TrainingScheduleRepository,
    training_schedule_to_dict,
)
from app.models import TrainingSchedule, User
from app.time_utils import build_schedule_datetime


class FakeResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_id=None, scalar_values=None, scalars_rows=None, execute_rows=None) -> None:
        self.row_by_id = row_by_id or {}
        self.user = User(telegram_user_id=42, uuid=UUID("11111111-1111-4111-8111-111111111111"))
        self.scalar_values = list(scalar_values or [])
        self.scalars_rows = list(scalars_rows or [])
        self.execute_rows = list(execute_rows or [])
        self.added = []
        self.flushed = False

    def get(self, model, primary_key):
        if model is User and primary_key == self.user.telegram_user_id:
            return self.user
        return self.row_by_id.get(primary_key)

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        return FakeResult(self.scalars_rows)

    def execute(self, statement):
        return FakeResult(self.execute_rows.pop(0) if self.execute_rows else [])

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_schedule(**overrides) -> TrainingSchedule:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "id": 501,
        "user_uuid": UUID("11111111-1111-4111-8111-111111111111"),
        "schedule_type": "daily",
        "scheduled_for": now,
        "schedule_date": now.date(),
        "period_code": None,
        "source_session_id": None,
        "status": "pending",
        "notified": None,
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return TrainingSchedule(**values)


def test_training_schedule_to_dict_includes_optional_chat_id() -> None:
    payload = training_schedule_to_dict(make_schedule(), chat_id=99)

    assert payload["id"] == 501
    assert payload["chat_id"] == 99


def test_get_existing_and_next_return_payload_or_none() -> None:
    row = make_schedule()
    repository = TrainingScheduleRepository(FakeSessionManager(FakeSession(scalar_values=[row, None])))

    assert repository.get_existing_for_date(42, row.schedule_date, schedule_types=("daily",))["id"] == 501
    assert repository.get_next(42, row.scheduled_for) is None


def test_create_or_replace_cancels_existing_and_persists_new_schedule() -> None:
    existing = make_schedule(id=1, status="sent")
    scheduled_for = datetime(2026, 4, 7, 19, 0, 0)
    session = FakeSession(scalars_rows=[existing])
    repository = TrainingScheduleRepository(FakeSessionManager(session))

    payload = repository.create_or_replace(
        42,
        "manual",
        scheduled_for,
        period_code="evening",
        source_session_id=77,
    )

    assert existing.status == "cancelled"
    assert session.flushed is True
    assert session.added[0].schedule_type == "manual"
    assert session.added[0].schedule_date == scheduled_for.date()
    assert payload["period_code"] == "evening"
    assert payload["source_session_id"] == 77


def test_ensure_daily_skips_non_matching_or_existing_schedule_and_creates_new_one() -> None:
    current_time = datetime(2026, 4, 6, 19, 25, 0)
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    skipped_session = FakeSession(
        execute_rows=[[(user_uuid, 20, 0), (user_uuid, 18, 0), (user_uuid, 21, 0)]],
        scalar_values=[1, 1],
    )
    skipped_repository = TrainingScheduleRepository(FakeSessionManager(skipped_session))

    skipped_repository.ensure_daily(current_time)

    assert skipped_session.added == []

    create_session = FakeSession(execute_rows=[[(user_uuid, 20, 0)]], scalar_values=[0])
    create_repository = TrainingScheduleRepository(FakeSessionManager(create_session))

    create_repository.ensure_daily(current_time)

    assert len(create_session.added) == 1
    assert create_session.added[0].scheduled_for == build_schedule_datetime(current_time, current_time.date(), 20)


def test_ensure_daily_creates_new_weekly_row_after_previous_completed_schedule() -> None:
    current_time = datetime(2026, 4, 13, 10, 0, 0)
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    session = FakeSession(execute_rows=[[(user_uuid, 12, 0)]], scalar_values=[0])
    repository = TrainingScheduleRepository(FakeSessionManager(session))

    repository.ensure_daily(current_time)

    assert len(session.added) == 1
    assert session.added[0].scheduled_for == build_schedule_datetime(current_time, current_time.date(), 12)
    assert session.added[0].status == "pending"


def test_get_due_ensures_daily_marks_pending_rows_sent_and_adds_chat_id() -> None:
    current_time = datetime(2026, 4, 6, 20, 0, 0)
    row = make_schedule()
    session = FakeSession(execute_rows=[[], [(row, 1001, 42)]])
    repository = TrainingScheduleRepository(FakeSessionManager(session))

    payload = repository.get_due(current_time)

    assert payload[0]["chat_id"] == 1001
    assert row.status == "sent"
    assert row.notified == current_time


def test_get_update_status_and_complete_due_mutate_rows() -> None:
    current_time = datetime(2026, 4, 6, 10, 7, 0)
    first = make_schedule(id=1, status="sent")
    second = make_schedule(id=2, status="pending")
    session = FakeSession(row_by_id={1: first, 2: second}, scalar_values=[42], scalars_rows=[first, second])
    repository = TrainingScheduleRepository(FakeSessionManager(session))

    assert repository.get(404) is None
    assert repository.get(1)["id"] == 1

    repository.update_status(2, "skipped")
    repository.update_status(404, "skipped")
    assert second.status == "skipped"

    repository.complete_due(42, current_time, exclude_schedule_id=2)
    assert [row.status for row in (first, second)] == ["completed", "completed"]
