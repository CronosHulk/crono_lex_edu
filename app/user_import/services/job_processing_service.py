from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.user_import.helpers.job_identity import resolve_job_user_uuid
from app.user_import.services.error_logging import log_user_import_pipeline_error
from app.user_import.services.job_task_result_service import UserImportJobTaskResultService


class UserImportJobProcessingTaskLogsPort(Protocol):
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


class UserImportJobProcessingJobsPort(Protocol):
    def list_unfinished_items(self, job_id: int) -> list[dict[str, Any]]: ...

    def list_items(self, job_id: int) -> list[dict[str, Any]]: ...

    def complete(
        self,
        job_id: int,
        *,
        status: str,
        current_time: datetime,
        last_error: str | None = None,
    ) -> None: ...


class UserImportJobProcessingDictionaryLookupPort(Protocol):
    def create_user_core_word_assignment(
        self,
        telegram_user_id: int,
        word_id: int,
        *,
        current_time: datetime | None = None,
    ) -> None: ...


class UserImportJobProcessingDatabasePort(Protocol):
    @property
    def task_logs(self) -> UserImportJobProcessingTaskLogsPort: ...

    @property
    def user_import_jobs(self) -> UserImportJobProcessingJobsPort: ...

    @property
    def dictionary_lookup(self) -> UserImportJobProcessingDictionaryLookupPort: ...


class UserImportJobProcessingService:
    def __init__(
        self,
        db: UserImportJobProcessingDatabasePort,
        *,
        prepare_import_job_items: Callable[..., None],
        job_task_result_service: UserImportJobTaskResultService,
        build_task_error_context: Callable[..., dict[str, Any]],
        sanitize_external_error_text: Callable[[str], str],
    ) -> None:
        self.db = db
        self.prepare_import_job_items = prepare_import_job_items
        self.job_task_result_service = job_task_result_service
        self.build_task_error_context = build_task_error_context
        self.sanitize_external_error_text = sanitize_external_error_text

    def process_claimed_job(
        self,
        job: dict[str, Any],
        *,
        current_time: datetime,
        wordnik_quota: dict[str, Any],
        wordnik_budget: int,
        wordnik_hourly_limit: int,
    ) -> tuple[dict[str, Any], int]:
        task_log = self._create_processing_task_log(job, current_time)
        try:
            self.prepare_import_job_items(job, current_time, task_log_id=task_log["id"])
            unfinished_items = self.db.user_import_jobs.list_unfinished_items(job["id"])
            if unfinished_items:
                self._pause_job(job, task_log, current_time, unfinished_items_count=len(unfinished_items))
                return wordnik_quota, wordnik_budget

            self._process_existing_core_assignments(job, current_time=current_time)
            self._complete_job(job, task_log, current_time)
        except Exception as error:
            self._fail_job(job, task_log, current_time, error)
        return wordnik_quota, wordnik_budget

    def _create_processing_task_log(self, job: dict[str, Any], current_time: datetime) -> dict[str, Any]:
        payload = {
            "task_type": "user_vocabulary_import_job_process",
            "status": "processing",
            "current_time": current_time,
            "source_type": job["source_type"],
            "source_identifier": job["source_identifier"],
            "import_job_id": job["id"],
            "description": (
                f"user vocabulary import job processing started: "
                f"import_job_id={job['id']} source_identifier={job['source_identifier']}"
            ),
        }
        user_uuid = resolve_job_user_uuid(job)
        if user_uuid is not None and hasattr(self.db.task_logs, "create_for_user_uuid"):
            return self.db.task_logs.create_for_user_uuid(user_uuid=user_uuid, **payload)
        return self.db.task_logs.create(telegram_user_id=job.get("telegram_user_id"), **payload)

    def _pause_job(
        self,
        job: dict[str, Any],
        task_log: dict[str, Any],
        current_time: datetime,
        *,
        unfinished_items_count: int,
    ) -> None:
        self.db.task_logs.update(
            task_log["id"],
            status="success",
            current_time=current_time,
            description=(
                f"user vocabulary import job processing paused: "
                f"import_job_id={job['id']} unfinished_items={unfinished_items_count}"
            ),
            result_json=self.job_task_result_service.build_import_job_task_result(
                job["id"],
                import_job_status="processing",
            ),
            import_job_id=job["id"],
        )

    def _process_existing_core_assignments(self, job: dict[str, Any], *, current_time: datetime) -> None:
        user_uuid = resolve_job_user_uuid(job)
        for item in self.db.user_import_jobs.list_items(job["id"]):
            if item["status"] == "found_existing" and item["existing_word_id"] is not None:
                if user_uuid is not None and hasattr(
                    self.db.dictionary_lookup,
                    "create_user_core_word_assignment_for_user_uuid",
                ):
                    self.db.dictionary_lookup.create_user_core_word_assignment_for_user_uuid(
                        str(user_uuid),
                        item["existing_word_id"],
                        current_time=current_time,
                    )
                    continue
                telegram_user_id = job.get("telegram_user_id")
                if telegram_user_id is None:
                    continue
                self.db.dictionary_lookup.create_user_core_word_assignment(
                    telegram_user_id,
                    item["existing_word_id"],
                    current_time=current_time,
                )

    def _complete_job(self, job: dict[str, Any], task_log: dict[str, Any], current_time: datetime) -> None:
        self.db.user_import_jobs.complete(job["id"], status="completed", current_time=current_time)
        self.db.task_logs.update(
            task_log["id"],
            status="success",
            current_time=current_time,
            description=f"user vocabulary import job completed: import_job_id={job['id']}",
            result_json=self.job_task_result_service.build_import_job_task_result(
                job["id"],
                import_job_status="completed",
            ),
            import_job_id=job["id"],
        )

    def _fail_job(
        self,
        job: dict[str, Any],
        task_log: dict[str, Any],
        current_time: datetime,
        error: Exception,
    ) -> None:
        error_text = self.sanitize_external_error_text(str(error))
        error_context = self.build_task_error_context(
            task_log_id=task_log["id"],
            telegram_user_id=job.get("telegram_user_id"),
            source_type=job["source_type"],
            source_identifier=job["source_identifier"],
            import_job_id=job["id"],
        )
        log_user_import_pipeline_error(
            self.db,
            level="fatal",
            stage="import_job_processing",
            error_text=error_text,
            error=error,
            task_key="user_import.job_processing",
            import_job_id=int(job["id"]),
            task_log_id=int(task_log["id"]),
            telegram_user_id=job.get("telegram_user_id"),
            current_time=current_time,
            context_json=error_context,
        )
        self.db.user_import_jobs.complete(
            job["id"],
            status="failed",
            current_time=current_time,
            last_error=error_text,
        )
        self.db.task_logs.update(
            task_log["id"],
            status="fatal",
            current_time=current_time,
            description=f"user vocabulary import job crashed: import_job_id={job['id']}",
            error_text=error_text,
            result_json=self.job_task_result_service.build_import_job_task_result(
                job["id"],
                import_job_status="failed",
            ),
            import_job_id=job["id"],
        )
