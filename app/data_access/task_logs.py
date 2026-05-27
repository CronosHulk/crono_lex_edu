from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select

from app.data_access.filtering import normalize_filter_values
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import TaskLog
from app.orm import SessionManager
from app.reference.task_logs import (
    BILLING_TASK_LOG_PREFIXES,
    TASK_LOG_STATUS_OPTIONS,
    task_log_type_options_for_scope,
    validate_task_log_scope,
    validate_task_status,
)

FINISHED_TASK_LOG_STATUSES = {"success", "error", "fatal"}


def task_log_to_dict(row: TaskLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "task_type": row.task_type,
        "status": row.status,
        "user_id": str(row.user_uuid) if row.user_uuid else None,
        "user_uuid": str(row.user_uuid) if row.user_uuid else None,
        "source_type": row.source_type,
        "source_identifier": row.source_identifier,
        "import_job_id": row.import_job_id,
        "description": row.description,
        "error_text": row.error_text,
        "result_json": row.result_json or {},
        "started": row.started,
        "finished": row.finished,
        "created": row.created,
        "updated": row.updated,
    }


class TaskLogRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

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
    ) -> dict[str, Any]:
        validate_task_status(status)
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id) if telegram_user_id is not None else None
            row = TaskLog(
                task_type=task_type,
                status=status,
                user_uuid=user_uuid,
                source_type=source_type,
                source_identifier=source_identifier,
                import_job_id=import_job_id,
                description=description,
                error_text=error_text,
                result_json=result_json or {},
                started=current_time,
                finished=current_time if status in FINISHED_TASK_LOG_STATUSES else None,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return task_log_to_dict(row)

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
    ) -> dict[str, Any]:
        validate_task_status(status)
        with self.session_manager.session() as session:
            row = TaskLog(
                task_type=task_type,
                status=status,
                user_uuid=UUID(str(user_uuid)) if user_uuid else None,
                source_type=source_type,
                source_identifier=source_identifier,
                import_job_id=import_job_id,
                description=description,
                error_text=error_text,
                result_json=result_json or {},
                started=current_time,
                finished=current_time if status in FINISHED_TASK_LOG_STATUSES else None,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return task_log_to_dict(row)

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
    ) -> dict[str, Any] | None:
        validate_task_status(status)
        with self.session_manager.session() as session:
            row = session.get(TaskLog, task_log_id)
            if row is None:
                return None
            row.status = status
            row.description = description
            row.error_text = error_text
            row.result_json = result_json or {}
            row.import_job_id = import_job_id
            row.updated = current_time
            row.finished = current_time if status in FINISHED_TASK_LOG_STATUSES else None
            return task_log_to_dict(row)

    def claim_queued(
        self,
        *,
        task_type: str,
        current_time: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(TaskLog)
                .where(TaskLog.task_type == task_type, TaskLog.status == "queued")
                .order_by(TaskLog.created.asc(), TaskLog.id.asc())
                .limit(max(int(limit), 1))
                .with_for_update(skip_locked=True)
            ).all()
            payload: list[dict[str, Any]] = []
            for row in rows:
                row.status = "processing"
                row.updated = current_time
                payload.append(task_log_to_dict(row))
            return payload

    def iter_claim_queued(
        self,
        *,
        task_type: str,
        current_time: datetime,
    ) -> Iterator[dict[str, Any]]:
        while True:
            payload = self.claim_queued(task_type=task_type, current_time=current_time, limit=1)
            if not payload:
                return
            yield payload[0]

    def requeue_stale_processing(
        self,
        *,
        task_type: str,
        current_time: datetime,
        stale_before: datetime,
        limit: int | None = None,
    ) -> int:
        with self.session_manager.session() as session:
            stmt = (
                select(TaskLog)
                .where(
                    TaskLog.task_type == task_type,
                    TaskLog.status == "processing",
                    TaskLog.updated <= stale_before,
                )
                .order_by(TaskLog.updated.asc(), TaskLog.id.asc())
                .with_for_update(skip_locked=True)
            )
            if limit is not None:
                stmt = stmt.limit(max(int(limit), 1))
            rows = session.scalars(stmt).all()
            for row in rows:
                row.status = "queued"
                row.updated = current_time
                row.finished = None
                row.result_json = {
                    **(row.result_json or {}),
                    "requeued_at": current_time.isoformat(),
                    "requeue_reason": "stale_processing",
                }
            return len(rows)

    def mark_stale_processing_fatal(
        self,
        *,
        task_type: str,
        current_time: datetime,
        stale_before: datetime,
        description: str,
        error_text: str,
        result_json: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> int:
        with self.session_manager.session() as session:
            stmt = (
                select(TaskLog)
                .where(
                    TaskLog.task_type == task_type,
                    TaskLog.status == "processing",
                    TaskLog.updated <= stale_before,
                )
                .order_by(TaskLog.updated.asc(), TaskLog.id.asc())
                .with_for_update(skip_locked=True)
            )
            if limit is not None:
                stmt = stmt.limit(max(int(limit), 1))
            rows = session.scalars(stmt).all()
            for row in rows:
                row.status = "fatal"
                row.description = description
                row.error_text = error_text
                row.finished = current_time
                row.updated = current_time
                row.result_json = {
                    **(row.result_json or {}),
                    **(result_json or {}),
                    "stale_marked_at": current_time.isoformat(),
                }
            return len(rows)

    def has_active_for_user(
        self,
        *,
        task_type: str,
        user_uuid: str | UUID,
        statuses: set[str] | None = None,
    ) -> bool:
        normalized_statuses = statuses or {"queued", "processing"}
        for status in normalized_statuses:
            validate_task_status(status)
        with self.session_manager.session() as session:
            count = session.scalar(
                select(func.count(TaskLog.id)).where(
                    TaskLog.task_type == task_type,
                    TaskLog.user_uuid == UUID(str(user_uuid)),
                    TaskLog.status.in_(normalized_statuses),
                )
            )
            return bool(int(count or 0))

    def has_for_user_source(
        self,
        *,
        task_type: str,
        user_uuid: str | UUID,
        source_identifier: str,
        statuses: set[str],
        source_type: str | None = None,
    ) -> bool:
        normalized_statuses = {str(status) for status in statuses}
        for status in normalized_statuses:
            validate_task_status(status)
        normalized_source_identifier = str(source_identifier or "").strip()
        if not normalized_source_identifier:
            return False
        filters = [
            TaskLog.task_type == task_type,
            TaskLog.user_uuid == UUID(str(user_uuid)),
            TaskLog.source_identifier == normalized_source_identifier,
            TaskLog.status.in_(normalized_statuses),
        ]
        if source_type is not None:
            filters.append(TaskLog.source_type == source_type)
        with self.session_manager.session() as session:
            count = session.scalar(select(func.count(TaskLog.id)).where(*filters))
            return bool(int(count or 0))

    def get(self, task_log_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(TaskLog, task_log_id)
            return task_log_to_dict(row) if row is not None else None

    def list_admin(
        self,
        *,
        page: int,
        page_size: int,
        task_type: str | list[str] | None = None,
        status: str | list[str] | None = None,
        user_id: str | None = None,
        import_job_id: int | None = None,
        search: str = "",
        scope: str = "operations",
    ) -> dict[str, Any]:
        validate_task_log_scope(scope)
        offset = (max(page, 1) - 1) * page_size
        with self.session_manager.session() as session:
            filters = _task_log_scope_filters(scope)
            task_type_values = normalize_filter_values(task_type)
            if task_type_values:
                filters.append(TaskLog.task_type.in_(task_type_values))
            status_values = normalize_filter_values(status)
            if status_values:
                filters.append(TaskLog.status.in_(status_values))
            if user_id:
                filters.append(TaskLog.user_uuid == user_id)
            if import_job_id is not None:
                filters.append(TaskLog.import_job_id == import_job_id)
            normalized_search = search.strip().lower()
            if normalized_search:
                like_value = f"%{normalized_search}%"
                filters.append(
                    or_(
                        func.lower(TaskLog.task_type).like(like_value),
                        func.lower(TaskLog.source_type).like(like_value),
                        func.lower(TaskLog.source_identifier).like(like_value),
                        func.lower(TaskLog.description).like(like_value),
                        func.lower(TaskLog.error_text).like(like_value),
                    )
                )

            query = select(TaskLog).where(*filters)
            count_query = select(func.count(TaskLog.id)).where(*filters)
            total = int(session.scalar(count_query) or 0)
            rows = session.scalars(
                query.order_by(TaskLog.created.desc(), TaskLog.id.desc()).offset(offset).limit(page_size)
            ).all()
            return {
                "items": [task_log_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }

    def get_filter_metadata(self, *, scope: str = "operations") -> dict[str, Any]:
        validate_task_log_scope(scope)
        task_types = task_log_type_options_for_scope(scope)
        return {
            "entity": "task_logs",
            "scope": scope,
            "page_sizes": [50, 100],
            "filters": [
                {"name": "search", "type": "text", "label": "Пошук"},
                {
                    "name": "task_type",
                    "type": "multi_select",
                    "label": "Task type",
                    "options": [{"value": value, "label": value} for value in task_types],
                },
                {
                    "name": "status",
                    "type": "multi_select",
                    "label": "Status",
                    "options": [{"value": value, "label": value} for value in TASK_LOG_STATUS_OPTIONS],
                },
                {"name": "user_id", "type": "text", "label": "User UUID"},
                {"name": "import_job_id", "type": "number", "label": "Import job ID"},
            ],
        }

    def get_latest_for_import_job(
        self,
        import_job_id: int,
        *,
        task_type: str | None = None,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            stmt = select(TaskLog).where(TaskLog.import_job_id == import_job_id)
            if task_type is not None:
                stmt = stmt.where(TaskLog.task_type == task_type)
            row = session.scalar(stmt.order_by(TaskLog.created.desc(), TaskLog.id.desc()).limit(1))
            return task_log_to_dict(row) if row is not None else None


def _task_log_scope_filters(scope: str) -> list[Any]:
    if scope == "all":
        return []
    billing_filter = or_(*(TaskLog.task_type.like(f"{prefix}%") for prefix in BILLING_TASK_LOG_PREFIXES))
    if scope == "billing":
        return [billing_filter]
    return [~billing_filter]
