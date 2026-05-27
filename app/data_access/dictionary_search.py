from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, literal, select, union_all

from app.data_access.user_dictionary import USER_DICTIONARY_READY
from app.data_access.user_dictionary_assignments import create_assignment
from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
)
from app.models import DictionaryEntry, UserDictionaryEntry
from app.models.shared import LanguageLevel
from app.orm import SessionManager


class DictionarySearchRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def search_words(
        self,
        *,
        user_uuid: str | UUID,
        query: str,
        page: int,
        page_size: int,
        level: str = "",
        allowed_core_levels: set[str] | None = None,
        include_user_words: bool = False,
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        normalized_query = query.strip().lower()
        normalized_level = level.strip()
        with self.session_manager.session() as session:
            core_filters = [
                DictionaryEntry.is_archived.is_(False),
                func.coalesce(DictionaryEntry.audio_path, "") != "",
                func.lower(DictionaryEntry.word).contains(normalized_query),
            ]
            if normalized_level:
                core_filters.append(LanguageLevel.title == normalized_level)
            if allowed_core_levels is not None:
                core_filters.append(LanguageLevel.title.in_(allowed_core_levels or {"__none__"}))

            core_query = (
                select(
                    literal(USER_WORD_SOURCE_CORE).label("word_source"),
                    DictionaryEntry.id.label("word_id"),
                    DictionaryEntry.word.label("word"),
                    DictionaryEntry.transcription.label("transcription"),
                    LanguageLevel.title.label("level"),
                    DictionaryEntry.translation_uk.label("translation_uk"),
                    DictionaryEntry.translation_ru.label("translation_ru"),
                    DictionaryEntry.translation_pl.label("translation_pl"),
                    DictionaryEntry.audio_path.label("audio_path"),
                    DictionaryEntry.word.label("word_sort"),
                )
                .select_from(DictionaryEntry)
                .join(LanguageLevel, LanguageLevel.id == DictionaryEntry.level_id)
                .where(*core_filters)
            )

            queries = [core_query]
            if include_user_words:
                user_filters = [
                    UserDictionaryEntry.created_by_user_uuid == UUID(str(user_uuid)),
                    UserDictionaryEntry.status == USER_DICTIONARY_READY,
                    func.coalesce(UserDictionaryEntry.audio_path, "") != "",
                    func.lower(UserDictionaryEntry.word).contains(normalized_query),
                ]
                if normalized_level:
                    user_filters.append(LanguageLevel.title == normalized_level)
                user_query = (
                    select(
                        literal(USER_WORD_SOURCE_USER).label("word_source"),
                        UserDictionaryEntry.id.label("word_id"),
                        UserDictionaryEntry.word.label("word"),
                        UserDictionaryEntry.transcription.label("transcription"),
                        LanguageLevel.title.label("level"),
                        UserDictionaryEntry.translation_uk.label("translation_uk"),
                        UserDictionaryEntry.translation_ru.label("translation_ru"),
                        UserDictionaryEntry.translation_pl.label("translation_pl"),
                        UserDictionaryEntry.audio_path.label("audio_path"),
                        UserDictionaryEntry.word.label("word_sort"),
                    )
                    .select_from(UserDictionaryEntry)
                    .join(LanguageLevel, LanguageLevel.id == UserDictionaryEntry.level_id)
                    .where(*user_filters)
                )
                queries.append(user_query)

            words_query = union_all(*queries).subquery()
            total = int(session.scalar(select(func.count()).select_from(words_query)) or 0)
            rows = session.execute(
                select(words_query)
                .order_by(words_query.c.word_sort.asc(), words_query.c.word_source.asc(), words_query.c.word_id.asc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [
                    {
                        "id": f"{row.word_source}:{row.word_id}",
                        "word_source": row.word_source,
                        "word_id": int(row.word_id),
                        "word": row.word,
                        "transcription": row.transcription,
                        "level": row.level,
                        "translation_uk": row.translation_uk,
                        "translation_ru": row.translation_ru,
                        "translation_pl": row.translation_pl,
                        "has_audio": bool(row.audio_path),
                    }
                    for row in rows
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size if total else 0,
            }

    def create_priority_assignment(
        self,
        *,
        user_uuid: str | UUID,
        word_source: str,
        word_id: int,
        current_time: datetime,
        allowed_core_levels: set[str] | None,
        include_user_words: bool,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            normalized_user_uuid = UUID(str(user_uuid))
            if word_source == USER_WORD_SOURCE_CORE:
                filters = [
                    DictionaryEntry.id == int(word_id),
                    DictionaryEntry.is_archived.is_(False),
                    func.coalesce(DictionaryEntry.audio_path, "") != "",
                ]
                if allowed_core_levels is not None:
                    filters.append(LanguageLevel.title.in_(allowed_core_levels or {"__none__"}))
                exists = session.scalar(
                    select(DictionaryEntry.id)
                    .join(LanguageLevel, LanguageLevel.id == DictionaryEntry.level_id)
                    .where(*filters)
                    .limit(1)
                )
                if exists is None:
                    return None
            elif word_source == USER_WORD_SOURCE_USER:
                if not include_user_words:
                    return None
                exists = session.scalar(
                    select(UserDictionaryEntry.id)
                    .where(
                        UserDictionaryEntry.id == int(word_id),
                        UserDictionaryEntry.created_by_user_uuid == normalized_user_uuid,
                        UserDictionaryEntry.status == USER_DICTIONARY_READY,
                        func.coalesce(UserDictionaryEntry.audio_path, "") != "",
                    )
                    .limit(1)
                )
                if exists is None:
                    return None
            else:
                return None
            return create_assignment(
                session,
                user_uuid=normalized_user_uuid,
                word_source=word_source,
                word_id=int(word_id),
                current_time=current_time,
                status=USER_WORD_ASSIGNMENT_AVAILABLE,
                priority_rank=_highest_priority_rank(current_time),
            )

    def audio_path_for_word(
        self,
        *,
        user_uuid: str | UUID,
        word_source: str,
        word_id: int,
        allowed_core_levels: set[str] | None,
        include_user_words: bool,
    ) -> str | None:
        with self.session_manager.session() as session:
            if word_source == USER_WORD_SOURCE_CORE:
                filters = [
                    DictionaryEntry.id == int(word_id),
                    DictionaryEntry.is_archived.is_(False),
                    func.coalesce(DictionaryEntry.audio_path, "") != "",
                ]
                if allowed_core_levels is not None:
                    filters.append(LanguageLevel.title.in_(allowed_core_levels or {"__none__"}))
                return session.scalar(
                    select(DictionaryEntry.audio_path)
                    .join(LanguageLevel, LanguageLevel.id == DictionaryEntry.level_id)
                    .where(*filters)
                    .limit(1)
                )
            if word_source == USER_WORD_SOURCE_USER and include_user_words:
                return session.scalar(
                    select(UserDictionaryEntry.audio_path)
                    .where(
                        UserDictionaryEntry.id == int(word_id),
                        UserDictionaryEntry.created_by_user_uuid == UUID(str(user_uuid)),
                        UserDictionaryEntry.status == USER_DICTIONARY_READY,
                        func.coalesce(UserDictionaryEntry.audio_path, "") != "",
                    )
                    .limit(1)
                )
        return None


def _highest_priority_rank(current_time: datetime) -> int:
    return int(current_time.timestamp() * 1_000_000) + 999_999
