from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.context import AdminRouterContext
from app.admin_api.dashboard.router import build_dashboard_router
from app.application.admin.dashboard.errors import (
    AdminDashboardAccessDeniedError,
    AdminDashboardSameUserError,
    AdminDashboardUserNotFoundError,
)


class FakeAdminDashboardService:
    def __init__(self) -> None:
        self.summary_calls = []
        self.assign_calls = []
        self.unassign_calls = []

    def summarize(self, *, actor):
        self.summary_calls.append({"actor": actor})
        return {"actor": actor, "summary": {"users_total": 2}}

    def assign_student_to_teacher(self, *, actor, teacher_user_id, student_user_id):
        self.assign_calls.append(
            {
                "actor": actor,
                "teacher_user_id": teacher_user_id,
                "student_user_id": student_user_id,
            }
        )
        return {
            "actor": actor,
            "teacher_user_id": teacher_user_id,
            "student_user_id": student_user_id,
            "status": "ok",
        }

    def unassign_student_from_teacher(self, *, actor, student_user_id):
        self.unassign_calls.append({"actor": actor, "student_user_id": student_user_id})
        return {"actor": actor, "student_user_id": student_user_id, "status": "ok"}


class SameUserAdminDashboardService(FakeAdminDashboardService):
    def assign_student_to_teacher(self, *, actor, teacher_user_id, student_user_id):
        self.assign_calls.append(
            {
                "actor": actor,
                "teacher_user_id": teacher_user_id,
                "student_user_id": student_user_id,
            }
        )
        raise AdminDashboardSameUserError()


class MissingUserAdminDashboardService(FakeAdminDashboardService):
    def unassign_student_from_teacher(self, *, actor, student_user_id):
        self.unassign_calls.append({"actor": actor, "student_user_id": student_user_id})
        raise AdminDashboardUserNotFoundError()


class DeniedSummaryAdminDashboardService(FakeAdminDashboardService):
    def summarize(self, *, actor):
        self.summary_calls.append({"actor": actor})
        raise AdminDashboardAccessDeniedError("Dashboard access is not allowed")


def build_dashboard_test_client(dashboard_service, actor: dict) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_dashboard_router(
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("ai usage service should not be used")
                ),
                admin_auth_service=lambda: (_ for _ in ()).throw(AssertionError("auth service should not be used")),
                admin_billing_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("billing service should not be used")
                ),
                admin_bootstrap_service=lambda: (_ for _ in ()).throw(
                    AssertionError("bootstrap service should not be used")
                ),
                admin_dashboard_service=lambda: dashboard_service,
                admin_dictionary_action_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary action service should not be used")
                ),
                admin_dictionary_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary read service should not be used")
                ),
                admin_dictionary_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary service should not be used")
                ),
                admin_entity_service=lambda: (_ for _ in ()).throw(
                    AssertionError("entity service should not be used")
                ),
                admin_exercise_text_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text service should not be used")
                ),
                admin_exercise_text_generation_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text generation service should not be used")
                ),
                admin_exercise_text_tts_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text tts service should not be used")
                ),
                admin_import_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("import read service should not be used")
                ),
                admin_log_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("log read service should not be used")
                ),
                admin_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("read service should not be used")
                ),
                admin_settings_service=lambda: (_ for _ in ()).throw(
                    AssertionError("settings service should not be used")
                ),
                admin_user_dictionary_bulk_action=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary bulk action should not be used")
                ),
                admin_user_dictionary_promote_action=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary promote action should not be used")
                ),
                admin_user_dictionary_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary read service should not be used")
                ),
                admin_user_action_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user action service should not be used")
                ),
                admin_user_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user read service should not be used")
                ),
            )
        )
    )
    return TestClient(app)


def test_admin_dashboard_routes_use_dashboard_service_context_directly() -> None:
    dashboard_service = FakeAdminDashboardService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dashboard_test_client(dashboard_service, actor)
    teacher_user_id = "11111111-1111-4111-8111-111111111111"
    student_user_id = "22222222-2222-4222-8222-222222222222"

    summary_response = client.get("/dashboard/summary")
    assign_response = client.post(
        "/dashboard/teacher-assignments",
        json={
            "teacher_user_id": teacher_user_id,
            "student_user_id": student_user_id,
        },
    )
    unassign_response = client.delete(f"/dashboard/teacher-assignments/{student_user_id}")

    assert summary_response.status_code == 200
    assert summary_response.json() == {"actor": actor, "summary": {"users_total": 2}}
    assert assign_response.status_code == 200
    assert assign_response.json() == {
        "actor": actor,
        "teacher_user_id": teacher_user_id,
        "student_user_id": student_user_id,
        "status": "ok",
    }
    assert unassign_response.status_code == 200
    assert unassign_response.json() == {
        "actor": actor,
        "student_user_id": student_user_id,
        "status": "ok",
    }
    assert dashboard_service.summary_calls == [{"actor": actor}]
    assert dashboard_service.assign_calls == [
        {
            "actor": actor,
            "teacher_user_id": teacher_user_id,
            "student_user_id": student_user_id,
        }
    ]
    assert dashboard_service.unassign_calls == [{"actor": actor, "student_user_id": student_user_id}]


def test_admin_dashboard_router_maps_assignment_validation_errors() -> None:
    dashboard_service = SameUserAdminDashboardService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dashboard_test_client(dashboard_service, actor)
    user_id = "11111111-1111-4111-8111-111111111111"

    response = client.post(
        "/dashboard/teacher-assignments",
        json={"teacher_user_id": user_id, "student_user_id": user_id},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Teacher and student must be different users"}
    assert dashboard_service.assign_calls == [
        {"actor": actor, "teacher_user_id": user_id, "student_user_id": user_id}
    ]


def test_admin_dashboard_router_maps_summary_access_denied_errors() -> None:
    dashboard_service = DeniedSummaryAdminDashboardService()
    actor = {"telegram_user_id": 1, "acl_group_title": "readonly"}
    client = build_dashboard_test_client(dashboard_service, actor)

    response = client.get("/dashboard/summary")

    assert response.status_code == 403
    assert response.json() == {"detail": "Dashboard access is not allowed"}
    assert dashboard_service.summary_calls == [{"actor": actor}]


def test_admin_dashboard_router_maps_assignment_not_found_errors() -> None:
    dashboard_service = MissingUserAdminDashboardService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_dashboard_test_client(dashboard_service, actor)
    student_user_id = "22222222-2222-4222-8222-222222222222"

    response = client.delete(f"/dashboard/teacher-assignments/{student_user_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    assert dashboard_service.unassign_calls == [{"actor": actor, "student_user_id": student_user_id}]
