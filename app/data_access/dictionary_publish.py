from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_access.serialization import normalize_examples_json
from app.models import (
    DictionaryCategory,
    DictionaryEntry,
    DictionaryEntryCategory,
    DictionaryEntryPartOfSpeech,
    DictionaryPartOfSpeech,
)
from app.reference.dictionary_entries import normalize_dictionary_entry_type


def normalize_part_of_speech_code(value: str) -> str:
    return "_".join(part for part in str(value).strip().lower().replace("/", " ").split() if part)


def load_dictionary_entry_metadata(session: Session, entry_ids: Iterable[int]) -> dict[int, dict[str, list[str]]]:
    normalized_ids = [int(entry_id) for entry_id in entry_ids]
    if not normalized_ids:
        return {}

    metadata: dict[int, dict[str, list[str]]] = {
        entry_id: {"parts_of_speech": [], "categories": []}
        for entry_id in normalized_ids
    }

    part_rows = session.execute(
        select(
            DictionaryEntryPartOfSpeech.entry_id,
            DictionaryEntryPartOfSpeech.part_of_speech_id,
            DictionaryEntryPartOfSpeech.created,
            DictionaryPartOfSpeech.title,
        )
        .join(DictionaryPartOfSpeech, DictionaryPartOfSpeech.id == DictionaryEntryPartOfSpeech.part_of_speech_id)
        .where(DictionaryEntryPartOfSpeech.entry_id.in_(normalized_ids))
        .order_by(
            DictionaryEntryPartOfSpeech.entry_id.asc(),
            DictionaryEntryPartOfSpeech.created.asc(),
            DictionaryEntryPartOfSpeech.part_of_speech_id.asc(),
        )
    ).all()
    for entry_id, _, _, title in part_rows:
        bucket = metadata.setdefault(int(entry_id), {"parts_of_speech": [], "categories": []})["parts_of_speech"]
        candidate = str(title).strip()
        if candidate and candidate not in bucket:
            bucket.append(candidate)

    category_rows = session.execute(
        select(
            DictionaryEntryCategory.entry_id,
            DictionaryEntryCategory.category_id,
            DictionaryEntryCategory.created,
            DictionaryCategory.code,
        )
        .join(DictionaryCategory, DictionaryCategory.id == DictionaryEntryCategory.category_id)
        .where(DictionaryEntryCategory.entry_id.in_(normalized_ids))
        .order_by(
            DictionaryEntryCategory.entry_id.asc(),
            DictionaryEntryCategory.created.asc(),
            DictionaryEntryCategory.category_id.asc(),
        )
    ).all()
    for entry_id, _, _, code in category_rows:
        bucket = metadata.setdefault(int(entry_id), {"parts_of_speech": [], "categories": []})["categories"]
        candidate = str(code).strip()
        if candidate and candidate not in bucket:
            bucket.append(candidate)

    return metadata


def dictionary_entry_to_dict(
    entry: DictionaryEntry,
    *,
    metadata: dict[str, list[str]] | None = None,
    review_priority: int = 0,
    is_priority: bool = False,
) -> dict[str, Any]:
    resolved_metadata = metadata or {"parts_of_speech": [], "categories": []}
    level = getattr(entry, "level", None)
    return {
        "id": entry.id,
        "word": entry.word,
        "part_of_speech": ", ".join(resolved_metadata.get("parts_of_speech", [])),
        "parts_of_speech": list(resolved_metadata.get("parts_of_speech", [])),
        "categories": list(resolved_metadata.get("categories", [])),
        "phonetic_us": entry.transcription,
        "audio_path": entry.audio_path,
        "examples_json": normalize_examples_json(entry.examples_json),
        "level_id": entry.level_id,
        "level_title": getattr(level, "title", None),
        "entry_type": normalize_dictionary_entry_type(entry.entry_type or "word"),
        "has_embedding": entry.embedding is not None,
        "translation_uk": entry.translation_uk,
        "translation_ru": entry.translation_ru,
        "translation_pl": entry.translation_pl,
        "is_archived": entry.is_archived,
        "is_teacher_verified": bool(getattr(entry, "is_teacher_verified", False)),
        "teacher_verified_by_user_uuid": (
            str(entry.teacher_verified_by_user_uuid) if getattr(entry, "teacher_verified_by_user_uuid", None) else None
        ),
        "teacher_verified_at": getattr(entry, "teacher_verified_at", None),
        "review_priority": review_priority,
        "is_priority": is_priority,
    }
