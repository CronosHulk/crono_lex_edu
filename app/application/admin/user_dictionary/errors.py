from __future__ import annotations


class AdminUserDictionaryReadError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminUserDictionaryReadAccessDeniedError(AdminUserDictionaryReadError):
    pass


class AdminUserDictionaryReadNotFoundError(AdminUserDictionaryReadError):
    pass


class AdminUserDictionaryReadEntryNotFoundError(AdminUserDictionaryReadNotFoundError):
    def __init__(self) -> None:
        super().__init__("User dictionary entry was not found")


class AdminUserDictionaryReadAudioNotFoundError(AdminUserDictionaryReadNotFoundError):
    def __init__(self) -> None:
        super().__init__("Audio not found")


class AdminUserDictionaryReadValidationError(AdminUserDictionaryReadError):
    pass


class AdminUserDictionaryReadLevelIdFilterError(AdminUserDictionaryReadValidationError):
    def __init__(self) -> None:
        super().__init__("level_id must contain numeric values")


class AdminUserDictionaryActionError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminUserDictionaryActionAccessDeniedError(AdminUserDictionaryActionError):
    pass


class AdminUserDictionaryActionValidationError(AdminUserDictionaryActionError):
    pass


class AdminUserDictionaryActionNotFoundError(AdminUserDictionaryActionError):
    pass
