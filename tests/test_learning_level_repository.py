from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

import pytest

from app.data_access.learning_levels import (
    LearningLevelRepository,
    language_level_to_dict,
    level_run_to_dict,
)
from app.models import LanguageLevel, User, UserLevelRun

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_key=None, scalar_values=None, scalars_rows=None) -> None:
        self.row_by_key = row_by_key or {}
        self.scalar_values = list(scalar_values or [])
        self.scalars_rows = list(scalars_rows or [])
        self.added = []
        self.flushed = False

    def get(self, model, primary_key):
        return self.row_by_key.get((model, primary_key))

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        rows = self.scalars_rows.pop(0) if self.scalars_rows and isinstance(self.scalars_rows[0], list) else self.scalars_rows
        return FakeScalarsResult(rows)

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True
        if self.added and self.added[-1].id is None:
            self.added[-1].id = 900


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_level_run(**overrides) -> UserLevelRun:
    now = datetime(2026, 4, 7, 12, 0, 0)
    values = {
        "id": 101,
        "user_uuid": USER_UUID,
        "level_id": 3,
        "run_no": 2,
        "status": "active",
        "created": now,
        "updated": now,
        "completed": None,
    }
    values.update(overrides)
    return UserLevelRun(**values)


def test_serializers_preserve_public_payload_shape() -> None:
    level = LanguageLevel(id=3, title="B1", description="Intermediate")
    run = make_level_run()

    assert language_level_to_dict(level) == {"id": 3, "title": "B1", "description": "Intermediate"}
    assert level_run_to_dict(run)["run_no"] == 2


def test_save_language_level_updates_user_or_raises_for_missing_level_or_user() -> None:
    level = LanguageLevel(id=3, title="B1", description="Intermediate")
    user = User(uuid=USER_UUID, telegram_user_id=42, language_level_id=1)
    repository = LearningLevelRepository(
        FakeSessionManager(FakeSession(row_by_key={(User, 42): user}, scalar_values=[level, None, level]))
    )

    repository.save_language_level(42, "B1")

    assert user.language_level_id == 3
    with pytest.raises(ValueError, match="Language level not found"):
        repository.save_language_level(42, "C2")
    with pytest.raises(ValueError, match="Language level not found"):
        repository.save_language_level(404, "B1")


def test_list_active_and_latest_reads_return_payloads_or_none() -> None:
    level = LanguageLevel(id=1, title="A1", description=None)
    active_run = make_level_run(id=10)
    latest_run = make_level_run(id=11, status="completed")
    session = FakeSession(
        row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
        scalar_values=[active_run, None, latest_run, None],
        scalars_rows=[[level]],
    )
    repository = LearningLevelRepository(FakeSessionManager(session))

    assert repository.list_language_levels() == [{"id": 1, "title": "A1", "description": None}]
    assert repository.get_active(42, 3)["id"] == 10
    assert repository.get_active(42, 3) is None
    assert repository.get_latest(42, 3)["status"] == "completed"
    assert repository.get_latest(42, 3) is None


def test_list_levels_matches_language_level_contract() -> None:
    level = LanguageLevel(id=1, title="A1", description=None)
    repository = LearningLevelRepository(FakeSessionManager(FakeSession(scalars_rows=[[level]])))

    assert repository.list_levels() == [{"id": 1, "title": "A1", "description": None}]


def test_create_abandons_existing_active_runs_and_increments_run_no() -> None:
    first = make_level_run(id=1, run_no=1)
    second = make_level_run(id=2, run_no=2)
    session = FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)}, scalar_values=[2], scalars_rows=[[first, second]])
    repository = LearningLevelRepository(FakeSessionManager(session))

    payload = repository.create(42, 3)

    assert [row.status for row in (first, second)] == ["abandoned", "abandoned"]
    assert first.completed is not None
    assert session.flushed is True
    assert payload["id"] == 900
    assert payload["run_no"] == 3
    assert payload["status"] == "active"


def test_ensure_active_reuses_existing_run_or_creates_new_one() -> None:
    existing = make_level_run(id=55)
    reuse_repository = LearningLevelRepository(
        FakeSessionManager(FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)}, scalar_values=[existing]))
    )

    assert reuse_repository.ensure_active(42, 3)["id"] == 55

    create_session = FakeSession(
        row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
        scalar_values=[None, 0],
        scalars_rows=[[]],
    )
    create_repository = LearningLevelRepository(FakeSessionManager(create_session))

    assert create_repository.ensure_active(42, 3)["run_no"] == 1
    assert len(create_session.added) == 1


def test_complete_noops_for_missing_or_already_completed_and_closes_active_run() -> None:
    completed = make_level_run(id=1, status="completed")
    active = make_level_run(id=2, status="active")
    current_time = datetime(2026, 4, 7, 13, 0, 0)
    repository = LearningLevelRepository(
        FakeSessionManager(FakeSession(row_by_key={(UserLevelRun, 1): completed, (UserLevelRun, 2): active}))
    )

    repository.complete(404, current_time)
    repository.complete(1, current_time)
    repository.complete(2, current_time)

    assert completed.completed is None
    assert active.status == "completed"
    assert active.completed == current_time
    assert active.updated == current_time
