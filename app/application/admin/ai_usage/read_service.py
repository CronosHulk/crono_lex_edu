from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any, ParamSpec, Protocol, TypeVar

import app.validation.pagination as validation_pagination
import app.validation.request_values as request_values
from app.application.admin.ai_usage.errors import (
    AdminAIUsageReadAccessDeniedError,
    AdminAIUsageReadValidationError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    ensure_super_admin_actor_allowed,
    require_admin_access_allowed,
)
from app.time_utils import TimeService

DEFAULT_PAGE_SIZE = 50
ALLOWED_PAGE_SIZES = {50, 100}
USAGE_PERIODS = {"day", "week", "month", "all"}
P = ParamSpec("P")
T = TypeVar("T")


class AdminAIUsageReadAclPermissionsPort(Protocol):
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None: ...


class AdminAIUsageSessionsPort(Protocol):
    def summarize_admin(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def list_admin(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def delete_all(self) -> dict[str, int]: ...


class AdminAIUsageActionOtpVerifierPort(Protocol):
    def verify_action_otp(self, *, user: dict[str, Any], action_key: str, challenge_id: int, otp: str) -> None: ...


class AdminAIUsageReadDatabasePort(Protocol):
    acl_permissions: AdminAIUsageReadAclPermissionsPort
    ai_usage_sessions: AdminAIUsageSessionsPort


class AdminAIUsageReadService:
    def __init__(
        self,
        db: AdminAIUsageReadDatabasePort,
        time_service: TimeService,
        action_otp_verifier: AdminAIUsageActionOtpVerifierPort | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.action_otp_verifier = action_otp_verifier

    def summarize(self, *, actor: dict[str, Any], period: str) -> dict[str, Any]:
        self._require_ai_usage_access(actor, action="logs/list_task_logs", detail="AI usage access is not allowed")
        normalized_period = _ai_usage_read_validation(request_values.ensure_allowed_value, period, USAGE_PERIODS, "period")
        return {
            "period": normalized_period,
            **self.db.ai_usage_sessions.summarize_admin(created_from=self._created_from(normalized_period)),
        }

    def list_sessions(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_ai_usage_access(actor, action="logs/list_task_logs", detail="AI usage access is not allowed")
        page, page_size = _ai_usage_read_validation(
            validation_pagination.normalize_pagination,
            params,
            default_page_size=DEFAULT_PAGE_SIZE,
            allowed_page_sizes=ALLOWED_PAGE_SIZES,
        )
        period = _ai_usage_read_validation(
            request_values.ensure_allowed_value,
            str(params.get("period") or "week"),
            USAGE_PERIODS,
            "period",
        )
        return self.db.ai_usage_sessions.list_admin(
            page=page,
            page_size=page_size,
            created_from=self._created_from(period),
            task_scope=_ai_usage_read_validation(
                request_values.ensure_values_match_pattern,
                params.get("task_scope"),
                "task_scope",
            ),
            task_key=_ai_usage_read_validation(
                request_values.ensure_values_match_pattern,
                params.get("task_key"),
                "task_key",
            ),
            provider_key=_ai_usage_read_validation(
                request_values.ensure_values_match_pattern,
                params.get("provider_key"),
                "provider_key",
            ),
            model=_ai_usage_read_validation(
                request_values.ensure_values_match_pattern,
                params.get("model"),
                "model",
            ),
            actor_user_id=params.get("actor_user_id"),
            search=_ai_usage_read_validation(
                request_values.ensure_text,
                params.get("search"),
                "search",
                max_length=120,
            ),
        )

    def authorize_delete_all_sessions(self, *, actor: dict[str, Any]) -> None:
        self._require_ai_usage_access(actor, action="acl/manage")

    def delete_all_sessions(self, *, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_ai_usage_access(actor, action="logs/list_task_logs", detail="AI usage access is not allowed")
        self._ensure_super_admin(actor)
        return {"status": "ok", **self.db.ai_usage_sessions.delete_all()}

    def delete_all_sessions_with_otp(self, *, actor: dict[str, Any], challenge_id: int, otp: str) -> dict[str, Any]:
        if self.action_otp_verifier is None:
            raise RuntimeError("Action OTP verifier is required for AI usage cleanup")
        self.authorize_delete_all_sessions(actor=actor)
        self.action_otp_verifier.verify_action_otp(
            user=actor,
            action_key="delete_ai_usage_log",
            challenge_id=challenge_id,
            otp=otp,
        )
        return self.delete_all_sessions(actor=actor)

    def _created_from(self, period: str):
        if period == "all":
            return None
        days = {"day": 1, "week": 7, "month": 31}[period]
        return self.time_service.now() - timedelta(days=days)

    def _require_ai_usage_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminAIUsageReadAccessDeniedError(error.detail) from error

    def _ensure_super_admin(self, actor: dict[str, Any]) -> None:
        try:
            ensure_super_admin_actor_allowed(actor)
        except AdminPermissionDeniedError as error:
            raise AdminAIUsageReadAccessDeniedError(error.detail) from error


def _ai_usage_read_validation(validator: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return validator(*args, **kwargs)
    except request_values.RequestValueValidationError as error:
        raise AdminAIUsageReadValidationError(error.detail) from error
