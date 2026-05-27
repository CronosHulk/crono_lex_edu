from __future__ import annotations


class AdminImportReadError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminImportReadAccessDeniedError(AdminImportReadError):
    pass


class AdminImportReadNotFoundError(AdminImportReadError):
    def __init__(self) -> None:
        super().__init__("Import job not found")


class AdminImportReadValidationError(AdminImportReadError):
    pass
