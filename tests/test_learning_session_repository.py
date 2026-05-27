from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from app.data_access.learning_sessions import (
    LearningSessionRepository,
    learning_session_to_dict,
    session_word_from_dictionary_entry,
    session_word_to_dict,
)
from app.models import (
    DictionaryEntry,
    LearningAnswer,
    LearningSession,
    LearningSessionWord,
    User,
    UserWordAssignment,
)

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


class FakeResult:
    def __init__(self, rows=None, one_row=None) -> None:
        self.rows = list(rows or [])
        self.one_row = one_row

    def all(self):
        return list(self.rows)

    def one(self):
        return self.one_row


class FakeSession:
    def __init__(
        self,
        *,
        row_by_key=None,
        scalar_values=None,
        scalars_results=None,
        execute_results=None,
        refresh_words=None,
    ) -> None:
        self.row_by_key = row_by_key or {}
        self.scalar_values = list(scalar_values or [])
        self.scalars_results = list(scalars_results or [])
        self.execute_results = list(execute_results or [])
        self.refresh_words = refresh_words or {}
        self.added = []

    def get(self, model, primary_key):
        return self.row_by_key.get((model, primary_key))

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        return FakeResult(self.scalars_results.pop(0) if self.scalars_results else [])

    def execute(self, statement):
        return self.execute_results.pop(0)

    def add(self, row) -> None:
        if isinstance(row, LearningSession) and row.id is None:
            row.id = 700 + len([item for item in self.added if isinstance(item, LearningSession)])
        if isinstance(row, LearningSessionWord) and row.id is None:
            row.id = 800 + len([item for item in self.added if isinstance(item, LearningSessionWord)])
        if isinstance(row, LearningSessionWord) and row.word_id in self.refresh_words:
            row.word = self.refresh_words[row.word_id]
        self.added.append(row)

    def flush(self) -> None:
        return None

    def refresh(self, row) -> None:
        if isinstance(row, LearningSessionWord) and row.word_id in self.refresh_words:
            row.word = self.refresh_words[row.word_id]


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_session(**overrides) -> LearningSession:
    now = datetime(2026, 4, 8, 10, 0, 0)
    values = {
        "id": 77,
        "user_uuid": USER_UUID,
        "language_level_id": 2,
        "level_run_id": 5,
        "source_session_id": None,
        "session_type": "regular",
        "words_target_count": 10,
        "status": "active",
        "current_stage": "card",
        "stage_queue_json": [11],
        "stage_position": 0,
        "created": now,
        "updated": now,
        "completed": None,
    }
    values.update(overrides)
    return LearningSession(**values)


def make_entry(**overrides) -> DictionaryEntry:
    values = {
        "id": 101,
        "source_namespace": "core",
        "source_ref": "core:learn",
        "entry_key": "learn__verb__entry",
        "word": "learn",
        "normalized_word": "learn",
        "level_id": 2,
        "transcription": "/lɜːrn/",
        "translation_uk": "вивчати",
        "translation_ru": "учить",
        "translation_pl": "uczyc sie",
        "audio_path": "word_base/word_audio/learn.mp3",
        "examples_json": ["We learn."],
        "entry_type": "word",
    }
    values.update(overrides)
    return DictionaryEntry(**values)


def make_session_word(**overrides) -> LearningSessionWord:
    entry = overrides.pop("word", None) or make_entry()
    values = {
        "id": 11,
        "session_id": 77,
        "word_source": "core",
        "word_id": entry.id,
        "item_order": 1,
        "card_status": "pending",
        "en_uk_attempts": 0,
        "en_uk_correct": False,
        "uk_en_attempts": 0,
        "uk_en_correct": False,
        "gap_attempts": 0,
        "gap_correct": False,
    }
    values.update(overrides)
    row = LearningSessionWord(**values)
    row.word = entry
    return row


def test_learning_session_to_dict_preserves_contract_shape() -> None:
    payload = learning_session_to_dict(make_session(stage_queue_json=None))

    assert payload["id"] == 77
    assert payload["stage_queue_json"] == []
    assert payload["current_stage"] == "card"
    assert payload["session_words_count"] is None


def test_session_word_serializers_preserve_fallback_and_metadata_shapes() -> None:
    row = make_session_word()

    fallback = session_word_to_dict(row)
    enriched = session_word_from_dictionary_entry(
        row,
        row.word,
        metadata={"parts_of_speech": ["verb"], "categories": ["study"]},
    )

    assert fallback["parts_of_speech"] == []
    assert enriched["part_of_speech"] == "verb"
    assert enriched["categories"] == ["study"]


def test_get_active_and_get_session_return_serialized_rows_or_none() -> None:
    active = make_session(id=88)
    stored = make_session(id=99)
    repository = LearningSessionRepository(
        FakeSessionManager(
            FakeSession(
                scalar_values=[active, 2, 3],
                row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42), (LearningSession, 99): stored},
            )
        )
    )

    active_payload = repository.get_active_session(42)
    assert active_payload["id"] == 88
    assert active_payload["session_words_count"] == 2
    assert repository.get_active_session(404) is None
    stored_payload = repository.get_session(99)
    assert stored_payload["id"] == 99
    assert stored_payload["session_words_count"] == 3
    assert repository.get_session(404) is None


def test_get_and_claim_resumable_session_include_completed_summary_rows() -> None:
    completed = make_session(id=88, status="completed", current_stage="completed", active_interface="telegram_user")
    repository = LearningSessionRepository(
        FakeSessionManager(
            FakeSession(
                row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
                scalar_values=[completed, 2, completed, 2],
            )
        )
    )

    resumable_payload = repository.get_resumable_session(42)
    claimed_payload = repository.claim_resumable_session(42, "client_web")

    assert resumable_payload["id"] == 88
    assert resumable_payload["status"] == "completed"
    assert resumable_payload["session_words_count"] == 2
    assert claimed_payload["id"] == 88
    assert claimed_payload["active_interface"] == "client_web"
    assert completed.active_interface == "client_web"


def test_resumable_session_does_not_fall_back_to_older_learning_rows() -> None:
    finished = make_session(id=99, status="completed", current_stage="finished", active_interface="client_web")
    older_completed = make_session(id=88, status="completed", current_stage="completed", active_interface="telegram_user")
    repository = LearningSessionRepository(
        FakeSessionManager(
            FakeSession(
                row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
                scalar_values=[finished, finished],
            )
        )
    )

    assert repository.get_resumable_session(42) is None
    assert repository.claim_resumable_session(42, "client_web") is None
    assert older_completed.active_interface == "telegram_user"


def test_finish_completed_summary_removes_session_from_resumable_stage() -> None:
    completed = make_session(id=88, status="completed", current_stage="completed", active_interface="client_web")
    repository = LearningSessionRepository(FakeSessionManager(FakeSession(row_by_key={(LearningSession, 88): completed})))

    repository.finish_completed_summary(88)
    repository.finish_completed_summary(404)

    assert completed.status == "completed"
    assert completed.current_stage == "finished"
    assert completed.completed is not None


def test_cancel_active_sessions_marks_all_returned_rows_cancelled() -> None:
    rows = [make_session(id=1), make_session(id=2)]
    repository = LearningSessionRepository(
        FakeSessionManager(FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)}, scalars_results=[rows]))
    )

    repository.cancel_active_sessions(42)

    assert [row.status for row in rows] == ["cancelled", "cancelled"]
    assert all(row.completed is not None for row in rows)


def test_create_session_adds_session_and_ordered_words() -> None:
    session = FakeSession(row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)})
    repository = LearningSessionRepository(FakeSessionManager(session))

    payload = repository.create_session(
        telegram_user_id=42,
        level_id=2,
        level_run_id=5,
        words_target_count=2,
        words=[{"id": 101}, {"id": 102}],
        session_type="followup",
        source_session_id=77,
    )

    assert payload["id"] == 700
    assert payload["current_stage"] == "card"
    assert payload["session_words_count"] == 2
    added_words = [row for row in session.added if isinstance(row, LearningSessionWord)]
    assert [row.word_id for row in added_words] == [101, 102]
    assert [row.item_order for row in added_words] == [1, 2]


def test_create_regular_session_marks_selected_assignments_seen_and_introduced(monkeypatch) -> None:
    current_time = datetime(2026, 5, 11, 12, 0, 0)
    priority_assignment = UserWordAssignment(
        user_uuid=USER_UUID,
        word_source="core",
        word_id=101,
        status="available_for_rotation",
        priority_rank=1777390200,
        priority_state="pending",
        learning_state="learning",
        is_known=False,
        review_priority=0,
    )
    regular_assignment = UserWordAssignment(
        user_uuid=USER_UUID,
        word_source="user",
        word_id=88,
        status="available_for_rotation",
        priority_rank=0,
        priority_state="none",
        learning_state="learning",
        is_known=False,
        review_priority=0,
    )
    session = FakeSession(
        row_by_key={(User, 42): User(uuid=USER_UUID, telegram_user_id=42)},
        scalars_results=[[priority_assignment, regular_assignment]],
    )
    monkeypatch.setattr("app.data_access.learning_sessions._current_datetime", lambda: current_time)
    repository = LearningSessionRepository(FakeSessionManager(session))

    repository.create_session(
        telegram_user_id=42,
        level_id=2,
        level_run_id=5,
        words_target_count=2,
        words=[
            {"id": 101, "word_source": "core", "word_id": 101},
            {"id": 88, "word_source": "user", "word_id": 88},
        ],
    )

    assert priority_assignment.last_seen_at == current_time
    assert priority_assignment.priority_state == "introduced"
    assert priority_assignment.updated == current_time
    assert regular_assignment.last_seen_at == current_time
    assert regular_assignment.priority_state == "none"


def test_get_session_words_uses_dictionary_entries_and_metadata(monkeypatch) -> None:
    entry = make_entry()
    row = make_session_word(word=entry)
    fallback_entry = make_entry(id=102, word="fallback", normalized_word="fallback", entry_key="fallback__verb__entry")
    fallback_row = make_session_word(id=12, word=fallback_entry)
    session = FakeSession(scalars_results=[[row, fallback_row], [entry]])
    monkeypatch.setattr(
        "app.data_access.learning_sessions.load_dictionary_entry_metadata",
        lambda received_session, entry_ids: {101: {"parts_of_speech": ["verb"], "categories": ["study"]}},
    )
    repository = LearningSessionRepository(FakeSessionManager(session))

    payload = repository.get_session_words(77)

    assert payload[0]["word"] == "learn"
    assert payload[0]["parts_of_speech"] == ["verb"]
    assert payload[0]["categories"] == ["study"]
    assert payload[1]["word"] == "fallback"
    assert payload[1]["parts_of_speech"] == []


def test_get_session_word_handles_missing_row_and_missing_dictionary_entry(monkeypatch) -> None:
    row = make_session_word()
    session = FakeSession(row_by_key={(LearningSessionWord, 11): row, (DictionaryEntry, 101): None})
    repository = LearningSessionRepository(FakeSessionManager(session))

    assert repository.get_session_word(404) is None
    assert repository.get_session_word(11)["word"] == "learn"

    session.row_by_key[(DictionaryEntry, 101)] = row.word
    monkeypatch.setattr(
        "app.data_access.learning_sessions.load_dictionary_entry_metadata",
        lambda received_session, entry_ids: {101: {"parts_of_speech": ["verb"], "categories": []}},
    )

    assert repository.get_session_word(11)["part_of_speech"] == "verb"


def test_update_session_state_and_card_status_ignore_missing_rows() -> None:
    session_row = make_session()
    word_row = make_session_word()
    repository = LearningSessionRepository(
        FakeSessionManager(
            FakeSession(
                row_by_key={
                    (LearningSession, 77): session_row,
                    (LearningSessionWord, 11): word_row,
                }
            )
        )
    )

    repository.update_session_state(77, "quiz", [11, 12], 1)
    repository.update_session_state(404, "ignored", [], 0)
    repository.set_card_status(11, "known")
    repository.set_card_status(404, "known")

    assert session_row.current_stage == "quiz"
    assert session_row.stage_queue_json == [11, 12]
    assert session_row.stage_position == 1
    assert word_row.card_status == "known"


def test_append_and_replace_session_word_return_serialized_rows() -> None:
    old_entry = make_entry(id=101, word="old")
    new_entry = make_entry(id=102, word="new", normalized_word="new", entry_key="new__verb__entry")
    row = make_session_word(
        word=old_entry,
        en_uk_attempts=2,
        en_uk_correct=True,
        uk_en_attempts=2,
        uk_en_correct=True,
        gap_attempts=1,
        gap_correct=True,
        card_status="known",
    )
    session = FakeSession(
        row_by_key={(LearningSessionWord, 11): row},
        scalar_values=[3],
        refresh_words={102: new_entry, 103: make_entry(id=103, word="extra", normalized_word="extra", entry_key="extra__verb__entry")},
    )
    repository = LearningSessionRepository(FakeSessionManager(session))

    appended = repository.append_session_word(77, 103)
    replaced = repository.replace_session_word(11, 102)

    assert appended["item_order"] == 4
    assert replaced["word"] == "new"
    assert row.card_status == "pending"
    assert row.en_uk_attempts == 0
    assert row.en_uk_correct is False
    assert repository.replace_session_word(404, 102) is None


def test_record_answer_and_update_exercise_result() -> None:
    row = make_session_word()
    session = FakeSession(row_by_key={(LearningSessionWord, 11): row})
    repository = LearningSessionRepository(FakeSessionManager(session))

    repository.record_answer(
        session_id=77,
        session_word_id=11,
        exercise_type="en_uk",
        prompt_text="learn",
        correct_answer="вивчати",
        user_answer="вивчати",
        is_correct=True,
        attempt_no=1,
    )
    repository.update_exercise_result(11, "en_uk", 1, True)
    repository.update_exercise_result(404, "gap", 2, False)

    assert isinstance(session.added[0], LearningAnswer)
    assert session.added[0].correct_answer == "вивчати"
    assert row.en_uk_attempts == 1
    assert row.en_uk_correct is True


def test_complete_session_and_summary_stats() -> None:
    row = make_session(status="active", current_stage="summary")
    session = FakeSession(
        row_by_key={(LearningSession, 77): row},
        execute_results=[
            FakeResult(one_row=(2, 3)),
            FakeResult(one_row=(1, 3)),
            FakeResult(one_row=(0, 3)),
        ],
    )
    repository = LearningSessionRepository(FakeSessionManager(session))

    repository.complete_session(77)
    repository.complete_session(404)
    payload = repository.get_summary_stats(77)

    assert row.status == "completed"
    assert row.current_stage == "completed"
    assert row.completed is not None
    assert payload == [
        {"exercise_type": "en_uk", "correct_count": 2, "total_count": 3},
        {"exercise_type": "uk_en", "correct_count": 1, "total_count": 3},
        {"exercise_type": "gap", "correct_count": 0, "total_count": 3},
    ]
