from __future__ import annotations

import pytest

from app.application.admin.auth.auth_service import AdminAuthService
from app.application.admin.auth.target_path import normalize_admin_target_path
from app.auth.identity import normalize_username
from app.auth.otp import normalize_otp
from app.auth.password import validate_password_complexity
from app.auth.request_context import WebRequestContext
from app.auth.secrets import hash_secret, verify_secret


def test_admin_auth_helpers_normalize_user_input() -> None:
    assert normalize_username(" @Admin_User ") == "admin_user"
    assert normalize_otp("123 456") == "123456"
    assert normalize_admin_target_path("/admin/users") == "/admin/users"
    assert normalize_admin_target_path("https://evil.test/admin") == "/admin/user-dictionary"


def test_admin_auth_secret_hash_verification() -> None:
    stored_hash = hash_secret("secret", salt="fixed-salt")

    assert verify_secret("secret", stored_hash) is True
    assert verify_secret("wrong", stored_hash) is False


def test_admin_auth_password_complexity_requires_letters_and_digits() -> None:
    validate_password_complexity("Strong123")

    with pytest.raises(ValueError, match="Latin letters"):
        validate_password_complexity("12345678")


def test_web_request_context_builds_stable_device_fingerprint() -> None:
    context = WebRequestContext(api_origin="https://cronolex.local", client_ip="127.0.0.1", user_agent="agent")

    assert context.device_fingerprint_hash == WebRequestContext(
        api_origin="https://cronolex.local",
        client_ip="127.0.0.1",
        user_agent="agent",
    ).device_fingerprint_hash


def test_admin_auth_service_lives_in_application_boundary() -> None:
    assert AdminAuthService.__module__ == "app.application.admin.auth.auth_service"
