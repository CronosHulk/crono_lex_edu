from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.data_access.exercise_texts import (
    ExerciseTextRepository,
    TTSVoiceRepository,
    exercise_text_to_dict,
    tts_voice_to_dict,
)
from app.domain.exercise_texts.errors import ExerciseTextVersionConflictError
from app.models import ExerciseText, ExerciseTextTopic, TTSVoice


class FakeScalarRows:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, scalar_rows=None, scalars_rows=None, get_row=None) -> None:
        self.scalar_rows = list(scalar_rows or [])
        self.scalars_rows = list(scalars_rows or [])
        self.get_row = get_row
        self.added = []
        self.executed = []

    def add(self, row) -> None:
        if isinstance(row, ExerciseText) and row.id is None:
            row.id = 10
            row.uuid = UUID("018f6f6a-1111-7222-8333-0123456789ab")
        self.added.append(row)

    def flush(self) -> None:
        return None

    def scalar(self, statement):
        return self.scalar_rows.pop(0) if self.scalar_rows else None

    def scalars(self, statement):
        rows = self.scalars_rows.pop(0) if self.scalars_rows else []
        return FakeScalarRows(rows)

    def get(self, model, row_id):
        return self.get_row

    def execute(self, statement):
        self.executed.append(statement)
        return FakeScalarRows([])


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self.session_obj = session

    @contextmanager
    def session(self):
        yield self.session_obj


def make_exercise_text(**overrides) -> ExerciseText:
    now = datetime(2026, 5, 12, 10, 20, 30, tzinfo=UTC)
    values = {
        "id": 10,
        "uuid": UUID("018f6f6a-1111-7222-8333-0123456789ab"),
        "title": "A Day at the Tech Museum",
        "status": "draft",
        "difficulty_band": "A1_A2",
        "text_types": ["it", "article"],
        "content_jsonb": {"schema_version": 1},
        "version": 1,
        "created_by_user_uuid": UUID("018f6f6a-1111-7222-8333-111111111111"),
        "updated_by_user_uuid": UUID("018f6f6a-1111-7222-8333-111111111111"),
        "published_at": None,
        "archived_at": None,
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    row = ExerciseText(**values)
    row.topic_links = [ExerciseTextTopic(exercise_text_id=row.id, grammar_topic_id=3)]
    return row


def make_voice(**overrides) -> TTSVoice:
    values = {
        "id": 1,
        "provider": "google_tts",
        "code": "en-US-Neural2-C",
        "display_name": "Google en-US Neural2 C",
        "language_code": "en-US",
        "gender": "female",
        "is_active": True,
        "sort_order": 10,
    }
    values.update(overrides)
    return TTSVoice(**values)


def test_exercise_text_serializer_preserves_storage_shape() -> None:
    payload = exercise_text_to_dict(make_exercise_text())

    assert payload["uuid"] == "018f6f6a-1111-7222-8333-0123456789ab"
    assert payload["text_types"] == ["it", "article"]
    assert payload["content_jsonb"] == {"schema_version": 1}
    assert payload["version"] == 1
    assert payload["topic_ids"] == [3]


def test_exercise_text_repository_creates_record_and_topic_links() -> None:
    session = FakeSession()
    repository = ExerciseTextRepository(FakeSessionManager(session))
    now = datetime(2026, 5, 12, 10, 20, 30, tzinfo=UTC)

    payload = repository.create(
        title="Museum",
        difficulty_band="A1_A2",
        text_types=["it"],
        content_jsonb={"schema_version": 1},
        topic_ids=[3, 3, 4],
        actor_user_uuid="018f6f6a-1111-7222-8333-111111111111",
        current_time=now,
    )

    assert payload["id"] == 10
    assert payload["topic_ids"] == [3, 4]
    assert session.added[0].title == "Museum"
    assert [row.grammar_topic_id for row in session.added if isinstance(row, ExerciseTextTopic)] == [3, 4]


def test_exercise_text_repository_updates_version_and_topics() -> None:
    row = make_exercise_text()
    session = FakeSession(get_row=row)
    repository = ExerciseTextRepository(FakeSessionManager(session))
    now = datetime(2026, 5, 12, 11, 0, 0, tzinfo=UTC)

    payload = repository.update(
        10,
        expected_version=1,
        values={"title": "Updated", "text_types": ["science"], "content_jsonb": {"schema_version": 1, "changed": True}},
        topic_ids=[5],
        actor_user_uuid="018f6f6a-1111-7222-8333-222222222222",
        current_time=now,
    )

    assert payload is not None
    assert payload["title"] == "Updated"
    assert payload["version"] == 2
    assert payload["topic_ids"] == [5]
    assert row.updated == now
    assert session.executed


def test_exercise_text_repository_rejects_stale_version() -> None:
    repository = ExerciseTextRepository(FakeSessionManager(FakeSession(get_row=make_exercise_text(version=2))))

    with pytest.raises(ExerciseTextVersionConflictError):
        repository.update(10, expected_version=1, values={"title": "stale"})


def test_exercise_text_repository_lists_page_with_metadata() -> None:
    row = make_exercise_text()
    repository = ExerciseTextRepository(FakeSessionManager(FakeSession(scalar_rows=[1], scalars_rows=[[row]])))

    payload = repository.list_page(page=1, page_size=50)

    assert payload["total"] == 1
    assert payload["pages"] == 1
    assert payload["items"][0]["id"] == 10


def test_tts_voice_repository_lists_active_voices() -> None:
    voice = make_voice()
    repository = TTSVoiceRepository(FakeSessionManager(FakeSession(scalars_rows=[[voice]])))

    assert repository.list_active(provider="google_tts") == [tts_voice_to_dict(voice)]
