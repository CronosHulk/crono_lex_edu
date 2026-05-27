from __future__ import annotations

from fastapi import HTTPException

from app.application.admin.users.errors import (
    AdminUserActionAccessDeniedError,
    AdminUserActionError,
    AdminUserActionForbiddenError,
    AdminUserActionNotFoundError,
    AdminUserReadAccessDeniedError,
    AdminUserReadError,
    AdminUserReadNotFoundError,
)


def admin_user_read_http_exception(error: AdminUserReadError) -> HTTPException:
    return HTTPException(status_code=admin_user_read_error_status_code(error), detail=error.detail)


def admin_user_action_http_exception(error: AdminUserActionError) -> HTTPException:
    return HTTPException(status_code=admin_user_action_error_status_code(error), detail=error.detail)


def admin_user_read_error_status_code(error: AdminUserReadError) -> int:
    if isinstance(error, AdminUserReadAccessDeniedError):
        return 403
    if isinstance(error, AdminUserReadNotFoundError):
        return 404
    return 400


def admin_user_action_error_status_code(error: AdminUserActionError) -> int:
    if isinstance(error, (AdminUserActionAccessDeniedError, AdminUserActionForbiddenError)):
        return 403
    if isinstance(error, AdminUserActionNotFoundError):
        return 404
    return 400
