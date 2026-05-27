from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol, cast

from app.user_import.services.google_doc_progress import (
    parse_google_doc_since_progress,
)
from app.user_import.services.intake_manual_bind_progress_service import (
    UserImportManualBindProgressService,
)
from app.user_import.services.intake_manual_bind_validation_service import (
    UserImportManualBindValidationService,
)


class UserImportBoundGoogleDocSyncGoogleDocRepository(Protocol):
    def get_progress(self, telegram_user_id: int, doc_id: str) -> dict[str, Any] | None: ...

    def mark_progress(
        self,
        telegram_user_id: int,
        doc_id: str,
        *,
        current_time: datetime,
        last_processed_line: int,
        last_processed_line_hash: str | None,
        last_processed_lookup_word: str | None,
    ) -> None: ...

    def mark_sync_success(self, telegram_user_id: int, *, current_time: datetime) -> None: ...

    def mark_sync_failure(
        self,
        telegram_user_id: int,
        *,
        current_time: datetime,
        error_text: str,
        retry_count: int,
        next_retry_at: datetime | None,
    ) -> None: ...


class UserImportBoundGoogleDocSyncJobsPort(Protocol):
    def get_existing_lookup_words(self, telegram_user_id: int, lookup_words: list[str]) -> set[str]: ...


class UserImportBoundGoogleDocSyncTaskLogsPort(Protocol):
    def update(
        self,
        task_log_id: int,
        *,
        status: str,
        current_time: datetime,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
        import_job_id: int | None = None,
    ) -> dict[str, Any] | None: ...


class UserImportBoundGoogleDocSyncDatabasePort(Protocol):
    task_logs: UserImportBoundGoogleDocSyncTaskLogsPort
    user_import_jobs: UserImportBoundGoogleDocSyncJobsPort


class UserImportBoundGoogleDocSyncCandidateFilterPort(Protocol):
    def list_assigned_lookup_words(self, user_uuid: str | None) -> set[str]: ...

    def filter_already_assigned_words(
        self,
        parsed_words: list[Any],
        *,
        user_uuid: str | None,
    ) -> Any: ...


class UserImportBoundGoogleDocSyncImportModeResolver(Protocol):
    def __call__(self, user_uuid: str, *, current_time: datetime) -> str | None: ...


class UserImportBoundGoogleDocSyncPipelineErrorLogger(Protocol):
    def __call__(
        self,
        *,
        stage: str,
        error_text: str | None = None,
        error: Exception | None = None,
        level: str = "warn",
        task_key: str | None = None,
        provider_key: str | None = None,
        user_dictionary_entry_id: int | None = None,
        import_item_id: int | None = None,
        import_job_id: int | None = None,
        task_log_id: int | None = None,
        telegram_user_id: int | None = None,
        lookup_word: str | None = None,
        attempt_count: int | None = None,
        current_time: datetime | None = None,
        context_json: dict[str, Any] | None = None,
    ) -> None: ...


class UserImportBoundGoogleDocSyncIntakeJobPort(Protocol):
    def build_user_import_intake_snapshot(
        self,
        parsed_words: list[Any],
        existing_lookup_words: set[str],
        invalid_fragments: list[str],
        *,
        max_words_per_bind: int,
    ) -> dict[str, Any]: ...

    def create_user_import_job_from_words(
        self,
        *,
        telegram_user_id: int,
        source_identifier: str,
        parsed_words: list[Any],
        current_time: datetime,
        task_log_id: int | None = None,
        source_type: str = "google_doc",
        max_words_per_job: int | None = None,
    ) -> tuple[int, int, int | None]: ...


class SupportsClearGoogleDocProgress(Protocol):
    def clear_progress(self, telegram_user_id: int, doc_id: str, *, current_time: datetime) -> None: ...


class UserImportBoundGoogleDocSyncProcessor:
    def __init__(
        self,
        db: UserImportBoundGoogleDocSyncDatabasePort,
        google_docs: UserImportBoundGoogleDocSyncGoogleDocRepository,
        *,
        intake_job_service: UserImportBoundGoogleDocSyncIntakeJobPort,
        build_google_doc_export_url: Callable[[str], str],
        fetch_google_doc_text: Callable[[str], str],
        parse_user_vocabulary_text_result: Callable[[str], Any],
        sanitize_external_error_text: Callable[[str], str],
        candidate_filter: UserImportBoundGoogleDocSyncCandidateFilterPort,
        import_mode_for_user: UserImportBoundGoogleDocSyncImportModeResolver,
        max_import_entries_per_submission: Callable[[], int],
        log_pipeline_error: UserImportBoundGoogleDocSyncPipelineErrorLogger,
        validation_service: Any | None = None,
    ) -> None:
        self.db = db
        self.google_docs = google_docs
        self.intake_job_service = intake_job_service
        self.build_google_doc_export_url = build_google_doc_export_url
        self.fetch_google_doc_text = fetch_google_doc_text
        self.parse_user_vocabulary_text_result = parse_user_vocabulary_text_result
        self.sanitize_external_error_text = sanitize_external_error_text
        self.candidate_filter = candidate_filter
        self.max_import_entries_per_submission = max_import_entries_per_submission
        self.log_pipeline_error = log_pipeline_error
        self.validation_flow = UserImportManualBindValidationService(
            validation_service=validation_service,
            import_mode_for_user=import_mode_for_user,
        )
        self.progress_service = UserImportManualBindProgressService(google_docs)

    def process_bound_google_doc_sync_row(
        self,
        row: dict[str, Any],
        current_time: datetime,
        *,
        task_log_id: int,
        max_import_entries: int | None = None,
        task_scope: str = "bound_google_doc_sync",
        restart_from_beginning: bool = False,
    ) -> dict[str, Any]:
        doc_id = str(row["source_identifier"])
        if restart_from_beginning and hasattr(self.google_docs, "clear_progress"):
            cast(SupportsClearGoogleDocProgress, self.google_docs).clear_progress(
                row["telegram_user_id"],
                doc_id,
                current_time=current_time,
            )
        export_url = self.build_google_doc_export_url(doc_id)
        raw_text = self.fetch_google_doc_text(export_url)
        progress = None if restart_from_beginning else self.google_docs.get_progress(row["telegram_user_id"], doc_id)
        max_words_per_bind = max(int(max_import_entries or self._max_import_entries_per_submission()), 1)
        actor_user_uuid = str(row.get("user_uuid") or "")
        assigned_lookup_words = self.candidate_filter.list_assigned_lookup_words(actor_user_uuid)
        scope = parse_google_doc_since_progress(
            raw_text,
            progress,
            self.parse_user_vocabulary_text_result,
            max_parsed_words=max_words_per_bind,
            skip_lookup_words=assigned_lookup_words,
        )
        parse_result = scope.parse_result
        if not parse_result.parsed_words:
            already_seen_lookup_words = {str(item) for item in getattr(scope, "skipped_lookup_words", []) if item}
            self.progress_service.mark_google_doc_progress(
                telegram_user_id=row["telegram_user_id"],
                doc_id=doc_id,
                scope=scope,
                existing_lookup_words=already_seen_lookup_words,
                max_words_per_bind=max_words_per_bind,
                current_time=current_time,
            )
            self.google_docs.mark_sync_success(
                row["telegram_user_id"],
                current_time=current_time,
            )
            return {
                "parsed_words_count": 0,
                "invalid_fragments_count": len(parse_result.invalid_fragments),
                "invalid_fragments": parse_result.invalid_fragments,
                "queued_new_words_count": 0,
                "skipped_duplicates_count": 0,
                "created_import_job_id": None,
                "existing_lookup_words": sorted(already_seen_lookup_words),
                "queued_lookup_words": [],
            }
        candidate_filter_result = self.candidate_filter.filter_already_assigned_words(
            parse_result.parsed_words,
            user_uuid=actor_user_uuid,
        )
        if not candidate_filter_result.eligible_words:
            skipped_assigned_lookup_words = {
                str(getattr(item, "lookup_word", "") or "")
                for item in candidate_filter_result.skipped_existing_words
                if str(getattr(item, "lookup_word", "") or "")
            }
            already_seen_lookup_words = {
                *skipped_assigned_lookup_words,
                *(str(item) for item in getattr(scope, "skipped_lookup_words", []) if item),
            }
            self.progress_service.mark_google_doc_progress(
                telegram_user_id=row["telegram_user_id"],
                doc_id=doc_id,
                scope=scope,
                existing_lookup_words=already_seen_lookup_words,
                max_words_per_bind=max_words_per_bind,
                current_time=current_time,
            )
            self.google_docs.mark_sync_success(
                row["telegram_user_id"],
                current_time=current_time,
            )
            return {
                "parsed_words_count": len(parse_result.parsed_words),
                "invalid_fragments_count": len(parse_result.invalid_fragments),
                "invalid_fragments": parse_result.invalid_fragments,
                "queued_new_words_count": 0,
                "skipped_duplicates_count": 0,
                "created_import_job_id": None,
                "existing_lookup_words": sorted(already_seen_lookup_words),
                "queued_lookup_words": [],
            }
        validation_outcome = self.validation_flow.validate_parsed_words(
            candidate_filter_result.eligible_words,
            user_uuid=actor_user_uuid,
            current_time=current_time,
        )
        validated_words = validation_outcome.valid_words
        invalid_fragments = [
            *parse_result.invalid_fragments,
            *self.validation_flow.rejected_fragments(validation_outcome.rejected_items),
        ]
        already_seen_lookup_words = self.db.user_import_jobs.get_existing_lookup_words(
            row["telegram_user_id"],
            [item.lookup_word for item in validated_words],
        )
        already_seen_lookup_words.update(getattr(scope, "skipped_lookup_words", []))
        already_seen_lookup_words.update(
            str(getattr(item, "lookup_word", "") or "")
            for item in candidate_filter_result.skipped_existing_words
        )
        intake_snapshot = self.intake_job_service.build_user_import_intake_snapshot(
            validated_words,
            already_seen_lookup_words,
            invalid_fragments,
            max_words_per_bind=max_words_per_bind,
        )
        skipped_assigned_lookup_words = [
            str(getattr(item, "lookup_word", "") or "")
            for item in candidate_filter_result.skipped_existing_words
            if str(getattr(item, "lookup_word", "") or "")
        ]
        skipped_assigned_lookup_words.extend(str(item) for item in getattr(scope, "skipped_lookup_words", []) if item)
        created_count, skipped_count, job_id = self.intake_job_service.create_user_import_job_from_words(
            telegram_user_id=row["telegram_user_id"],
            source_identifier=doc_id,
            parsed_words=validated_words,
            current_time=current_time,
            task_log_id=task_log_id,
            source_type="bound_google_doc",
            max_words_per_job=max_words_per_bind,
        )
        self.validation_flow.record_usage(
            validation_outcome,
            task_scope=task_scope,
            actor_user_uuid=actor_user_uuid,
            source_type="bound_google_doc",
            source_identifier=doc_id,
            import_job_id=job_id,
            task_log_id=task_log_id,
            batch_key=f"{task_scope}:{row['telegram_user_id']}:{doc_id}:word_validation",
            current_time=current_time,
        )
        self.progress_service.mark_google_doc_progress(
            telegram_user_id=row["telegram_user_id"],
            doc_id=doc_id,
            scope=scope,
            existing_lookup_words=already_seen_lookup_words,
            max_words_per_bind=max_words_per_bind,
            current_time=current_time,
        )
        self.google_docs.mark_sync_success(
            row["telegram_user_id"],
            current_time=current_time,
        )
        return {
            "parsed_words_count": len(parse_result.parsed_words),
            "invalid_fragments_count": intake_snapshot["invalid_fragments_count"],
            "invalid_fragments": intake_snapshot["invalid_fragments"],
            "queued_new_words_count": created_count,
            "skipped_duplicates_count": skipped_count,
            "created_import_job_id": job_id,
            "existing_lookup_words": sorted(
                {str(item) for item in [*intake_snapshot["existing_lookup_words"], *skipped_assigned_lookup_words]}
            ),
            "queued_lookup_words": intake_snapshot["queued_lookup_words"],
        }

    def mark_bound_google_doc_sync_failed(
        self,
        row: dict[str, Any],
        current_time: datetime,
        error: Exception,
        *,
        task_log_id: int,
        build_task_error_context: Callable[..., dict[str, Any]],
        build_next_retry_at: Callable[[datetime, int], datetime | None],
    ) -> None:
        error_text = self.sanitize_external_error_text(str(error))
        error_context = build_task_error_context(
            task_log_id=task_log_id,
            telegram_user_id=row["telegram_user_id"],
            source_type="google_doc",
            source_identifier=row["source_identifier"],
        )
        self.log_pipeline_error(
            stage="google_doc_sync",
            error_text=error_text,
            error=error,
            task_key="user_import.google_doc_sync",
            provider_key="google_docs",
            task_log_id=task_log_id,
            telegram_user_id=int(row["telegram_user_id"]),
            current_time=current_time,
            context_json={
                **error_context,
                "source_type": "google_doc",
                "source_identifier": row["source_identifier"],
            },
        )
        retry_count = int(row.get("retry_count", 0)) + 1
        next_retry_at = build_next_retry_at(current_time, retry_count)
        self.google_docs.mark_sync_failure(
            row["telegram_user_id"],
            current_time=current_time,
            error_text=error_text,
            retry_count=retry_count,
            next_retry_at=next_retry_at,
        )
        self.db.task_logs.update(
            task_log_id,
            status="error",
            current_time=current_time,
            description=(
                f"bound google doc sync failed: "
                f"telegram_user_id={row['telegram_user_id']} source_identifier={row['source_identifier']}"
            ),
            error_text=error_text,
            result_json={
                "retry_count": retry_count,
                "next_retry_at": next_retry_at.isoformat() if next_retry_at is not None else None,
            },
        )

    def _max_import_entries_per_submission(self) -> int:
        return max(int(self.max_import_entries_per_submission()), 1)
