from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, literal, select, union_all

from app.data_access.dictionary_publish import load_dictionary_entry_metadata
from app.data_access.filtering import normalize_filter_values
from app.data_access.user_dictionary import USER_DICTIONARY_READY
from app.data_access.user_dictionary_assignments import (
    normalize_learning_state,
    user_word_assignment_to_dict,
)
from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_LEARNED,
    USER_WORD_LEARNING,
    USER_WORD_NEEDS_WORK,
    USER_WORD_PRIORITY_CONSUMED,
    USER_WORD_PRIORITY_INTRODUCED,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
)
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import (
    DictionaryCategory,
    DictionaryEntry,
    DictionaryEntryCategory,
    UserDictionaryEntry,
    UserLevelRun,
    UserWordAssignment,
)
from app.models.shared import LanguageLevel
from app.orm import SessionManager


def learning_assignment_to_progress_dict(row: UserWordAssignment) -> dict[str, Any]:
    payload = user_word_assignment_to_dict(row)
    payload["level_run_id"] = row.last_level_run_id
    return payload


def _current_datetime() -> datetime:
    return datetime.now(datetime.now().astimezone().tzinfo)


class LearningProgressRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def update(
        self,
        telegram_user_id: int,
        word_id: int,
        *,
        word_source: str = USER_WORD_SOURCE_CORE,
        level_run_id: int,
        is_known: bool | None = None,
        learning_state: str | None = None,
        control_success_streak: int | None = None,
        review_priority_delta: int = 0,
        review_stage: int | None = None,
        mistake_count_delta: int = 0,
        completed_now: bool = False,
        next_review_at: datetime | None = None,
        last_reviewed_at: datetime | None = None,
        current_time: datetime | None = None,
    ) -> None:
        now = current_time or _current_datetime()
        normalized_source = str(word_source or USER_WORD_SOURCE_CORE).strip().lower()
        if normalized_source not in {USER_WORD_SOURCE_CORE, USER_WORD_SOURCE_USER}:
            raise ValueError("word_source must be one of: core, user")
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            row = self._get_assignment(session, user_uuid, normalized_source, int(word_id))
            if row is None:
                row = UserWordAssignment(
                    user_uuid=user_uuid,
                    word_source=normalized_source,
                    word_id=int(word_id),
                    status=USER_WORD_ASSIGNMENT_AVAILABLE,
                    priority_rank=0,
                    is_known=False,
                    learning_state=USER_WORD_LEARNING,
                    control_success_streak=0,
                    review_priority=0,
                    review_stage=0,
                    mistake_count=0,
                    created=now,
                    updated=now,
                )
                session.add(row)
                session.flush()
            if is_known is not None:
                row.is_known = bool(is_known)
            if learning_state is not None:
                row.learning_state = normalize_learning_state(learning_state)
            if control_success_streak is not None:
                row.control_success_streak = int(control_success_streak)
            if review_stage is not None:
                row.review_stage = max(int(review_stage), 0)
            if mistake_count_delta:
                row.mistake_count = max(int(row.mistake_count or 0) + int(mistake_count_delta), 0)
            row.review_priority = 0 if completed_now else max(int(row.review_priority or 0) + review_priority_delta, 0)
            row.last_level_run_id = level_run_id
            if completed_now:
                row.last_completed = now
            if next_review_at is not None:
                row.next_review_at = next_review_at
            if last_reviewed_at is not None:
                row.last_reviewed_at = last_reviewed_at
            if row.priority_state == USER_WORD_PRIORITY_INTRODUCED and row.learning_state != USER_WORD_NEEDS_WORK:
                row.priority_state = USER_WORD_PRIORITY_CONSUMED
            row.updated = now
            if is_known is True:
                row.is_known = True
                row.learning_state = USER_WORD_LEARNED

    def get(
        self,
        word_id: int,
        *,
        level_run_id: int,
        word_source: str = USER_WORD_SOURCE_CORE,
    ) -> dict[str, Any] | None:
        normalized_source = str(word_source or USER_WORD_SOURCE_CORE).strip().lower()
        with self.session_manager.session() as session:
            level_run = session.get(UserLevelRun, level_run_id)
            if level_run is None:
                return None
            row = self._get_assignment(session, level_run.user_uuid, normalized_source, int(word_id))
            return learning_assignment_to_progress_dict(row) if row is not None else None

    def get_level_word_totals(self) -> dict[int, int]:
        with self.session_manager.session() as session:
            rows = session.execute(
                select(DictionaryEntry.level_id, func.count(DictionaryEntry.id))
                .where(DictionaryEntry.level_id.is_not(None))
                .group_by(DictionaryEntry.level_id)
            ).all()
            return {level_id: total for level_id, total in rows}

    def get_user_level_summary(
        self,
        telegram_user_id: int,
        level_id: int,
        *,
        level_run_id: int | None = None,
    ) -> dict[str, int]:
        _ = level_run_id
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {"learned_count": 0, "in_progress_count": 0, "needs_work_count": 0}
            learned_count, in_progress_count, needs_work_count = session.execute(
                select(
                    func.count(UserWordAssignment.id).filter(UserWordAssignment.learning_state == USER_WORD_LEARNED),
                    func.count(UserWordAssignment.id).filter(UserWordAssignment.learning_state == USER_WORD_LEARNING),
                    func.count(UserWordAssignment.id).filter(UserWordAssignment.learning_state == USER_WORD_NEEDS_WORK),
                )
                .select_from(UserWordAssignment)
                .join(
                    DictionaryEntry,
                    and_(
                        UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                        UserWordAssignment.word_id == DictionaryEntry.id,
                    ),
                )
                .where(
                    UserWordAssignment.user_uuid == user_uuid,
                    UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                    DictionaryEntry.level_id == level_id,
                )
            ).one()
            return {
                "learned_count": learned_count or 0,
                "in_progress_count": in_progress_count or 0,
                "needs_work_count": needs_work_count or 0,
            }

    def get_user_assignment_summary(self, telegram_user_id: int) -> dict[str, int]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {
                    "learned_count": 0,
                    "in_progress_count": 0,
                    "needs_work_count": 0,
                    "total_count": 0,
                }
            learned_count, in_progress_count, needs_work_count, total_count = session.execute(
                select(
                    func.count(UserWordAssignment.id).filter(UserWordAssignment.learning_state == USER_WORD_LEARNED),
                    func.count(UserWordAssignment.id).filter(UserWordAssignment.learning_state == USER_WORD_LEARNING),
                    func.count(UserWordAssignment.id).filter(UserWordAssignment.learning_state == USER_WORD_NEEDS_WORK),
                    func.count(UserWordAssignment.id),
                ).where(
                    UserWordAssignment.user_uuid == user_uuid,
                    UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                )
            ).one()
            return {
                "learned_count": learned_count or 0,
                "in_progress_count": in_progress_count or 0,
                "needs_work_count": needs_work_count or 0,
                "total_count": total_count or 0,
            }

    def list_user_words(
        self,
        telegram_user_id: int,
        *,
        mode: str,
        page: int,
        page_size: int,
        word: str = "",
        topic: str | list[str] = "",
        level: str = "",
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        states = (USER_WORD_LEARNED,) if mode == "learned" else (USER_WORD_LEARNING, USER_WORD_NEEDS_WORK)
        normalized_word = word.strip().lower()
        topic_values = normalize_filter_values(topic)
        normalized_level = level.strip()

        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
            core_filters = [
                UserWordAssignment.user_uuid == user_uuid,
                UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                UserWordAssignment.learning_state.in_(states),
            ]
            user_filters = [
                UserWordAssignment.user_uuid == user_uuid,
                UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                UserWordAssignment.learning_state.in_(states),
                UserDictionaryEntry.status == USER_DICTIONARY_READY,
            ]
            if normalized_word:
                core_filters.append(func.lower(DictionaryEntry.word).contains(normalized_word))
                user_filters.append(func.lower(UserDictionaryEntry.word).contains(normalized_word))
            if normalized_level:
                core_filters.append(LanguageLevel.title == normalized_level)
                user_filters.append(LanguageLevel.title == normalized_level)
            if topic_values:
                topic_entry_ids = (
                    select(DictionaryEntryCategory.entry_id)
                    .join(DictionaryCategory, DictionaryCategory.id == DictionaryEntryCategory.category_id)
                    .where(DictionaryCategory.code.in_(topic_values))
                )
                core_filters.append(DictionaryEntry.id.in_(topic_entry_ids))
                user_filters.append(literal(False))

            core_query = (
                select(
                    literal(USER_WORD_SOURCE_CORE).label("word_source"),
                    DictionaryEntry.id.label("word_id"),
                    DictionaryEntry.word.label("word"),
                    LanguageLevel.title.label("level"),
                    DictionaryEntry.translation_uk.label("translation_uk"),
                    DictionaryEntry.translation_ru.label("translation_ru"),
                    DictionaryEntry.translation_pl.label("translation_pl"),
                    UserWordAssignment.learning_state.label("learning_state"),
                    UserWordAssignment.review_priority.label("review_priority"),
                    UserWordAssignment.next_review_at.label("next_review_at"),
                    UserWordAssignment.priority_rank.label("priority_rank"),
                    (UserWordAssignment.priority_rank > 0).label("is_priority"),
                    UserWordAssignment.updated.label("updated_sort"),
                    DictionaryEntry.id.label("core_entry_id"),
                )
                .select_from(UserWordAssignment)
                .join(DictionaryEntry, DictionaryEntry.id == UserWordAssignment.word_id)
                .join(LanguageLevel, LanguageLevel.id == DictionaryEntry.level_id)
                .where(*core_filters)
            )
            user_query = (
                select(
                    literal(USER_WORD_SOURCE_USER).label("word_source"),
                    UserDictionaryEntry.id.label("word_id"),
                    UserDictionaryEntry.word.label("word"),
                    LanguageLevel.title.label("level"),
                    UserDictionaryEntry.translation_uk.label("translation_uk"),
                    UserDictionaryEntry.translation_ru.label("translation_ru"),
                    UserDictionaryEntry.translation_pl.label("translation_pl"),
                    UserWordAssignment.learning_state.label("learning_state"),
                    UserWordAssignment.review_priority.label("review_priority"),
                    UserWordAssignment.next_review_at.label("next_review_at"),
                    UserWordAssignment.priority_rank.label("priority_rank"),
                    (UserWordAssignment.priority_rank > 0).label("is_priority"),
                    UserWordAssignment.updated.label("updated_sort"),
                    literal(None).label("core_entry_id"),
                )
                .select_from(UserWordAssignment)
                .join(UserDictionaryEntry, UserDictionaryEntry.id == UserWordAssignment.word_id)
                .join(LanguageLevel, LanguageLevel.id == UserDictionaryEntry.level_id)
                .where(*user_filters)
            )
            words_query = union_all(core_query, user_query).subquery()
            total = session.scalar(select(func.count()).select_from(words_query))
            rows = session.execute(
                select(words_query)
                .order_by(
                    words_query.c.priority_rank.desc(),
                    words_query.c.review_priority.desc(),
                    words_query.c.updated_sort.desc(),
                    words_query.c.word.asc(),
                )
                .offset(offset)
                .limit(page_size)
            ).all()

            entry_ids = [int(row.core_entry_id) for row in rows if row.core_entry_id is not None]
            metadata_by_id = load_dictionary_entry_metadata(session, entry_ids)

            items = []
            for row in rows:
                core_entry_id = int(row.core_entry_id) if row.core_entry_id is not None else None
                metadata = metadata_by_id.get(core_entry_id or -1, {"categories": []})
                categories = metadata.get("categories", [])
                items.append(
                    {
                        "id": int(row.word_id),
                        "word_source": row.word_source,
                        "word_id": int(row.word_id),
                        "word": row.word,
                        "topic": ", ".join(categories),
                        "level": row.level,
                        "translation": row.translation_uk,
                        "translation_uk": row.translation_uk,
                        "translation_ru": row.translation_ru,
                        "translation_pl": row.translation_pl,
                        "learning_state": row.learning_state,
                        "review_priority": int(row.review_priority or 0),
                        "priority_rank": int(row.priority_rank or 0),
                        "is_priority": bool(row.is_priority),
                        "next_review_at": row.next_review_at,
                    }
                )

            total_count = int(total or 0)
            return {
                "items": items,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "pages": (total_count + page_size - 1) // page_size if total_count else 0,
            }

    def _get_assignment(
        self,
        session,
        user_uuid,
        word_source: str,
        word_id: int,
    ) -> UserWordAssignment | None:
        return session.scalar(
            select(UserWordAssignment)
            .where(
                UserWordAssignment.user_uuid == user_uuid,
                UserWordAssignment.word_source == word_source,
                UserWordAssignment.word_id == int(word_id),
            )
            .limit(1)
        )
