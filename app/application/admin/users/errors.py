from __future__ import annotations


class AdminUserReadError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminUserReadAccessDeniedError(AdminUserReadError):
    pass


class AdminUserReadNotFoundError(AdminUserReadError):
    def __init__(self) -> None:
        super().__init__("User not found")


class AdminUserReadValidationError(AdminUserReadError):
    pass


class AdminUserActionError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminUserActionAccessDeniedError(AdminUserActionError):
    pass


class AdminUserActionValidationError(AdminUserActionError):
    pass


class AdminUserActionForbiddenError(AdminUserActionError):
    pass


class AdminUserActionNotFoundError(AdminUserActionError):
    pass
