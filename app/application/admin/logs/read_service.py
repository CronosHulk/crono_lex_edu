from __future__ import annotations

from collections.abc import Callable
from typing import Any, ParamSpec, Protocol, TypeVar

import app.validation.pagination as validation_pagination
import app.validation.request_values as request_values
from app.application.admin.logs.errors import (
    AdminLogReadAccessDeniedError,
    AdminLogReadNotFoundError,
    AdminLogReadValidationError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.reference.task_logs import (
    TASK_LOG_SCOPES,
    TASK_LOG_STATUSES,
    task_log_filter_values_for_scope,
)

DEFAULT_PAGE_SIZE = 50
ALLOWED_PAGE_SIZES = {50, 100}
LOGIN_HISTORY_INTERFACE_CONTEXTS = {"admin", "admin_web", "admin_bot", "client_web"}
LOGIN_HISTORY_RESULTS = {"success", "failure"}
ERROR_LOG_LEVELS = {"warn", "debug", "fatal"}
P = ParamSpec("P")
T = TypeVar("T")


class AdminLogReadAclPermissionsPort(Protocol):
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None: ...


class AdminLogReadWebLoginHistoryPort(Protocol):
    def list_admin(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...


class AdminLogReadTaskLogsPort(Protocol):
    def list_admin(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...

    def get_filter_metadata(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...


class AdminLogReadUsersPort(Protocol):
    def get_by_id(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...


class AdminLogReadImportJobsPort(Protocol):
    def get_job(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...


class AdminLogReadErrorLogsPort(Protocol):
    def list_admin(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_filter_metadata(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...


class AdminLogReadDatabasePort(Protocol):
    acl_permissions: AdminLogReadAclPermissionsPort
    web_login_history: AdminLogReadWebLoginHistoryPort
    task_logs: AdminLogReadTaskLogsPort
    admin_users: AdminLogReadUsersPort
    user_import_jobs: AdminLogReadImportJobsPort
    error_logs: AdminLogReadErrorLogsPort


class AdminLogReadService:
    def __init__(self, db: AdminLogReadDatabasePort) -> None:
        self.db = db

    def list_login_history(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_logs_access(actor, action="logs/list_login_history")
        page, page_size = _log_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        return self.db.web_login_history.list_admin(
            page=page,
            page_size=page_size,
            user_id=params.get("user_id"),
            interface_context=_log_read_validation(
                request_values.ensure_allowed_values,
                params.get("interface_context"),
                LOGIN_HISTORY_INTERFACE_CONTEXTS,
                "interface_context",
            ),
            result=_log_read_validation(
                request_values.ensure_allowed_values,
                params.get("result"),
                LOGIN_HISTORY_RESULTS,
                "result",
            ),
            api_origin=_log_read_validation(
                request_values.ensure_text,
                params.get("api_origin"),
                "api_origin",
                max_length=255,
            ),
        )

    def list_task_logs(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_logs_access(actor, action="logs/list_task_logs")
        page, page_size = _log_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        scope = _log_read_validation(
            request_values.ensure_allowed_value,
            params.get("scope") or "operations",
            TASK_LOG_SCOPES,
            "scope",
        )
        return self.db.task_logs.list_admin(
            page=page,
            page_size=page_size,
            task_type=_log_read_validation(
                request_values.ensure_allowed_values,
                params.get("task_type"),
                set(task_log_filter_values_for_scope(scope)),
                "task_type",
            ),
            status=_log_read_validation(
                request_values.ensure_allowed_values,
                params.get("status"),
                TASK_LOG_STATUSES,
                "status",
            ),
            user_id=params.get("user_id"),
            import_job_id=params.get("import_job_id"),
            search=_log_read_validation(
                request_values.ensure_text,
                params.get("search"),
                "search",
                max_length=120,
            ),
            scope=scope,
        )

    def get_task_log_detail(self, *, actor: dict[str, Any], task_log_id: int) -> dict[str, Any]:
        self._require_logs_access(actor, action="logs/view_task_log", detail="Task log access is not allowed")
        task_log = self.db.task_logs.get(task_log_id)
        if task_log is None:
            raise AdminLogReadNotFoundError("Task log not found")
        user = None
        if task_log.get("user_id") is not None:
            user = self.db.admin_users.get_by_id(str(task_log["user_id"]))
        import_job = None
        if task_log.get("import_job_id") is not None:
            import_job = self.db.user_import_jobs.get_job(int(task_log["import_job_id"]))
        return {
            "task_log": task_log,
            "user": user,
            "import_job": import_job,
        }

    def list_error_logs(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_logs_access(actor, action="logs/list_error_log")
        page, page_size = _log_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        return self.db.error_logs.list_admin(
            page=page,
            page_size=page_size,
            level=_log_read_validation(
                request_values.ensure_allowed_values,
                params.get("level"),
                ERROR_LOG_LEVELS,
                "level",
            ),
            search=_log_read_validation(
                request_values.ensure_text,
                params.get("search"),
                "search",
                max_length=120,
            ),
        )

    def get_task_log_filter_metadata(self, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        values = params or {}
        scope = _log_read_validation(
            request_values.ensure_allowed_value,
            values.get("scope") or "operations",
            TASK_LOG_SCOPES,
            "scope",
        )
        return self.db.task_logs.get_filter_metadata(scope=scope)

    def get_error_log_filter_metadata(self) -> dict[str, Any]:
        return self.db.error_logs.get_filter_metadata()

    def _require_logs_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminLogReadAccessDeniedError(error.detail) from error


def _log_read_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise AdminLogReadValidationError(error.detail) from error
