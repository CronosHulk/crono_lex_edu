from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_ADMIN_ROLES = {"admin", "admin_editor", "super_admin"}


@dataclass(frozen=True)
class AdminAuthStartResult:
    challenge_id: int | None
    requires_otp: bool
    requires_password_setup: bool
    requires_password: bool = False
    dev_otp_hint: str | None = None


@dataclass(frozen=True)
class AdminAuthVerifyResult:
    session_token: str
    requires_password_setup: bool
    user: dict[str, Any]
    target_path: str | None = None
