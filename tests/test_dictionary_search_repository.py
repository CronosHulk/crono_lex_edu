from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

from app.data_access.dictionary_search import DictionarySearchRepository
from app.data_access.user_dictionary_constants import USER_WORD_SOURCE_CORE, USER_WORD_SOURCE_USER

USER_UUID = UUID("11111111-1111-4111-8111-111111111111")


class FakeResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeSession:
    def __init__(self, *, scalar_values=None, execute_rows=None) -> None:
        self.scalar_values = list(scalar_values or [])
        self.execute_rows = list(execute_rows or [])

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def execute(self, statement):
        return FakeResult(self.execute_rows.pop(0) if self.execute_rows else [])


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_search_words_serializes_dictionary_rows() -> None:
    row = SimpleNamespace(
        word_source=USER_WORD_SOURCE_CORE,
        word_id=501,
        word="intention",
        transcription="/in-ten-shun/",
        level="A1",
        translation_uk="намір",
        translation_ru="намерение",
        translation_pl="zamiar",
        audio_path="audio/intention.mp3",
    )
    repository = DictionarySearchRepository(FakeSessionManager(FakeSession(scalar_values=[1], execute_rows=[[row]])))

    result = repository.search_words(
        user_uuid=USER_UUID,
        query=" int ",
        page=1,
        page_size=50,
        level="A1",
        allowed_core_levels={"A1", "A2"},
        include_user_words=True,
    )

    assert result == {
        "items": [
            {
                "id": "core:501",
                "word_source": USER_WORD_SOURCE_CORE,
                "word_id": 501,
                "word": "intention",
                "transcription": "/in-ten-shun/",
                "level": "A1",
                "translation_uk": "намір",
                "translation_ru": "намерение",
                "translation_pl": "zamiar",
                "has_audio": True,
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 50,
        "pages": 1,
    }


def test_create_priority_assignment_for_allowed_core_word(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    calls = []

    def fake_create_assignment(session, **kwargs):
        calls.append(kwargs)
        return {"word_source": kwargs["word_source"], "word_id": kwargs["word_id"], "priority_rank": kwargs["priority_rank"]}

    monkeypatch.setattr("app.data_access.dictionary_search.create_assignment", fake_create_assignment)
    repository = DictionarySearchRepository(FakeSessionManager(FakeSession(scalar_values=[501])))

    result = repository.create_priority_assignment(
        user_uuid=USER_UUID,
        word_source=USER_WORD_SOURCE_CORE,
        word_id=501,
        current_time=current_time,
        allowed_core_levels={"A1", "A2"},
        include_user_words=False,
    )

    expected_rank = int(current_time.timestamp() * 1_000_000) + 999_999
    assert result == {"word_source": USER_WORD_SOURCE_CORE, "word_id": 501, "priority_rank": expected_rank}
    assert calls == [
        {
            "user_uuid": USER_UUID,
            "word_source": USER_WORD_SOURCE_CORE,
            "word_id": 501,
            "current_time": current_time,
            "status": "available_for_rotation",
            "priority_rank": expected_rank,
        }
    ]


def test_create_priority_assignment_rejects_user_word_without_premium_access(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("app.data_access.dictionary_search.create_assignment", lambda *args, **kwargs: calls.append(kwargs))
    repository = DictionarySearchRepository(FakeSessionManager(FakeSession(scalar_values=[88])))

    result = repository.create_priority_assignment(
        user_uuid=USER_UUID,
        word_source=USER_WORD_SOURCE_USER,
        word_id=88,
        current_time=datetime(2026, 4, 28, 15, 30, 0),
        allowed_core_levels={"A1", "A2"},
        include_user_words=False,
    )

    assert result is None
    assert calls == []
