from __future__ import annotations


class AdminAuthError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminAuthValidationError(AdminAuthError):
    pass


class AdminAuthUnauthorizedError(AdminAuthError):
    pass


class AdminAuthAccessDeniedError(AdminAuthError):
    pass


class AdminAuthTooManyAttemptsError(AdminAuthError):
    pass
