from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.data_access.dictionary_publish import (
    dictionary_entry_to_dict,
    load_dictionary_entry_metadata,
)
from app.data_access.lesson_selection_payloads import (
    build_lesson_bucket_quotas,
    build_lesson_entry_type_quotas,
    finalize_selected_words,
    payload_key,
    payload_word_id,
    serialize_followup_words,
)
from app.data_access.user_dictionary import (
    USER_DICTIONARY_READY,
    user_dictionary_entry_to_lesson_word,
)
from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_LEARNING,
    USER_WORD_NEEDS_WORK,
    USER_WORD_PRIORITY_NONE,
    USER_WORD_PRIORITY_PENDING,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
)
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import (
    DictionaryEntry,
    LearningSession,
    LearningSessionWord,
    UserDictionaryEntry,
    UserWordAssignment,
)
from app.orm import SessionManager


class LessonWordSelectionRepository:
    def __init__(self, session_manager: SessionManager, settings: Settings) -> None:
        self.session_manager = session_manager
        self.settings = settings

    def _fetch_word_candidates(self, session: Session, stmt, limit: int) -> list[dict[str, Any]]:
        rows = session.execute(stmt.limit(limit)).all()
        entry_ids = [int(row[0].id) for row in rows]
        metadata_by_id = load_dictionary_entry_metadata(session, entry_ids)
        payload: list[dict[str, Any]] = []
        for row in rows:
            entry = row[0]
            review_priority = row[1] if len(row) > 1 else 0
            priority_rank = row[2] if len(row) > 2 else 0
            priority_state = row[3] if len(row) > 3 else USER_WORD_PRIORITY_NONE
            last_seen_at = row[4] if len(row) > 4 else None
            next_review_at = row[5] if len(row) > 5 else None
            learning_state = row[6] if len(row) > 6 else USER_WORD_LEARNING
            payload.append(
                {
                    **dictionary_entry_to_dict(
                        entry,
                        metadata=metadata_by_id.get(int(entry.id)),
                        review_priority=review_priority or 0,
                        is_priority=bool(priority_rank),
                    ),
                    "priority_rank": int(priority_rank or 0),
                    "priority_state": str(priority_state or USER_WORD_PRIORITY_NONE),
                    "last_seen_at": last_seen_at,
                    "next_review_at": next_review_at,
                    "learning_state": str(learning_state or USER_WORD_LEARNING),
                    "word_source": USER_WORD_SOURCE_CORE,
                    "word_id": int(entry.id),
                }
            )
        return payload

    def _fetch_user_word_candidates(self, session: Session, stmt, limit: int) -> list[dict[str, Any]]:
        rows = session.execute(stmt.limit(limit)).all()
        payload = []
        for row in rows:
            entry = row[0]
            review_priority = row[1] if len(row) > 1 else 0
            priority_rank = row[2] if len(row) > 2 else 0
            priority_state = row[3] if len(row) > 3 else USER_WORD_PRIORITY_NONE
            last_seen_at = row[4] if len(row) > 4 else None
            next_review_at = row[5] if len(row) > 5 else None
            learning_state = row[6] if len(row) > 6 else USER_WORD_LEARNING
            payload.append(
                user_dictionary_entry_to_lesson_word(
                    entry,
                    review_priority=review_priority or 0,
                    is_priority=bool(priority_rank),
                )
                | {
                    "priority_rank": int(priority_rank or 0),
                    "priority_state": str(priority_state or USER_WORD_PRIORITY_NONE),
                    "last_seen_at": last_seen_at,
                    "next_review_at": next_review_at,
                    "learning_state": str(learning_state or USER_WORD_LEARNING),
                }
            )
        return payload

    def select_lesson_words(self, telegram_user_id: int, level_id: int, words_limit: int) -> list[dict[str, Any]]:
        current_time = datetime.now(datetime.now().astimezone().tzinfo)
        cooldown_boundary = current_time - timedelta(days=max(self.settings.app_word_cooldown_days, 0))
        quotas = build_lesson_bucket_quotas(words_limit)

        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            selected: list[dict[str, Any]] = []
            selected_keys: set[tuple[str, int]] = set()

            if user_uuid is not None:
                self._extend_with_due_assignments(
                    session,
                    selected,
                    selected_keys,
                    user_uuid,
                    level_id,
                    min(quotas["due"], words_limit - len(selected)),
                    current_time=current_time,
                    cooldown_boundary=cooldown_boundary,
                )
                self._extend_with_pending_priority_assignments(
                    session,
                    selected,
                    selected_keys,
                    user_uuid,
                    min(quotas["priority"], words_limit - len(selected)),
                )
                self._extend_with_needs_work_assignments(
                    session,
                    selected,
                    selected_keys,
                    user_uuid,
                    level_id,
                    min(quotas["needs_work"], words_limit - len(selected)),
                    current_time=current_time,
                    cooldown_boundary=cooldown_boundary,
                )
                self._extend_with_fresh_core_quotas(
                    session,
                    selected,
                    selected_keys,
                    user_uuid,
                    level_id,
                    words_limit,
                    current_time=current_time,
                )
                self._extend_with_user_assignments(
                    session,
                    selected,
                    selected_keys,
                    user_uuid,
                    min(quotas["fresh"], words_limit - len(selected)),
                    current_time=current_time,
                    cooldown_boundary=cooldown_boundary,
                )
                self._extend_with_fresh_core_assignments(
                    session,
                    selected,
                    selected_keys,
                    user_uuid,
                    level_id,
                    min(quotas["fresh"], words_limit - len(selected)),
                    current_time=current_time,
                )
                self._backfill_lesson_words(
                    session,
                    selected,
                    selected_keys,
                    user_uuid,
                    level_id,
                    words_limit,
                    current_time=current_time,
                    cooldown_boundary=cooldown_boundary,
                )
            return finalize_selected_words(selected, words_limit)

    def select_next_lesson_word(
        self,
        telegram_user_id: int,
        level_id: int,
        excluded_word_ids: list[int],
        excluded_words: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        current_time = datetime.now(datetime.now().astimezone().tzinfo)
        cooldown_boundary = current_time - timedelta(days=max(self.settings.app_word_cooldown_days, 0))
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            selected: list[dict[str, Any]] = []
            selected_keys = self._excluded_keys(excluded_word_ids, excluded_words)
            self._extend_with_pending_priority_assignments(session, selected, selected_keys, user_uuid, 1)
            if selected:
                return finalize_selected_words(selected, 1)[0]
            self._extend_with_needs_work_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                level_id,
                1,
                current_time=current_time,
                cooldown_boundary=cooldown_boundary,
            )
            if selected:
                return finalize_selected_words(selected, 1)[0]
            self._extend_with_due_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                level_id,
                1,
                current_time=current_time,
                cooldown_boundary=cooldown_boundary,
            )
            if selected:
                return finalize_selected_words(selected, 1)[0]
            self._extend_with_user_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                1,
                current_time=current_time,
                cooldown_boundary=cooldown_boundary,
            )
            if selected:
                return finalize_selected_words(selected, 1)[0]
            self._extend_with_fresh_core_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                level_id,
                1,
                current_time=current_time,
            )
            return finalize_selected_words(selected, 1)[0] if selected else None

    def select_followup_words(self, source_session_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            source_session = session.scalar(select(LearningSession).where(LearningSession.id == source_session_id).limit(1))
            if source_session is None:
                return []
            session_words = session.scalars(
                select(LearningSessionWord)
                .where(
                    LearningSessionWord.session_id == source_session_id,
                    LearningSessionWord.card_status != "known",
                )
                .order_by(LearningSessionWord.item_order.asc())
            ).all()
            core_ids = [
                int(row.word_id)
                for row in session_words
                if (row.word_source or USER_WORD_SOURCE_CORE) == USER_WORD_SOURCE_CORE
            ]
            user_ids = [
                int(row.word_id)
                for row in session_words
                if (row.word_source or USER_WORD_SOURCE_CORE) == USER_WORD_SOURCE_USER
            ]
            core_entries = session.scalars(select(DictionaryEntry).where(DictionaryEntry.id.in_(core_ids or {-1}))).all()
            user_entries = session.scalars(select(UserDictionaryEntry).where(UserDictionaryEntry.id.in_(user_ids or {-1}))).all()
            assignments = session.scalars(
                select(UserWordAssignment).where(
                    UserWordAssignment.user_uuid == source_session.user_uuid,
                    or_(
                        and_(
                            UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                            UserWordAssignment.word_id.in_(core_ids or {-1}),
                        ),
                        and_(
                            UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                            UserWordAssignment.word_id.in_(user_ids or {-1}),
                        ),
                    ),
                )
            ).all()
            review_by_key = {
                (str(row.word_source or USER_WORD_SOURCE_CORE), int(row.word_id)): int(row.review_priority or 0)
                for row in assignments
            }
            return serialize_followup_words(session, session_words, core_entries, user_entries, review_by_key)

    def _extend_with_pending_priority_assignments(
        self,
        session: Session,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        user_uuid,
        words_limit: int,
    ) -> None:
        limit = max(words_limit, 0)
        if limit <= 0:
            return
        user_stmt = self._user_assignment_stmt(user_uuid, selected_keys).where(
            UserWordAssignment.priority_rank > 0,
            UserWordAssignment.priority_state == USER_WORD_PRIORITY_PENDING,
        ).order_by(*self._priority_order())
        core_stmt = self._core_assignment_stmt(user_uuid, selected_keys).where(
            UserWordAssignment.priority_rank > 0,
            UserWordAssignment.priority_state == USER_WORD_PRIORITY_PENDING,
        ).order_by(*self._priority_order())
        words = [
            *self._fetch_user_word_candidates(session, user_stmt, limit),
            *self._fetch_word_candidates(session, core_stmt, limit),
        ]
        self._extend_selected(selected, selected_keys, finalize_selected_words(words, limit))

    def _extend_with_user_assignments(
        self,
        session: Session,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        user_uuid,
        words_limit: int,
        *,
        current_time: datetime,
        cooldown_boundary: datetime,
    ) -> None:
        limit = max(words_limit, 0)
        if limit <= 0:
            return
        stmt = (
            self._user_assignment_stmt(user_uuid, selected_keys)
            .where(
                self._not_pending_priority(),
                UserWordAssignment.learning_state == USER_WORD_LEARNING,
                self._ready_for_regular_rotation(current_time, cooldown_boundary),
            )
            .order_by(
                UserWordAssignment.next_review_at.asc().nullsfirst(),
                UserWordAssignment.last_seen_at.asc().nullsfirst(),
                func.random(),
            )
        )
        self._extend_selected(selected, selected_keys, self._fetch_user_word_candidates(session, stmt, limit))

    def _user_assignment_stmt(self, user_uuid, selected_keys: set[tuple[str, int]]):
        return (
            select(
                UserDictionaryEntry,
                UserWordAssignment.review_priority,
                UserWordAssignment.priority_rank,
                UserWordAssignment.priority_state,
                UserWordAssignment.last_seen_at,
                UserWordAssignment.next_review_at,
                UserWordAssignment.learning_state,
            )
            .join(
                UserWordAssignment,
                and_(
                    UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                    UserWordAssignment.word_id == UserDictionaryEntry.id,
                    UserWordAssignment.user_uuid == user_uuid,
                ),
            )
            .where(
                UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                UserWordAssignment.is_known.is_(False),
                UserWordAssignment.learning_state.in_((USER_WORD_LEARNING, USER_WORD_NEEDS_WORK)),
                UserDictionaryEntry.status == USER_DICTIONARY_READY,
                func.coalesce(UserDictionaryEntry.audio_path, "") != "",
                UserDictionaryEntry.is_embedding_ready.is_(True),
                UserDictionaryEntry.embedding.is_not(None),
                ~UserDictionaryEntry.id.in_(self._ids_for_source(selected_keys, USER_WORD_SOURCE_USER) or {-1}),
            )
        )

    def _extend_with_needs_work_assignments(
        self,
        session: Session,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        user_uuid,
        level_id: int,
        limit: int,
        *,
        current_time: datetime,
        cooldown_boundary: datetime,
    ) -> None:
        if limit <= 0:
            return
        user_stmt = (
            self._user_assignment_stmt(user_uuid, selected_keys)
            .where(
                self._not_pending_priority(),
                UserWordAssignment.learning_state == USER_WORD_NEEDS_WORK,
                self._ready_for_needs_work_rotation(current_time, cooldown_boundary),
            )
            .order_by(*self._needs_work_order())
        )
        core_stmt = (
            self._core_assignment_stmt(user_uuid, selected_keys)
            .where(
                self._not_pending_priority(),
                DictionaryEntry.level_id == level_id,
                UserWordAssignment.learning_state == USER_WORD_NEEDS_WORK,
                self._ready_for_needs_work_rotation(current_time, cooldown_boundary),
            )
            .order_by(*self._needs_work_order())
        )
        words = [
            *self._fetch_user_word_candidates(session, user_stmt, limit),
            *self._fetch_word_candidates(session, core_stmt, limit),
        ]
        self._extend_selected(selected, selected_keys, finalize_selected_words(words, limit))

    def _extend_with_due_assignments(
        self,
        session: Session,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        user_uuid,
        level_id: int,
        limit: int,
        *,
        current_time: datetime,
        cooldown_boundary: datetime,
    ) -> None:
        if limit <= 0:
            return
        user_stmt = (
            self._user_assignment_stmt(user_uuid, selected_keys)
            .where(
                self._not_pending_priority(),
                UserWordAssignment.learning_state == USER_WORD_LEARNING,
                self._ready_for_regular_rotation(current_time, cooldown_boundary),
            )
            .order_by(*self._due_order())
        )
        core_stmt = (
            self._core_assignment_stmt(user_uuid, selected_keys)
            .where(
                self._not_pending_priority(),
                DictionaryEntry.level_id == level_id,
                UserWordAssignment.learning_state == USER_WORD_LEARNING,
                self._ready_for_regular_rotation(current_time, cooldown_boundary),
            )
            .order_by(*self._due_order())
        )
        words = [
            *self._fetch_user_word_candidates(session, user_stmt, limit),
            *self._fetch_word_candidates(session, core_stmt, limit),
        ]
        self._extend_selected(selected, selected_keys, finalize_selected_words(words, limit))

    def _extend_with_due_core_assignments(
        self,
        session: Session,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        user_uuid,
        level_id: int,
        limit: int,
        *,
        current_time: datetime,
        cooldown_boundary: datetime,
    ) -> None:
        if limit <= 0:
            return
        stmt = (
            self._core_assignment_stmt(user_uuid, selected_keys)
            .where(
                self._not_pending_priority(),
                DictionaryEntry.level_id == level_id,
                UserWordAssignment.learning_state == USER_WORD_LEARNING,
                self._ready_for_regular_rotation(current_time, cooldown_boundary),
            )
            .order_by(*self._due_order())
        )
        self._extend_selected(selected, selected_keys, self._fetch_word_candidates(session, stmt, limit))

    def _extend_with_fresh_core_quotas(
        self,
        session: Session,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        user_uuid,
        level_id: int,
        words_limit: int,
        *,
        current_time: datetime,
    ) -> None:
        for entry_type, quota_count in build_lesson_entry_type_quotas(words_limit).items():
            current_type_count = sum(1 for word in selected if word.get("entry_type") == entry_type)
            limit = min(max(quota_count - current_type_count, 0), words_limit - len(selected))
            if limit <= 0:
                continue
            self._extend_with_fresh_core_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                level_id,
                limit,
                current_time=current_time,
                entry_type=entry_type,
            )

    def _extend_with_fresh_core_assignments(
        self,
        session: Session,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        user_uuid,
        level_id: int,
        limit: int,
        *,
        current_time: datetime,
        entry_type: str | None = None,
    ) -> None:
        if limit <= 0:
            return
        stmt = (
            select(
                DictionaryEntry,
                literal(0),
                literal(0),
                literal(USER_WORD_PRIORITY_NONE),
                literal(None),
                literal(None),
                literal(USER_WORD_LEARNING),
            )
            .outerjoin(
                UserWordAssignment,
                and_(
                    UserWordAssignment.user_uuid == user_uuid,
                    UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                    UserWordAssignment.word_id == DictionaryEntry.id,
                ),
            )
            .where(
                DictionaryEntry.level_id == level_id,
                func.coalesce(DictionaryEntry.audio_path, "") != "",
                DictionaryEntry.is_embedding_ready.is_(True),
                DictionaryEntry.embedding.is_not(None),
                UserWordAssignment.id.is_(None),
                ~DictionaryEntry.id.in_(self._ids_for_source(selected_keys, USER_WORD_SOURCE_CORE) or {-1}),
            )
            .order_by(func.random())
        )
        if entry_type is not None:
            stmt = stmt.where(DictionaryEntry.entry_type == entry_type)
        words = self._fetch_word_candidates(session, stmt, limit)
        self._create_core_assignments(session, user_uuid, words, current_time=current_time)
        self._extend_selected(selected, selected_keys, words)

    def _core_assignment_stmt(self, user_uuid, selected_keys: set[tuple[str, int]]):
        return (
            select(
                DictionaryEntry,
                UserWordAssignment.review_priority,
                UserWordAssignment.priority_rank,
                UserWordAssignment.priority_state,
                UserWordAssignment.last_seen_at,
                UserWordAssignment.next_review_at,
                UserWordAssignment.learning_state,
            )
            .join(
                UserWordAssignment,
                and_(
                    UserWordAssignment.user_uuid == user_uuid,
                    UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                    UserWordAssignment.word_id == DictionaryEntry.id,
                ),
            )
            .where(
                UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                UserWordAssignment.is_known.is_(False),
                UserWordAssignment.learning_state.in_((USER_WORD_LEARNING, USER_WORD_NEEDS_WORK)),
                func.coalesce(DictionaryEntry.audio_path, "") != "",
                DictionaryEntry.is_embedding_ready.is_(True),
                DictionaryEntry.embedding.is_not(None),
                ~DictionaryEntry.id.in_(self._ids_for_source(selected_keys, USER_WORD_SOURCE_CORE) or {-1}),
            )
        )

    def _create_core_assignments(
        self,
        session: Session,
        user_uuid,
        words: list[dict[str, Any]],
        *,
        current_time: datetime,
    ) -> None:
        rows = [
            {
                "user_uuid": user_uuid,
                "word_source": USER_WORD_SOURCE_CORE,
                "word_id": payload_word_id(word),
                "status": USER_WORD_ASSIGNMENT_AVAILABLE,
                "priority_rank": 0,
                "priority_state": USER_WORD_PRIORITY_NONE,
                "is_known": False,
                "learning_state": USER_WORD_LEARNING,
                "control_success_streak": 0,
                "review_priority": 0,
                "review_stage": 0,
                "mistake_count": 0,
                "created": current_time,
                "updated": current_time,
            }
            for word in words
        ]
        if not rows:
            return
        session.execute(
            pg_insert(UserWordAssignment)
            .values(rows)
            .on_conflict_do_nothing(
                index_elements=[
                    UserWordAssignment.user_uuid,
                    UserWordAssignment.word_source,
                    UserWordAssignment.word_id,
                ]
            )
        )
        session.flush()

    def _backfill_lesson_words(
        self,
        session: Session,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        user_uuid,
        level_id: int,
        words_limit: int,
        *,
        current_time: datetime,
        cooldown_boundary: datetime,
    ) -> None:
        for extender in (
            lambda limit: self._extend_with_due_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                level_id,
                limit,
                current_time=current_time,
                cooldown_boundary=cooldown_boundary,
            ),
            lambda limit: self._extend_with_needs_work_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                level_id,
                limit,
                current_time=current_time,
                cooldown_boundary=cooldown_boundary,
            ),
            lambda limit: self._extend_with_user_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                limit,
                current_time=current_time,
                cooldown_boundary=cooldown_boundary,
            ),
            lambda limit: self._extend_with_fresh_core_assignments(
                session,
                selected,
                selected_keys,
                user_uuid,
                level_id,
                limit,
                current_time=current_time,
            ),
        ):
            remaining = words_limit - len(selected)
            if remaining <= 0:
                return
            extender(remaining)

    def _not_pending_priority(self):
        return UserWordAssignment.priority_state != USER_WORD_PRIORITY_PENDING

    def _ready_for_regular_rotation(self, current_time: datetime, cooldown_boundary: datetime):
        return or_(
            UserWordAssignment.next_review_at <= current_time,
            and_(
                UserWordAssignment.next_review_at.is_(None),
                or_(
                    UserWordAssignment.last_seen_at.is_(None),
                    UserWordAssignment.last_seen_at <= cooldown_boundary,
                ),
            ),
        )

    def _ready_for_needs_work_rotation(self, current_time: datetime, cooldown_boundary: datetime):
        needs_work_boundary = current_time - timedelta(hours=6)
        return or_(
            UserWordAssignment.next_review_at <= current_time,
            and_(
                UserWordAssignment.next_review_at.is_(None),
                or_(
                    UserWordAssignment.last_seen_at.is_(None),
                    UserWordAssignment.last_seen_at <= needs_work_boundary,
                    UserWordAssignment.last_seen_at <= cooldown_boundary,
                ),
            ),
        )

    def _priority_order(self):
        return (
            UserWordAssignment.priority_rank.desc(),
            UserWordAssignment.last_seen_at.asc().nullsfirst(),
            UserWordAssignment.next_review_at.asc().nullsfirst(),
            func.random(),
        )

    def _due_order(self):
        return (
            UserWordAssignment.next_review_at.asc().nullsfirst(),
            UserWordAssignment.review_priority.desc(),
            UserWordAssignment.last_seen_at.asc().nullsfirst(),
            func.random(),
        )

    def _needs_work_order(self):
        return (
            UserWordAssignment.review_priority.desc(),
            UserWordAssignment.next_review_at.asc().nullsfirst(),
            UserWordAssignment.last_seen_at.asc().nullsfirst(),
            func.random(),
        )

    def _extend_selected(
        self,
        selected: list[dict[str, Any]],
        selected_keys: set[tuple[str, int]],
        words: list[dict[str, Any]],
    ) -> None:
        for word in words:
            key = payload_key(word)
            if key in selected_keys:
                continue
            selected.append(word)
            selected_keys.add(key)

    def _excluded_keys(
        self,
        excluded_word_ids: list[int],
        excluded_words: list[dict[str, Any]] | None,
    ) -> set[tuple[str, int]]:
        keys = {(USER_WORD_SOURCE_CORE, int(word_id)) for word_id in excluded_word_ids}
        for item in excluded_words or []:
            keys.add(payload_key(item))
        return keys

    def _ids_for_source(self, keys: set[tuple[str, int]], source: str) -> set[int]:
        return {word_id for word_source, word_id in keys if word_source == source}
