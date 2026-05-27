from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.data_access.filtering import normalize_filter_values
from app.data_access.user_dictionary_assignments import USER_WORD_SOURCE_USER
from app.data_access.user_import_serialization import import_item_to_dict
from app.models import (
    LanguageLevel,
    UserDictionaryEntry,
    UserVocabularyImportItem,
    UserWordAssignment,
)
from app.reference.dictionary_entries import DICTIONARY_PART_OF_SPEECH_TYPES


def list_admin_entries(
    session,
    *,
    page: int,
    page_size: int,
    search: str = "",
    status: str | list[str] | None = None,
    part_of_speech: str | list[str] | None = None,
    level_id: int | list[int] | None = None,
    user_dictionary_statuses: tuple[str, ...],
) -> dict[str, Any]:
    from app.data_access.user_dictionary import user_dictionary_entry_to_dict

    offset = (max(page, 1) - 1) * page_size
    filters = []
    normalized_search = search.strip()
    if normalized_search:
        like_value = f"%{normalized_search.lower()}%"
        filters.append(
            or_(
                func.lower(UserDictionaryEntry.word).like(like_value),
                func.lower(UserDictionaryEntry.normalized_word).like(like_value),
                func.lower(UserDictionaryEntry.translation_uk).like(like_value),
                func.lower(UserDictionaryEntry.translation_ru).like(like_value),
                func.lower(UserDictionaryEntry.translation_pl).like(like_value),
            )
        )
    status_values = normalize_filter_values(status)
    if status_values:
        filters.append(UserDictionaryEntry.status.in_(status_values))
    part_of_speech_values = normalize_filter_values(part_of_speech)
    if part_of_speech_values:
        filters.append(UserDictionaryEntry.part_of_speech.in_(part_of_speech_values))
    level_values = [int(value) for value in normalize_filter_values(level_id)]
    if level_values:
        filters.append(UserDictionaryEntry.level_id.in_(level_values))

    assignment_counts = (
        select(
            UserWordAssignment.word_id.label("entry_id"),
            func.count(UserWordAssignment.id).label("assignment_count"),
        )
        .where(UserWordAssignment.word_source == USER_WORD_SOURCE_USER)
        .group_by(UserWordAssignment.word_id)
        .subquery()
    )
    total = int(session.scalar(select(func.count(UserDictionaryEntry.id)).where(*filters)) or 0)
    rows = session.execute(
        select(UserDictionaryEntry, assignment_counts.c.assignment_count)
        .options(selectinload(UserDictionaryEntry.level))
        .outerjoin(assignment_counts, assignment_counts.c.entry_id == UserDictionaryEntry.id)
        .where(*filters)
        .order_by(UserDictionaryEntry.updated.desc(), UserDictionaryEntry.id.desc())
        .offset(offset)
        .limit(page_size)
    ).all()
    items = []
    for entry, assignment_count in rows:
        payload = user_dictionary_entry_to_dict(entry)
        payload["assignment_count"] = int(assignment_count or 0)
        payload["failure_reason"] = failure_reason_from_provider_status(
            payload.get("source_provider_status_json")
        )
        payload["audio_url"] = f"/api/v1/admin/user-dictionary/entries/{entry.id}/audio" if entry.audio_path else None
        items.append(payload)
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


def get_admin_entry_detail(session, *, entry_id: int) -> dict[str, Any] | None:
    from app.data_access.user_dictionary import user_dictionary_entry_to_dict

    entry = session.scalar(
        select(UserDictionaryEntry)
        .options(selectinload(UserDictionaryEntry.level))
        .where(UserDictionaryEntry.id == entry_id)
        .limit(1)
    )
    if entry is None:
        return None
    import_items = session.scalars(
        select(UserVocabularyImportItem)
        .where(UserVocabularyImportItem.user_dictionary_entry_id == entry_id)
        .order_by(UserVocabularyImportItem.updated.desc(), UserVocabularyImportItem.id.desc())
    ).all()
    assignments_count = int(
        session.scalar(
            select(func.count(UserWordAssignment.id)).where(
                UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                UserWordAssignment.word_id == entry_id,
            )
        )
        or 0
    )
    payload = user_dictionary_entry_to_dict(entry)
    item_payloads = [import_item_to_dict(row) for row in import_items]
    payload["assignment_count"] = assignments_count
    payload["audio_url"] = f"/api/v1/admin/user-dictionary/entries/{entry.id}/audio" if entry.audio_path else None
    payload["import_items"] = item_payloads
    payload["failure_reason"] = failure_reason_from_import_items(
        item_payloads,
        payload.get("source_provider_status_json"),
    )
    payload["error_log_search"] = f"user_dictionary_entry_id={entry_id}"
    return payload


def failure_reason_from_import_items(
    import_items: list[dict[str, Any]],
    provider_status: Any,
) -> str | None:
    for item in import_items:
        error_text = str(item.get("error_text") or "").strip()
        if error_text:
            return error_text
    return failure_reason_from_provider_status(provider_status)


def failure_reason_from_provider_status(provider_status: Any) -> str | None:
    if not isinstance(provider_status, dict):
        return None
    candidates = (
        ("details_phase", "error"),
        ("details_validation", "error"),
        ("word_details_provider", "error"),
        ("google_tts", "error"),
        ("google_tts", "last_error"),
        ("embedding_phase", "last_error"),
        ("embedding_phase", "error"),
    )
    for section, key in candidates:
        section_payload = provider_status.get(section)
        if not isinstance(section_payload, dict):
            continue
        value = str(section_payload.get(key) or "").strip()
        if value:
            return value
    return None


def get_admin_filter_metadata(session, *, user_dictionary_statuses: tuple[str, ...]) -> dict[str, Any]:
    levels = session.scalars(select(LanguageLevel).order_by(LanguageLevel.id.asc())).all()
    return {
        "entity": "user_dictionary",
        "page_sizes": [50, 100],
        "filters": [
            {"name": "search", "type": "text", "label": "Search"},
            {
                "name": "status",
                "type": "multi_select",
                "label": "Status",
                "options": [{"value": value, "label": value} for value in user_dictionary_statuses],
            },
            {
                "name": "part_of_speech",
                "type": "multi_select",
                "label": "Part of speech",
                "options": [{"value": value, "label": value} for value in DICTIONARY_PART_OF_SPEECH_TYPES],
            },
            {
                "name": "level_id",
                "type": "multi_select",
                "label": "Level",
                "options": [{"value": str(row.id), "label": row.title} for row in levels],
            },
        ],
    }
