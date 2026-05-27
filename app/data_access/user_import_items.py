from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from app.data_access.dictionary_publish import load_dictionary_entry_metadata
from app.data_access.filtering import normalize_filter_values
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.data_access.user_import_jobs import import_item_to_dict
from app.models import DictionaryEntry, UserDictionaryEntry, UserVocabularyImportItem
from app.models.dictionary import DictionaryCategory, DictionaryEntryCategory
from app.models.shared import LanguageLevel
from app.orm import SessionManager

IMPORTED_ROTATION_STATUSES = ("found_existing", "imported")
IMPORTED_PENDING_STATUSES = (
    "pending",
    "waiting_for_user_dictionary_entry",
    "queued_for_details",
    "queued_for_audio",
    "queued_for_embedding",
)


class UserImportItemRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def mark_existing_word(self, item_id: int, *, word_id: int, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(UserVocabularyImportItem, item_id)
            if row is None:
                return
            row.status = "found_existing"
            row.existing_word_id = word_id
            row.user_dictionary_entry_id = None
            row.error_text = None
            row.processed = current_time
            row.updated = current_time

    def list_learning_words(
        self,
        telegram_user_id: int,
        *,
        mode: str,
        page: int,
        page_size: int,
        word: str = "",
        topic: str | list[str] = "",
        level: str = "",
    ) -> dict[str, Any]:
        offset = (page - 1) * page_size
        statuses = IMPORTED_ROTATION_STATUSES if mode == "imported_rotation" else IMPORTED_PENDING_STATUSES
        normalized_word = word.strip().lower()
        topic_values = normalize_filter_values(topic)
        normalized_level = level.strip()

        dictionary_level = aliased(LanguageLevel)
        pending_level = aliased(LanguageLevel)

        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
            filters = [
                UserVocabularyImportItem.user_uuid == user_uuid,
                UserVocabularyImportItem.status.in_(statuses),
            ]
            if normalized_word:
                like_value = f"%{normalized_word}%"
                filters.append(
                    or_(
                        func.lower(UserVocabularyImportItem.raw_value).like(like_value),
                        func.lower(UserVocabularyImportItem.lookup_word).like(like_value),
                        func.lower(DictionaryEntry.word).like(like_value),
                        func.lower(UserDictionaryEntry.word).like(like_value),
                    )
                )
            if normalized_level:
                filters.append(or_(dictionary_level.title == normalized_level, pending_level.title == normalized_level))
            if topic_values:
                filters.append(
                    UserVocabularyImportItem.existing_word_id.in_(
                        select(DictionaryEntryCategory.entry_id)
                        .join(DictionaryCategory, DictionaryCategory.id == DictionaryEntryCategory.category_id)
                        .where(DictionaryCategory.code.in_(topic_values))
                    )
                )

            base_query = (
                select(UserVocabularyImportItem)
                .outerjoin(DictionaryEntry, DictionaryEntry.id == UserVocabularyImportItem.existing_word_id)
                .outerjoin(UserDictionaryEntry, UserDictionaryEntry.id == UserVocabularyImportItem.user_dictionary_entry_id)
                .outerjoin(dictionary_level, dictionary_level.id == DictionaryEntry.level_id)
                .outerjoin(pending_level, pending_level.id == UserDictionaryEntry.level_id)
                .where(*filters)
            )
            total = session.scalar(select(func.count()).select_from(base_query.subquery()))
            rows = session.execute(
                select(UserVocabularyImportItem, DictionaryEntry, UserDictionaryEntry, dictionary_level.title, pending_level.title)
                .outerjoin(DictionaryEntry, DictionaryEntry.id == UserVocabularyImportItem.existing_word_id)
                .outerjoin(UserDictionaryEntry, UserDictionaryEntry.id == UserVocabularyImportItem.user_dictionary_entry_id)
                .outerjoin(dictionary_level, dictionary_level.id == DictionaryEntry.level_id)
                .outerjoin(pending_level, pending_level.id == UserDictionaryEntry.level_id)
                .where(*filters)
                .order_by(UserVocabularyImportItem.updated.desc(), UserVocabularyImportItem.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            existing_entry_ids = [int(entry.id) for _, entry, _, _, _ in rows if entry is not None]
            metadata_by_id = load_dictionary_entry_metadata(session, existing_entry_ids)

            items = []
            for item, entry, user_entry, dictionary_level_title, pending_level_title in rows:
                word = entry.word if entry is not None else user_entry.word if user_entry is not None else item.raw_value
                translations = _read_word_translations(entry, user_entry)
                translation = (
                    translations["translation_uk"]
                    or translations["translation_ru"]
                    or translations["translation_pl"]
                )
                categories = metadata_by_id.get(int(entry.id), {"categories": []}).get("categories", []) if entry is not None else []
                items.append(
                    {
                        "id": int(item.id),
                        "word": word,
                        "topic": ", ".join(categories),
                        "level": dictionary_level_title or pending_level_title or "",
                        "translation": translation,
                        **translations,
                        "learning_state": item.status,
                        "import_job_id": int(item.import_job_id),
                    }
                )

            total_count = int(total or 0)
            return {
                "items": items,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "pages": (total_count + page_size - 1) // page_size if total_count else 0,
            }

    def mark_user_dictionary_entry(
        self,
        item_id: int,
        *,
        user_dictionary_entry_id: int,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None:
        with self.session_manager.session() as session:
            row = session.get(UserVocabularyImportItem, item_id)
            if row is None:
                return
            row.status = status
            row.existing_word_id = None
            row.user_dictionary_entry_id = user_dictionary_entry_id
            row.error_text = error_text
            row.processed = current_time
            row.updated = current_time

    def mark_rejected(self, item_id: int, *, error_text: str, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(UserVocabularyImportItem, item_id)
            if row is None:
                return
            row.status = "rejected"
            row.error_text = error_text
            row.processed = current_time
            row.updated = current_time

    def sync_for_user_dictionary_entry(
        self,
        user_dictionary_entry_id: int,
        *,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(UserVocabularyImportItem).where(
                    UserVocabularyImportItem.user_dictionary_entry_id == user_dictionary_entry_id
                )
            ).all()
            for row in rows:
                row.status = status
                row.error_text = error_text
                row.processed = current_time
                row.updated = current_time

    def list_by_user_dictionary_entry(self, user_dictionary_entry_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(UserVocabularyImportItem)
                .where(UserVocabularyImportItem.user_dictionary_entry_id == user_dictionary_entry_id)
                .order_by(UserVocabularyImportItem.id.asc())
            ).all()
            return [import_item_to_dict(row) for row in rows]

    def count_import_report_sources(self, *, since: datetime, until: datetime) -> dict[str, int]:
        counted_statuses = (
            "found_existing",
            "queued_for_details",
            "queued_for_audio",
            "queued_for_embedding",
            "ready_for_rotation",
            "imported",
        )
        with self.session_manager.session() as session:
            rows = session.execute(
                select(
                    func.count(UserVocabularyImportItem.id),
                    func.count(UserVocabularyImportItem.existing_word_id),
                    func.count(UserVocabularyImportItem.user_dictionary_entry_id),
                ).where(
                    UserVocabularyImportItem.updated > since,
                    UserVocabularyImportItem.updated <= until,
                    UserVocabularyImportItem.status.in_(counted_statuses),
                )
            ).one()
            return {
                "total_count": int(rows[0] or 0),
                "dictionary_count": int(rows[1] or 0),
                "user_dictionary_count": int(rows[2] or 0),
            }

def _read_word_translations(entry, user_entry) -> dict[str, str]:
    source = entry if entry is not None else user_entry
    if source is None:
        return {"translation_uk": "", "translation_ru": "", "translation_pl": ""}
    return {
        "translation_uk": str(source.translation_uk or ""),
        "translation_ru": str(source.translation_ru or ""),
        "translation_pl": str(source.translation_pl or ""),
    }
