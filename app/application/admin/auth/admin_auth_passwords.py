from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.admin.auth.errors import AdminAuthUnauthorizedError, AdminAuthValidationError
from app.auth.identity import normalize_username
from app.auth.password import validate_password_complexity
from app.auth.secrets import hash_secret, verify_secret
from app.time_utils import TimeService

from .admin_auth_ports import AdminAuthDatabasePort


class AdminAuthPasswords:
    def __init__(
        self,
        db: AdminAuthDatabasePort,
        time_service: TimeService,
        *,
        is_dev_login_enabled: Callable[[], bool],
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.is_dev_login_enabled = is_dev_login_enabled

    def set_password_hash(self, *, user: dict[str, Any], password: str) -> None:
        try:
            validate_password_complexity(password)
        except ValueError as error:
            raise AdminAuthValidationError(str(error)) from error
        current_time = self.time_service.now()
        self.db.admin_auth.set_password_hash(
            int(user["telegram_user_id"]),
            hash_secret(password),
            current_time=current_time,
        )

    def update_password(self, *, user: dict[str, Any], current_password: str | None, password: str) -> dict[str, Any]:
        credential = self.db.admin_auth.get_credential(int(user["telegram_user_id"]))
        if credential and credential.get("password_hash"):
            if not current_password or not verify_secret(current_password, credential["password_hash"]):
                raise AdminAuthUnauthorizedError("Invalid current password")
        self.set_password_hash(user=user, password=password)
        fresh_user = self.db.admin_users.get_by_id(int(user["telegram_user_id"])) or user
        return self.with_auth_flags(fresh_user)

    def mark_password_prompted(self, *, user: dict[str, Any]) -> dict[str, Any]:
        self.db.admin_auth.mark_password_prompted(
            int(user["telegram_user_id"]),
            current_time=self.time_service.now(),
        )
        fresh_user = self.db.admin_users.get_by_id(int(user["telegram_user_id"])) or {
            **user,
            "admin_web_password_prompted": True,
        }
        return self.with_auth_flags(fresh_user)

    def with_auth_flags(self, user: dict[str, Any], *, credential: dict[str, Any] | None = None) -> dict[str, Any]:
        credential = credential if credential is not None else self.db.admin_auth.get_credential(int(user["telegram_user_id"]))
        has_password = bool(credential and credential.get("password_hash"))
        is_dev_admin = self.is_dev_login_enabled() and normalize_username(str(user.get("username") or "")) == "admin"
        return {
            **user,
            "has_password": has_password or is_dev_admin,
            "requires_password_setup": not is_dev_admin and not has_password and not bool(user.get("admin_web_password_prompted")),
        }
