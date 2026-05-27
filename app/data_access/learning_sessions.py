from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select

from app.data_access.dictionary_publish import load_dictionary_entry_metadata
from app.data_access.serialization import normalize_examples_json
from app.data_access.user_dictionary import (
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
    user_dictionary_entry_to_lesson_word,
)
from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_PRIORITY_INTRODUCED,
    USER_WORD_PRIORITY_PENDING,
)
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import (
    DictionaryEntry,
    LearningAnswer,
    LearningSession,
    LearningSessionWord,
    UserDictionaryEntry,
    UserWordAssignment,
)
from app.orm import SessionManager
from app.reference.dictionary_entries import normalize_dictionary_entry_type


def learning_session_to_dict(session: LearningSession, *, session_words_count: int | None = None) -> dict[str, Any]:
    return {
        "id": session.id,
        "user_id": str(session.user_uuid),
        "user_uuid": str(session.user_uuid),
        "language_level_id": session.language_level_id,
        "level_run_id": session.level_run_id,
        "source_session_id": session.source_session_id,
        "session_type": session.session_type,
        "words_target_count": session.words_target_count,
        "status": session.status,
        "current_stage": session.current_stage,
        "stage_queue_json": session.stage_queue_json or [],
        "stage_position": session.stage_position,
        "active_interface": session.active_interface,
        "interface_revision": session.interface_revision,
        "created": session.created,
        "updated": session.updated,
        "completed": session.completed,
        "session_words_count": session_words_count,
    }


def session_word_to_dict(row: LearningSessionWord) -> dict[str, Any]:
    entry = row.word
    if entry is None:
        return {
            "session_word_id": row.id,
            "session_id": row.session_id,
            "word_source": row.word_source,
            "word_id": row.word_id,
            "id": row.word_id,
            "item_order": row.item_order,
            "card_status": row.card_status,
            "en_uk_attempts": row.en_uk_attempts,
            "en_uk_correct": row.en_uk_correct,
            "uk_en_attempts": row.uk_en_attempts,
            "uk_en_correct": row.uk_en_correct,
            "gap_attempts": row.gap_attempts,
            "gap_correct": row.gap_correct,
            "word": "",
            "part_of_speech": "",
            "parts_of_speech": [],
            "categories": [],
            "phonetic_us": None,
            "audio_path": None,
            "examples_json": [],
            "level_id": None,
            "entry_type": "word",
            "translation_uk": None,
            "translation_ru": None,
            "translation_pl": None,
        }
    examples_json = normalize_examples_json(entry.examples_json)
    return {
        "session_word_id": row.id,
        "session_id": row.session_id,
        "word_source": row.word_source or USER_WORD_SOURCE_CORE,
        "word_id": row.word_id,
        "id": row.word_id,
        "item_order": row.item_order,
        "card_status": row.card_status,
        "en_uk_attempts": row.en_uk_attempts,
        "en_uk_correct": row.en_uk_correct,
        "uk_en_attempts": row.uk_en_attempts,
        "uk_en_correct": row.uk_en_correct,
        "gap_attempts": row.gap_attempts,
        "gap_correct": row.gap_correct,
        "word": entry.word,
        "part_of_speech": "",
        "parts_of_speech": [],
        "categories": [],
        "phonetic_us": entry.transcription,
        "audio_path": entry.audio_path,
        "examples_json": examples_json,
        "level_id": entry.level_id,
        "entry_type": normalize_dictionary_entry_type(entry.entry_type or "word"),
        "translation_uk": entry.translation_uk,
        "translation_ru": entry.translation_ru,
        "translation_pl": entry.translation_pl,
    }


def session_word_from_dictionary_entry(
    row: LearningSessionWord,
    entry: DictionaryEntry,
    *,
    metadata: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    resolved_metadata = metadata or {"parts_of_speech": [], "categories": []}
    return {
        "session_word_id": row.id,
        "session_id": row.session_id,
        "word_source": row.word_source or USER_WORD_SOURCE_CORE,
        "word_id": row.word_id,
        "id": row.word_id,
        "item_order": row.item_order,
        "card_status": row.card_status,
        "en_uk_attempts": row.en_uk_attempts,
        "en_uk_correct": row.en_uk_correct,
        "uk_en_attempts": row.uk_en_attempts,
        "uk_en_correct": row.uk_en_correct,
        "gap_attempts": row.gap_attempts,
        "gap_correct": row.gap_correct,
        "word": entry.word,
        "part_of_speech": ", ".join(resolved_metadata.get("parts_of_speech", [])),
        "parts_of_speech": list(resolved_metadata.get("parts_of_speech", [])),
        "categories": list(resolved_metadata.get("categories", [])),
        "phonetic_us": entry.transcription,
        "audio_path": entry.audio_path,
        "examples_json": normalize_examples_json(entry.examples_json),
        "level_id": entry.level_id,
        "entry_type": normalize_dictionary_entry_type(entry.entry_type or "word"),
        "translation_uk": entry.translation_uk,
        "translation_ru": entry.translation_ru,
        "translation_pl": entry.translation_pl,
    }


def session_word_from_user_dictionary_entry(
    row: LearningSessionWord,
    entry: UserDictionaryEntry,
) -> dict[str, Any]:
    return {
        **user_dictionary_entry_to_lesson_word(entry),
        "session_word_id": row.id,
        "session_id": row.session_id,
        "item_order": row.item_order,
        "card_status": row.card_status,
        "en_uk_attempts": row.en_uk_attempts,
        "en_uk_correct": row.en_uk_correct,
        "uk_en_attempts": row.uk_en_attempts,
        "uk_en_correct": row.uk_en_correct,
        "gap_attempts": row.gap_attempts,
        "gap_correct": row.gap_correct,
    }


def _current_datetime() -> datetime:
    return datetime.now(datetime.now().astimezone().tzinfo)


class LearningSessionRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            row = session.scalar(
                select(LearningSession)
                .where(
                    LearningSession.user_uuid == user_uuid,
                    LearningSession.status == "active",
                )
                .order_by(LearningSession.created.desc())
                .limit(1)
            )
            return self._serialize_session_with_word_count(session, row)

    def get_resumable_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            row = session.scalar(
                select(LearningSession)
                .where(
                    LearningSession.user_uuid == user_uuid,
                )
                .order_by(LearningSession.created.desc())
                .limit(1)
            )
            if not self._is_resumable_session(row):
                return None
            return self._serialize_session_with_word_count(session, row)

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(LearningSession, session_id)
            return self._serialize_session_with_word_count(session, row)

    def cancel_active_sessions(self, telegram_user_id: int) -> None:
        now = _current_datetime()
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return
            sessions = session.scalars(
                select(LearningSession).where(
                    LearningSession.user_uuid == user_uuid,
                    LearningSession.status == "active",
                )
            ).all()
            for item in sessions:
                item.status = "cancelled"
                item.completed = now

    def create_session(
        self,
        telegram_user_id: int,
        level_id: int,
        level_run_id: int | None,
        words_target_count: int,
        words: list[dict[str, Any]],
        *,
        session_type: str = "regular",
        source_session_id: int | None = None,
        active_interface: str = "telegram_user",
    ) -> dict[str, Any]:
        now = _current_datetime()
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            item = LearningSession(
                user_uuid=user_uuid,
                language_level_id=level_id,
                level_run_id=level_run_id,
                source_session_id=source_session_id,
                session_type=session_type,
                words_target_count=words_target_count,
                current_stage="card",
                stage_queue_json=[],
                stage_position=0,
                active_interface=active_interface,
                interface_revision=0,
            )
            session.add(item)
            session.flush()
            for item_order, word in enumerate(words, start=1):
                session.add(
                    LearningSessionWord(
                        session_id=item.id,
                        word_source=word.get("word_source", USER_WORD_SOURCE_CORE),
                        word_id=word["id"],
                        item_order=item_order,
                    )
                )
            self._mark_session_words_seen(
                session,
                user_uuid,
                words,
                current_time=now,
                is_regular_session=session_type == "regular",
            )
            session.flush()
            return learning_session_to_dict(item, session_words_count=len(words))

    def _mark_session_words_seen(
        self,
        session,
        user_uuid,
        words: list[dict[str, Any]],
        *,
        current_time: datetime,
        is_regular_session: bool,
    ) -> None:
        filters = []
        for word in words:
            word_source = str(word.get("word_source") or USER_WORD_SOURCE_CORE)
            word_id = int(word.get("word_id") or word["id"])
            filters.append(
                and_(
                    UserWordAssignment.word_source == word_source,
                    UserWordAssignment.word_id == word_id,
                )
            )
        if not filters:
            return
        assignments = session.scalars(
            select(UserWordAssignment).where(
                UserWordAssignment.user_uuid == user_uuid,
                UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                or_(*filters),
            )
        ).all()
        for assignment in assignments:
            assignment.last_seen_at = current_time
            if is_regular_session and assignment.priority_state == USER_WORD_PRIORITY_PENDING:
                assignment.priority_state = USER_WORD_PRIORITY_INTRODUCED
            assignment.updated = current_time

    def get_session_words(self, session_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(LearningSessionWord)
                .where(LearningSessionWord.session_id == session_id)
                .order_by(LearningSessionWord.item_order)
            ).all()
            core_entry_ids = [int(row.word_id) for row in rows if row.word_source == USER_WORD_SOURCE_CORE]
            user_entry_ids = [int(row.word_id) for row in rows if row.word_source == USER_WORD_SOURCE_USER]
            entries = session.scalars(select(DictionaryEntry).where(DictionaryEntry.id.in_(core_entry_ids or [-1]))).all()
            user_entries = session.scalars(
                select(UserDictionaryEntry).where(UserDictionaryEntry.id.in_(user_entry_ids or [-1]))
            ).all()
            entries_by_id = {int(entry.id): entry for entry in entries}
            user_entries_by_id = {int(entry.id): entry for entry in user_entries}
            metadata_by_id = load_dictionary_entry_metadata(session, core_entry_ids)
            payload: list[dict[str, Any]] = []
            for row in rows:
                if row.word_source == USER_WORD_SOURCE_USER:
                    user_entry = user_entries_by_id.get(int(row.word_id))
                    if user_entry is not None:
                        payload.append(session_word_from_user_dictionary_entry(row, user_entry))
                        continue
                    payload.append(session_word_to_dict(row))
                    continue
                entry = entries_by_id.get(int(row.word_id))
                if entry is not None:
                    payload.append(
                        session_word_from_dictionary_entry(
                            row,
                            entry,
                            metadata=metadata_by_id.get(int(entry.id)),
                        )
                    )
                    continue
                payload.append(session_word_to_dict(row))
            return payload

    def get_session_word(self, session_word_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(LearningSessionWord, session_word_id)
            if row is None:
                return None
            if row.word_source == USER_WORD_SOURCE_USER:
                user_entry = session.get(UserDictionaryEntry, row.word_id)
                if user_entry is None:
                    return session_word_to_dict(row)
                return session_word_from_user_dictionary_entry(row, user_entry)
            entry = session.get(DictionaryEntry, row.word_id)
            if entry is None:
                return session_word_to_dict(row)
            metadata_by_id = load_dictionary_entry_metadata(session, [int(entry.id)])
            return session_word_from_dictionary_entry(
                row,
                entry,
                metadata=metadata_by_id.get(int(entry.id)),
            )

    def update_session_state(
        self,
        session_id: int,
        current_stage: str,
        stage_queue: list[int],
        stage_position: int,
    ) -> None:
        with self.session_manager.session() as session:
            item = session.get(LearningSession, session_id)
            if item is None:
                return
            item.current_stage = current_stage
            item.stage_queue_json = list(stage_queue)
            item.stage_position = stage_position
            item.updated = _current_datetime()

    def claim_active_session(self, telegram_user_id: int, active_interface: str) -> dict[str, Any] | None:
        now = _current_datetime()
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            item = session.scalar(
                select(LearningSession)
                .where(
                    LearningSession.user_uuid == user_uuid,
                    LearningSession.status == "active",
                )
                .order_by(LearningSession.created.desc())
                .limit(1)
            )
            if item is None:
                return None
            item.active_interface = active_interface
            item.interface_revision = int(item.interface_revision or 0) + 1
            item.updated = now
            session.flush()
            return self._serialize_session_with_word_count(session, item)

    def claim_resumable_session(self, telegram_user_id: int, active_interface: str) -> dict[str, Any] | None:
        now = _current_datetime()
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            item = session.scalar(
                select(LearningSession)
                .where(
                    LearningSession.user_uuid == user_uuid,
                )
                .order_by(LearningSession.created.desc())
                .limit(1)
            )
            if not self._is_resumable_session(item):
                return None
            item.active_interface = active_interface
            item.interface_revision = int(item.interface_revision or 0) + 1
            item.updated = now
            session.flush()
            return self._serialize_session_with_word_count(session, item)

    def _serialize_session_with_word_count(self, session, row: LearningSession | None) -> dict[str, Any] | None:
        if row is None:
            return None
        session_words_count = session.scalar(
            select(func.count(LearningSessionWord.id)).where(LearningSessionWord.session_id == row.id)
        )
        return learning_session_to_dict(row, session_words_count=int(session_words_count or 0))

    def _is_resumable_session(self, row: LearningSession | None) -> bool:
        if row is None:
            return False
        if row.status == "active":
            return True
        return row.status == "completed" and row.current_stage in {"summary", "completed"}

    def set_card_status(self, session_word_id: int, status: str) -> None:
        with self.session_manager.session() as session:
            row = session.get(LearningSessionWord, session_word_id)
            if row is not None:
                row.card_status = status

    def append_session_word(
        self,
        session_id: int,
        word_id: int,
        *,
        word_source: str = USER_WORD_SOURCE_CORE,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            max_item_order = session.scalar(
                select(func.max(LearningSessionWord.item_order)).where(LearningSessionWord.session_id == session_id)
            )
            row = LearningSessionWord(
                session_id=session_id,
                word_source=word_source,
                word_id=word_id,
                item_order=int(max_item_order or 0) + 1,
            )
            session.add(row)
            session.flush()
            if word_source == USER_WORD_SOURCE_USER:
                entry = session.get(UserDictionaryEntry, word_id)
                if entry is not None:
                    return session_word_from_user_dictionary_entry(row, entry)
            return session_word_to_dict(row)

    def replace_session_word(
        self,
        session_word_id: int,
        word_id: int,
        *,
        word_source: str = USER_WORD_SOURCE_CORE,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(LearningSessionWord, session_word_id)
            if row is None:
                return None
            row.word_source = word_source
            row.word_id = word_id
            row.card_status = "pending"
            row.en_uk_attempts = 0
            row.en_uk_correct = False
            row.uk_en_attempts = 0
            row.uk_en_correct = False
            row.gap_attempts = 0
            row.gap_correct = False
            session.flush()
            session.refresh(row)
            if row.word_source == USER_WORD_SOURCE_USER:
                entry = session.get(UserDictionaryEntry, row.word_id)
                if entry is not None:
                    return session_word_from_user_dictionary_entry(row, entry)
            return session_word_to_dict(row)

    def record_answer(
        self,
        session_id: int,
        session_word_id: int,
        exercise_type: str,
        prompt_text: str,
        correct_answer: str,
        user_answer: str,
        is_correct: bool,
        attempt_no: int,
    ) -> None:
        with self.session_manager.session() as session:
            session.add(
                LearningAnswer(
                    session_id=session_id,
                    session_word_id=session_word_id,
                    exercise_type=exercise_type,
                    prompt_text=prompt_text,
                    correct_answer=correct_answer,
                    user_answer=user_answer,
                    is_correct=is_correct,
                    attempt_no=attempt_no,
                )
            )

    def update_exercise_result(
        self,
        session_word_id: int,
        exercise_type: str,
        attempts: int,
        is_correct: bool,
    ) -> None:
        with self.session_manager.session() as session:
            row = session.get(LearningSessionWord, session_word_id)
            if row is None:
                return
            setattr(row, f"{exercise_type}_attempts", attempts)
            setattr(row, f"{exercise_type}_correct", is_correct)

    def complete_session(self, session_id: int) -> None:
        now = _current_datetime()
        with self.session_manager.session() as session:
            row = session.get(LearningSession, session_id)
            if row is not None:
                row.status = "completed"
                row.current_stage = "completed"
                row.completed = now

    def finish_completed_summary(self, session_id: int) -> None:
        now = _current_datetime()
        with self.session_manager.session() as session:
            row = session.get(LearningSession, session_id)
            if row is not None and row.status == "completed" and row.current_stage in {"summary", "completed"}:
                row.current_stage = "finished"
                row.updated = now
                if row.completed is None:
                    row.completed = now

    def get_summary_stats(self, session_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            result = []
            for exercise_type, correct_field in (
                ("en_uk", LearningSessionWord.en_uk_correct),
                ("uk_en", LearningSessionWord.uk_en_correct),
                ("gap", LearningSessionWord.gap_correct),
            ):
                correct_count, total_count = session.execute(
                    select(
                        func.count(LearningSessionWord.id).filter(correct_field.is_(True)),
                        func.count(LearningSessionWord.id),
                    ).where(LearningSessionWord.session_id == session_id)
                ).one()
                result.append(
                    {
                        "exercise_type": exercise_type,
                        "correct_count": correct_count or 0,
                        "total_count": total_count or 0,
                    }
                )
            return result
