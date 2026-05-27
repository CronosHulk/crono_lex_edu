from __future__ import annotations

from app.application.admin.ai_usage.errors import (
    AdminAIUsageReadAccessDeniedError,
    AdminAIUsageReadError,
    AdminAIUsageReadTooManyAttemptsError,
    AdminAIUsageReadUnauthorizedError,
)


def admin_ai_usage_read_error_status_code(error: AdminAIUsageReadError) -> int:
    if isinstance(error, AdminAIUsageReadTooManyAttemptsError):
        return 429
    if isinstance(error, AdminAIUsageReadUnauthorizedError):
        return 401
    if isinstance(error, AdminAIUsageReadAccessDeniedError):
        return 403
    return 400
