from __future__ import annotations


class ClientWebImportError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ClientWebImportValidationError(ClientWebImportError):
    pass


class ClientWebImportProviderUnavailableError(ClientWebImportError):
    pass


class ClientWebImportNotFoundError(ClientWebImportError):
    pass
