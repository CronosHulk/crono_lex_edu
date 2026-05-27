from __future__ import annotations

from collections.abc import Callable
from typing import Any, ParamSpec, Protocol, TypeVar

import app.validation.pagination as validation_pagination
import app.validation.request_values as request_values
from app.application.admin.imports.errors import (
    AdminImportReadAccessDeniedError,
    AdminImportReadNotFoundError,
    AdminImportReadValidationError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.domain.user_import.statuses import (
    ACTIVE_IMPORT_ITEM_STATUSES,
    FAILED_IMPORT_ITEM_STATUSES,
    SUCCESSFUL_IMPORT_ITEM_STATUSES,
)

DEFAULT_PAGE_SIZE = 50
ALLOWED_PAGE_SIZES = {50, 100}
IMPORT_JOB_STATUSES = {"queued", "processing", "completed", "failed"}
IMPORT_ITEM_STATUSES = (
    set(ACTIVE_IMPORT_ITEM_STATUSES)
    | set(FAILED_IMPORT_ITEM_STATUSES)
    | set(SUCCESSFUL_IMPORT_ITEM_STATUSES)
)
P = ParamSpec("P")
T = TypeVar("T")


class AdminImportReadAclPermissionsPort(Protocol):
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None: ...


class AdminImportReadJobsPort(Protocol):
    def list_admin_jobs(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def list_admin_items(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_admin_job_filter_metadata(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_admin_item_filter_metadata(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_job(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...

    def list_item_status_counts(self, *args: Any, **kwargs: Any) -> dict[str, int]: ...


class AdminImportReadTaskLogsPort(Protocol):
    def get(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...

    def get_latest_for_import_job(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...


class AdminImportReadUsersPort(Protocol):
    def get_by_id(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...


class AdminImportReadDatabasePort(Protocol):
    acl_permissions: AdminImportReadAclPermissionsPort
    user_import_jobs: AdminImportReadJobsPort
    task_logs: AdminImportReadTaskLogsPort
    admin_users: AdminImportReadUsersPort


class AdminImportReadService:
    def __init__(self, db: AdminImportReadDatabasePort) -> None:
        self.db = db

    def list_import_jobs(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_imports_access(actor, action="imports/list_jobs", detail="Import jobs access is not allowed")
        page, page_size = _import_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        return self.db.user_import_jobs.list_admin_jobs(
            page=page,
            page_size=page_size,
            status=_import_read_validation(
                request_values.ensure_allowed_values,
                params.get("status"),
                IMPORT_JOB_STATUSES,
                "status",
            ),
            source_type=_import_read_validation(
                request_values.ensure_values_match_pattern,
                params.get("source_type"),
                "source_type",
            ),
            user_id=params.get("user_id"),
            search=_import_read_validation(
                request_values.ensure_text,
                params.get("search"),
                "search",
                max_length=120,
            ),
        )

    def list_import_items(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_imports_access(actor, action="imports/list_items", detail="Import items access is not allowed")
        page, page_size = _import_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        return self.db.user_import_jobs.list_admin_items(
            page=page,
            page_size=page_size,
            status=_import_read_validation(
                request_values.ensure_allowed_values,
                params.get("status"),
                IMPORT_ITEM_STATUSES,
                "status",
            ),
            import_job_id=params.get("import_job_id"),
            user_id=params.get("user_id"),
            search=_import_read_validation(
                request_values.ensure_text,
                params.get("search"),
                "search",
                max_length=120,
            ),
        )

    def get_import_job_filter_metadata(self) -> dict[str, Any]:
        return self.db.user_import_jobs.get_admin_job_filter_metadata()

    def get_import_item_filter_metadata(self) -> dict[str, Any]:
        return self.db.user_import_jobs.get_admin_item_filter_metadata()

    def get_import_job_detail(self, *, actor: dict[str, Any], import_job_id: int) -> dict[str, Any]:
        self._require_imports_access(actor, action="imports/view_job", detail="Import job access is not allowed")
        job = self.db.user_import_jobs.get_job(import_job_id)
        if job is None:
            raise AdminImportReadNotFoundError()
        status_counts = self.db.user_import_jobs.list_item_status_counts(import_job_id)
        origin_task_log = None
        if job.get("task_log_id") is not None:
            origin_task_log = self.db.task_logs.get(int(job["task_log_id"]))
        processing_task_log = self.db.task_logs.get_latest_for_import_job(
            import_job_id,
            task_type="user_vocabulary_import_job_process",
        )
        return {
            "job": job,
            "status_counts": status_counts,
            "origin_task_log": origin_task_log,
            "processing_task_log": processing_task_log,
            "user": self.db.admin_users.get_by_id(str(job["user_id"])),
        }

    def _require_imports_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminImportReadAccessDeniedError(error.detail) from error


def _import_read_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise AdminImportReadValidationError(error.detail) from error
