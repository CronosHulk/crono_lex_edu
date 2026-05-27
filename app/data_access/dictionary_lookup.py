from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select

from app.data_access.dictionary_publish import (
    dictionary_entry_to_dict,
    load_dictionary_entry_metadata,
    normalize_part_of_speech_code,
)
from app.data_access.user_dictionary_assignments import create_assignment
from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_SOURCE_CORE,
)
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import (
    DictionaryCategory,
    DictionaryEntry,
    DictionaryEntryPartOfSpeech,
    DictionaryPartOfSpeech,
)
from app.orm import SessionManager


class DictionaryLookupRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def create_user_core_word_assignment(
        self,
        telegram_user_id: int,
        word_id: int,
        *,
        current_time: datetime | None = None,
    ) -> None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return
            self._create_user_core_word_assignment_for_uuid_in_session(
                session,
                user_uuid,
                word_id,
                current_time=current_time,
            )

    def create_user_core_word_assignment_for_user_uuid(
        self,
        user_uuid: str,
        word_id: int,
        *,
        current_time: datetime | None = None,
    ) -> None:
        with self.session_manager.session() as session:
            self._create_user_core_word_assignment_for_uuid_in_session(
                session,
                UUID(str(user_uuid)),
                word_id,
                current_time=current_time,
            )

    def _create_user_core_word_assignment_for_uuid_in_session(
        self,
        session,
        user_uuid,
        word_id: int,
        *,
        current_time: datetime | None,
    ) -> None:
        now = current_time or datetime.now(UTC)
        create_assignment(
            session,
            user_uuid=user_uuid,
            word_source=USER_WORD_SOURCE_CORE,
            word_id=word_id,
            current_time=now,
            status=USER_WORD_ASSIGNMENT_AVAILABLE,
        )

    def find_by_word(self, word: str) -> dict[str, Any] | None:
        rows = self.list_by_word(word)
        return rows[0] if rows else None

    def list_by_word(self, word: str) -> list[dict[str, Any]]:
        normalized_word = str(word).strip().lower()
        if not normalized_word:
            return []
        with self.session_manager.session() as session:
            rows = (
                session.scalars(
                    select(DictionaryEntry)
                    .where(
                        or_(
                            func.lower(DictionaryEntry.normalized_word) == normalized_word,
                            func.lower(DictionaryEntry.word) == normalized_word,
                        )
                    )
                    .order_by(DictionaryEntry.id.asc())
                ).all()
                or []
            )
            entry_ids = [int(row.id) for row in rows]
            metadata_by_id = load_dictionary_entry_metadata(session, entry_ids)
            return [
                dictionary_entry_to_dict(row, metadata=metadata_by_id.get(int(row.id)))
                for row in rows
            ]

    def find_by_word_and_part_of_speech(self, word: str, part_of_speech: str | None) -> dict[str, Any] | None:
        normalized_word = str(word).strip().lower()
        if not normalized_word:
            return None
        normalized_part_of_speech = normalize_part_of_speech_code(part_of_speech or "")
        if not normalized_part_of_speech:
            return self.find_by_word(word)
        with self.session_manager.session() as session:
            row = session.scalar(
                select(DictionaryEntry)
                .join(DictionaryEntryPartOfSpeech, DictionaryEntryPartOfSpeech.entry_id == DictionaryEntry.id)
                .join(DictionaryPartOfSpeech, DictionaryPartOfSpeech.id == DictionaryEntryPartOfSpeech.part_of_speech_id)
                .where(
                    or_(
                        func.lower(DictionaryEntry.normalized_word) == normalized_word,
                        func.lower(DictionaryEntry.word) == normalized_word,
                    ),
                    DictionaryPartOfSpeech.code == normalized_part_of_speech,
                )
                .limit(1)
            )
            if row is None:
                return None
            metadata_by_id = load_dictionary_entry_metadata(session, [int(row.id)])
            return dictionary_entry_to_dict(row, metadata=metadata_by_id.get(int(row.id)))

    def list_categories(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(select(DictionaryCategory).order_by(DictionaryCategory.code.asc())).all()
            return [{"code": row.code, "title": row.title} for row in rows]
