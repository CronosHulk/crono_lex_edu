from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from app.data_access.user_dictionary import (
    USER_DICTIONARY_QUEUED_AUDIO,
    USER_DICTIONARY_READY,
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_SOURCE_USER,
    UserDictionaryRepository,
    normalize_user_word_source,
    user_dictionary_entry_to_dict,
)
from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_HIDDEN,
    USER_WORD_LEARNED,
    USER_WORD_LEARNING,
    USER_WORD_NEEDS_WORK,
)
from app.helpers.priority_rank import priority_rank_from_datetime
from app.models import (
    DictionaryEntry,
    LearningSessionWord,
    UserDictionaryEntry,
    UserVocabularyImportItem,
    UserWordAssignment,
)
from app.storage.audio import FileSystemAudioStorageProvider


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeExecuteResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(
        self,
        *,
        row_by_id=None,
        scalar_values_sequence=None,
        scalars_rows=None,
        scalars_rows_sequence=None,
        execute_rows_sequence=None,
    ) -> None:
        self.row_by_id = row_by_id or {}
        self.scalar_values = list(scalar_values_sequence or [])
        self.scalars_rows = list(scalars_rows or [])
        self.scalars_rows_sequence = list(scalars_rows_sequence or [])
        self.execute_rows_sequence = list(execute_rows_sequence or [])
        self.added = []
        self.deleted = []
        self.next_id = 100

    def get(self, model, primary_key):
        if isinstance(primary_key, dict):
            return self.row_by_id.get((model, tuple(sorted(primary_key.items()))))
        return self.row_by_id.get((model, primary_key), self.row_by_id.get(primary_key))

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        if self.scalars_rows_sequence:
            return FakeScalarsResult(self.scalars_rows_sequence.pop(0))
        return FakeScalarsResult(self.scalars_rows)

    def execute(self, statement):
        _ = statement
        return FakeExecuteResult(self.execute_rows_sequence.pop(0) if self.execute_rows_sequence else [])

    def add(self, row) -> None:
        self.added.append(row)

    def delete(self, row) -> None:
        self.deleted.append(row)

    def flush(self) -> None:
        for row in self.added:
            if getattr(row, "id", None) is None:
                row.id = self.next_id
                self.next_id += 1

    @contextmanager
    def begin_nested(self):
        yield


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_user_entry(**overrides) -> UserDictionaryEntry:
    values = {
        "id": 7,
        "word": "extension cord",
        "normalized_word": "extension cord",
        "entry_key": "user__extension-cord__noun",
        "entry_type": "word",
        "part_of_speech": "noun",
        "translation_uk": "подовжувач",
        "translation_ru": "удлинитель",
        "translation_pl": "przedłużacz",
        "examples_json": ["The extension cord reached behind the heavy desk."],
        "audio_path": "word_base/user/noun/extension-cord.mp3",
        "is_embedding_ready": False,
        "status": "ready_for_rotation",
        "source_provider_status_json": {"details": "ok"},
        "created": datetime(2026, 5, 3, 10, 0, 0),
        "updated": datetime(2026, 5, 3, 10, 0, 0),
    }
    values.update(overrides)
    return UserDictionaryEntry(**values)


def make_assignment(**overrides) -> UserWordAssignment:
    values = {
        "id": 9,
        "user_uuid": UUID("11111111-1111-4111-8111-111111111111"),
        "word_source": "user",
        "word_id": 7,
        "status": "available_for_rotation",
        "created": datetime(2026, 5, 3, 10, 0, 0),
        "updated": datetime(2026, 5, 3, 10, 0, 0),
    }
    values.update(overrides)
    return UserWordAssignment(**values)


def make_core_entry(**overrides) -> DictionaryEntry:
    values = {
        "id": 77,
        "source_namespace": "core",
        "source_ref": "core:77",
        "entry_key": "extension_cord__noun__entry",
        "word": "extension cord",
        "normalized_word": "extension cord",
        "entry_type": "word",
        "level_id": 2,
        "transcription": "/cord/",
        "translation_uk": "подовжувач",
        "translation_ru": "удлинитель",
        "translation_pl": "przedłużacz",
        "examples_json": ["Core example."],
        "audio_path": "word_base/base/noun/extension-cord.mp3",
        "is_embedding_ready": False,
    }
    values.update(overrides)
    return DictionaryEntry(**values)


def test_user_dictionary_entry_to_dict_normalizes_json_defaults() -> None:
    payload = user_dictionary_entry_to_dict(make_user_entry(examples_json=None, source_provider_status_json=None))

    assert payload["id"] == 7
    assert payload["examples_json"] == []
    assert payload["source_provider_status_json"] == {}
    assert payload["created_by_user_uuid"] is None


def test_find_entry_by_word_and_part_of_speech_returns_normalized_match() -> None:
    row = make_user_entry()
    repository = UserDictionaryRepository(FakeSessionManager(FakeSession(scalar_values_sequence=[row, None])))

    assert repository.find_entry_by_word_and_part_of_speech(" Extension   Cord ", "Noun")["id"] == 7
    assert repository.find_entry_by_word_and_part_of_speech("missing", "noun") is None


def test_create_entry_normalizes_part_of_speech_and_entry_type() -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    session = FakeSession()
    repository = UserDictionaryRepository(FakeSessionManager(session))

    payload = repository.create_entry(
        word="Look after",
        part_of_speech="verb pattern",
        created_by_user_uuid=user_uuid,
        translation_uk="піклуватися",
        current_time=current_time,
    )

    row = session.added[0]
    assert payload["id"] == 100
    assert row.normalized_word == "look after"
    assert row.part_of_speech == "phrase pattern"
    assert row.entry_type == "phrase_pattern"
    assert row.entry_key == "user__look-after__phrase-pattern"
    assert row.created_by_user_uuid == user_uuid


def test_create_assignment_inserts_or_updates_existing_assignment() -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    existing = make_assignment(status="waiting_for_entry")
    session = FakeSession(scalar_values_sequence=[None, existing])
    repository = UserDictionaryRepository(FakeSessionManager(session))

    created = repository.create_assignment(
        user_uuid=user_uuid,
        word_source=USER_WORD_SOURCE_USER,
        word_id=7,
        import_job_id=3,
        import_item_id=4,
        current_time=current_time,
    )
    updated = repository.create_assignment(
        user_uuid=user_uuid,
        word_source=USER_WORD_SOURCE_USER,
        word_id=7,
        status=USER_WORD_ASSIGNMENT_AVAILABLE,
        current_time=current_time,
    )

    assert created["id"] == 100
    assert session.added[0].user_uuid == user_uuid
    assert session.added[0].word_source == "user"
    assert session.added[0].import_job_id == 3
    assert created["priority_rank"] == priority_rank_from_datetime(current_time)
    assert created["priority_state"] == "pending"
    assert updated["id"] == 9
    assert existing.status == "available_for_rotation"
    assert existing.is_known is False
    assert existing.learning_state == USER_WORD_LEARNING
    assert existing.priority_rank == priority_rank_from_datetime(current_time)
    assert existing.priority_state == "pending"
    assert existing.updated == current_time


def test_list_assigned_lookup_words_for_user_merges_core_and_user_words() -> None:
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    session = FakeSession(
        execute_rows_sequence=[
            [("APPLE", "Apple"), (None, "Look after")],
            [("extension cord", "Extension cord")],
        ]
    )
    repository = UserDictionaryRepository(FakeSessionManager(session))

    assert repository.list_assigned_lookup_words_for_user(user_uuid) == {
        "apple",
        "look after",
        "extension cord",
    }


def test_create_assignment_requeues_learned_assignment_without_resurrecting_hidden() -> None:
    current_time = datetime(2026, 5, 3, 11, 0, 0)
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    learned = make_assignment(
        status=USER_WORD_ASSIGNMENT_AVAILABLE,
        is_known=True,
        learning_state=USER_WORD_LEARNED,
        priority_rank=1,
    )
    hidden = make_assignment(
        status=USER_WORD_ASSIGNMENT_HIDDEN,
        is_known=True,
        learning_state=USER_WORD_LEARNED,
        priority_rank=1,
    )
    repository = UserDictionaryRepository(FakeSessionManager(FakeSession(scalar_values_sequence=[learned, hidden])))

    learned_payload = repository.create_assignment(
        user_uuid=user_uuid,
        word_source=USER_WORD_SOURCE_USER,
        word_id=7,
        current_time=current_time,
    )
    hidden_payload = repository.create_assignment(
        user_uuid=user_uuid,
        word_source=USER_WORD_SOURCE_USER,
        word_id=7,
        current_time=current_time,
    )

    assert learned_payload["learning_state"] == USER_WORD_LEARNING
    assert learned.is_known is False
    assert learned.learning_state == USER_WORD_LEARNING
    assert learned.priority_rank == priority_rank_from_datetime(current_time)
    assert learned.priority_state == "pending"
    assert hidden_payload["status"] == USER_WORD_ASSIGNMENT_HIDDEN
    assert hidden.status == USER_WORD_ASSIGNMENT_HIDDEN
    assert hidden.is_known is True
    assert hidden.learning_state == USER_WORD_LEARNED
    assert hidden.priority_rank == priority_rank_from_datetime(current_time)


def test_update_entry_details_keeps_audio_when_spelling_is_unchanged(tmp_path: Path) -> None:
    audio_file = tmp_path / "word_base/user/noun/extension-cord.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"audio")
    audio_storage_provider = FileSystemAudioStorageProvider(project_root=tmp_path)
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    row = make_user_entry(
        audio_path="word_base/user/noun/extension-cord.mp3",
        embedding=[0.1, 0.2],
        embedding_model="model",
        is_embedding_ready=True,
        status=USER_DICTIONARY_READY,
    )
    repository = UserDictionaryRepository(FakeSessionManager(FakeSession(row_by_id={7: row})))

    payload = repository.update_entry_details(
        7,
        word="extension cord",
        entry_type="word",
        part_of_speech="noun",
        level_id=2,
        transcription="/cord/",
        translation_uk="новий переклад",
        translation_ru="удлинитель",
        translation_pl="przedłużacz",
        examples_json=["The extension cord reached behind the heavy desk."],
        source_provider_status_json={"details": "ok"},
        status=USER_DICTIONARY_READY,
        audio_storage_provider=audio_storage_provider,
        audio_roots=[tmp_path / "word_base/user"],
        current_time=current_time,
    )

    assert payload is not None
    assert row.audio_path == "word_base/user/noun/extension-cord.mp3"
    assert audio_file.exists()
    assert row.status == USER_DICTIONARY_READY
    assert row.embedding is None
    assert row.is_embedding_ready is False


def test_update_entry_details_invalidates_audio_when_spelling_changes(tmp_path: Path) -> None:
    audio_file = tmp_path / "word_base/user/noun/extension-cord.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"audio")
    audio_storage_provider = FileSystemAudioStorageProvider(project_root=tmp_path)
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    row = make_user_entry(
        audio_path="word_base/user/noun/extension-cord.mp3",
        embedding=[0.1, 0.2],
        embedding_model="model",
        is_embedding_ready=True,
        status=USER_DICTIONARY_READY,
    )
    repository = UserDictionaryRepository(FakeSessionManager(FakeSession(row_by_id={7: row})))

    payload = repository.update_entry_details(
        7,
        word="power cord",
        entry_type="word",
        part_of_speech="noun",
        level_id=2,
        transcription="/cord/",
        translation_uk="кабель живлення",
        translation_ru="кабель питания",
        translation_pl="przewód zasilający",
        examples_json=["The power cord reached behind the heavy desk."],
        source_provider_status_json={"details": "ok"},
        status=USER_DICTIONARY_READY,
        audio_storage_provider=audio_storage_provider,
        audio_roots=[tmp_path / "word_base/user"],
        current_time=current_time,
    )

    assert payload is not None
    assert row.word == "power cord"
    assert row.normalized_word == "power cord"
    assert row.audio_path is None
    assert not audio_file.exists()
    assert row.status == USER_DICTIONARY_QUEUED_AUDIO
    assert row.embedding is None
    assert row.embedding_model is None
    assert row.is_embedding_ready is False


def test_promote_entry_to_core_moves_user_references_and_deletes_user_entry(monkeypatch) -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    user_entry = make_user_entry()
    core_entry = make_core_entry()
    assignment = make_assignment(
        import_job_id=3,
        import_item_id=4,
        learning_state="needs_work",
        control_success_streak=2,
        review_priority=9,
    )
    session_word = LearningSessionWord(
        id=13,
        session_id=20,
        word_source="user",
        word_id=7,
        item_order=1,
        card_status="next",
        en_uk_attempts=2,
        en_uk_correct=True,
    )
    import_item = UserVocabularyImportItem(
        id=31,
        user_uuid=UUID("11111111-1111-4111-8111-111111111111"),
        import_job_id=30,
        raw_value="extension cord",
        lookup_word="extension cord",
        user_dictionary_entry_id=7,
        status="ready_for_rotation",
        created=current_time,
        updated=current_time,
    )
    session = FakeSession(
        row_by_id={7: user_entry},
        scalar_values_sequence=[core_entry, SimpleNamespace(id=5, code="noun", title="noun"), None, None],
        scalars_rows_sequence=[[assignment], [session_word], [import_item]],
    )
    monkeypatch.setattr("app.data_access.user_dictionary_promotion.load_dictionary_entry_metadata", lambda *_: {})
    repository = UserDictionaryRepository(FakeSessionManager(session))

    payload = repository.promote_entry_to_core(7, audio_path="word_base/base/noun/extension-cord.mp3", current_time=current_time)

    assert payload["id"] == 77
    assert assignment.word_source == "core"
    assert assignment.word_id == 77
    assert assignment.review_priority == 9
    assert assignment.learning_state == "needs_work"
    assert session_word.word_source == "core"
    assert session_word.word_id == 77
    assert session_word.en_uk_attempts == 2
    assert import_item.existing_word_id == 77
    assert import_item.user_dictionary_entry_id is None
    assert user_entry in session.deleted


def test_promote_entry_to_core_keeps_suppressed_core_assignment_status(monkeypatch) -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    user_entry = make_user_entry()
    core_entry = make_core_entry()
    assignment = make_assignment(
        status=USER_WORD_ASSIGNMENT_AVAILABLE,
        priority_rank=priority_rank_from_datetime(current_time),
        learning_state=USER_WORD_NEEDS_WORK,
    )
    existing = make_assignment(
        id=10,
        word_source="core",
        word_id=77,
        status=USER_WORD_ASSIGNMENT_HIDDEN,
        priority_rank=1,
        learning_state=USER_WORD_LEARNING,
    )
    session = FakeSession(
        row_by_id={7: user_entry},
        scalar_values_sequence=[core_entry, SimpleNamespace(id=5, code="noun", title="noun"), existing],
        scalars_rows_sequence=[[assignment], [], []],
    )
    monkeypatch.setattr("app.data_access.user_dictionary_promotion.load_dictionary_entry_metadata", lambda *_: {})
    repository = UserDictionaryRepository(FakeSessionManager(session))

    payload = repository.promote_entry_to_core(7, audio_path="word_base/base/noun/extension-cord.mp3", current_time=current_time)

    assert payload["id"] == 77
    assert existing.status == USER_WORD_ASSIGNMENT_HIDDEN
    assert existing.priority_rank == priority_rank_from_datetime(current_time)
    assert existing.learning_state == USER_WORD_NEEDS_WORK
    assert assignment in session.deleted


def test_promote_entry_to_core_requires_part_of_speech() -> None:
    current_time = datetime(2026, 5, 3, 10, 0, 0)
    session = FakeSession(row_by_id={7: make_user_entry(part_of_speech="")})
    repository = UserDictionaryRepository(FakeSessionManager(session))

    try:
        repository.promote_entry_to_core(7, audio_path="word_base/base/noun/extension-cord.mp3", current_time=current_time)
    except ValueError as error:
        assert "part_of_speech is required" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_normalize_user_word_source_rejects_unknown_source() -> None:
    assert normalize_user_word_source(" User ") == "user"
    try:
        normalize_user_word_source("pending")
    except ValueError as error:
        assert "word_source must be one of" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")
