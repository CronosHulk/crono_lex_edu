from __future__ import annotations


class AdminDictionaryReadError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminDictionaryReadAccessDeniedError(AdminDictionaryReadError):
    pass


class AdminDictionaryReadNotFoundError(AdminDictionaryReadError):
    pass


class AdminDictionaryReadEntryNotFoundError(AdminDictionaryReadNotFoundError):
    def __init__(self) -> None:
        super().__init__("Dictionary entry not found")


class AdminDictionaryReadValidationError(AdminDictionaryReadError):
    pass


class AdminDictionaryReadVerifiedFilterError(AdminDictionaryReadValidationError):
    def __init__(self) -> None:
        super().__init__("verified must be one of: all, verified, unverified")


class AdminDictionaryServiceError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminDictionaryServiceAccessDeniedError(AdminDictionaryServiceError):
    pass


class AdminDictionaryServiceNotFoundError(AdminDictionaryServiceError):
    pass


class AdminDictionaryServiceEntryNotFoundError(AdminDictionaryServiceNotFoundError):
    def __init__(self) -> None:
        super().__init__("Dictionary entry not found")


class AdminDictionaryServiceAudioNotFoundError(AdminDictionaryServiceNotFoundError):
    def __init__(self) -> None:
        super().__init__("Audio not found")


class AdminDictionaryServiceValidationError(AdminDictionaryServiceError):
    pass


class AdminDictionaryActionError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminDictionaryActionAccessDeniedError(AdminDictionaryActionError):
    pass


class AdminDictionaryActionNotFoundError(AdminDictionaryActionError):
    pass


class AdminDictionaryActionEntityNotFoundError(AdminDictionaryActionNotFoundError):
    def __init__(self) -> None:
        super().__init__("Entity not found")


class AdminDictionaryActionConflictError(AdminDictionaryActionError):
    pass


class AdminDictionaryActionAssignedEntryError(AdminDictionaryActionConflictError):
    def __init__(self) -> None:
        super().__init__("Dictionary entry is assigned to users and cannot be deleted")
