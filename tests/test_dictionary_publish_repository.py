from __future__ import annotations

from contextlib import contextmanager

from app.data_access.dictionary_publish import (
    dictionary_entry_to_dict,
    load_dictionary_entry_metadata,
    normalize_part_of_speech_code,
)
from app.models import DictionaryEntry


class FakeRowsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_id=None, scalar_values=None, execute_rows_sequence=None) -> None:
        self.row_by_id = row_by_id or {}
        self.scalar_values = list(scalar_values or [])
        self.execute_rows_sequence = list(execute_rows_sequence or [])
        self.added = []

    def get(self, model, primary_key):
        if isinstance(primary_key, dict):
            return self.row_by_id.get((model, repr(primary_key)))
        return self.row_by_id.get((model, repr(primary_key))) or self.row_by_id.get(primary_key)

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def execute(self, statement):
        rows = self.execute_rows_sequence.pop(0) if self.execute_rows_sequence else []
        return FakeRowsResult(rows)

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        for index, row in enumerate(self.added, start=1):
            if getattr(row, "id", None) is None:
                row.id = 500 + index


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_normalize_part_of_speech_code() -> None:
    assert normalize_part_of_speech_code("Phrasal / Verb") == "phrasal_verb"


def test_load_dictionary_entry_metadata_returns_empty_for_empty_ids() -> None:
    assert load_dictionary_entry_metadata(FakeSession(), []) == {}


def test_dictionary_entry_to_dict_uses_metadata_and_normalizes_examples() -> None:
    entry = DictionaryEntry(
        id=501,
        word="carry on",
        normalized_word="carry on",
        transcription="/x/",
        translation_uk="продовжувати",
        examples_json=[{"text": " Carry on. "}],
        audio_path="runtime/user_import_audio/carry_on.mp3",
        entry_type="phrasal_verb",
    )

    payload = dictionary_entry_to_dict(
        entry,
        metadata={"parts_of_speech": ["phrasal verb"], "categories": ["core"]},
        review_priority=3,
        is_priority=True,
    )

    assert payload["part_of_speech"] == "phrasal verb"
    assert payload["categories"] == ["core"]
    assert payload["examples_json"] == ["Carry on."]
    assert payload["review_priority"] == 3
    assert payload["is_priority"] is True
