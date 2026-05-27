from __future__ import annotations

from app.application.admin.imports.errors import (
    AdminImportReadAccessDeniedError,
    AdminImportReadError,
    AdminImportReadNotFoundError,
)


def admin_import_read_error_status_code(error: AdminImportReadError) -> int:
    if isinstance(error, AdminImportReadAccessDeniedError):
        return 403
    if isinstance(error, AdminImportReadNotFoundError):
        return 404
    return 400
