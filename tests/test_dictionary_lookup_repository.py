from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.data_access.dictionary_lookup import DictionaryLookupRepository
from app.helpers.priority_rank import priority_rank_from_datetime
from app.models import DictionaryCategory, DictionaryEntry, UserWordAssignment

USER_UUID = UUID("11111111-1111-4111-8111-111111111111")


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeSession:
    def __init__(self, *, row_by_id=None, scalar_values=None, flush_error: Exception | None = None) -> None:
        self.row_by_id = row_by_id or {}
        self.scalar_values = list(scalar_values or [])
        self.flush_error = flush_error
        self.added = []

    def get(self, model, primary_key):
        return self.row_by_id.get((model, repr(primary_key)))

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def execute(self, statement):
        return FakeResult([])

    def scalars(self, statement):
        return FakeResult(self.scalar_values.pop(0) if self.scalar_values else [])

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        if self.flush_error is not None:
            error = self.flush_error
            self.flush_error = None
            raise error
        pass

    @contextmanager
    def begin_nested(self):
        yield


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_dictionary_entry() -> DictionaryEntry:
    return DictionaryEntry(
        id=501,
        source_namespace="core",
        source_ref="core:touched",
        entry_key="touched__adjective__entry",
        word="touched",
        normalized_word="touched",
        level_id=2,
        transcription="/tʌtʃt/",
        translation_uk="зворушений",
        translation_ru="тронутый",
        translation_pl="wzruszony",
        audio_path="audio/touched.mp3",
        examples_json=["He sounded deeply touched."],
        entry_type="word",
        is_archived=False,
    )


def test_find_by_word_returns_serialized_payload_with_metadata(monkeypatch) -> None:
    session = FakeSession(scalar_values=[[make_dictionary_entry()]])
    repository = DictionaryLookupRepository(FakeSessionManager(session))

    monkeypatch.setattr(
        "app.data_access.dictionary_lookup.load_dictionary_entry_metadata",
        lambda db_session, entry_ids: {501: {"parts_of_speech": ["adjective"], "categories": ["emotion"]}},
    )

    payload = repository.find_by_word("touched")

    assert payload is not None
    assert payload["word"] == "touched"
    assert payload["part_of_speech"] == "adjective"
    assert payload["categories"] == ["emotion"]
    assert payload["translation_uk"] == "зворушений"
    assert payload["examples_json"] == ["He sounded deeply touched."]


def test_find_by_word_returns_none_when_entry_is_missing() -> None:
    repository = DictionaryLookupRepository(FakeSessionManager(FakeSession(scalar_values=[[]])))

    payload = repository.find_by_word("missing")

    assert payload is None


def test_list_by_word_returns_all_matching_dictionary_entries(monkeypatch) -> None:
    noun_entry = make_dictionary_entry()
    noun_entry.id = 501
    noun_entry.entry_key = "record__noun__entry"
    noun_entry.word = "record"
    verb_entry = make_dictionary_entry()
    verb_entry.id = 502
    verb_entry.entry_key = "record__verb__entry"
    verb_entry.word = "record"
    session = FakeSession(scalar_values=[[noun_entry, verb_entry]])
    repository = DictionaryLookupRepository(FakeSessionManager(session))

    monkeypatch.setattr(
        "app.data_access.dictionary_lookup.load_dictionary_entry_metadata",
        lambda db_session, entry_ids: {
            501: {"parts_of_speech": ["noun"], "categories": []},
            502: {"parts_of_speech": ["verb"], "categories": []},
        },
    )

    payload = repository.list_by_word("record")

    assert [entry["id"] for entry in payload] == [501, 502]
    assert [entry["part_of_speech"] for entry in payload] == ["noun", "verb"]


def test_list_by_word_normalizes_lookup_whitespace(monkeypatch) -> None:
    entry = make_dictionary_entry()
    session = FakeSession(scalar_values=[[entry]])
    repository = DictionaryLookupRepository(FakeSessionManager(session))

    monkeypatch.setattr(
        "app.data_access.dictionary_lookup.load_dictionary_entry_metadata",
        lambda db_session, entry_ids: {501: {"parts_of_speech": ["adjective"], "categories": []}},
    )

    payload = repository.list_by_word("  TOUCHED  ")

    assert [row["id"] for row in payload] == [501]


def test_list_categories_returns_dictionary_category_options() -> None:
    rows = [
        DictionaryCategory(id=1, code="business", title="Business"),
        DictionaryCategory(id=2, code="travel", title="Travel"),
    ]
    repository = DictionaryLookupRepository(FakeSessionManager(FakeSession(scalar_values=[rows])))

    assert repository.list_categories() == [
        {"code": "business", "title": "Business"},
        {"code": "travel", "title": "Travel"},
    ]


def test_create_user_core_word_assignment_adds_missing_assignment(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    session = FakeSession()
    repository = DictionaryLookupRepository(FakeSessionManager(session))
    monkeypatch.setattr("app.data_access.dictionary_lookup.get_user_uuid_by_telegram_id", lambda db_session, user_id: USER_UUID)

    repository.create_user_core_word_assignment(telegram_user_id=10, word_id=501, current_time=current_time)

    assert len(session.added) == 1
    assert isinstance(session.added[0], UserWordAssignment)
    assert session.added[0].user_uuid == USER_UUID
    assert session.added[0].word_source == "core"
    assert session.added[0].word_id == 501
    assert session.added[0].priority_rank == priority_rank_from_datetime(current_time)


def test_create_user_core_word_assignment_touches_existing_assignment(monkeypatch) -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    existing = UserWordAssignment(user_uuid=USER_UUID, word_source="core", word_id=501)
    existing.updated = datetime(2026, 4, 27, 10, 0, 0)
    existing.priority_rank = 0
    session = FakeSession(scalar_values=[existing])
    repository = DictionaryLookupRepository(FakeSessionManager(session))
    monkeypatch.setattr("app.data_access.dictionary_lookup.get_user_uuid_by_telegram_id", lambda db_session, user_id: USER_UUID)

    repository.create_user_core_word_assignment(telegram_user_id=10, word_id=501, current_time=current_time)

    assert session.added == []
    assert existing.updated == current_time
    assert existing.priority_rank == priority_rank_from_datetime(current_time)


def test_create_user_core_word_assignment_for_user_uuid_adds_missing_assignment() -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    session = FakeSession()
    repository = DictionaryLookupRepository(FakeSessionManager(session))

    repository.create_user_core_word_assignment_for_user_uuid(str(USER_UUID), word_id=501, current_time=current_time)

    assert len(session.added) == 1
    assert isinstance(session.added[0], UserWordAssignment)
    assert session.added[0].user_uuid == USER_UUID
    assert session.added[0].word_source == "core"
    assert session.added[0].word_id == 501
    assert session.added[0].priority_rank == priority_rank_from_datetime(current_time)


def test_create_user_core_word_assignment_recovers_when_assignment_was_created_concurrently() -> None:
    current_time = datetime(2026, 4, 28, 15, 30, 0)
    existing = UserWordAssignment(user_uuid=USER_UUID, word_source="core", word_id=501)
    existing.updated = datetime(2026, 4, 27, 10, 0, 0)
    existing.priority_rank = 0
    session = FakeSession(
        scalar_values=[None, existing],
        flush_error=IntegrityError("INSERT user_word_assignment", {}, Exception("duplicate")),
    )
    repository = DictionaryLookupRepository(FakeSessionManager(session))

    repository.create_user_core_word_assignment_for_user_uuid(str(USER_UUID), word_id=501, current_time=current_time)

    assert existing.updated == current_time
    assert existing.priority_rank == priority_rank_from_datetime(current_time)
