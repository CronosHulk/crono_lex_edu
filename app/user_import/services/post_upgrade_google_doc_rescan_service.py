from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, cast

from app.user_import.services.post_upgrade_google_doc_rescan_queue_service import (
    SupportsClaimQueued,
    SupportsCreateForUserUuidTaskLog,
    SupportsGetBoundGoogleDocForTelegramUser,
    SupportsHasActiveForUserTaskLog,
    SupportsHasForUserSourceTaskLog,
    SupportsIterClaimQueued,
    SupportsListPostUpgradeRescanCandidates,
    SupportsRequeueStaleProcessing,
    UserImportPostUpgradeGoogleDocRescanQueueService,
)

POST_UPGRADE_GOOGLE_DOC_RESCAN_LIMIT = 300
POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE = "post_upgrade_google_doc_rescan"
POST_UPGRADE_GOOGLE_DOC_RESCAN_STALE_HOURS = 24
POST_UPGRADE_GOOGLE_DOC_RESCAN_DEDUP_STATUSES = {"queued", "processing", "success"}

__all__ = [
    "POST_UPGRADE_GOOGLE_DOC_RESCAN_DEDUP_STATUSES",
    "POST_UPGRADE_GOOGLE_DOC_RESCAN_LIMIT",
    "POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE",
    "POST_UPGRADE_GOOGLE_DOC_RESCAN_STALE_HOURS",
    "PostUpgradeGoogleDocRescanDatabasePort",
    "ProcessBoundGoogleDocSyncRow",
    "MarkBoundGoogleDocSyncFailed",
    "SupportsClaimQueued",
    "SupportsCreateForUserUuidTaskLog",
    "SupportsGetBoundGoogleDocForTelegramUser",
    "SupportsHasActiveForUserTaskLog",
    "SupportsHasForUserSourceTaskLog",
    "SupportsIterClaimQueued",
    "SupportsListPostUpgradeRescanCandidates",
    "SupportsRequeueStaleProcessing",
    "UserImportBoundSyncTaskLogsPort",
    "UserImportPostUpgradeGoogleDocRescanService",
]


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


class PostUpgradeGoogleDocRescanDatabasePort(Protocol):
    task_logs: UserImportBoundSyncTaskLogsPort


class ProcessBoundGoogleDocSyncRow(Protocol):
    def __call__(
        self,
        row: dict[str, Any],
        current_time: datetime,
        *,
        task_log_id: int,
        max_import_entries: int | None = None,
        task_scope: str = "bound_google_doc_sync",
        restart_from_beginning: bool = False,
    ) -> dict[str, Any]: ...


class MarkBoundGoogleDocSyncFailed(Protocol):
    def __call__(
        self,
        row: dict[str, Any],
        current_time: datetime,
        error: Exception,
        *,
        task_log_id: int,
    ) -> None: ...


class UserImportPostUpgradeGoogleDocRescanService:
    def __init__(
        self,
        db: PostUpgradeGoogleDocRescanDatabasePort,
        google_docs: object,
        *,
        process_bound_google_doc_sync_row: ProcessBoundGoogleDocSyncRow,
        mark_bound_google_doc_sync_failed: MarkBoundGoogleDocSyncFailed,
    ) -> None:
        self.db = db
        self.google_docs = google_docs
        self.process_bound_google_doc_sync_row = process_bound_google_doc_sync_row
        self.mark_bound_google_doc_sync_failed = mark_bound_google_doc_sync_failed
        self.post_upgrade_rescan_queue_service = UserImportPostUpgradeGoogleDocRescanQueueService(
            db,
            google_docs,
            process_bound_google_doc_sync_row=process_bound_google_doc_sync_row,
            mark_bound_google_doc_sync_failed=mark_bound_google_doc_sync_failed,
            rescan_limit=POST_UPGRADE_GOOGLE_DOC_RESCAN_LIMIT,
            task_scope=POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE,
            stale_hours=POST_UPGRADE_GOOGLE_DOC_RESCAN_STALE_HOURS,
            dedup_statuses=POST_UPGRADE_GOOGLE_DOC_RESCAN_DEDUP_STATUSES,
        )

    def rescan_after_plan_upgrade(
        self,
        *,
        telegram_user_id: int,
        user_uuid: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        if not hasattr(self.google_docs, "get_bound_doc_for_telegram_user"):
            return None
        google_docs = cast(SupportsGetBoundGoogleDocForTelegramUser, self.google_docs)
        row = google_docs.get_bound_doc_for_telegram_user(telegram_user_id)
        if row is None:
            return None
        row = {
            **row,
            "telegram_user_id": telegram_user_id,
            "user_id": user_uuid,
            "user_uuid": user_uuid,
            "source_identifier": row.get("source_identifier") or row.get("google_doc_id"),
        }
        if not row.get("source_identifier"):
            return None
        task_log = self.db.task_logs.create(
            task_type=POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE,
            status="processing",
            current_time=current_time,
            telegram_user_id=telegram_user_id,
            source_type="google_doc",
            source_identifier=row["source_identifier"],
            description=(
                "post-upgrade google doc rescan started: "
                f"telegram_user_id={telegram_user_id} source_identifier={row['source_identifier']}"
            ),
        )
        try:
            result = self.process_bound_google_doc_sync_row(
                row,
                current_time,
                task_log_id=task_log["id"],
                max_import_entries=POST_UPGRADE_GOOGLE_DOC_RESCAN_LIMIT,
                task_scope=POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE,
                restart_from_beginning=True,
            )
            self.db.task_logs.update(
                task_log["id"],
                status="success",
                current_time=current_time,
                description=(
                    "post-upgrade google doc rescan completed: "
                    f"telegram_user_id={telegram_user_id} source_identifier={row['source_identifier']}"
                ),
                error_text=None,
                result_json={**result, "rescan_limit": POST_UPGRADE_GOOGLE_DOC_RESCAN_LIMIT},
                import_job_id=result.get("created_import_job_id"),
            )
            return result
        except Exception as error:
            self.mark_bound_google_doc_sync_failed(row, current_time, error, task_log_id=task_log["id"])
            return {
                "status": "failed",
                "error": "Post-upgrade Google Doc rescan failed",
                "task_log_id": task_log["id"],
            }

    def queue_post_upgrade_rescan(
        self,
        *,
        telegram_user_id: int,
        user_uuid: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        return self.post_upgrade_rescan_queue_service.queue_post_upgrade_rescan(
            telegram_user_id=telegram_user_id,
            user_uuid=user_uuid,
            current_time=current_time,
        )

    def enqueue_post_upgrade_rescans(self, current_time: datetime, claimed_until: datetime) -> None:
        self.post_upgrade_rescan_queue_service.enqueue_post_upgrade_rescans(current_time, claimed_until)
