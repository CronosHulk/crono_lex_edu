from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any, Protocol

import app.validation.request_values as request_values
from app.application.admin.dashboard.errors import (
    AdminDashboardAccessDeniedError,
    AdminDashboardActiveAssignmentNotFoundError,
    AdminDashboardSameUserError,
    AdminDashboardStudentRoleError,
    AdminDashboardTeacherRoleError,
    AdminDashboardUserNotFoundError,
    AdminDashboardValidationError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.time_utils import TimeService

DASHBOARD_AI_PERIODS = {"week", "month", "quarter", "half_year", "year"}


class AdminDashboardAclPermissionsPort(Protocol):
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None: ...


class AdminDashboardRepositoryPort(Protocol):
    def summarize(self, *, active_since: Any) -> dict[str, Any]: ...

    def count_active_users(self, *args: Any, **kwargs: Any) -> int: ...


class AdminDashboardAIUsageSessionsPort(Protocol):
    def summarize_admin(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def summarize_totals(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...


class AdminDashboardUsersPort(Protocol):
    def get_by_id(self, user_id: str) -> dict[str, Any] | None: ...


class AdminDashboardTeacherStudentLinksPort(Protocol):
    def assign_student_to_teacher(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...

    def unassign_student(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None: ...


class AdminDashboardDatabasePort(Protocol):
    acl_permissions: AdminDashboardAclPermissionsPort
    admin_dashboard: AdminDashboardRepositoryPort
    ai_usage_sessions: AdminDashboardAIUsageSessionsPort
    admin_users: AdminDashboardUsersPort
    teacher_student_links: AdminDashboardTeacherStudentLinksPort


class AdminDashboardService:
    def __init__(self, db: AdminDashboardDatabasePort, time_service: TimeService) -> None:
        self.db = db
        self.time_service = time_service

    def summarize(self, *, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_dashboard_access(actor, action="users/list", detail="Dashboard access is not allowed")
        now = self.time_service.now()
        summary = self.db.admin_dashboard.summarize(active_since=now - timedelta(days=7))
        return {
            **summary,
            "ai_costs": {
                period: self._summarize_ai_cost(period)
                for period in ("week", "month", "quarter", "half_year", "year")
            },
        }

    def assign_student_to_teacher(
        self,
        *,
        actor: dict[str, Any],
        teacher_user_id: str,
        student_user_id: str,
    ) -> dict[str, Any]:
        self._require_dashboard_access(
            actor,
            action="users/update_learning_role",
            detail="Teacher assignment is not allowed",
        )
        if teacher_user_id == student_user_id:
            raise AdminDashboardSameUserError()
        teacher = self.db.admin_users.get_by_id(teacher_user_id)
        student = self.db.admin_users.get_by_id(student_user_id)
        if teacher is None or student is None:
            raise AdminDashboardUserNotFoundError()
        if teacher.get("learning_role") != "teacher":
            raise AdminDashboardTeacherRoleError()
        if student.get("learning_role") != "student":
            raise AdminDashboardStudentRoleError()
        current_time = self.time_service.now()
        link = self.db.teacher_student_links.assign_student_to_teacher(
            teacher_user_id=teacher_user_id,
            student_user_id=student_user_id,
            current_time=current_time,
        )
        if link is None:
            raise AdminDashboardUserNotFoundError()
        return {"status": "ok", "assignment": link}

    def unassign_student_from_teacher(self, *, actor: dict[str, Any], student_user_id: str) -> dict[str, Any]:
        self._require_dashboard_access(
            actor,
            action="users/update_learning_role",
            detail="Teacher assignment is not allowed",
        )
        student = self.db.admin_users.get_by_id(student_user_id)
        if student is None:
            raise AdminDashboardUserNotFoundError()
        if student.get("learning_role") != "student":
            raise AdminDashboardStudentRoleError()
        link = self.db.teacher_student_links.unassign_student(
            student_user_id=student_user_id,
            current_time=self.time_service.now(),
        )
        if link is None:
            raise AdminDashboardActiveAssignmentNotFoundError()
        return {"status": "ok", "assignment": link}

    def _summarize_ai_cost(self, period: str) -> dict[str, Any]:
        try:
            normalized_period = request_values.ensure_allowed_value(period, DASHBOARD_AI_PERIODS, "period")
        except request_values.RequestValueValidationError as error:
            raise AdminDashboardValidationError(error.detail) from error
        created_from = self.time_service.now() - timedelta(days=_period_days(normalized_period))
        usage_summary = self.db.ai_usage_sessions.summarize_admin(created_from=created_from)
        items = usage_summary.get("items", [])
        usage_totals = self.db.ai_usage_sessions.summarize_totals(created_from=created_from)
        total_cost = sum(Decimal(str(item.get("estimated_cost_usd") or "0")) for item in items)
        request_count = sum(int(item.get("request_count") or 0) for item in items)
        total_tokens = sum(int(item.get("total_tokens") or 0) for item in items)
        active_user_count = int(_count_active_users_for_period(self.db.admin_dashboard, created_from))
        ai_active_user_count = int(usage_totals.get("ai_active_user_count") or 0)
        return {
            "period": normalized_period,
            "estimated_cost_usd": str(total_cost),
            "request_count": request_count,
            "total_tokens": total_tokens,
            "ai_active_user_count": ai_active_user_count,
            "average_cost_per_active_user_usd": str(_safe_decimal_average(total_cost, active_user_count)),
            "average_cost_per_ai_active_user_usd": str(_safe_decimal_average(total_cost, ai_active_user_count)),
        }

    def _require_dashboard_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminDashboardAccessDeniedError(error.detail) from error


def _period_days(period: str) -> int:
    return {
        "week": 7,
        "month": 31,
        "quarter": 92,
        "half_year": 183,
        "year": 366,
    }[period]


def _safe_decimal_average(value: Decimal, divisor: int) -> Decimal:
    if divisor <= 0:
        return Decimal("0")
    return value / Decimal(divisor)


def _count_active_users_for_period(repository: Any, active_since: Any) -> int:
    if not hasattr(repository, "count_active_users"):
        return 0
    try:
        return int(repository.count_active_users(active_since=active_since))
    except TypeError:
        return int(repository.count_active_users())
