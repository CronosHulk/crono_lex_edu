from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from app.data_access.learning_word_priority import LearningWordPriorityRepository
from app.helpers.priority_rank import priority_rank_from_datetime
from app.models import DictionaryEntry, User, UserWordAssignment

USER_UUID = UUID("11111111-1111-4111-8111-111111111111")


class FakeSession:
    def __init__(self, *, row_by_key=None, scalar_values=None) -> None:
        self.row_by_key = row_by_key or {}
        self.scalar_values = list(scalar_values or [])
        self.added = []

    def get(self, model, primary_key):
        key = tuple(sorted(primary_key.items())) if isinstance(primary_key, dict) else primary_key
        return self.row_by_key.get((model, key))

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def add(self, row) -> None:
        self.added.append(row)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_core_entry() -> DictionaryEntry:
    return DictionaryEntry(
        id=501,
        source_namespace="core",
        source_ref="core:501",
        entry_key="sample__noun__entry",
        word="sample",
        normalized_word="sample",
        level_id=1,
        translation_uk="приклад",
        examples_json=[],
        entry_type="word",
        is_archived=False,
    )


def test_prioritize_core_word_touches_assignment() -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    assignment = UserWordAssignment(
        user_uuid=USER_UUID,
        word_source="core",
        word_id=501,
        status="available_for_rotation",
        priority_rank=0,
    )
    session = FakeSession(
        row_by_key={
            (User, 42): User(uuid=USER_UUID, telegram_user_id=42),
            (DictionaryEntry, 501): make_core_entry(),
        },
        scalar_values=[assignment],
    )
    repository = LearningWordPriorityRepository(FakeSessionManager(session))

    result = repository.prioritize_word(42, word_source="core", word_id=501, current_time=current_time)

    expected_rank = priority_rank_from_datetime(current_time)
    assert result == {"word_source": "core", "word_id": 501, "priority_rank": expected_rank}
    assert session.added == []
    assert assignment.priority_rank == expected_rank
    assert assignment.priority_state == "pending"
    assert assignment.updated == current_time


def test_prioritize_core_word_returns_none_without_existing_assignment() -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    session = FakeSession(
        row_by_key={
            (User, 42): User(uuid=USER_UUID, telegram_user_id=42),
            (DictionaryEntry, 501): make_core_entry(),
        },
    )
    repository = LearningWordPriorityRepository(FakeSessionManager(session))

    result = repository.prioritize_word(42, word_source="core", word_id=501, current_time=current_time)

    assert result is None
    assert session.added == []


def test_prioritize_core_word_does_not_resurrect_hidden_assignment() -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    assignment = UserWordAssignment(user_uuid=USER_UUID, word_source="core", word_id=501, status="hidden", priority_rank=0)
    session = FakeSession(
        row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
        scalar_values=[assignment],
    )
    repository = LearningWordPriorityRepository(FakeSessionManager(session))

    result = repository.prioritize_word(42, word_source="core", word_id=501, current_time=current_time)

    assert result is None
    assert assignment.priority_rank == 0


def test_prioritize_user_word_touches_available_assignment() -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    assignment = UserWordAssignment(
        user_uuid=USER_UUID,
        word_source="user",
        word_id=88,
        status="available_for_rotation",
        priority_rank=0,
        is_known=True,
        learning_state="learned",
    )
    session = FakeSession(
        row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
        scalar_values=[assignment],
    )
    repository = LearningWordPriorityRepository(FakeSessionManager(session))

    result = repository.prioritize_word(42, word_source="user", word_id=88, current_time=current_time)

    expected_rank = priority_rank_from_datetime(current_time)
    assert result == {"word_source": "user", "word_id": 88, "priority_rank": expected_rank}
    assert assignment.priority_rank == expected_rank
    assert assignment.priority_state == "pending"
    assert assignment.is_known is False
    assert assignment.learning_state == "learning"
    assert assignment.updated == current_time


def test_prioritize_word_returns_none_when_user_or_word_is_missing() -> None:
    repository = LearningWordPriorityRepository(FakeSessionManager(FakeSession()))

    assert repository.prioritize_word(42, word_source="core", word_id=501, current_time=datetime(2026, 4, 28)) is None
