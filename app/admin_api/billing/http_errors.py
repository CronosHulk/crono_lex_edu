from __future__ import annotations

from app.application.admin.billing.errors import (
    AdminBillingReadAccessDeniedError,
    AdminBillingReadError,
    AdminBillingReadNotFoundError,
)


def admin_billing_read_error_status_code(error: AdminBillingReadError) -> int:
    if isinstance(error, AdminBillingReadAccessDeniedError):
        return 403
    if isinstance(error, AdminBillingReadNotFoundError):
        return 404
    return 400
