from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any, Protocol, cast
from uuid import UUID

from app.subscriptions.plans import PLAN_PREMIUM, PLAN_PREMIUM_PLUS


class SupportsGetBoundGoogleDocForTelegramUser(Protocol):
    def get_bound_doc_for_telegram_user(self, telegram_user_id: int) -> dict[str, Any] | None: ...


class SupportsListPostUpgradeRescanCandidates(Protocol):
    def list_post_upgrade_rescan_candidates(
        self,
        *,
        current_time: datetime,
        paid_plan_keys: set[str],
        limit: int,
    ) -> list[dict[str, Any]]: ...


class UserImportPostUpgradeGoogleDocRescanQueueTaskLogsPort(Protocol):
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


class SupportsCreateForUserUuidTaskLog(Protocol):
    def create_for_user_uuid(
        self,
        *,
        task_type: str,
        status: str,
        current_time: datetime,
        user_uuid: str | UUID | None = None,
        source_type: str | None = None,
        source_identifier: str | None = None,
        import_job_id: int | None = None,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class SupportsRequeueStaleProcessing(Protocol):
    def requeue_stale_processing(
        self,
        *,
        task_type: str,
        current_time: datetime,
        stale_before: datetime,
        limit: int | None = None,
    ) -> int: ...


class SupportsIterClaimQueued(Protocol):
    def iter_claim_queued(
        self,
        *,
        task_type: str,
        current_time: datetime,
    ) -> Iterator[dict[str, Any]]: ...


class SupportsClaimQueued(Protocol):
    def claim_queued(
        self,
        *,
        task_type: str,
        current_time: datetime,
        limit: int,
    ) -> list[dict[str, Any]]: ...


class SupportsHasForUserSourceTaskLog(Protocol):
    def has_for_user_source(
        self,
        *,
        task_type: str,
        user_uuid: str | UUID,
        source_identifier: str,
        statuses: set[str],
        source_type: str | None = None,
    ) -> bool: ...


class SupportsHasActiveForUserTaskLog(Protocol):
    def has_active_for_user(
        self,
        *,
        task_type: str,
        user_uuid: str | UUID,
        statuses: set[str] | None = None,
    ) -> bool: ...


class PostUpgradeGoogleDocRescanQueueDatabasePort(Protocol):
    task_logs: UserImportPostUpgradeGoogleDocRescanQueueTaskLogsPort


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


class UserImportPostUpgradeGoogleDocRescanQueueService:
    def __init__(
        self,
        db: PostUpgradeGoogleDocRescanQueueDatabasePort,
        google_docs: object,
        *,
        process_bound_google_doc_sync_row: ProcessBoundGoogleDocSyncRow,
        mark_bound_google_doc_sync_failed: MarkBoundGoogleDocSyncFailed,
        rescan_limit: int,
        task_scope: str,
        stale_hours: int,
        dedup_statuses: set[str],
    ) -> None:
        self.db = db
        self.google_docs = google_docs
        self.process_bound_google_doc_sync_row = process_bound_google_doc_sync_row
        self.mark_bound_google_doc_sync_failed = mark_bound_google_doc_sync_failed
        self.rescan_limit = rescan_limit
        self.task_scope = task_scope
        self.stale_hours = stale_hours
        self.dedup_statuses = dedup_statuses

    def queue_post_upgrade_rescan(
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
        source_identifier = row.get("source_identifier") or row.get("google_doc_id")
        if not source_identifier:
            return None
        if self._has_existing_post_upgrade_rescan(
            user_uuid=user_uuid,
            source_identifier=str(source_identifier),
        ):
            return {"status": "queued", "task_log_id": None, "rescan_limit": self.rescan_limit}
        task_log = self._create_post_upgrade_rescan_task(
            telegram_user_id=telegram_user_id,
            user_uuid=user_uuid,
            source_identifier=str(source_identifier),
            current_time=current_time,
        )
        return {
            "status": "queued",
            "task_log_id": task_log["id"],
            "rescan_limit": self.rescan_limit,
        }

    def enqueue_post_upgrade_rescans(self, current_time: datetime, claimed_until: datetime) -> None:
        _ = claimed_until
        self._queue_missing_post_upgrade_rescans(current_time)
        if hasattr(self.db.task_logs, "requeue_stale_processing"):
            requeue_task_logs = cast(SupportsRequeueStaleProcessing, self.db.task_logs)
            requeue_task_logs.requeue_stale_processing(
                task_type=self.task_scope,
                current_time=current_time,
                stale_before=current_time - timedelta(hours=self.stale_hours),
            )
        if hasattr(self.db.task_logs, "iter_claim_queued"):
            streaming_task_logs = cast(SupportsIterClaimQueued, self.db.task_logs)
            for task_log in streaming_task_logs.iter_claim_queued(
                task_type=self.task_scope,
                current_time=current_time,
            ):
                self._process_post_upgrade_rescan_task(task_log, current_time)
            return
        if not hasattr(self.db.task_logs, "claim_queued"):
            return
        claiming_task_logs = cast(SupportsClaimQueued, self.db.task_logs)
        while True:
            task_logs = claiming_task_logs.claim_queued(
                task_type=self.task_scope,
                current_time=current_time,
                limit=1,
            )
            if not task_logs:
                return
            task_log = task_logs[0]
            self._process_post_upgrade_rescan_task(task_log, current_time)

    def _create_post_upgrade_rescan_task(
        self,
        *,
        telegram_user_id: int,
        user_uuid: str,
        source_identifier: str,
        current_time: datetime,
    ) -> dict[str, Any]:
        payload = {
            "task_type": self.task_scope,
            "status": "queued",
            "current_time": current_time,
            "source_type": "google_doc",
            "source_identifier": source_identifier,
            "description": (
                "post-upgrade google doc rescan queued: "
                f"telegram_user_id={telegram_user_id} source_identifier={source_identifier}"
            ),
            "result_json": {
                "telegram_user_id": telegram_user_id,
                "rescan_limit": self.rescan_limit,
            },
        }
        if hasattr(self.db.task_logs, "create_for_user_uuid"):
            task_logs_with_user_uuid = cast(SupportsCreateForUserUuidTaskLog, self.db.task_logs)
            return task_logs_with_user_uuid.create_for_user_uuid(user_uuid=user_uuid, **payload)
        return self.db.task_logs.create(telegram_user_id=telegram_user_id, **payload)

    def _queue_missing_post_upgrade_rescans(self, current_time: datetime) -> None:
        if not hasattr(self.google_docs, "list_post_upgrade_rescan_candidates"):
            return
        google_docs = cast(SupportsListPostUpgradeRescanCandidates, self.google_docs)
        for row in google_docs.list_post_upgrade_rescan_candidates(
            current_time=current_time,
            paid_plan_keys={PLAN_PREMIUM, PLAN_PREMIUM_PLUS},
            limit=self.rescan_limit,
        ):
            user_uuid = str(row.get("user_uuid") or row.get("user_id") or "").strip()
            source_identifier = str(row.get("source_identifier") or row.get("google_doc_id") or "").strip()
            if not user_uuid or not source_identifier:
                continue
            if self._has_existing_post_upgrade_rescan(
                user_uuid=user_uuid,
                source_identifier=source_identifier,
            ):
                continue
            self._create_post_upgrade_rescan_task(
                telegram_user_id=int(row["telegram_user_id"]),
                user_uuid=user_uuid,
                source_identifier=source_identifier,
                current_time=current_time,
            )

    def _has_existing_post_upgrade_rescan(self, *, user_uuid: str, source_identifier: str) -> bool:
        normalized_source_identifier = str(source_identifier or "").strip()
        if not normalized_source_identifier:
            return False
        if hasattr(self.db.task_logs, "has_for_user_source"):
            task_logs_with_source_dedup = cast(SupportsHasForUserSourceTaskLog, self.db.task_logs)
            return bool(
                task_logs_with_source_dedup.has_for_user_source(
                    task_type=self.task_scope,
                    user_uuid=user_uuid,
                    source_type="google_doc",
                    source_identifier=normalized_source_identifier,
                    statuses=self.dedup_statuses,
                )
            )
        if hasattr(self.db.task_logs, "has_active_for_user"):
            task_logs_with_active_dedup = cast(SupportsHasActiveForUserTaskLog, self.db.task_logs)
            return bool(
                task_logs_with_active_dedup.has_active_for_user(
                    task_type=self.task_scope,
                    user_uuid=user_uuid,
                )
            )
        return False

    def _has_successful_post_upgrade_rescan(self, *, user_uuid: str, source_identifier: str) -> bool:
        normalized_source_identifier = str(source_identifier or "").strip()
        if not normalized_source_identifier or not hasattr(self.db.task_logs, "has_for_user_source"):
            return False
        task_logs_with_source_dedup = cast(SupportsHasForUserSourceTaskLog, self.db.task_logs)
        return bool(
            task_logs_with_source_dedup.has_for_user_source(
                task_type=self.task_scope,
                user_uuid=user_uuid,
                source_type="google_doc",
                source_identifier=normalized_source_identifier,
                statuses={"success"},
            )
        )

    def _process_post_upgrade_rescan_task(self, task_log: dict[str, Any], current_time: datetime) -> None:
        result_json = task_log.get("result_json") or {}
        telegram_user_id = int(result_json.get("telegram_user_id") or 0)
        source_identifier = str(task_log.get("source_identifier") or "").strip()
        user_uuid = str(task_log.get("user_uuid") or task_log.get("user_id") or "").strip()
        if not telegram_user_id or not source_identifier or not user_uuid:
            self.db.task_logs.update(
                int(task_log["id"]),
                status="error",
                current_time=current_time,
                description="post-upgrade google doc rescan failed: missing queued task metadata",
                error_text="Missing telegram_user_id, user_uuid or source_identifier",
                result_json={**result_json, "rescan_limit": self.rescan_limit},
            )
            return
        if self._has_successful_post_upgrade_rescan(user_uuid=user_uuid, source_identifier=source_identifier):
            self.db.task_logs.update(
                int(task_log["id"]),
                status="success",
                current_time=current_time,
                description=(
                    "post-upgrade google doc rescan skipped: "
                    f"already completed for user_uuid={user_uuid} source_identifier={source_identifier}"
                ),
                error_text=None,
                result_json={
                    **result_json,
                    "rescan_limit": self.rescan_limit,
                    "skipped_reason": "post_upgrade_rescan_already_completed",
                },
            )
            return
        row = {
            "telegram_user_id": telegram_user_id,
            "user_id": user_uuid,
            "user_uuid": user_uuid,
            "source_identifier": source_identifier,
        }
        try:
            result = self.process_bound_google_doc_sync_row(
                row,
                current_time,
                task_log_id=int(task_log["id"]),
                max_import_entries=self.rescan_limit,
                task_scope=self.task_scope,
                restart_from_beginning=True,
            )
            self.db.task_logs.update(
                int(task_log["id"]),
                status="success",
                current_time=current_time,
                description=(
                    "post-upgrade google doc rescan completed: "
                    f"telegram_user_id={telegram_user_id} source_identifier={source_identifier}"
                ),
                error_text=None,
                result_json={**result, "rescan_limit": self.rescan_limit},
                import_job_id=result.get("created_import_job_id"),
            )
        except Exception as error:
            self.mark_bound_google_doc_sync_failed(row, current_time, error, task_log_id=int(task_log["id"]))
