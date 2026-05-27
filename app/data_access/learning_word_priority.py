from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, select

from app.data_access.user_dictionary import (
    USER_DICTIONARY_READY,
    normalize_user_word_source,
)
from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_LEARNED,
    USER_WORD_LEARNING,
    USER_WORD_PRIORITY_PENDING,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
)
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.helpers.priority_rank import priority_rank_from_datetime
from app.models import DictionaryEntry, UserDictionaryEntry, UserWordAssignment
from app.orm import SessionManager


class LearningWordPriorityRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def prioritize_word(
        self,
        telegram_user_id: int,
        *,
        word_source: str,
        word_id: int,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        normalized_source = normalize_user_word_source(word_source)
        priority_rank = priority_rank_from_datetime(current_time)
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            if normalized_source == USER_WORD_SOURCE_CORE:
                assignment = session.scalar(
                    select(UserWordAssignment)
                    .join(
                        DictionaryEntry,
                        and_(
                            UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                            UserWordAssignment.word_id == DictionaryEntry.id,
                        ),
                    )
                    .where(
                        UserWordAssignment.user_uuid == user_uuid,
                        UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                        UserWordAssignment.word_id == int(word_id),
                        UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                    )
                    .limit(1)
                )
                if assignment is None:
                    return None
                if assignment.status != USER_WORD_ASSIGNMENT_AVAILABLE:
                    return None
                assignment.priority_rank = priority_rank
                assignment.priority_state = USER_WORD_PRIORITY_PENDING
                assignment.is_known = False
                if assignment.learning_state == USER_WORD_LEARNED:
                    assignment.learning_state = USER_WORD_LEARNING
                assignment.updated = current_time
                return {"word_source": normalized_source, "word_id": int(word_id), "priority_rank": priority_rank}

            assignment = session.scalar(
                select(UserWordAssignment)
                .join(
                    UserDictionaryEntry,
                    and_(
                        UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                        UserWordAssignment.word_id == UserDictionaryEntry.id,
                    ),
                )
                .where(
                    UserWordAssignment.user_uuid == user_uuid,
                    UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                    UserWordAssignment.word_id == int(word_id),
                    UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
                    UserDictionaryEntry.status == USER_DICTIONARY_READY,
                )
                .limit(1)
            )
            if assignment is None:
                return None
            assignment.priority_rank = priority_rank
            assignment.priority_state = USER_WORD_PRIORITY_PENDING
            assignment.is_known = False
            if assignment.learning_state == USER_WORD_LEARNED:
                assignment.learning_state = USER_WORD_LEARNING
            assignment.updated = current_time
            return {"word_source": normalized_source, "word_id": int(word_id), "priority_rank": priority_rank}
