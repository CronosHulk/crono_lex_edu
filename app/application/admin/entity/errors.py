from __future__ import annotations


class AdminEntityError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminEntityAccessDeniedError(AdminEntityError):
    pass


class AdminEntityNotFoundError(AdminEntityError):
    pass


class AdminEntityUnknownError(AdminEntityNotFoundError):
    def __init__(self) -> None:
        super().__init__("Unknown entity")


class AdminEntityValidationError(AdminEntityError):
    pass


class AdminEntityConflictError(AdminEntityError):
    pass


class AdminEntityInvalidIdError(AdminEntityValidationError):
    def __init__(self) -> None:
        super().__init__("entity_id must be an integer")
