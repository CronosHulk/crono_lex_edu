from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from app.data_access.learning_progress import (
    LearningProgressRepository,
    learning_assignment_to_progress_dict,
)
from app.models import User, UserLevelRun, UserWordAssignment

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


class FakeExecuteResult:
    def __init__(self, rows=None, one_row=None) -> None:
        self.rows = rows or []
        self.one_row = one_row

    def all(self):
        return list(self.rows)

    def one(self):
        return self.one_row


class FakeSession:
    def __init__(self, *, row_by_key=None, scalar_values=None, execute_results=None) -> None:
        self.row_by_key = row_by_key or {}
        self.scalar_values = list(scalar_values or [])
        self.execute_results = list(execute_results or [])
        self.added = []

    def get(self, model, primary_key):
        key = tuple(sorted(primary_key.items())) if isinstance(primary_key, dict) else primary_key
        return self.row_by_key.get((model, key))

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def execute(self, statement):
        return self.execute_results.pop(0)

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        pass


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_assignment(**overrides) -> UserWordAssignment:
    now = datetime(2026, 4, 8, 10, 0, 0)
    values = {
        "id": 1,
        "user_uuid": USER_UUID,
        "word_source": "core",
        "word_id": 1001,
        "status": "available_for_rotation",
        "priority_rank": 0,
        "is_known": False,
        "learning_state": "learning",
        "control_success_streak": 1,
        "review_priority": 2,
        "last_level_run_id": 7,
        "last_completed": None,
        "last_seen_at": None,
        "last_reviewed_at": None,
        "next_review_at": None,
        "priority_state": "none",
        "review_stage": 0,
        "mistake_count": 0,
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return UserWordAssignment(**values)


def test_learning_assignment_to_progress_dict_preserves_payload_shape() -> None:
    row = make_assignment()

    payload = learning_assignment_to_progress_dict(row)

    assert payload["level_run_id"] == 7
    assert payload["word_source"] == "core"
    assert payload["word_id"] == 1001
    assert payload["learning_state"] == "learning"
    assert payload["priority_state"] == "none"
    assert payload["last_seen_at"] is None
    assert payload["last_reviewed_at"] is None
    assert payload["review_stage"] == 0
    assert payload["mistake_count"] == 0


def test_update_creates_missing_progress_with_defaults_and_completed_state() -> None:
    current_time = datetime(2026, 4, 8, 11, 0, 0)
    next_review_at = datetime(2026, 4, 9, 11, 0, 0)
    session = FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)})
    repository = LearningProgressRepository(FakeSessionManager(session))

    repository.update(
        42,
        1001,
        level_run_id=7,
        review_priority_delta=-3,
        completed_now=True,
        next_review_at=next_review_at,
        current_time=current_time,
    )

    row = session.added[0]
    assert row.is_known is False
    assert row.word_source == "core"
    assert row.learning_state == "learning"
    assert row.control_success_streak == 0
    assert row.review_priority == 0
    assert row.last_completed == current_time
    assert row.next_review_at == next_review_at
    assert row.updated == current_time


def test_update_uses_runtime_clock_when_current_time_is_omitted() -> None:
    session = FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)})
    repository = LearningProgressRepository(FakeSessionManager(session))

    repository.update(42, 1001, level_run_id=7)

    assert session.added[0].updated is not None


def test_update_existing_progress_applies_mutations_and_known_override() -> None:
    current_time = datetime(2026, 4, 8, 12, 0, 0)
    next_review_at = datetime(2026, 4, 10, 12, 0, 0)
    row = make_assignment(review_priority=2)
    repository = LearningProgressRepository(
        FakeSessionManager(FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)}, scalar_values=[row]))
    )

    repository.update(
        42,
        1001,
        level_run_id=7,
        is_known=True,
        learning_state="needs_work",
        control_success_streak=3,
        review_priority_delta=5,
        next_review_at=next_review_at,
        current_time=current_time,
    )

    assert row.is_known is True
    assert row.learning_state == "learned"
    assert row.control_success_streak == 3
    assert row.review_priority == 7
    assert row.next_review_at == next_review_at
    assert row.updated == current_time


def test_update_existing_progress_applies_srs_fields_and_consumes_introduced_priority() -> None:
    current_time = datetime(2026, 4, 8, 12, 30, 0)
    next_review_at = datetime(2026, 4, 12, 12, 30, 0)
    row = make_assignment(priority_state="introduced", review_stage=1, mistake_count=2)
    repository = LearningProgressRepository(
        FakeSessionManager(FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)}, scalar_values=[row]))
    )

    repository.update(
        42,
        1001,
        level_run_id=7,
        learning_state="learning",
        review_stage=2,
        mistake_count_delta=1,
        next_review_at=next_review_at,
        last_reviewed_at=current_time,
        current_time=current_time,
    )

    assert row.priority_state == "consumed"
    assert row.review_stage == 2
    assert row.mistake_count == 3
    assert row.last_reviewed_at == current_time
    assert row.next_review_at == next_review_at


def test_update_existing_progress_keeps_needs_work_priority_introduced() -> None:
    current_time = datetime(2026, 4, 8, 12, 45, 0)
    row = make_assignment(priority_state="introduced", review_stage=2, mistake_count=0)
    repository = LearningProgressRepository(
        FakeSessionManager(FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)}, scalar_values=[row]))
    )

    repository.update(
        42,
        1001,
        level_run_id=7,
        learning_state="needs_work",
        review_stage=1,
        mistake_count_delta=1,
        current_time=current_time,
    )

    assert row.priority_state == "introduced"
    assert row.learning_state == "needs_work"
    assert row.review_stage == 1
    assert row.mistake_count == 1


def test_update_existing_completed_progress_resets_priority_and_completion_time() -> None:
    current_time = datetime(2026, 4, 8, 13, 0, 0)
    row = make_assignment(review_priority=9)
    repository = LearningProgressRepository(
        FakeSessionManager(FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)}, scalar_values=[row]))
    )

    repository.update(42, 1001, level_run_id=7, review_priority_delta=5, completed_now=True, current_time=current_time)

    assert row.review_priority == 0
    assert row.last_completed == current_time
    assert row.updated == current_time


def test_get_returns_progress_payload_or_none() -> None:
    row = make_assignment()
    repository = LearningProgressRepository(
        FakeSessionManager(
            FakeSession(
                row_by_key={(UserLevelRun, 7): UserLevelRun(id=7, user_uuid=USER_UUID, level_id=1, run_no=1)},
                scalar_values=[row],
            )
        )
    )

    assert repository.get(1001, level_run_id=7)["review_priority"] == 2
    assert repository.get(404, level_run_id=7) is None


def test_get_reports_assignment_last_level_run_metadata() -> None:
    row = make_assignment(last_level_run_id=5)
    repository = LearningProgressRepository(
        FakeSessionManager(
            FakeSession(
                row_by_key={(UserLevelRun, 9): UserLevelRun(id=9, user_uuid=USER_UUID, level_id=1, run_no=2)},
                scalar_values=[row],
            )
        )
    )

    assert repository.get(1001, level_run_id=9)["level_run_id"] == 5


def test_update_and_get_user_source_progress() -> None:
    session = FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)})
    repository = LearningProgressRepository(FakeSessionManager(session))

    repository.update(42, 88, level_run_id=7, word_source="user", review_priority_delta=3)

    assert session.added[0].word_source == "user"


def test_level_totals_and_user_summary_reads() -> None:
    latest_run = UserLevelRun(id=55, user_uuid=USER_UUID, level_id=3, run_no=4, status="completed")
    session = FakeSession(
        row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
        scalar_values=[latest_run],
        execute_results=[
            FakeExecuteResult(rows=[(1, 10), (2, 0)]),
            FakeExecuteResult(one_row=(None, 2, 3)),
            FakeExecuteResult(one_row=(1, 0, None)),
        ],
    )
    repository = LearningProgressRepository(FakeSessionManager(session))

    assert repository.get_level_word_totals() == {1: 10, 2: 0}
    assert repository.get_user_level_summary(42, 3) == {
        "learned_count": 0,
        "in_progress_count": 2,
        "needs_work_count": 3,
    }
    assert repository.get_user_level_summary(42, 3, level_run_id=7) == {
        "learned_count": 1,
        "in_progress_count": 0,
        "needs_work_count": 0,
    }


def test_user_assignment_summary_counts_all_available_sources() -> None:
    session = FakeSession(
        row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
        execute_results=[FakeExecuteResult(one_row=(2, 3, 1, 6))],
    )
    repository = LearningProgressRepository(FakeSessionManager(session))

    assert repository.get_user_assignment_summary(42) == {
        "learned_count": 2,
        "in_progress_count": 3,
        "needs_work_count": 1,
        "total_count": 6,
    }


def test_list_user_words_maps_priority_rank_and_word_identity(monkeypatch) -> None:
    row = SimpleNamespace(
        word_source="core",
        word_id=501,
        word="sample",
        level="B2",
        translation_uk="приклад",
        translation_ru="пример",
        translation_pl="przyklad",
        learning_state="learning",
        review_priority=0,
        priority_rank=1777390200,
        is_priority=True,
        next_review_at=None,
        core_entry_id=501,
    )
    session = FakeSession(
        row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
        scalar_values=[1],
        execute_results=[FakeExecuteResult(rows=[row])],
    )
    repository = LearningProgressRepository(FakeSessionManager(session))
    monkeypatch.setattr(
        "app.data_access.learning_progress.load_dictionary_entry_metadata",
        lambda db_session, entry_ids: {501: {"categories": ["business"]}},
    )

    payload = repository.list_user_words(42, mode="learning", page=1, page_size=20)

    assert payload["total"] == 1
    assert payload["items"] == [
        {
            "id": 501,
            "word_source": "core",
            "word_id": 501,
            "word": "sample",
            "topic": "business",
            "level": "B2",
            "translation": "приклад",
            "translation_uk": "приклад",
            "translation_ru": "пример",
            "translation_pl": "przyklad",
            "learning_state": "learning",
            "review_priority": 0,
            "priority_rank": 1777390200,
            "is_priority": True,
            "next_review_at": None,
        }
    ]
