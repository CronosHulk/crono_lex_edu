from __future__ import annotations


class AdminBillingReadError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminBillingReadAccessDeniedError(AdminBillingReadError):
    pass


class AdminBillingReadNotFoundError(AdminBillingReadError):
    pass


class AdminBillingPaymentNotFoundError(AdminBillingReadNotFoundError):
    def __init__(self) -> None:
        super().__init__("Billing payment not found")


class AdminBillingAuditLogNotFoundError(AdminBillingReadNotFoundError):
    def __init__(self) -> None:
        super().__init__("Monobank audit log not found")


class AdminBillingReadValidationError(AdminBillingReadError):
    pass
