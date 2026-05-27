from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.user_import.runtime_settings import read_user_import_runtime_settings
from app.user_import.services.post_upgrade_google_doc_rescan_service import (
    POST_UPGRADE_GOOGLE_DOC_RESCAN_DEDUP_STATUSES,
    POST_UPGRADE_GOOGLE_DOC_RESCAN_LIMIT,
    POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE,
    POST_UPGRADE_GOOGLE_DOC_RESCAN_STALE_HOURS,
    SupportsClaimQueued,
    SupportsCreateForUserUuidTaskLog,
    SupportsGetBoundGoogleDocForTelegramUser,
    SupportsHasActiveForUserTaskLog,
    SupportsHasForUserSourceTaskLog,
    SupportsIterClaimQueued,
    SupportsListPostUpgradeRescanCandidates,
    SupportsRequeueStaleProcessing,
    UserImportPostUpgradeGoogleDocRescanService,
)

__all__ = [
    "POST_UPGRADE_GOOGLE_DOC_RESCAN_DEDUP_STATUSES",
    "POST_UPGRADE_GOOGLE_DOC_RESCAN_LIMIT",
    "POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE",
    "POST_UPGRADE_GOOGLE_DOC_RESCAN_STALE_HOURS",
    "SupportsClaimQueued",
    "SupportsCreateForUserUuidTaskLog",
    "SupportsGetBoundGoogleDocForTelegramUser",
    "SupportsHasActiveForUserTaskLog",
    "SupportsHasForUserSourceTaskLog",
    "SupportsIterClaimQueued",
    "SupportsListPostUpgradeRescanCandidates",
    "SupportsRequeueStaleProcessing",
    "UserImportBoundGoogleDocSyncProcessorPort",
    "UserImportBoundGoogleDocSyncService",
    "UserImportBoundSyncDatabasePort",
    "UserImportBoundSyncJobsPort",
    "UserImportBoundSyncTaskLogsPort",
    "UserImportGoogleDocSyncRepository",
    "UserImportPostUpgradeGoogleDocRescanService",
]


class UserImportGoogleDocSyncRepository(Protocol):
    def claim_due_syncs(
        self,
        current_time: datetime,
        sync_hour: int,
        sync_interval_days: int,
        claimed_until: datetime,
        sync_weekdays: list[int] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...


class UserImportBoundSyncTaskLogsPort(Protocol):
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


class UserImportBoundSyncJobsPort(Protocol):
    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None: ...

    def list_unfinished_items(self, job_id: int) -> list[dict[str, Any]]: ...

    def complete(
        self,
        job_id: int,
        *,
        status: str,
        current_time: datetime,
        last_error: str | None = None,
    ) -> None: ...


class UserImportBoundSyncDatabasePort(Protocol):
    task_logs: UserImportBoundSyncTaskLogsPort
    user_import_jobs: UserImportBoundSyncJobsPort


class UserImportBoundGoogleDocSyncProcessorPort(Protocol):
    def process_bound_google_doc_sync_row(
        self,
        row: dict[str, Any],
        current_time: datetime,
        *,
        task_log_id: int,
        max_import_entries: int | None = None,
        task_scope: str = "bound_google_doc_sync",
        restart_from_beginning: bool = False,
    ) -> dict[str, Any]: ...

    def mark_bound_google_doc_sync_failed(
        self,
        row: dict[str, Any],
        current_time: datetime,
        error: Exception,
        *,
        task_log_id: int,
        build_task_error_context: Callable[..., dict[str, Any]],
        build_next_retry_at: Callable[[datetime, int], datetime | None],
    ) -> None: ...


class UserImportBoundGoogleDocSyncService:
    def __init__(
        self,
        db: UserImportBoundSyncDatabasePort,
        google_docs: UserImportGoogleDocSyncRepository,
        sync_processor: UserImportBoundGoogleDocSyncProcessorPort,
        *,
        build_task_error_context: Callable[..., dict[str, Any]],
        build_next_retry_at: Callable[[datetime, int], datetime | None],
        max_doc_syncs_per_run: int,
        prepare_import_job_items: Callable[..., None] | None = None,
    ) -> None:
        self.db = db
        self.google_docs = google_docs
        self.sync_processor = sync_processor
        self.build_task_error_context = build_task_error_context
        self.build_next_retry_at = build_next_retry_at
        self.max_doc_syncs_per_run = max_doc_syncs_per_run
        self.prepare_import_job_items = prepare_import_job_items
        self.post_upgrade_rescan_service = UserImportPostUpgradeGoogleDocRescanService(
            db,
            google_docs,
            process_bound_google_doc_sync_row=self.process_bound_google_doc_sync_row,
            mark_bound_google_doc_sync_failed=self.mark_bound_google_doc_sync_failed,
        )

    def enqueue_due_bound_google_doc_imports(self, current_time: datetime, claimed_until: datetime) -> None:
        runtime_settings = read_user_import_runtime_settings(self.db)
        sync_hour = int(runtime_settings["google_doc_sync_hour"])
        sync_interval_days = int(runtime_settings["google_doc_sync_interval_days"])
        sync_weekdays = runtime_settings.get("google_doc_sync_weekdays")
        for row in self.google_docs.claim_due_syncs(
            current_time,
            sync_hour,
            sync_interval_days,
            claimed_until,
            sync_weekdays=sync_weekdays if isinstance(sync_weekdays, list) else None,
            limit=self.max_doc_syncs_per_run,
        ):
            task_log = self.db.task_logs.create(
                task_type="bound_google_doc_sync",
                status="processing",
                current_time=current_time,
                telegram_user_id=row["telegram_user_id"],
                source_type="google_doc",
                source_identifier=row["source_identifier"],
                description=(
                    f"bound google doc sync started: "
                    f"telegram_user_id={row['telegram_user_id']} source_identifier={row['source_identifier']}"
                ),
            )
            try:
                result = self.process_bound_google_doc_sync_row(row, current_time, task_log_id=task_log["id"])
                self.db.task_logs.update(
                    task_log["id"],
                    status="success",
                    current_time=current_time,
                    description=(
                        f"bound google doc sync completed: "
                        f"telegram_user_id={row['telegram_user_id']} source_identifier={row['source_identifier']}"
                    ),
                    error_text=None,
                    result_json=result,
                    import_job_id=result.get("created_import_job_id"),
                )
            except Exception as error:
                self.mark_bound_google_doc_sync_failed(row, current_time, error, task_log_id=task_log["id"])

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
        result = self.sync_processor.process_bound_google_doc_sync_row(
            row,
            current_time,
            task_log_id=task_log_id,
            max_import_entries=max_import_entries,
            task_scope=task_scope,
            restart_from_beginning=restart_from_beginning,
        )
        self._prepare_created_job(row, result, current_time, task_log_id=task_log_id)
        return result

    def rescan_after_plan_upgrade(
        self,
        *,
        telegram_user_id: int,
        user_uuid: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        return self.post_upgrade_rescan_service.rescan_after_plan_upgrade(
            telegram_user_id=telegram_user_id,
            user_uuid=user_uuid,
            current_time=current_time,
        )

    def queue_post_upgrade_rescan(
        self,
        *,
        telegram_user_id: int,
        user_uuid: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        return self.post_upgrade_rescan_service.queue_post_upgrade_rescan(
            telegram_user_id=telegram_user_id,
            user_uuid=user_uuid,
            current_time=current_time,
        )

    def enqueue_post_upgrade_rescans(self, current_time: datetime, claimed_until: datetime) -> None:
        self.post_upgrade_rescan_service.enqueue_post_upgrade_rescans(current_time, claimed_until)

    def _prepare_created_job(
        self,
        row: dict[str, Any],
        result: dict[str, Any],
        current_time: datetime,
        *,
        task_log_id: int,
    ) -> None:
        if self.prepare_import_job_items is None:
            return
        job_id = result.get("created_import_job_id")
        if job_id is None:
            return
        job = self.db.user_import_jobs.get_job_for_user(int(row["telegram_user_id"]), int(job_id))
        if job is None:
            return
        self.prepare_import_job_items(job, current_time, task_log_id=task_log_id)
        if self.db.user_import_jobs.list_unfinished_items(int(job_id)):
            return
        self.db.user_import_jobs.complete(int(job_id), status="completed", current_time=current_time)

    def mark_bound_google_doc_sync_failed(
        self,
        row: dict[str, Any],
        current_time: datetime,
        error: Exception,
        *,
        task_log_id: int,
    ) -> None:
        self.sync_processor.mark_bound_google_doc_sync_failed(
            row,
            current_time,
            error,
            task_log_id=task_log_id,
            build_task_error_context=self.build_task_error_context,
            build_next_retry_at=self.build_next_retry_at,
        )
