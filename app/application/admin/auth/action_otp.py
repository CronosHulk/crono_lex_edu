from __future__ import annotations

from typing import Any, Protocol


class ActionOtpVerifier(Protocol):
    def verify_action_otp(self, *, user: dict[str, Any], action_key: str, challenge_id: int, otp: str) -> None:
        ...
