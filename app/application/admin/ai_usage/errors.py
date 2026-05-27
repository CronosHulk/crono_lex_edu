from __future__ import annotations


class AdminAIUsageReadError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminAIUsageReadAccessDeniedError(AdminAIUsageReadError):
    pass


class AdminAIUsageReadUnauthorizedError(AdminAIUsageReadError):
    pass


class AdminAIUsageReadTooManyAttemptsError(AdminAIUsageReadError):
    pass


class AdminAIUsageReadValidationError(AdminAIUsageReadError):
    pass
