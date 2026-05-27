from __future__ import annotations


class ClientWebLearningError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class ClientWebLearningValidationError(ClientWebLearningError):
    pass


class ClientWebLearningPaymentRequiredError(ClientWebLearningError):
    pass


class ClientWebLearningNotFoundError(ClientWebLearningError):
    pass


class ClientWebLearningConflictError(ClientWebLearningError):
    pass
