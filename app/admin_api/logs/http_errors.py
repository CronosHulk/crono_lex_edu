from __future__ import annotations

from fastapi import HTTPException

from app.application.admin.logs.errors import (
    AdminLogReadAccessDeniedError,
    AdminLogReadError,
    AdminLogReadNotFoundError,
)


def admin_log_read_error_status_code(error: AdminLogReadError) -> int:
    if isinstance(error, AdminLogReadAccessDeniedError):
        return 403
    if isinstance(error, AdminLogReadNotFoundError):
        return 404
    return 400


def admin_log_read_http_exception(error: AdminLogReadError) -> HTTPException:
    return HTTPException(status_code=admin_log_read_error_status_code(error), detail=error.detail)
