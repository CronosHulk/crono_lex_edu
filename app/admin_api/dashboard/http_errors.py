from __future__ import annotations

from fastapi import HTTPException

from app.application.admin.dashboard.errors import (
    AdminDashboardAccessDeniedError,
    AdminDashboardError,
    AdminDashboardNotFoundError,
)


def admin_dashboard_error_status_code(error: AdminDashboardError) -> int:
    if isinstance(error, AdminDashboardAccessDeniedError):
        return 403
    if isinstance(error, AdminDashboardNotFoundError):
        return 404
    return 400


def admin_dashboard_http_exception(error: AdminDashboardError) -> HTTPException:
    return HTTPException(status_code=admin_dashboard_error_status_code(error), detail=error.detail)
