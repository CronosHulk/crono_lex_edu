from __future__ import annotations

from typing import Any

from app.domain.user_import.statuses import (
    ACTIVE_IMPORT_ITEM_STATUSES as _ACTIVE_IMPORT_ITEM_STATUSES,
)
from app.domain.user_import.statuses import (
    FAILED_IMPORT_ITEM_STATUSES as _FAILED_IMPORT_ITEM_STATUSES,
)
from app.domain.user_import.statuses import (
    SUCCESSFUL_IMPORT_ITEM_STATUSES as _SUCCESSFUL_IMPORT_ITEM_STATUSES,
)
from app.models import UserVocabularyImportItem, UserVocabularyImportJob

ACTIVE_IMPORT_ITEM_STATUSES = _ACTIVE_IMPORT_ITEM_STATUSES
SUCCESSFUL_IMPORT_ITEM_STATUSES = _SUCCESSFUL_IMPORT_ITEM_STATUSES
FAILED_IMPORT_ITEM_STATUSES = _FAILED_IMPORT_ITEM_STATUSES


def normalize_filter_values(value: str | list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_values = value.split(",")
    else:
        raw_values = list(value)
    return [str(item).strip() for item in raw_values if str(item).strip()]


def import_job_to_dict(row: UserVocabularyImportJob) -> dict[str, Any]:
    user_uuid = str(row.user_uuid) if getattr(row, "user_uuid", None) is not None else None
    return {
        "id": row.id,
        "user_id": user_uuid,
        "user_uuid": user_uuid,
        "task_log_id": row.task_log_id,
        "source_type": row.source_type,
        "source_identifier": row.source_identifier,
        "storage_path": row.storage_path,
        "status": row.status,
        "total_items": row.total_items,
        "processed_items": row.processed_items,
        "successful_items": row.successful_items,
        "failed_items": row.failed_items,
        "summary_sent": row.summary_sent,
        "publish_summary_sent": row.publish_summary_sent,
        "processing_claimed_until": row.processing_claimed_until,
        "last_error": row.last_error,
        "completed": row.completed,
        "created": row.created,
        "updated": row.updated,
    }


def import_item_to_dict(row: UserVocabularyImportItem) -> dict[str, Any]:
    user_uuid = str(row.user_uuid) if getattr(row, "user_uuid", None) is not None else None
    return {
        "id": row.id,
        "import_job_id": row.import_job_id,
        "user_id": user_uuid,
        "user_uuid": user_uuid,
        "task_log_id": row.task_log_id,
        "raw_value": row.raw_value,
        "lookup_word": row.lookup_word,
        "translation_hint": row.translation_hint,
        "validated_lookup_word": row.validated_lookup_word,
        "validated_part_of_speech": row.validated_part_of_speech,
        "validated_translation_uk": row.validated_translation_uk,
        "validated_translation_ru": row.validated_translation_ru,
        "validated_translation_pl": row.validated_translation_pl,
        "status": row.status,
        "error_text": row.error_text,
        "existing_word_id": row.existing_word_id,
        "user_dictionary_entry_id": row.user_dictionary_entry_id,
        "created": row.created,
        "updated": row.updated,
        "processed": row.processed,
    }
