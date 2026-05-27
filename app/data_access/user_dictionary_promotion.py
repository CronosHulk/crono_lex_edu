from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select

from app.data_access.dictionary_publish import (
    dictionary_entry_to_dict,
    load_dictionary_entry_metadata,
    normalize_part_of_speech_code,
)
from app.data_access.serialization import normalize_examples_json
from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_ARCHIVED,
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_ASSIGNMENT_HIDDEN,
    USER_WORD_ASSIGNMENT_WAITING,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
)
from app.models import (
    DictionaryEntry,
    DictionaryEntryPartOfSpeech,
    DictionaryPartOfSpeech,
    LearningSessionWord,
    UserDictionaryEntry,
    UserVocabularyImportItem,
    UserWordAssignment,
)
from app.reference.dictionary_entries import (
    normalize_dictionary_entry_type,
    normalize_dictionary_part_of_speech,
)


def promote_user_dictionary_entry_to_core(
    session,
    entry_id: int,
    *,
    audio_path: str,
    current_time: datetime,
) -> dict[str, Any] | None:
    user_entry = session.get(UserDictionaryEntry, entry_id)
    if user_entry is None:
        return None

    normalized_word = _normalize_lookup_word(user_entry.word)
    part_of_speech = normalize_dictionary_part_of_speech(user_entry.part_of_speech)
    part_of_speech_code = normalize_part_of_speech_code(part_of_speech)
    entry = _find_core_entry_by_word_and_part_of_speech(session, normalized_word, part_of_speech_code)
    if entry is None:
        entry = _create_core_entry_from_user_entry(
            session,
            user_entry,
            normalized_word=normalized_word,
            audio_path=audio_path,
            current_time=current_time,
        )
    _ensure_dictionary_part_of_speech_link(session, entry, part_of_speech)

    move_user_entry_references_to_core(
        session,
        user_entry_id=int(user_entry.id),
        core_entry_id=int(entry.id),
        current_time=current_time,
    )
    session.delete(user_entry)
    session.flush()
    metadata_by_id = load_dictionary_entry_metadata(session, [int(entry.id)])
    return dictionary_entry_to_dict(entry, metadata=metadata_by_id.get(int(entry.id)))


def _find_core_entry_by_word_and_part_of_speech(
    session,
    normalized_word: str,
    part_of_speech_code: str,
) -> DictionaryEntry | None:
    return session.scalar(
        select(DictionaryEntry)
        .join(
            DictionaryEntryPartOfSpeech,
            DictionaryEntryPartOfSpeech.entry_id == DictionaryEntry.id,
        )
        .join(
            DictionaryPartOfSpeech,
            DictionaryPartOfSpeech.id == DictionaryEntryPartOfSpeech.part_of_speech_id,
        )
        .where(
            or_(
                func.lower(DictionaryEntry.normalized_word) == normalized_word,
                func.lower(DictionaryEntry.word) == normalized_word,
            ),
            DictionaryPartOfSpeech.code == part_of_speech_code,
        )
        .limit(1)
    )


def _create_core_entry_from_user_entry(
    session,
    user_entry: UserDictionaryEntry,
    *,
    normalized_word: str,
    audio_path: str,
    current_time: datetime,
) -> DictionaryEntry:
    entry = DictionaryEntry(
        source_namespace="user_dictionary",
        source_ref=f"user_dictionary:{user_entry.id}",
        entry_key=f"user_dictionary_{user_entry.id}",
        word=user_entry.word,
        normalized_word=normalized_word,
        entry_type=normalize_dictionary_entry_type(user_entry.entry_type or "word"),
        level_id=user_entry.level_id,
        transcription=user_entry.transcription,
        translation_uk=str(user_entry.translation_uk or ""),
        translation_ru=str(user_entry.translation_ru or "") or None,
        translation_pl=str(user_entry.translation_pl or "") or None,
        examples_json=normalize_examples_json(user_entry.examples_json),
        audio_path=audio_path,
        embedding=user_entry.embedding,
        embedding_model=user_entry.embedding_model,
        is_embedding_ready=bool(user_entry.is_embedding_ready),
        created=current_time,
        updated=current_time,
    )
    session.add(entry)
    session.flush()
    return entry


def move_user_entry_references_to_core(
    session,
    *,
    user_entry_id: int,
    core_entry_id: int,
    current_time: datetime,
) -> None:
    _move_user_assignments_to_core(
        session,
        user_entry_id=user_entry_id,
        core_entry_id=core_entry_id,
        current_time=current_time,
    )
    _move_session_words_to_core(
        session,
        user_entry_id=user_entry_id,
        core_entry_id=core_entry_id,
        current_time=current_time,
    )
    _move_import_items_to_core(
        session,
        user_entry_id=user_entry_id,
        core_entry_id=core_entry_id,
        current_time=current_time,
    )


def _move_user_assignments_to_core(
    session,
    *,
    user_entry_id: int,
    core_entry_id: int,
    current_time: datetime,
) -> None:
    rows = session.scalars(
        select(UserWordAssignment).where(
            UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
            UserWordAssignment.word_id == user_entry_id,
        )
    ).all()
    for row in rows:
        existing = session.scalar(
            select(UserWordAssignment)
            .where(
                UserWordAssignment.user_uuid == row.user_uuid,
                UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                UserWordAssignment.word_id == core_entry_id,
            )
            .limit(1)
        )
        if existing is None:
            row.word_source = USER_WORD_SOURCE_CORE
            row.word_id = core_entry_id
            row.updated = current_time
            continue
        existing.status = _merge_assignment_status(existing.status, row.status)
        _merge_assignment_learning(existing, row, current_time=current_time)
        existing.import_job_id = existing.import_job_id or row.import_job_id
        existing.import_item_id = existing.import_item_id or row.import_item_id
        existing.updated = current_time
        session.delete(row)


def _merge_assignment_status(left: str | None, right: str | None) -> str:
    statuses = {left or USER_WORD_ASSIGNMENT_AVAILABLE, right or USER_WORD_ASSIGNMENT_AVAILABLE}
    if USER_WORD_ASSIGNMENT_ARCHIVED in statuses:
        return USER_WORD_ASSIGNMENT_ARCHIVED
    if USER_WORD_ASSIGNMENT_HIDDEN in statuses:
        return USER_WORD_ASSIGNMENT_HIDDEN
    if USER_WORD_ASSIGNMENT_AVAILABLE in statuses:
        return USER_WORD_ASSIGNMENT_AVAILABLE
    return USER_WORD_ASSIGNMENT_WAITING


def _merge_assignment_learning(target: UserWordAssignment, source: UserWordAssignment, *, current_time: datetime) -> None:
    target.priority_rank = max(int(target.priority_rank or 0), int(source.priority_rank or 0))
    target.is_known = bool(target.is_known or source.is_known)
    target.learning_state = _merge_learning_state(target.learning_state, source.learning_state)
    target.control_success_streak = max(int(target.control_success_streak or 0), int(source.control_success_streak or 0))
    target.review_priority = max(int(target.review_priority or 0), int(source.review_priority or 0))
    target.last_level_run_id = target.last_level_run_id or source.last_level_run_id
    target.last_completed = _max_datetime(target.last_completed, source.last_completed)
    target.next_review_at = _min_datetime(target.next_review_at, source.next_review_at)
    target.updated = current_time


def _merge_learning_state(left: str | None, right: str | None) -> str:
    order = {"learning": 0, "needs_work": 1, "learned": 2}
    return max((left or "learning", right or "learning"), key=lambda item: order.get(item, 0))


def _move_session_words_to_core(
    session,
    *,
    user_entry_id: int,
    core_entry_id: int,
    current_time: datetime,
) -> None:
    rows = session.scalars(
        select(LearningSessionWord).where(
            LearningSessionWord.word_source == USER_WORD_SOURCE_USER,
            LearningSessionWord.word_id == user_entry_id,
        )
    ).all()
    for row in rows:
        existing = session.scalar(
            select(LearningSessionWord)
            .where(
                LearningSessionWord.session_id == row.session_id,
                LearningSessionWord.word_source == USER_WORD_SOURCE_CORE,
                LearningSessionWord.word_id == core_entry_id,
            )
            .limit(1)
        )
        if existing is None:
            row.word_source = USER_WORD_SOURCE_CORE
            row.word_id = core_entry_id
            if row.session is not None:
                row.session.updated = current_time
            continue
        _merge_session_word(existing, row)
        if existing.session is not None:
            existing.session.updated = current_time
        session.delete(row)


def _merge_session_word(target: LearningSessionWord, source: LearningSessionWord) -> None:
    target.en_uk_attempts = max(int(target.en_uk_attempts or 0), int(source.en_uk_attempts or 0))
    target.en_uk_correct = bool(target.en_uk_correct or source.en_uk_correct)
    target.uk_en_attempts = max(int(target.uk_en_attempts or 0), int(source.uk_en_attempts or 0))
    target.uk_en_correct = bool(target.uk_en_correct or source.uk_en_correct)
    target.gap_attempts = max(int(target.gap_attempts or 0), int(source.gap_attempts or 0))
    target.gap_correct = bool(target.gap_correct or source.gap_correct)
    if _card_status_rank(source.card_status) > _card_status_rank(target.card_status):
        target.card_status = source.card_status


def _card_status_rank(value: str | None) -> int:
    order = {"pending": 0, "next": 1, "completed": 2}
    return order.get(value or "pending", 0)


def _move_import_items_to_core(
    session,
    *,
    user_entry_id: int,
    core_entry_id: int,
    current_time: datetime,
) -> None:
    rows = session.scalars(
        select(UserVocabularyImportItem).where(UserVocabularyImportItem.user_dictionary_entry_id == user_entry_id)
    ).all()
    for row in rows:
        row.existing_word_id = core_entry_id
        row.user_dictionary_entry_id = None
        row.updated = current_time


def _max_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _min_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def _normalize_lookup_word(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _ensure_dictionary_part_of_speech_link(session, entry: DictionaryEntry, part_of_speech_title: str) -> None:
    title = str(part_of_speech_title or "").strip()
    if not title:
        return
    part_of_speech_code = normalize_part_of_speech_code(title)
    part_of_speech = session.scalar(
        select(DictionaryPartOfSpeech).where(DictionaryPartOfSpeech.code == part_of_speech_code).limit(1)
    )
    if part_of_speech is None:
        part_of_speech = DictionaryPartOfSpeech(code=part_of_speech_code, title=title)
        session.add(part_of_speech)
        session.flush()
    link = session.get(
        DictionaryEntryPartOfSpeech,
        {"entry_id": entry.id, "part_of_speech_id": part_of_speech.id},
    )
    if link is None:
        session.add(
            DictionaryEntryPartOfSpeech(
                entry_id=entry.id,
                part_of_speech_id=part_of_speech.id,
            )
        )
