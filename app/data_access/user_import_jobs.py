from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import and_, case, delete, exists, func, or_, select, update

from app.data_access.user_dictionary_constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE,
    USER_WORD_SOURCE_CORE,
    USER_WORD_SOURCE_USER,
)
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.data_access.user_import_serialization import (
    ACTIVE_IMPORT_ITEM_STATUSES,
    FAILED_IMPORT_ITEM_STATUSES,
    SUCCESSFUL_IMPORT_ITEM_STATUSES,
    import_item_to_dict,
    import_job_to_dict,
    normalize_filter_values,
)
from app.helpers.audio_files import delete_audio_file_if_under_roots
from app.models import (
    DictionaryEntry,
    LearningSessionWord,
    User,
    UserDictionaryEntry,
    UserImportGoogleDocProgress,
    UserLearningSettings,
    UserVocabularyImportItem,
    UserVocabularyImportJob,
    UserWordAssignment,
)
from app.orm import SessionManager
from app.storage.audio import AudioStorageProvider

IMPORT_HISTORY_QUEUE_STATUSES = (
    "pending",
    "waiting_for_user_dictionary_entry",
    "queued_for_details",
    "queued_for_audio",
    "queued_for_embedding",
)
IMPORT_HISTORY_REJECTED_STATUSES = ("rejected", "failed", "details_failed", "audio_failed", "embedding_failed")


def _import_job_to_dict(row: UserVocabularyImportJob, *, telegram_user_id: int | None = None) -> dict[str, Any]:
    payload = import_job_to_dict(row)
    if telegram_user_id is not None:
        payload["telegram_user_id"] = telegram_user_id
    return payload


def _import_history_available_assignment_exists():
    return exists(
        select(1)
        .select_from(UserWordAssignment)
        .outerjoin(
            DictionaryEntry,
            (UserWordAssignment.word_source == USER_WORD_SOURCE_CORE)
            & (UserWordAssignment.word_id == DictionaryEntry.id),
        )
        .outerjoin(
            UserDictionaryEntry,
            (UserWordAssignment.word_source == USER_WORD_SOURCE_USER)
            & (UserWordAssignment.word_id == UserDictionaryEntry.id),
        )
        .where(
            UserWordAssignment.user_uuid == UserVocabularyImportItem.user_uuid,
            UserWordAssignment.status == USER_WORD_ASSIGNMENT_AVAILABLE,
            or_(
                UserWordAssignment.import_item_id == UserVocabularyImportItem.id,
                and_(
                    UserVocabularyImportItem.existing_word_id.is_not(None),
                    UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                    UserWordAssignment.word_id == UserVocabularyImportItem.existing_word_id,
                ),
                and_(
                    UserVocabularyImportItem.user_dictionary_entry_id.is_not(None),
                    UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                    UserWordAssignment.word_id == UserVocabularyImportItem.user_dictionary_entry_id,
                ),
                and_(
                    UserWordAssignment.word_source == USER_WORD_SOURCE_CORE,
                    func.lower(func.coalesce(DictionaryEntry.normalized_word, DictionaryEntry.word))
                    == func.lower(UserVocabularyImportItem.lookup_word),
                ),
                and_(
                    UserWordAssignment.word_source == USER_WORD_SOURCE_USER,
                    func.lower(func.coalesce(UserDictionaryEntry.normalized_word, UserDictionaryEntry.word))
                    == func.lower(UserVocabularyImportItem.lookup_word),
                ),
            ),
        )
    )


def _import_history_category_expression():
    return case(
        (UserVocabularyImportItem.status.in_(IMPORT_HISTORY_REJECTED_STATUSES), "rejected"),
        (_import_history_available_assignment_exists(), "added"),
        (UserVocabularyImportItem.status.in_(IMPORT_HISTORY_QUEUE_STATUSES), "queued"),
        else_="processing",
    )


def _import_history_lookup_key_expression():
    return func.lower(func.trim(UserVocabularyImportItem.lookup_word))


class UserImportJobRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get_existing_lookup_words(self, telegram_user_id: int, lookup_words: list[str]) -> set[str]:
        normalized_lookup_words = [word.lower() for word in lookup_words if word.strip()]
        if not normalized_lookup_words:
            return set()
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return set()
            rows = session.scalars(
                select(UserVocabularyImportItem.lookup_word).where(
                    UserVocabularyImportItem.user_uuid == user_uuid,
                    UserVocabularyImportItem.status.in_(ACTIVE_IMPORT_ITEM_STATUSES),
                    func.lower(UserVocabularyImportItem.lookup_word).in_(normalized_lookup_words),
                )
            ).all()
            return {str(row).lower() for row in rows}

    def create_job(
        self,
        telegram_user_id: int,
        source_type: str,
        source_identifier: str,
        storage_path: str,
        items: list[dict[str, Any]],
        current_time: datetime,
        task_log_id: int | None = None,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            row = UserVocabularyImportJob(
                user_uuid=user_uuid,
                task_log_id=task_log_id,
                source_type=source_type,
                source_identifier=source_identifier,
                storage_path=storage_path,
                status="queued",
                total_items=len(items),
                processed_items=0,
                successful_items=0,
                failed_items=0,
                summary_sent=False,
                publish_summary_sent=False,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            for item in items:
                session.add(
                    UserVocabularyImportItem(
                        import_job_id=row.id,
                        user_uuid=user_uuid,
                        task_log_id=task_log_id,
                        raw_value=item["raw_value"],
                        lookup_word=item["lookup_word"],
                        translation_hint=item.get("translation_hint"),
                        validated_lookup_word=item.get("validated_lookup_word"),
                        validated_part_of_speech=item.get("validated_part_of_speech"),
                        validated_translation_uk=item.get("validated_translation_uk"),
                        validated_translation_ru=item.get("validated_translation_ru"),
                        validated_translation_pl=item.get("validated_translation_pl"),
                        status=item.get("status") or "pending",
                        error_text=item.get("error_text"),
                        processed=current_time if item.get("status") in FAILED_IMPORT_ITEM_STATUSES else None,
                        created=current_time,
                        updated=current_time,
                    )
                )
            session.flush()
            return _import_job_to_dict(row, telegram_user_id=telegram_user_id)

    def append_items(
        self,
        job_id: int,
        telegram_user_id: int,
        items: list[dict[str, Any]],
        current_time: datetime,
        task_log_id: int | None = None,
    ) -> None:
        if not items:
            return
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return
            row = session.get(UserVocabularyImportJob, job_id)
            if row is None or row.user_uuid != user_uuid:
                return
            for item in items:
                session.add(
                    UserVocabularyImportItem(
                        import_job_id=row.id,
                        user_uuid=user_uuid,
                        task_log_id=task_log_id,
                        raw_value=item["raw_value"],
                        lookup_word=item["lookup_word"],
                        translation_hint=item.get("translation_hint"),
                        validated_lookup_word=item.get("validated_lookup_word"),
                        validated_part_of_speech=item.get("validated_part_of_speech"),
                        validated_translation_uk=item.get("validated_translation_uk"),
                        validated_translation_ru=item.get("validated_translation_ru"),
                        validated_translation_pl=item.get("validated_translation_pl"),
                        status=item.get("status") or "pending",
                        error_text=item.get("error_text"),
                        processed=current_time if item.get("status") in FAILED_IMPORT_ITEM_STATUSES else None,
                        created=current_time,
                        updated=current_time,
                    )
                )
            row.total_items = (row.total_items or 0) + len(items)
            row.updated = current_time

    def delete_all_import_data(
        self,
        *,
        audio_storage_provider: AudioStorageProvider,
        user_audio_roots: list[Path | str] | None = None,
    ) -> dict[str, int]:
        audio_paths: list[str] = []
        with self.session_manager.session() as session:
            user_entry_ids = select(UserDictionaryEntry.id)
            user_assignment_filter = and_(
                UserWordAssignment.word_source == "user",
                UserWordAssignment.word_id.in_(user_entry_ids),
            )
            import_assignment_filter = or_(
                UserWordAssignment.import_job_id.is_not(None),
                UserWordAssignment.import_item_id.is_not(None),
            )
            assignment_filter = or_(user_assignment_filter, import_assignment_filter)

            audio_paths = [
                str(path)
                for path in session.scalars(
                    select(UserDictionaryEntry.audio_path).where(
                        UserDictionaryEntry.audio_path.is_not(None),
                        UserDictionaryEntry.audio_path != "",
                    )
                ).all()
            ]
            item_count = int(session.scalar(select(func.count(UserVocabularyImportItem.id))) or 0)
            job_count = int(session.scalar(select(func.count(UserVocabularyImportJob.id))) or 0)
            google_doc_progress_count = int(
                session.scalar(select(func.count()).select_from(UserImportGoogleDocProgress)) or 0
            )
            user_dictionary_count = int(session.scalar(select(func.count(UserDictionaryEntry.id))) or 0)
            user_dictionary_embedding_count = int(
                session.scalar(
                    select(func.count(UserDictionaryEntry.id)).where(UserDictionaryEntry.embedding.is_not(None))
                )
                or 0
            )
            assignment_count = int(
                session.scalar(select(func.count(UserWordAssignment.id)).where(assignment_filter)) or 0
            )
            learning_session_word_count = int(
                session.scalar(
                    select(func.count(LearningSessionWord.id)).where(
                        LearningSessionWord.word_source == "user",
                        LearningSessionWord.word_id.in_(user_entry_ids),
                    )
                )
                or 0
            )
            google_doc_binding_count = int(
                session.scalar(
                    select(func.count(UserLearningSettings.user_uuid)).where(
                        or_(
                            UserLearningSettings.import_google_doc_id.is_not(None),
                            UserLearningSettings.is_import_google_doc_auto_sync_enabled.is_(True),
                            UserLearningSettings.import_google_doc_last_synced.is_not(None),
                            UserLearningSettings.import_google_doc_last_error.is_not(None),
                            UserLearningSettings.import_google_doc_retry_count != 0,
                            UserLearningSettings.import_google_doc_next_retry_at.is_not(None),
                            UserLearningSettings.import_google_doc_claimed_until.is_not(None),
                        )
                    )
                )
                or 0
            )
            session.execute(delete(UserWordAssignment).where(assignment_filter))
            session.execute(
                delete(LearningSessionWord).where(
                    LearningSessionWord.word_source == "user",
                    LearningSessionWord.word_id.in_(user_entry_ids),
                )
            )
            session.execute(delete(UserVocabularyImportItem))
            session.execute(delete(UserVocabularyImportJob))
            session.execute(delete(UserImportGoogleDocProgress))
            session.execute(delete(UserDictionaryEntry))
            session.execute(
                update(UserLearningSettings).values(
                    import_google_doc_id=None,
                    is_import_google_doc_auto_sync_enabled=False,
                    import_google_doc_last_synced=None,
                    import_google_doc_last_error=None,
                    import_google_doc_retry_count=0,
                    import_google_doc_next_retry_at=None,
                    import_google_doc_claimed_until=None,
                )
            )
        deleted_audio_file_count = sum(
            1
            for audio_path in audio_paths
            if delete_audio_file_if_under_roots(
                audio_path,
                user_audio_roots or [],
                storage_provider=audio_storage_provider,
            )
        )
        return {
            "deleted_import_items": item_count,
            "deleted_import_jobs": job_count,
            "deleted_google_doc_progress": google_doc_progress_count,
            "cleared_google_doc_bindings": google_doc_binding_count,
            "deleted_user_dictionary_entries": user_dictionary_count,
            "deleted_user_dictionary_embeddings": user_dictionary_embedding_count,
            "deleted_user_word_assignments": assignment_count,
            "deleted_user_learning_session_words": learning_session_word_count,
            "deleted_user_audio_files": deleted_audio_file_count,
        }

    def claim_queued(
        self,
        *,
        current_time: datetime,
        claimed_until: datetime,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            stmt = (
                select(UserVocabularyImportJob, User.telegram_user_id)
                .join(User, User.uuid == UserVocabularyImportJob.user_uuid)
                .where(
                    UserVocabularyImportJob.status.in_(("queued", "processing")),
                    UserVocabularyImportJob.summary_sent.is_(False),
                    or_(
                        UserVocabularyImportJob.processing_claimed_until.is_(None),
                        UserVocabularyImportJob.processing_claimed_until <= current_time,
                    ),
                )
                .order_by(UserVocabularyImportJob.created.asc(), UserVocabularyImportJob.id.asc())
                .with_for_update(skip_locked=True)
            )
            if limit is not None:
                stmt = stmt.limit(limit)
            rows = session.execute(stmt).all()
            for row, _telegram_user_id in rows:
                row.status = "processing"
                row.processing_claimed_until = claimed_until
                row.updated = current_time
            return [_import_job_to_dict(row, telegram_user_id=telegram_user_id) for row, telegram_user_id in rows]

    def list_completed_pending_summary(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.execute(
                select(UserVocabularyImportJob, User.telegram_user_id)
                .join(User, User.uuid == UserVocabularyImportJob.user_uuid)
                .where(
                    UserVocabularyImportJob.status.in_(("completed", "failed")),
                    UserVocabularyImportJob.summary_sent.is_(False),
                )
                .order_by(UserVocabularyImportJob.completed.asc(), UserVocabularyImportJob.id.asc())
            ).all()
            return [_import_job_to_dict(row, telegram_user_id=telegram_user_id) for row, telegram_user_id in rows]

    def mark_processing(self, job_id: int, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(UserVocabularyImportJob, job_id)
            if row is None:
                return
            row.status = "processing"
            row.processing_claimed_until = current_time
            row.updated = current_time
            row.last_error = None

    def complete(
        self,
        job_id: int,
        *,
        status: str,
        current_time: datetime,
        last_error: str | None = None,
    ) -> None:
        with self.session_manager.session() as session:
            row = session.get(UserVocabularyImportJob, job_id)
            if row is None:
                return
            counts = session.execute(
                select(
                    func.count(UserVocabularyImportItem.id),
                    func.count(UserVocabularyImportItem.id).filter(
                        UserVocabularyImportItem.status.in_(SUCCESSFUL_IMPORT_ITEM_STATUSES)
                    ),
                    func.count(UserVocabularyImportItem.id).filter(
                        UserVocabularyImportItem.status.in_(FAILED_IMPORT_ITEM_STATUSES)
                    ),
                ).where(UserVocabularyImportItem.import_job_id == job_id)
            ).one()
            row.total_items = counts[0] or 0
            row.processed_items = counts[0] or 0
            row.successful_items = counts[1] or 0
            row.failed_items = counts[2] or 0
            row.status = status
            row.processing_claimed_until = None
            row.last_error = last_error
            row.completed = current_time if status in {"completed", "failed"} else row.completed
            row.updated = current_time

    def list_unfinished_items(self, job_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(UserVocabularyImportItem)
                .where(
                    UserVocabularyImportItem.import_job_id == job_id,
                    UserVocabularyImportItem.status.in_(("pending", "collecting")),
                )
                .order_by(UserVocabularyImportItem.id.asc())
            ).all()
            return [import_item_to_dict(row) for row in rows]

    def mark_summary_sent(self, job_id: int, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(UserVocabularyImportJob, job_id)
            if row is None:
                return
            row.summary_sent = True
            row.updated = current_time

    def list_completed_pending_publish_summary(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.execute(
                select(UserVocabularyImportJob, User.telegram_user_id)
                .join(User, User.uuid == UserVocabularyImportJob.user_uuid)
                .where(
                    UserVocabularyImportJob.status == "completed",
                    UserVocabularyImportJob.publish_summary_sent.is_(False),
                    select(UserVocabularyImportItem.id)
                    .where(
                        UserVocabularyImportItem.import_job_id == UserVocabularyImportJob.id,
                        UserVocabularyImportItem.status == "imported",
                    )
                    .exists(),
                )
                .order_by(UserVocabularyImportJob.completed.asc(), UserVocabularyImportJob.id.asc())
            ).all()
            return [_import_job_to_dict(row, telegram_user_id=telegram_user_id) for row, telegram_user_id in rows]

    def mark_publish_summary_sent(self, job_id: int, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(UserVocabularyImportJob, job_id)
            if row is None:
                return
            row.publish_summary_sent = True
            row.updated = current_time

    def list_items(self, job_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(UserVocabularyImportItem)
                .where(UserVocabularyImportItem.import_job_id == job_id)
                .order_by(UserVocabularyImportItem.id.asc())
            ).all()
            return [import_item_to_dict(row) for row in rows]

    def list_item_status_counts(self, job_id: int) -> dict[str, int]:
        with self.session_manager.session() as session:
            rows = session.execute(
                select(UserVocabularyImportItem.status, func.count(UserVocabularyImportItem.id))
                .where(UserVocabularyImportItem.import_job_id == job_id)
                .group_by(UserVocabularyImportItem.status)
            ).all()
            return {str(status): int(count) for status, count in rows}

    def list_item_category_counts(self, job_id: int, telegram_user_id: int) -> dict[str, int]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {}
            category = _import_history_category_expression()
            rows = session.execute(
                select(category, func.count(UserVocabularyImportItem.id))
                .where(
                    UserVocabularyImportItem.import_job_id == job_id,
                    UserVocabularyImportItem.user_uuid == user_uuid,
                )
                .group_by(category)
            ).all()
            return {str(status_category): int(count) for status_category, count in rows}

    def list_user_item_status_counts(self, telegram_user_id: int) -> dict[str, int]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {}
            rows = session.execute(
                select(UserVocabularyImportItem.status, func.count(UserVocabularyImportItem.id))
                .where(UserVocabularyImportItem.user_uuid == user_uuid)
                .group_by(UserVocabularyImportItem.status)
            ).all()
            return {str(status): int(count) for status, count in rows}

    def list_user_item_category_counts(self, telegram_user_id: int) -> dict[str, int]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {}
            category = _import_history_category_expression()
            latest_item_ids = self._latest_user_import_item_ids_select(user_uuid)
            rows = session.execute(
                select(category, func.count(UserVocabularyImportItem.id))
                .where(
                    UserVocabularyImportItem.user_uuid == user_uuid,
                    UserVocabularyImportItem.id.in_(latest_item_ids),
                )
                .group_by(category)
            ).all()
            return {str(status_category): int(count) for status_category, count in rows}

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserVocabularyImportJob, job_id)
            return import_job_to_dict(row) if row is not None else None

    def list_admin_jobs(
        self,
        *,
        page: int,
        page_size: int,
        status: str | list[str] | None = None,
        source_type: str | list[str] | None = None,
        user_id: str | None = None,
        search: str = "",
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = []
            status_values = normalize_filter_values(status)
            if status_values:
                filters.append(UserVocabularyImportJob.status.in_(status_values))
            source_type_values = normalize_filter_values(source_type)
            if source_type_values:
                filters.append(UserVocabularyImportJob.source_type.in_(source_type_values))
            if user_id:
                filters.append(UserVocabularyImportJob.user_uuid == user_id)
            normalized_search = search.strip().lower()
            if normalized_search:
                like_value = f"%{normalized_search}%"
                filters.append(
                    or_(
                        func.lower(UserVocabularyImportJob.source_type).like(like_value),
                        func.lower(UserVocabularyImportJob.source_identifier).like(like_value),
                        func.lower(UserVocabularyImportJob.status).like(like_value),
                        func.lower(UserVocabularyImportJob.last_error).like(like_value),
                    )
                )

            query = select(UserVocabularyImportJob).where(*filters)
            count_query = select(func.count(UserVocabularyImportJob.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(UserVocabularyImportJob.created.desc(), UserVocabularyImportJob.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [import_job_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def get_admin_job_filter_metadata(self) -> dict[str, Any]:
        with self.session_manager.session() as session:
            statuses = session.scalars(
                select(UserVocabularyImportJob.status).distinct().order_by(UserVocabularyImportJob.status.asc())
            ).all()
            source_types = session.scalars(
                select(UserVocabularyImportJob.source_type).distinct().order_by(UserVocabularyImportJob.source_type.asc())
            ).all()
            return {
                "entity": "import_jobs",
                "page_sizes": [50, 100],
                "filters": [
                    {"name": "search", "type": "text", "label": "Пошук"},
                    {
                        "name": "status",
                        "type": "multi_select",
                        "label": "Status",
                        "options": [{"value": value, "label": value} for value in statuses if value],
                    },
                    {
                        "name": "source_type",
                        "type": "multi_select",
                        "label": "Source type",
                        "options": [{"value": value, "label": value} for value in source_types if value],
                    },
                    {"name": "user_id", "type": "text", "label": "User UUID"},
                ],
            }

    def list_items_for_user(self, telegram_user_id: int, job_id: int) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return []
            rows = session.scalars(
                select(UserVocabularyImportItem)
                .join(UserVocabularyImportJob, UserVocabularyImportJob.id == UserVocabularyImportItem.import_job_id)
                .where(
                    UserVocabularyImportItem.import_job_id == job_id,
                    UserVocabularyImportJob.user_uuid == user_uuid,
                )
                .order_by(UserVocabularyImportItem.id.asc())
            ).all()
            return [import_item_to_dict(row) for row in rows]

    def list_items_for_user_paginated(
        self,
        telegram_user_id: int,
        job_id: int,
        *,
        page: int,
        page_size: int,
        status: str | list[str] | set[str] | None = None,
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
            filters = [
                UserVocabularyImportItem.import_job_id == job_id,
                UserVocabularyImportJob.user_uuid == user_uuid,
            ]
            status_values = normalize_filter_values(status)
            if status_values:
                filters.append(UserVocabularyImportItem.status.in_(status_values))
            query = (
                select(UserVocabularyImportItem)
                .join(UserVocabularyImportJob, UserVocabularyImportJob.id == UserVocabularyImportItem.import_job_id)
                .where(*filters)
            )
            count_query = (
                select(func.count(UserVocabularyImportItem.id))
                .join(UserVocabularyImportJob, UserVocabularyImportJob.id == UserVocabularyImportItem.import_job_id)
                .where(*filters)
            )
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(UserVocabularyImportItem.created.desc(), UserVocabularyImportItem.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [import_item_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def list_items_for_user_by_category_paginated(
        self,
        telegram_user_id: int,
        job_id: int,
        *,
        page: int,
        page_size: int,
        status_category: str = "all",
    ) -> dict[str, Any]:
        return self._list_import_history_items_paginated(
            telegram_user_id,
            page=page,
            page_size=page_size,
            status_category=status_category,
            job_id=job_id,
        )

    def list_all_items_for_user_paginated(
        self,
        telegram_user_id: int,
        *,
        page: int,
        page_size: int,
        status: str | list[str] | set[str] | None = None,
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
            filters = [UserVocabularyImportItem.user_uuid == user_uuid]
            status_values = normalize_filter_values(status)
            if status_values:
                filters.append(UserVocabularyImportItem.status.in_(status_values))
            query = select(UserVocabularyImportItem).where(*filters)
            count_query = select(func.count(UserVocabularyImportItem.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(UserVocabularyImportItem.created.desc(), UserVocabularyImportItem.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [import_item_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def list_all_items_for_user_by_category_paginated(
        self,
        telegram_user_id: int,
        *,
        page: int,
        page_size: int,
        status_category: str = "all",
    ) -> dict[str, Any]:
        return self._list_import_history_items_paginated(
            telegram_user_id,
            page=page,
            page_size=page_size,
            status_category=status_category,
        )

    def _list_import_history_items_paginated(
        self,
        telegram_user_id: int,
        *,
        page: int,
        page_size: int,
        status_category: str,
        job_id: int | None = None,
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
            category = _import_history_category_expression()
            filters = [UserVocabularyImportItem.user_uuid == user_uuid]
            if job_id is not None:
                filters.append(UserVocabularyImportItem.import_job_id == job_id)
            else:
                filters.append(UserVocabularyImportItem.id.in_(self._latest_user_import_item_ids_select(user_uuid)))
            if status_category != "all":
                filters.append(category == status_category)
            query = select(UserVocabularyImportItem, category.label("status_category")).where(*filters)
            count_query = select(func.count(UserVocabularyImportItem.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.execute(
                query.order_by(UserVocabularyImportItem.created.desc(), UserVocabularyImportItem.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            items = []
            for row, computed_status_category in rows:
                item = import_item_to_dict(row)
                item["computed_status_category"] = str(computed_status_category)
                items.append(item)
            return {
                "items": items,
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def _latest_user_import_item_ids_select(self, user_uuid):
        ranked_items = (
            select(
                UserVocabularyImportItem.id.label("item_id"),
                func.row_number()
                .over(
                    partition_by=_import_history_lookup_key_expression(),
                    order_by=(UserVocabularyImportItem.created.desc(), UserVocabularyImportItem.id.desc()),
                )
                .label("row_number"),
            )
            .where(UserVocabularyImportItem.user_uuid == user_uuid)
            .subquery()
        )
        return select(ranked_items.c.item_id).where(ranked_items.c.row_number == 1)

    def list_admin_items(
        self,
        *,
        page: int,
        page_size: int,
        status: str | list[str] | None = None,
        import_job_id: int | None = None,
        user_id: str | None = None,
        search: str = "",
    ) -> dict[str, Any]:
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = []
            status_values = normalize_filter_values(status)
            if status_values:
                filters.append(UserVocabularyImportItem.status.in_(status_values))
            if import_job_id is not None:
                filters.append(UserVocabularyImportItem.import_job_id == import_job_id)
            if user_id:
                filters.append(UserVocabularyImportItem.user_uuid == user_id)
            normalized_search = search.strip().lower()
            if normalized_search:
                like_value = f"%{normalized_search}%"
                filters.append(
                    or_(
                        func.lower(UserVocabularyImportItem.raw_value).like(like_value),
                        func.lower(UserVocabularyImportItem.lookup_word).like(like_value),
                        func.lower(UserVocabularyImportItem.validated_lookup_word).like(like_value),
                        func.lower(UserVocabularyImportItem.translation_hint).like(like_value),
                        func.lower(UserVocabularyImportItem.validated_part_of_speech).like(like_value),
                        func.lower(UserVocabularyImportItem.validated_translation_uk).like(like_value),
                        func.lower(UserVocabularyImportItem.validated_translation_ru).like(like_value),
                        func.lower(UserVocabularyImportItem.validated_translation_pl).like(like_value),
                        func.lower(UserVocabularyImportItem.status).like(like_value),
                        func.lower(UserVocabularyImportItem.error_text).like(like_value),
                    )
                )

            query = select(UserVocabularyImportItem).where(*filters)
            count_query = select(func.count(UserVocabularyImportItem.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(UserVocabularyImportItem.created.desc(), UserVocabularyImportItem.id.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
            return {
                "items": [import_item_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def get_admin_item_filter_metadata(self) -> dict[str, Any]:
        with self.session_manager.session() as session:
            statuses = session.scalars(
                select(UserVocabularyImportItem.status).distinct().order_by(UserVocabularyImportItem.status.asc())
            ).all()
            status_values = sorted(
                {
                    *ACTIVE_IMPORT_ITEM_STATUSES,
                    *FAILED_IMPORT_ITEM_STATUSES,
                    *SUCCESSFUL_IMPORT_ITEM_STATUSES,
                    *[value for value in statuses if value],
                }
            )
            return {
                "entity": "import_items",
                "page_sizes": [50, 100],
                "filters": [
                    {"name": "search", "type": "text", "label": "Пошук"},
                    {
                        "name": "status",
                        "type": "multi_select",
                        "label": "Status",
                        "options": [{"value": value, "label": value} for value in status_values],
                    },
                    {"name": "user_id", "type": "text", "label": "User UUID"},
                    {"name": "import_job_id", "type": "number", "label": "Import job ID"},
                ],
            }

    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            row = session.scalar(
                select(UserVocabularyImportJob)
                .where(
                    UserVocabularyImportJob.id == job_id,
                    UserVocabularyImportJob.user_uuid == user_uuid,
                )
                .limit(1)
            )
            return _import_job_to_dict(row, telegram_user_id=telegram_user_id) if row is not None else None

    def get_latest_job_for_user(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return None
            row = session.scalar(
                select(UserVocabularyImportJob)
                .where(UserVocabularyImportJob.user_uuid == user_uuid)
                .order_by(UserVocabularyImportJob.created.desc(), UserVocabularyImportJob.id.desc())
                .limit(1)
            )
            return _import_job_to_dict(row, telegram_user_id=telegram_user_id) if row is not None else None
