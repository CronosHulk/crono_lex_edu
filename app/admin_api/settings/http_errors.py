from __future__ import annotations

from fastapi import HTTPException

from app.application.admin.settings.errors import (
    AdminSettingsAccessDeniedError,
    AdminSettingsError,
    AdminSettingsTooManyAttemptsError,
    AdminSettingsUnauthorizedError,
)


def admin_settings_error_status_code(error: AdminSettingsError) -> int:
    if isinstance(error, AdminSettingsAccessDeniedError):
        return 403
    if isinstance(error, AdminSettingsUnauthorizedError):
        return 401
    if isinstance(error, AdminSettingsTooManyAttemptsError):
        return 429
    return 400


def admin_settings_http_exception(error: AdminSettingsError) -> HTTPException:
    return HTTPException(status_code=admin_settings_error_status_code(error), detail=error.detail)
