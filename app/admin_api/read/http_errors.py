from __future__ import annotations

from fastapi import HTTPException

from app.application.admin.read.errors import (
    AdminReadAccessDeniedError,
    AdminReadError,
    AdminReadUnknownEntityError,
)


def admin_read_http_exception(error: AdminReadError) -> HTTPException:
    return HTTPException(status_code=admin_read_error_status_code(error), detail=error.detail)


def admin_read_error_status_code(error: AdminReadError) -> int:
    if isinstance(error, AdminReadAccessDeniedError):
        return 403
    if isinstance(error, AdminReadUnknownEntityError):
        return 404
    return 400
