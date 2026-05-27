from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, literal, select

from app.data_access.dictionary_publish import (
    dictionary_entry_to_dict,
    load_dictionary_entry_metadata,
)
from app.data_access.user_dictionary import (
    USER_DICTIONARY_READY,
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
    normalize_user_word_source,
    user_dictionary_entry_to_lesson_word,
)
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import (
    DictionaryEntry,
    DictionaryEntryPartOfSpeech,
    DictionaryPartOfSpeech,
    UserDictionaryEntry,
    UserWordAssignment,
)
from app.orm import SessionManager
from app.reference.distractors import has_distractor_conflict


class SimilarWordRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def find_similar_words(
        self,
        word_id: int,
        level_id: int,
        excluded_word_ids: list[int],
        limit: int,
        *,
        word_source: str = USER_WORD_SOURCE_CORE,
        telegram_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        normalized_source = normalize_user_word_source(word_source)
        excluded_core_ids = set(excluded_word_ids if normalized_source == USER_WORD_SOURCE_CORE else [])
        excluded_user_ids = set(excluded_word_ids if normalized_source == USER_WORD_SOURCE_USER else [])
        if normalized_source == USER_WORD_SOURCE_CORE:
            excluded_core_ids.add(word_id)
        else:
            excluded_user_ids.add(word_id)
        row_limit = max(limit * 4, limit, 1)
        with self.session_manager.session() as session:
            source = (
                session.get(DictionaryEntry, word_id)
                if normalized_source == USER_WORD_SOURCE_CORE
                else session.get(UserDictionaryEntry, word_id)
            )
            if source is None:
                return []

            user_uuid = self._resolve_user_uuid(session, telegram_user_id)
            source_part_of_speech = self._source_part_of_speech(session, source)
            rows: list[dict[str, Any]] = []
            if source.embedding is not None:
                core_distance = DictionaryEntry.embedding.op("<=>")(literal(source.embedding))
                core_statement = (
                    select(DictionaryEntry)
                    .where(
                        DictionaryEntry.id.not_in(excluded_core_ids or {-1}),
                        DictionaryEntry.level_id == level_id,
                        DictionaryEntry.is_archived.is_(False),
                        DictionaryEntry.is_embedding_ready.is_(True),
                        DictionaryEntry.embedding.is_not(None),
                    )
                    .order_by(core_distance)
                    .limit(row_limit)
                )
                core_rows = session.execute(
                    self._filter_core_by_part_of_speech(core_statement, source_part_of_speech)
                ).scalars().all()
                rows.extend(self._core_rows_to_payload(session, filter_safe_similar_word_rows(source, core_rows, limit)))
                if len(rows) < limit and user_uuid is not None:
                    user_distance = UserDictionaryEntry.embedding.op("<=>")(literal(source.embedding))
                    user_statement = (
                        self._filter_user_by_part_of_speech(
                            self._available_user_entries_statement(user_uuid),
                            source_part_of_speech,
                        )
                        .where(
                            UserDictionaryEntry.id.not_in(excluded_user_ids or {-1}),
                            UserDictionaryEntry.level_id == level_id,
                            UserDictionaryEntry.status == USER_DICTIONARY_READY,
                            UserDictionaryEntry.is_embedding_ready.is_(True),
                            UserDictionaryEntry.embedding.is_not(None),
                            func.coalesce(UserDictionaryEntry.audio_path, "") != "",
                        )
                        .order_by(user_distance)
                        .limit(row_limit)
                    )
                    user_rows = session.execute(user_statement).scalars().all()
                    rows.extend(
                        filter_safe_similar_word_payloads(
                            source,
                            [user_dictionary_entry_to_lesson_word(item) for item in user_rows],
                            limit - len(rows),
                        )
                    )
            else:
                rows = []

            if len(rows) < limit:
                extra_core_ids = excluded_core_ids | {
                    int(item["word_id"])
                    for item in rows
                    if item.get("word_source", USER_WORD_SOURCE_CORE) == USER_WORD_SOURCE_CORE
                }
                core_statement = (
                    select(DictionaryEntry)
                    .where(
                        DictionaryEntry.level_id == level_id,
                        DictionaryEntry.id.not_in(extra_core_ids or {-1}),
                        DictionaryEntry.is_archived.is_(False),
                        DictionaryEntry.is_embedding_ready.is_(True),
                        DictionaryEntry.embedding.is_not(None),
                    )
                    .order_by(DictionaryEntry.id.asc())
                    .limit(row_limit)
                )
                extras = session.scalars(self._filter_core_by_part_of_speech(core_statement, source_part_of_speech)).all()
                rows.extend(self._core_rows_to_payload(session, filter_safe_similar_word_rows(source, extras, limit - len(rows))))
            if len(rows) < limit and user_uuid is not None:
                extra_user_ids = excluded_user_ids | {
                    int(item["word_id"])
                    for item in rows
                    if item.get("word_source") == USER_WORD_SOURCE_USER
                }
                user_statement = (
                    self._filter_user_by_part_of_speech(
                        self._available_user_entries_statement(user_uuid),
                        source_part_of_speech,
                    )
                    .where(
                        UserDictionaryEntry.level_id == level_id,
                        UserDictionaryEntry.id.not_in(extra_user_ids or {-1}),
                        UserDictionaryEntry.status == USER_DICTIONARY_READY,
                        UserDictionaryEntry.is_embedding_ready.is_(True),
                        UserDictionaryEntry.embedding.is_not(None),
                        func.coalesce(UserDictionaryEntry.audio_path, "") != "",
                    )
                    .order_by(UserDictionaryEntry.id.asc())
                    .limit(row_limit)
                )
                user_extras = session.scalars(user_statement).all()
                rows.extend(
                    filter_safe_similar_word_payloads(
                        source,
                        [user_dictionary_entry_to_lesson_word(item) for item in user_extras],
                        limit - len(rows),
                    )
                )
            if len(rows) < limit:
                extra_core_ids = excluded_core_ids | {
                    int(item["word_id"])
                    for item in rows
                    if item.get("word_source", USER_WORD_SOURCE_CORE) == USER_WORD_SOURCE_CORE
                }
                core_statement = (
                    select(DictionaryEntry)
                    .where(
                        DictionaryEntry.id.not_in(extra_core_ids or {-1}),
                        DictionaryEntry.is_archived.is_(False),
                        DictionaryEntry.is_embedding_ready.is_(True),
                        DictionaryEntry.embedding.is_not(None),
                    )
                    .order_by(func.random(), DictionaryEntry.id.asc())
                    .limit(row_limit)
                )
                extras = session.scalars(self._filter_core_by_part_of_speech(core_statement, source_part_of_speech)).all()
                rows.extend(self._core_rows_to_payload(session, filter_safe_similar_word_rows(source, extras, limit - len(rows))))
            if len(rows) < limit and user_uuid is not None:
                extra_user_ids = excluded_user_ids | {
                    int(item["word_id"])
                    for item in rows
                    if item.get("word_source") == USER_WORD_SOURCE_USER
                }
                user_statement = (
                    self._filter_user_by_part_of_speech(
                        self._available_user_entries_statement(user_uuid),
                        source_part_of_speech,
                    )
                    .where(
                        UserDictionaryEntry.id.not_in(extra_user_ids or {-1}),
                        UserDictionaryEntry.status == USER_DICTIONARY_READY,
                        UserDictionaryEntry.is_embedding_ready.is_(True),
                        UserDictionaryEntry.embedding.is_not(None),
                        func.coalesce(UserDictionaryEntry.audio_path, "") != "",
                    )
                    .order_by(func.random(), UserDictionaryEntry.id.asc())
                    .limit(row_limit)
                )
                user_extras = session.scalars(user_statement).all()
                rows.extend(
                    filter_safe_similar_word_payloads(
                        source,
                        [user_dictionary_entry_to_lesson_word(item) for item in user_extras],
                        limit - len(rows),
                    )
                )
            return rows[:limit]

    def _resolve_user_uuid(self, session, telegram_user_id: int | None):
        if telegram_user_id is None:
            return None
        return get_user_uuid_by_telegram_id(session, telegram_user_id)

    def _source_part_of_speech(self, session, source: DictionaryEntry | UserDictionaryEntry) -> str | None:
        if isinstance(source, UserDictionaryEntry):
            return str(source.part_of_speech or "").strip() or None
        return session.scalar(
            select(DictionaryPartOfSpeech.code)
            .join(DictionaryEntryPartOfSpeech, DictionaryEntryPartOfSpeech.part_of_speech_id == DictionaryPartOfSpeech.id)
            .where(DictionaryEntryPartOfSpeech.entry_id == source.id)
            .order_by(DictionaryPartOfSpeech.code.asc())
            .limit(1)
        )

    def _filter_core_by_part_of_speech(self, statement, part_of_speech: str | None):
        if not part_of_speech:
            return statement
        return (
            statement.join(DictionaryEntryPartOfSpeech, DictionaryEntryPartOfSpeech.entry_id == DictionaryEntry.id)
            .join(DictionaryPartOfSpeech, DictionaryPartOfSpeech.id == DictionaryEntryPartOfSpeech.part_of_speech_id)
            .where(DictionaryPartOfSpeech.code == part_of_speech)
        )

    def _filter_user_by_part_of_speech(self, statement, part_of_speech: str | None):
        if not part_of_speech:
            return statement
        return statement.where(UserDictionaryEntry.part_of_speech == part_of_speech)

    def _available_user_entries_statement(self, user_uuid):
        return select(UserDictionaryEntry).join(
            UserWordAssignment,
            and_(
                UserWordAssignment.user_uuid == user_uuid,
                UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                UserWordAssignment.word_id == UserDictionaryEntry.id,
                UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
            ),
        )

    def _core_rows_to_payload(self, session, rows: list[DictionaryEntry]) -> list[dict[str, Any]]:
        metadata_by_id = load_dictionary_entry_metadata(session, [int(item.id) for item in rows])
        return [
            {
                **dictionary_entry_to_dict(item, metadata=metadata_by_id.get(int(item.id))),
                "word_source": USER_WORD_SOURCE_CORE,
                "word_id": int(item.id),
            }
            for item in rows
        ]


def word_payload_for_conflict(source: DictionaryEntry | UserDictionaryEntry | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, DictionaryEntry):
        return dictionary_entry_to_dict(source)
    if isinstance(source, UserDictionaryEntry):
        return user_dictionary_entry_to_lesson_word(source)
    return source


def filter_safe_similar_word_rows(
    source: DictionaryEntry | UserDictionaryEntry,
    rows: list[DictionaryEntry],
    limit: int,
) -> list[DictionaryEntry]:
    if limit <= 0:
        return []
    source_payload = word_payload_for_conflict(source)
    safe_rows: list[DictionaryEntry] = []
    for row in rows:
        if has_distractor_conflict(source_payload, dictionary_entry_to_dict(row)):
            continue
        safe_rows.append(row)
        if len(safe_rows) == limit:
            break
    return safe_rows


def filter_safe_similar_word_payloads(
    source: DictionaryEntry | UserDictionaryEntry,
    rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    source_payload = word_payload_for_conflict(source)
    safe_rows: list[dict[str, Any]] = []
    for row in rows:
        if has_distractor_conflict(source_payload, row):
            continue
        safe_rows.append(row)
        if len(safe_rows) == limit:
            break
    return safe_rows
