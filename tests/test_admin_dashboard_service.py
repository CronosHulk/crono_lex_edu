from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.admin.dashboard.dashboard_service import AdminDashboardService
from app.application.admin.dashboard.errors import (
    AdminDashboardAccessDeniedError,
    AdminDashboardActiveAssignmentNotFoundError,
    AdminDashboardTeacherRoleError,
    AdminDashboardValidationError,
)


class FakeAclPermissions:
    def __init__(self, rule: str | None = "enabled") -> None:
        self.rule = rule

    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        _ = group_title, action, environment
        return self.rule

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        _ = group_title, environment
        return []


class FakeDashboardRepository:
    def __init__(self) -> None:
        self.active_since = None
        self.count_active_since_values = []

    def count_active_users(self, *, active_since: datetime | None = None) -> int:
        self.count_active_since_values.append(active_since)
        return 4

    def summarize(self, *, active_since: datetime) -> dict:
        self.active_since = active_since
        return {
            "users": {"total": 3, "by_learning_role": {"student": 2, "teacher": 1}},
            "teacher_assignments": {"active_links": 1, "unassigned_active_students": 1},
            "dictionary": {"core_total": 10, "user_total": 2},
            "levels": {"A1": 2},
            "subscriptions": {"implemented": False, "tiers": []},
        }


class FakeAIUsageSessions:
    def __init__(self) -> None:
        self.created_from_values = []

    def summarize_admin(self, *, created_from: datetime | None = None) -> dict:
        self.created_from_values.append(created_from)
        return {"items": [{"estimated_cost_usd": "0.25", "request_count": 2, "total_tokens": 100}]}

    def summarize_totals(self, *, created_from: datetime | None = None) -> dict:
        _ = created_from
        return {"ai_active_user_count": 2}


class FakeAdminUsers:
    def __init__(self) -> None:
        self.rows = {
            "11111111-1111-4111-8111-111111111111": {
                "user_id": "11111111-1111-4111-8111-111111111111",
                "learning_role": "teacher",
            },
            "22222222-2222-4222-8222-222222222222": {
                "user_id": "22222222-2222-4222-8222-222222222222",
                "learning_role": "student",
            },
        }

    def get_by_id(self, user_id: str):
        return self.rows.get(user_id)


class FakeTeacherStudentLinks:
    def __init__(self) -> None:
        self.calls = []
        self.unassign_calls = []
        self.unassign_result = {
            "id": 7,
            "status": "archived",
            "teacher_user_id": "11111111-1111-4111-8111-111111111111",
            "student_user_id": "22222222-2222-4222-8222-222222222222",
        }

    def assign_student_to_teacher(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "id": 7,
            "status": "active",
            "teacher_user_id": kwargs["teacher_user_id"],
            "student_user_id": kwargs["student_user_id"],
        }

    def unassign_student(self, **kwargs):
        self.unassign_calls.append(kwargs)
        return self.unassign_result


class FakeDB:
    def __init__(self) -> None:
        self.acl_permissions = FakeAclPermissions()
        self.admin_dashboard = FakeDashboardRepository()
        self.ai_usage_sessions = FakeAIUsageSessions()
        self.admin_users = FakeAdminUsers()
        self.teacher_student_links = FakeTeacherStudentLinks()


class FakeTimeService:
    def __init__(self) -> None:
        self.value = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.value


def test_dashboard_summary_includes_metrics_and_ai_cost_periods() -> None:
    db = FakeDB()
    service = AdminDashboardService(db, FakeTimeService())

    payload = service.summarize(actor={"acl_group_title": "admin"})

    assert payload["users"]["total"] == 3
    assert payload["teacher_assignments"]["unassigned_active_students"] == 1
    assert db.admin_dashboard.active_since == datetime(2026, 4, 26, 10, 0, tzinfo=UTC)
    assert set(payload["ai_costs"]) == {"week", "month", "quarter", "half_year", "year"}
    assert payload["ai_costs"]["week"]["estimated_cost_usd"] == "0.25"
    assert payload["ai_costs"]["week"]["ai_active_user_count"] == 2
    assert payload["ai_costs"]["week"]["average_cost_per_active_user_usd"] == "0.0625"
    assert payload["ai_costs"]["week"]["average_cost_per_ai_active_user_usd"] == "0.125"
    assert db.admin_dashboard.count_active_since_values[0] == datetime(2026, 4, 26, 10, 0, tzinfo=UTC)


def test_dashboard_summary_rejects_denied_actor_before_loading_metrics() -> None:
    db = FakeDB()
    db.acl_permissions.rule = "disabled"
    service = AdminDashboardService(db, FakeTimeService())

    with pytest.raises(AdminDashboardAccessDeniedError) as error:
        service.summarize(actor={"acl_group_title": "readonly"})

    assert error.value.detail == "Dashboard access is not allowed"
    assert db.admin_dashboard.active_since is None
    assert db.ai_usage_sessions.created_from_values == []


def test_dashboard_ai_cost_rejects_unknown_period_with_local_validation_error() -> None:
    db = FakeDB()
    service = AdminDashboardService(db, FakeTimeService())

    with pytest.raises(AdminDashboardValidationError) as error:
        service._summarize_ai_cost("decade")

    assert error.value.detail == "period must be one of: half_year, month, quarter, week, year"


def test_assign_student_to_teacher_validates_roles_and_uses_uuid_links() -> None:
    db = FakeDB()
    time_service = FakeTimeService()
    service = AdminDashboardService(db, time_service)

    payload = service.assign_student_to_teacher(
        actor={"acl_group_title": "admin"},
        teacher_user_id="11111111-1111-4111-8111-111111111111",
        student_user_id="22222222-2222-4222-8222-222222222222",
    )

    assert payload["status"] == "ok"
    assert payload["assignment"]["teacher_user_id"] == "11111111-1111-4111-8111-111111111111"
    assert db.teacher_student_links.calls == [
        {
            "teacher_user_id": "11111111-1111-4111-8111-111111111111",
            "student_user_id": "22222222-2222-4222-8222-222222222222",
            "current_time": time_service.value,
        }
    ]


def test_assign_student_to_teacher_rejects_denied_actor_before_business_validation() -> None:
    db = FakeDB()
    db.acl_permissions.rule = "disabled"
    service = AdminDashboardService(db, FakeTimeService())
    user_id = "11111111-1111-4111-8111-111111111111"

    with pytest.raises(AdminDashboardAccessDeniedError) as error:
        service.assign_student_to_teacher(
            actor={"acl_group_title": "readonly"},
            teacher_user_id=user_id,
            student_user_id=user_id,
        )

    assert error.value.detail == "Teacher assignment is not allowed"
    assert db.teacher_student_links.calls == []


def test_assign_student_to_teacher_rejects_wrong_learning_roles() -> None:
    db = FakeDB()
    db.admin_users.rows["11111111-1111-4111-8111-111111111111"]["learning_role"] = "student"
    service = AdminDashboardService(db, FakeTimeService())

    with pytest.raises(AdminDashboardTeacherRoleError) as error:
        service.assign_student_to_teacher(
            actor={"acl_group_title": "admin"},
            teacher_user_id="11111111-1111-4111-8111-111111111111",
            student_user_id="22222222-2222-4222-8222-222222222222",
        )

    assert "teacher learning role" in str(error.value.detail)


def test_unassign_student_from_teacher_archives_active_link() -> None:
    db = FakeDB()
    time_service = FakeTimeService()
    service = AdminDashboardService(db, time_service)

    payload = service.unassign_student_from_teacher(
        actor={"acl_group_title": "admin"},
        student_user_id="22222222-2222-4222-8222-222222222222",
    )

    assert payload == {
        "status": "ok",
        "assignment": db.teacher_student_links.unassign_result,
    }
    assert db.teacher_student_links.unassign_calls == [
        {
            "student_user_id": "22222222-2222-4222-8222-222222222222",
            "current_time": time_service.value,
        }
    ]


def test_unassign_student_from_teacher_rejects_missing_active_link() -> None:
    db = FakeDB()
    db.teacher_student_links.unassign_result = None
    service = AdminDashboardService(db, FakeTimeService())

    with pytest.raises(AdminDashboardActiveAssignmentNotFoundError) as error:
        service.unassign_student_from_teacher(
            actor={"acl_group_title": "admin"},
            student_user_id="22222222-2222-4222-8222-222222222222",
        )

    assert "Active teacher assignment" in str(error.value.detail)
