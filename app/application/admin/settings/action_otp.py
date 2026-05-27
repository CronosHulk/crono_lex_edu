from __future__ import annotations

from typing import Any

from app.application.admin.auth.action_otp import ActionOtpVerifier
from app.application.admin.auth.errors import (
    AdminAuthAccessDeniedError,
    AdminAuthTooManyAttemptsError,
    AdminAuthUnauthorizedError,
)
from app.application.admin.settings.errors import (
    AdminSettingsAccessDeniedError,
    AdminSettingsTooManyAttemptsError,
    AdminSettingsUnauthorizedError,
)


class AdminSettingsActionOtpVerifier:
    def __init__(self, verifier: ActionOtpVerifier) -> None:
        self.verifier = verifier

    def verify_action_otp(
        self,
        *,
        user: dict[str, Any],
        action_key: str,
        challenge_id: int,
        otp: str,
    ) -> None:
        try:
            self.verifier.verify_action_otp(
                user=user,
                action_key=action_key,
                challenge_id=challenge_id,
                otp=otp,
            )
        except AdminAuthUnauthorizedError as error:
            raise AdminSettingsUnauthorizedError(error.detail) from error
        except AdminAuthTooManyAttemptsError as error:
            raise AdminSettingsTooManyAttemptsError(error.detail) from error
        except AdminAuthAccessDeniedError as error:
            raise AdminSettingsAccessDeniedError(error.detail) from error
