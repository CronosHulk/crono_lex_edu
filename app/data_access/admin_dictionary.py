from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.data_access.dictionary_publish import (
    dictionary_entry_to_dict,
    load_dictionary_entry_metadata,
)
from app.data_access.filtering import normalize_filter_values
from app.data_access.serialization import normalize_examples_json
from app.helpers.audio_files import delete_audio_file_if_under_roots
from app.models import (
    DictionaryCategory,
    DictionaryEntry,
    DictionaryEntryCategory,
    DictionaryEntryPartOfSpeech,
    DictionaryPartOfSpeech,
)
from app.orm import SessionManager
from app.reference.dictionary_entries import (
    DICTIONARY_ENTRY_TYPE_LABELS,
    DICTIONARY_ENTRY_TYPES,
    normalize_dictionary_entry_type,
)
from app.storage.audio import AudioStorageProvider


def enrich_admin_dictionary_row(row: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(row)
    enriched["audio_url"] = f"/api/v1/admin/dictionary/entries/{row['id']}/audio" if row.get("audio_path") else None
    enriched["translations_multiline"] = "\n".join(
        [
            f"uk: {row.get('translation_uk') or ''}",
            f"ru: {row.get('translation_ru') or ''}",
            f"pl: {row.get('translation_pl') or ''}",
        ]
    )
    return enriched


class AdminDictionaryRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def list_entries(
        self,
        *,
        page: int,
        page_size: int,
        archived: bool,
        search: str = "",
        part_of_speech: str | list[str] | None = None,
        category: str | list[str] | None = None,
        entry_type: str | list[str] | None = None,
        verified: str | None = None,
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = [DictionaryEntry.is_archived.is_(archived)]
            normalized_search = search.strip()
            if normalized_search:
                like_value = f"%{normalized_search.lower()}%"
                filters.append(
                    or_(
                        func.lower(DictionaryEntry.word).like(like_value),
                        func.lower(DictionaryEntry.normalized_word).like(like_value),
                        func.lower(DictionaryEntry.translation_uk).like(like_value),
                        func.lower(DictionaryEntry.translation_ru).like(like_value),
                        func.lower(DictionaryEntry.translation_pl).like(like_value),
                    )
                )
            entry_type_values = normalize_filter_values(entry_type)
            if entry_type_values:
                filters.append(DictionaryEntry.entry_type.in_([normalize_dictionary_entry_type(value) for value in entry_type_values]))
            if verified == "verified":
                filters.append(DictionaryEntry.is_teacher_verified.is_(True))
            elif verified == "unverified":
                filters.append(DictionaryEntry.is_teacher_verified.is_(False))

            query = select(DictionaryEntry).options(selectinload(DictionaryEntry.level)).where(*filters)
            count_query = select(func.count(func.distinct(DictionaryEntry.id))).where(*filters)

            pos_values = normalize_filter_values(part_of_speech)
            if pos_values:
                query = query.join(DictionaryEntryPartOfSpeech).join(DictionaryPartOfSpeech)
                count_query = count_query.join(DictionaryEntryPartOfSpeech).join(DictionaryPartOfSpeech)
                query = query.where(DictionaryPartOfSpeech.code.in_(pos_values))
                count_query = count_query.where(DictionaryPartOfSpeech.code.in_(pos_values))

            category_values = normalize_filter_values(category)
            if category_values:
                query = query.join(DictionaryEntryCategory).join(DictionaryCategory)
                count_query = count_query.join(DictionaryEntryCategory).join(DictionaryCategory)
                query = query.where(DictionaryCategory.code.in_(category_values))
                count_query = count_query.where(DictionaryCategory.code.in_(category_values))

            total = int(session.scalar(count_query) or 0)
            entries = session.scalars(
                query.distinct()
                .order_by(DictionaryEntry.word.asc(), DictionaryEntry.id.asc())
                .offset(offset)
                .limit(page_size)
            ).all()
            metadata = load_dictionary_entry_metadata(session, [int(entry.id) for entry in entries])
            return {
                "items": [
                    enrich_admin_dictionary_row(
                        dictionary_entry_to_dict(entry, metadata=metadata.get(int(entry.id)))
                    )
                    for entry in entries
                ],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            entry = session.get(DictionaryEntry, entry_id)
            if entry is None:
                return None
            metadata = load_dictionary_entry_metadata(session, [int(entry.id)])
            return enrich_admin_dictionary_row(dictionary_entry_to_dict(entry, metadata=metadata.get(int(entry.id))))

    def update_entry(
        self,
        entry_id: int,
        *,
        audio_storage_provider: AudioStorageProvider,
        word: str | None = None,
        transcription: str | None = None,
        translation_uk: str | None = None,
        translation_ru: str | None = None,
        translation_pl: str | None = None,
        examples_json: list[str] | None = None,
        entry_type: str | None = None,
        audio_roots: list[Path | str] | None = None,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            entry = session.get(DictionaryEntry, entry_id)
            if entry is None:
                return None

            embedding_sensitive_changed = False
            if word is not None and entry.word != word:
                old_audio_path = entry.audio_path
                entry.word = word
                entry.normalized_word = word.lower()
                if old_audio_path:
                    delete_audio_file_if_under_roots(
                        old_audio_path,
                        audio_roots or [],
                        storage_provider=audio_storage_provider,
                    )
                entry.audio_path = ""
                embedding_sensitive_changed = True
            if transcription is not None:
                entry.transcription = transcription or None
            if translation_uk is not None and entry.translation_uk != translation_uk:
                entry.translation_uk = translation_uk
                embedding_sensitive_changed = True
            if translation_ru is not None and entry.translation_ru != (translation_ru or None):
                entry.translation_ru = translation_ru or None
                embedding_sensitive_changed = True
            if translation_pl is not None and entry.translation_pl != (translation_pl or None):
                entry.translation_pl = translation_pl or None
                embedding_sensitive_changed = True
            if examples_json is not None:
                normalized_examples = normalize_examples_json(examples_json)
                if normalize_examples_json(entry.examples_json) != normalized_examples:
                    entry.examples_json = normalized_examples
                    embedding_sensitive_changed = True
            if entry_type is not None:
                entry.entry_type = normalize_dictionary_entry_type(entry_type)
            if embedding_sensitive_changed:
                entry.embedding = None
                entry.embedding_model = None
                entry.is_embedding_ready = False
            entry.updated = current_time
            session.flush()
            metadata = load_dictionary_entry_metadata(session, [int(entry.id)])
            return enrich_admin_dictionary_row(dictionary_entry_to_dict(entry, metadata=metadata.get(int(entry.id))))

    def get_filter_metadata(self) -> dict[str, Any]:
        with self.session_manager.session() as session:
            parts = session.scalars(select(DictionaryPartOfSpeech).order_by(DictionaryPartOfSpeech.title.asc())).all()
            categories = session.scalars(select(DictionaryCategory).order_by(DictionaryCategory.code.asc())).all()
            return {
                "entity": "dictionary",
                "page_sizes": [50, 100],
                "filters": [
                    {"name": "search", "type": "text", "label": "Пошук"},
                    {
                        "name": "entry_type",
                        "type": "multi_select",
                        "label": "Entry type",
                        "options": [
                            {"value": value, "label": DICTIONARY_ENTRY_TYPE_LABELS[value]}
                            for value in DICTIONARY_ENTRY_TYPES
                        ],
                    },
                    {
                        "name": "part_of_speech",
                        "type": "multi_select",
                        "label": "Part of speech",
                        "options": [{"value": row.code, "label": row.title} for row in parts],
                    },
                    {
                        "name": "category",
                        "type": "multi_select",
                        "label": "Category",
                        "options": [{"value": row.code, "label": row.title} for row in categories],
                    },
                    {
                        "name": "verified",
                        "type": "select",
                        "label": "Teacher verified",
                        "options": [
                            {"value": "all", "label": "all"},
                            {"value": "verified", "label": "verified"},
                            {"value": "unverified", "label": "unverified"},
                        ],
                    },
                ],
            }

    def get_entry_audio(self, entry_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(DictionaryEntry, entry_id)
            if row is None or not row.audio_path:
                return None
            return {"id": row.id, "audio_path": row.audio_path}

    def set_entry_archived(self, entry_id: int, *, is_archived: bool, current_time: datetime) -> bool:
        with self.session_manager.session() as session:
            row = session.get(DictionaryEntry, entry_id)
            if row is None:
                return False
            row.is_archived = is_archived
            row.updated = current_time
            return True

    def mark_entries_teacher_verified(
        self,
        entry_ids: list[int],
        *,
        verified_by_user_uuid: str | UUID,
        current_time: datetime,
    ) -> int:
        normalized_ids = [int(entry_id) for entry_id in dict.fromkeys(entry_ids)]
        if not normalized_ids:
            return 0
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(DictionaryEntry).where(DictionaryEntry.id.in_(normalized_ids), DictionaryEntry.is_archived.is_(False))
            ).all()
            for row in rows:
                row.is_teacher_verified = True
                row.teacher_verified_by_user_uuid = verified_by_user_uuid
                row.teacher_verified_at = current_time
                row.updated = current_time
            return len(rows)

    def delete_entry(self, entry_id: int) -> bool:
        with self.session_manager.session() as session:
            row = session.get(DictionaryEntry, entry_id)
            if row is None:
                return False
            session.delete(row)
            return True
