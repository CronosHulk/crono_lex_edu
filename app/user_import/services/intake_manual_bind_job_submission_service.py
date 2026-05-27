from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class UserImportManualBindJobSubmissionJobsPort(Protocol):
    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None: ...

    def list_items(self, job_id: int) -> list[dict[str, Any]]: ...

    def complete(
        self,
        job_id: int,
        *,
        status: str,
        current_time: datetime,
        last_error: str | None = None,
    ) -> None: ...

    def mark_summary_sent(self, job_id: int, current_time: datetime) -> None: ...


class UserImportManualBindJobSubmissionTaskLogsPort(Protocol):
    def create(
        self,
        *,
        task_type: str,
        status: str,
        current_time: datetime,
        telegram_user_id: int | None = None,
        source_type: str | None = None,
        source_identifier: str | None = None,
        import_job_id: int | None = None,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

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


class UserImportManualBindJobSubmissionDatabasePort(Protocol):
    @property
    def user_import_jobs(self) -> UserImportManualBindJobSubmissionJobsPort: ...

    @property
    def task_logs(self) -> UserImportManualBindJobSubmissionTaskLogsPort: ...


class UserImportManualBindJobSubmissionIntakeJobPort(Protocol):
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


@dataclass(frozen=True)
class UserImportManualBindJobSubmissionResult:
    created_count: int
    skipped_count: int
    job_id: int | None
    bind_task_log: dict[str, Any] | None


class UserImportManualBindJobSubmissionService:
    def __init__(
        self,
        db: UserImportManualBindJobSubmissionDatabasePort,
        *,
        intake_job_service: UserImportManualBindJobSubmissionIntakeJobPort,
    ) -> None:
        self.db = db
        self.intake_job_service = intake_job_service

    def create_validated_import_job(
        self,
        *,
        telegram_user_id: int,
        source_identifier: str,
        parsed_words: list[Any],
        intake_snapshot: dict[str, Any],
        current_time: datetime,
        max_words_per_bind: int,
    ) -> UserImportManualBindJobSubmissionResult:
        bind_task_log = None
        if intake_snapshot["queued_lookup_words_count"] > 0:
            bind_task_log = self.db.task_logs.create(
                task_type="bound_google_doc_sync",
                status="processing",
                current_time=current_time,
                telegram_user_id=telegram_user_id,
                source_type="google_doc",
                source_identifier=source_identifier,
                description=(
                    "manual google doc bind started: "
                    f"telegram_user_id={telegram_user_id} source_identifier={source_identifier}"
                ),
                result_json=intake_snapshot,
            )

        created_count, skipped_count, job_id = self.intake_job_service.create_user_import_job_from_words(
            telegram_user_id=telegram_user_id,
            source_identifier=source_identifier,
            parsed_words=parsed_words,
            current_time=current_time,
            task_log_id=bind_task_log["id"] if bind_task_log is not None else None,
            source_type="bound_google_doc",
            max_words_per_job=max_words_per_bind,
        )
        return UserImportManualBindJobSubmissionResult(
            created_count=created_count,
            skipped_count=skipped_count,
            job_id=job_id,
            bind_task_log=bind_task_log,
        )

    def finalize_created_import_job(
        self,
        *,
        telegram_user_id: int,
        source_identifier: str,
        result: UserImportManualBindJobSubmissionResult,
        intake_snapshot: dict[str, Any],
        current_time: datetime,
        prepare_import_job_items: Callable[..., None],
        process_queued_attribute_builds_after_import: Callable[[int, datetime], None] | None = None,
    ) -> None:
        if result.created_count <= 0 or result.job_id is None:
            return

        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, result.job_id)
        if job is None:
            return

        prepare_import_job_items(
            job,
            current_time,
            task_log_id=int(job["task_log_id"]) if job.get("task_log_id") is not None else None,
        )
        if result.bind_task_log is not None:
            current_items = self.db.user_import_jobs.list_items(result.job_id)
            final_snapshot = {
                "existing_lookup_words": [
                    str(item["lookup_word"]) for item in current_items if item["status"] == "found_existing"
                ],
                "queued_lookup_words": [
                    str(item["lookup_word"]) for item in current_items if item["status"] == "queued_for_attributes"
                ],
                "invalid_fragments": intake_snapshot["invalid_fragments"],
                "invalid_fragments_count": intake_snapshot["invalid_fragments_count"],
            }
            self.db.task_logs.update(
                result.bind_task_log["id"],
                status="success",
                current_time=current_time,
                description=(
                    "manual google doc bind completed: "
                    f"telegram_user_id={telegram_user_id} source_identifier={source_identifier}"
                ),
                result_json={
                    **final_snapshot,
                    "created_import_job_id": result.job_id,
                    "queued_new_words_count": result.created_count,
                    "skipped_duplicates_count": result.skipped_count,
                },
                import_job_id=result.job_id,
            )
        self.db.user_import_jobs.complete(result.job_id, status="completed", current_time=current_time)
        self.db.user_import_jobs.mark_summary_sent(result.job_id, current_time)
        if process_queued_attribute_builds_after_import is not None:
            process_queued_attribute_builds_after_import(telegram_user_id, current_time)
