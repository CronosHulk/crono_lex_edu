from __future__ import annotations


class AdminSettingsError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class AdminSettingsAccessDeniedError(AdminSettingsError):
    pass


class AdminSettingsUnauthorizedError(AdminSettingsError):
    pass


class AdminSettingsTooManyAttemptsError(AdminSettingsError):
    pass


class AdminSettingsValidationError(AdminSettingsError):
    pass
