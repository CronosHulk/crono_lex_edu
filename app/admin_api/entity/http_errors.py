from __future__ import annotations

from app.application.admin.entity.errors import (
    AdminEntityAccessDeniedError,
    AdminEntityConflictError,
    AdminEntityError,
    AdminEntityNotFoundError,
)


def admin_entity_error_status_code(error: AdminEntityError) -> int:
    if isinstance(error, AdminEntityAccessDeniedError):
        return 403
    if isinstance(error, AdminEntityConflictError):
        return 409
    if isinstance(error, AdminEntityNotFoundError):
        return 404
    return 400
