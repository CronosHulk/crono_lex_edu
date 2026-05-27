from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.dashboard.http_errors import admin_dashboard_error_status_code
from app.admin_api.schemas import AdminTeacherAssignmentRequest
from app.application.admin.dashboard.errors import AdminDashboardError


def build_dashboard_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/dashboard/summary")
    def admin_dashboard_summary(request: Request) -> dict:
        try:
            return context.admin_dashboard_service().summarize(actor=context.current_admin_user(request))
        except AdminDashboardError as error:
            raise HTTPException(status_code=admin_dashboard_error_status_code(error), detail=error.detail) from error

    @router.post("/dashboard/teacher-assignments")
    def admin_assign_student_to_teacher(request: Request, payload: AdminTeacherAssignmentRequest) -> dict:
        try:
            return context.admin_dashboard_service().assign_student_to_teacher(
                actor=context.current_admin_user(request),
                teacher_user_id=str(payload.teacher_user_id),
                student_user_id=str(payload.student_user_id),
            )
        except AdminDashboardError as error:
            raise HTTPException(status_code=admin_dashboard_error_status_code(error), detail=error.detail) from error

    @router.delete("/dashboard/teacher-assignments/{student_user_id}")
    def admin_unassign_student_from_teacher(student_user_id: str, request: Request) -> dict:
        try:
            return context.admin_dashboard_service().unassign_student_from_teacher(
                actor=context.current_admin_user(request),
                student_user_id=student_user_id,
            )
        except AdminDashboardError as error:
            raise HTTPException(status_code=admin_dashboard_error_status_code(error), detail=error.detail) from error

    return router
