from __future__ import annotations


class AdminReadError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminReadAccessDeniedError(AdminReadError):
    pass


class AdminReadUnknownEntityError(AdminReadError):
    def __init__(self) -> None:
        super().__init__("Unknown entity")


class AdminReadValidationError(AdminReadError):
    pass
