from __future__ import annotations

from app.application.admin.auth.errors import (
    AdminAuthAccessDeniedError,
    AdminAuthError,
    AdminAuthTooManyAttemptsError,
    AdminAuthUnauthorizedError,
)


def admin_auth_error_status_code(error: AdminAuthError) -> int:
    if isinstance(error, AdminAuthAccessDeniedError):
        return 403
    if isinstance(error, AdminAuthTooManyAttemptsError):
        return 429
    if isinstance(error, AdminAuthUnauthorizedError):
        return 401
    return 400
