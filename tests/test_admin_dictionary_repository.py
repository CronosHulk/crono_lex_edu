from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.data_access.admin_dictionary import AdminDictionaryRepository, enrich_admin_dictionary_row
from app.models import DictionaryCategory, DictionaryEntry, DictionaryPartOfSpeech, LanguageLevel
from app.storage.audio import FileSystemAudioStorageProvider


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(
        self,
        *,
        row_by_id=None,
        scalars_rows=None,
        scalars_queue=None,
        scalar_values=None,
    ) -> None:
        self.row_by_id = row_by_id or {}
        self.scalars_rows = list(scalars_rows or [])
        self.scalars_queue = list(scalars_queue or [])
        self.scalar_values = list(scalar_values or [])
        self.deleted = []
        self.flushed = False

    def get(self, model, primary_key):
        return self.row_by_id.get(primary_key)

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        if self.scalars_queue:
            return FakeScalarsResult(self.scalars_queue.pop(0))
        return FakeScalarsResult(self.scalars_rows)

    def flush(self) -> None:
        self.flushed = True

    def delete(self, row) -> None:
        self.deleted.append(row)


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
        "source_ref": "core:harbor",
        "entry_key": "harbor__noun__entry",
        "word": "harbor",
        "normalized_word": "harbor",
        "level_id": 2,
        "transcription": "/ˈhɑːrbər/",
        "audio_path": "word_base/base/noun/harbor.mp3",
        "examples_json": ["The harbor was quiet."],
        "translation_uk": "гавань",
        "translation_ru": None,
        "translation_pl": None,
        "entry_type": "word",
        "is_archived": False,
        "is_teacher_verified": False,
        "embedding": [0.1, 0.2],
        "embedding_model": "model",
        "is_embedding_ready": True,
    }
    values.update(overrides)
    return DictionaryEntry(**values)


def test_enrich_admin_dictionary_row_adds_admin_fields() -> None:
    payload = enrich_admin_dictionary_row(
        {"id": 501, "audio_path": "audio.mp3", "translation_uk": "а", "translation_ru": "б", "translation_pl": ""}
    )

    assert payload["audio_url"] == "/api/v1/admin/dictionary/entries/501/audio"
    assert payload["translations_multiline"] == "uk: а\nru: б\npl: "


def test_list_entries_returns_paginated_enriched_payloads(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.data_access.admin_dictionary.load_dictionary_entry_metadata",
        lambda session, entry_ids: {501: {"parts_of_speech": ["noun"], "categories": ["travel"]}},
    )
    entry = make_entry()
    entry.level = LanguageLevel(id=2, title="A2", description=None)
    repository = AdminDictionaryRepository(FakeSessionManager(FakeSession(scalars_rows=[entry], scalar_values=[1])))

    payload = repository.list_entries(
        page=1,
        page_size=50,
        archived=False,
        search=" harbor ",
        part_of_speech=["noun"],
        category="travel",
        entry_type="word",
    )

    assert payload["total"] == 1
    assert payload["items"][0]["id"] == 501
    assert payload["items"][0]["level_title"] == "A2"
    assert payload["items"][0]["parts_of_speech"] == ["noun"]
    assert payload["items"][0]["audio_url"].endswith("/501/audio")


def test_get_entry_returns_payload_or_none(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.data_access.admin_dictionary.load_dictionary_entry_metadata",
        lambda session, entry_ids: {501: {"parts_of_speech": ["noun"], "categories": []}},
    )
    repository = AdminDictionaryRepository(FakeSessionManager(FakeSession(row_by_id={501: make_entry()})))

    assert repository.get_entry(501)["word"] == "harbor"
    assert repository.get_entry(404) is None


def test_update_entry_resets_embedding_and_audio_for_spelling_changes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.data_access.admin_dictionary.load_dictionary_entry_metadata",
        lambda session, entry_ids: {501: {"parts_of_speech": ["noun"], "categories": []}},
    )
    audio_file = tmp_path / "word_base/base/noun/harbor.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"audio")
    audio_storage_provider = FileSystemAudioStorageProvider(project_root=tmp_path)
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    row = make_entry()
    session = FakeSession(row_by_id={501: row})
    repository = AdminDictionaryRepository(FakeSessionManager(session))

    payload = repository.update_entry(
        501,
        word="Harbors",
        transcription="",
        translation_uk="порти",
        translation_ru="порт",
        translation_pl="port",
        examples_json=[" A harbor. ", ""],
        entry_type="phrasal_verb",
        audio_storage_provider=audio_storage_provider,
        audio_roots=[tmp_path / "word_base/base"],
        current_time=current_time,
    )

    assert payload is not None
    assert payload["word"] == "Harbors"
    assert row.normalized_word == "harbors"
    assert row.transcription is None
    assert row.embedding is None
    assert row.embedding_model is None
    assert row.is_embedding_ready is False
    assert row.audio_path == ""
    assert not audio_file.exists()
    assert row.entry_type == "phrasal_verb"
    assert row.updated == current_time
    assert session.flushed is True
    assert repository.update_entry(404, audio_storage_provider=audio_storage_provider, current_time=current_time) is None


def test_update_entry_keeps_audio_when_spelling_is_unchanged(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.data_access.admin_dictionary.load_dictionary_entry_metadata",
        lambda session, entry_ids: {501: {"parts_of_speech": ["noun"], "categories": []}},
    )
    audio_file = tmp_path / "word_base/base/noun/harbor.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"audio")
    audio_storage_provider = FileSystemAudioStorageProvider(project_root=tmp_path)
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    row = make_entry()
    repository = AdminDictionaryRepository(FakeSessionManager(FakeSession(row_by_id={501: row})))

    payload = repository.update_entry(
        501,
        translation_uk="порт",
        audio_storage_provider=audio_storage_provider,
        audio_roots=[tmp_path / "word_base/base"],
        current_time=current_time,
    )

    assert payload is not None
    assert row.audio_path == "word_base/base/noun/harbor.mp3"
    assert audio_file.exists()


def test_get_filter_metadata_returns_parts_and_categories() -> None:
    part = DictionaryPartOfSpeech(id=1, code="noun", title="Noun")
    category = DictionaryCategory(id=2, code="travel", title="Travel")
    repository = AdminDictionaryRepository(FakeSessionManager(FakeSession(scalars_queue=[[part], [category]])))

    payload = repository.get_filter_metadata()

    assert payload["entity"] == "dictionary"
    assert payload["filters"][1]["name"] == "entry_type"
    assert payload["filters"][2]["options"] == [{"value": "noun", "label": "Noun"}]
    assert payload["filters"][3]["options"] == [{"value": "travel", "label": "Travel"}]


def test_audio_archive_and_delete_branches() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    row = make_entry()
    session = FakeSession(row_by_id={501: row, 502: make_entry(id=502, audio_path="")})
    repository = AdminDictionaryRepository(FakeSessionManager(session))

    assert repository.get_entry_audio(501) == {"id": 501, "audio_path": "word_base/base/noun/harbor.mp3"}
    assert repository.get_entry_audio(502) is None
    assert repository.get_entry_audio(404) is None
    assert repository.set_entry_archived(501, is_archived=True, current_time=current_time) is True
    assert row.is_archived is True
    assert row.updated == current_time
    assert repository.set_entry_archived(404, is_archived=True, current_time=current_time) is False
    assert repository.delete_entry(501) is True
    assert session.deleted == [row]
    assert repository.delete_entry(404) is False


def test_mark_entries_teacher_verified_updates_unarchived_rows() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    first = make_entry()
    session = FakeSession(scalars_rows=[first])
    repository = AdminDictionaryRepository(FakeSessionManager(session))

    updated = repository.mark_entries_teacher_verified(
        [501, 502],
        verified_by_user_uuid="00000000-0000-4000-8000-000000000042",
        current_time=current_time,
    )

    assert updated == 1
    assert first.is_teacher_verified is True
    assert first.teacher_verified_by_user_uuid == "00000000-0000-4000-8000-000000000042"
    assert first.teacher_verified_at == current_time
