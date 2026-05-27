from __future__ import annotations

from math import ceil
from typing import Any

from app.data_access.dictionary_publish import (
    dictionary_entry_to_dict,
    load_dictionary_entry_metadata,
)
from app.data_access.user_dictionary import user_dictionary_entry_to_lesson_word
from app.data_access.user_dictionary_constants import USER_WORD_SOURCE_CORE, USER_WORD_SOURCE_USER

LESSON_ENTRY_TYPE_QUOTA_TYPES = ("idiom", "phrase_pattern", "phrasal_verb")
LESSON_DUE_REVIEW_RATIO = 0.40
LESSON_PENDING_PRIORITY_RATIO = 0.25
LESSON_NEEDS_WORK_RATIO = 0.20


def build_lesson_entry_type_quotas(words_limit: int) -> dict[str, int]:
    if words_limit < len(LESSON_ENTRY_TYPE_QUOTA_TYPES):
        return {}
    quota_size = max(ceil(words_limit * 0.10), 1)
    return {entry_type: quota_size for entry_type in LESSON_ENTRY_TYPE_QUOTA_TYPES}


def build_lesson_bucket_quotas(words_limit: int) -> dict[str, int]:
    if words_limit <= 0:
        return {"due": 0, "priority": 0, "needs_work": 0, "fresh": 0}
    due = int(words_limit * LESSON_DUE_REVIEW_RATIO)
    priority = int(words_limit * LESSON_PENDING_PRIORITY_RATIO)
    needs_work = int(words_limit * LESSON_NEEDS_WORK_RATIO)
    priority = max(priority, 1)
    if words_limit >= 2:
        due = max(due, 1)
    if words_limit >= 4:
        due = max(due, 1)
        needs_work = max(needs_work, 1)
    fresh = max(words_limit - due - priority - needs_work, 0)
    return {"due": due, "priority": priority, "needs_work": needs_work, "fresh": fresh}


def payload_word_id(word: dict[str, Any]) -> int:
    return int(word.get("word_id") or word["id"])


def payload_key(word: dict[str, Any]) -> tuple[str, int]:
    return str(word.get("word_source") or USER_WORD_SOURCE_CORE), payload_word_id(word)


def finalize_selected_words(words: list[dict[str, Any]], words_limit: int) -> list[dict[str, Any]]:
    priority_words = [word for word in words if word.get("is_priority")]
    regular_words = [word for word in words if not word.get("is_priority")]
    priority_words.sort(
        key=lambda word: (
            -int(word.get("priority_rank") or 0),
            -int(word.get("review_priority") or 0),
            _sort_datetime_value(word.get("last_seen_at")),
            _sort_datetime_value(word.get("next_review_at")),
        ),
    )
    return (priority_words + regular_words)[:words_limit]


def _sort_datetime_value(value: Any) -> float:
    if value is None:
        return 0.0
    if hasattr(value, "timestamp"):
        return float(value.timestamp())
    return 0.0


def serialize_followup_words(
    session,
    session_words,
    core_entries,
    user_entries,
    review_by_key: dict[tuple[str, int], int],
) -> list[dict[str, Any]]:
    core_entries_by_id = {int(entry.id): entry for entry in core_entries}
    user_entries_by_id = {int(entry.id): entry for entry in user_entries}
    metadata_by_id = load_dictionary_entry_metadata(session, list(core_entries_by_id))
    payload: list[dict[str, Any]] = []
    for session_word in session_words:
        word_source = session_word.word_source or USER_WORD_SOURCE_CORE
        word_id = int(session_word.word_id)
        review_priority = review_by_key.get((word_source, word_id), 0)
        if word_source == USER_WORD_SOURCE_USER:
            user_entry = user_entries_by_id.get(word_id)
            if user_entry is None:
                continue
            payload.append(user_dictionary_entry_to_lesson_word(user_entry, review_priority=review_priority))
            continue
        core_entry = core_entries_by_id.get(word_id)
        if core_entry is None:
            continue
        payload.append(
            {
                **dictionary_entry_to_dict(
                    core_entry,
                    metadata=metadata_by_id.get(word_id),
                    review_priority=review_priority,
                ),
                "word_source": USER_WORD_SOURCE_CORE,
                "word_id": word_id,
            }
        )
    return payload
