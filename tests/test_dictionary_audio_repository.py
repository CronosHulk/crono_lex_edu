from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from app.data_access.dictionary_audio import DictionaryAudioRepository
from app.models import DictionaryEntry


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


def make_entry(**overrides) -> DictionaryEntry:
    values = {
        "id": 501,
        "source_namespace": "core",
        "source_ref": "core:mute",
        "entry_key": "mute__adjective__entry",
        "word": "mute",
        "normalized_word": "mute",
        "level_id": 2,
        "transcription": "/mjuːt/",
        "translation_uk": "німий",
        "audio_path": "",
        "examples_json": ["A mute button."],
    }
    values.update(overrides)
    return DictionaryEntry(**values)


def test_list_without_audio_returns_entry_payloads() -> None:
    repository = DictionaryAudioRepository(FakeSessionManager(FakeSession(scalars_rows=[make_entry()])))

    payload = repository.list_without_audio(limit=5)

    assert payload[0]["id"] == 501
    assert payload[0]["word"] == "mute"
    assert payload[0]["audio_path"] == ""


def test_count_without_audio_returns_count() -> None:
    repository = DictionaryAudioRepository(FakeSessionManager(FakeSession(scalar_values=[3])))

    assert repository.count_without_audio() == 3


def test_count_without_audio_normalizes_none_to_zero() -> None:
    repository = DictionaryAudioRepository(FakeSessionManager(FakeSession()))

    assert repository.count_without_audio() == 0


def test_update_entry_audio_updates_row_and_ignores_missing() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    row = make_entry()
    repository = DictionaryAudioRepository(FakeSessionManager(FakeSession(row_by_id={501: row})))

    payload = repository.update_entry_audio(
        501,
        audio_path="runtime/user_import_audio/mute.mp3",
        current_time=current_time,
    )

    assert payload is not None
    assert payload["audio_path"] == "runtime/user_import_audio/mute.mp3"
    assert row.audio_path == "runtime/user_import_audio/mute.mp3"
    assert row.updated == current_time
    assert repository.update_entry_audio(999, audio_path="x.mp3", current_time=current_time) is None
