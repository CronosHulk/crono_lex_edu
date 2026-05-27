from __future__ import annotations

from typing import Any

from app.application.admin.ai_usage.errors import (
    AdminAIUsageReadAccessDeniedError,
    AdminAIUsageReadTooManyAttemptsError,
    AdminAIUsageReadUnauthorizedError,
)
from app.application.admin.auth.action_otp import ActionOtpVerifier
from app.application.admin.auth.errors import (
    AdminAuthAccessDeniedError,
    AdminAuthTooManyAttemptsError,
    AdminAuthUnauthorizedError,
)


class AdminAIUsageActionOtpVerifier:
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
            raise AdminAIUsageReadUnauthorizedError(error.detail) from error
        except AdminAuthTooManyAttemptsError as error:
            raise AdminAIUsageReadTooManyAttemptsError(error.detail) from error
        except AdminAuthAccessDeniedError as error:
            raise AdminAIUsageReadAccessDeniedError(error.detail) from error
