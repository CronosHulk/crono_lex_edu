from __future__ import annotations

from collections.abc import Callable
from typing import Any, ParamSpec, Protocol, TypeVar
from uuid import UUID

import app.validation.pagination as validation_pagination
import app.validation.request_values as request_values
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.application.admin.users.errors import (
    AdminUserReadAccessDeniedError,
    AdminUserReadNotFoundError,
    AdminUserReadValidationError,
)

DEFAULT_PAGE_SIZE = 50
ALLOWED_PAGE_SIZES = {50, 100}
ALLOWED_USER_TYPES = {"admin", "student", "teacher"}
P = ParamSpec("P")
T = TypeVar("T")


class AdminUserReadAclPermissionsPort(Protocol):
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None: ...


class AdminUserReadUsersPort(Protocol):
    def get_filter_metadata(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def list_admin(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def get_by_id(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...


class AdminUserReadWebLoginHistoryPort(Protocol):
    def list_latest_for_user(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]: ...


class AdminUserReadTaskLogsPort(Protocol):
    def list_admin(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...


class AdminUserReadAIUsageSessionsPort(Protocol):
    def summarize_by_actor_user_ids(self, *args: Any, **kwargs: Any) -> dict[str, dict[str, Any]]: ...


class AdminUserReadDatabasePort(Protocol):
    acl_permissions: AdminUserReadAclPermissionsPort
    admin_users: AdminUserReadUsersPort
    web_login_history: AdminUserReadWebLoginHistoryPort
    task_logs: AdminUserReadTaskLogsPort
    ai_usage_sessions: AdminUserReadAIUsageSessionsPort


class AdminUserReadService:
    def __init__(self, db: AdminUserReadDatabasePort) -> None:
        self.db = db

    def list_users(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="users/list")
        page, page_size = _user_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        metadata = self.db.admin_users.get_filter_metadata()
        user_type = _user_read_validation(
            request_values.ensure_allowed_value,
            params.get("user_type") or "student",
            ALLOWED_USER_TYPES,
            "user_type",
        )
        user_id = normalize_optional_user_uuid(params.get("user_id"))
        payload = self.db.admin_users.list_admin(
            page=page,
            page_size=page_size,
            archived=str(params.get("archived") or "false").lower() == "true",
            search=_user_read_validation(request_values.ensure_text, params.get("search"), "search", max_length=120),
            role=_user_read_validation(request_values.validate_filter_metadata_values, metadata, "role", params.get("role")),
            user_type=user_type,
            user_id=user_id,
            status=_user_read_validation(
                request_values.validate_filter_metadata_values,
                metadata,
                "status",
                params.get("status"),
            ),
        )
        self._attach_ai_usage_summaries(payload.get("items", []))
        return payload

    def list_latest_login_history_for_user(self, *, actor: dict[str, Any], user_id: str, limit: int = 10) -> dict[str, Any]:
        self._require_admin_access(actor, action="users/view_login_history")
        return {"items": self.db.web_login_history.list_latest_for_user(user_id, limit=limit)}

    def get_user_detail(self, *, actor: dict[str, Any], user_id: str) -> dict[str, Any]:
        self._require_admin_access(actor, action="users/view", detail="User access is not allowed")
        user = self.db.admin_users.get_by_id(user_id)
        if user is None:
            raise AdminUserReadNotFoundError()
        self._attach_ai_usage_summaries([user])
        recent_task_logs = self.db.task_logs.list_admin(
            page=1,
            page_size=10,
            user_id=user_id,
            scope="all",
        )
        return {
            "user": user,
            "latest_login_history": self.db.web_login_history.list_latest_for_user(user_id, limit=10),
            "recent_task_logs": recent_task_logs.get("items", []),
        }

    def get_filter_metadata(self) -> dict[str, Any]:
        return self.db.admin_users.get_filter_metadata()

    def _require_admin_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminUserReadAccessDeniedError(error.detail) from error

    def _attach_ai_usage_summaries(self, users: list[dict[str, Any]]) -> None:
        user_ids = [str(user.get("user_id") or "") for user in users if user.get("user_id")]
        summaries = self.db.ai_usage_sessions.summarize_by_actor_user_ids(user_ids)
        for user in users:
            user_id = str(user.get("user_id") or "")
            user["ai_usage_summary"] = summaries.get(user_id, _empty_ai_usage_summary())


def normalize_optional_user_uuid(value: Any) -> str:
    text = _user_read_validation(request_values.ensure_text, value, "user_id", max_length=64)
    if not text:
        return ""
    try:
        return str(UUID(text))
    except ValueError as error:
        raise AdminUserReadValidationError("user_id must be a valid UUID") from error


def _user_read_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise AdminUserReadValidationError(error.detail) from error


def _empty_ai_usage_summary() -> dict[str, Any]:
    return {
        "session_count": 0,
        "request_count": 0,
        "total_tokens": 0,
        "estimated_cost_usd": "0",
    }
