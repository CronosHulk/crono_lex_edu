from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.auth.router import admin_auth_http_exception, build_auth_router
from app.admin_api.context import AdminRouterContext
from app.application.admin.auth.errors import (
    AdminAuthAccessDeniedError,
    AdminAuthTooManyAttemptsError,
    AdminAuthUnauthorizedError,
    AdminAuthValidationError,
)
from app.application.admin.auth.models import AdminAuthStartResult


class FakeAdminAuthService:
    def __init__(self) -> None:
        self.start_login_calls = []

    def start_login(self, *, username, password=None, request_context=None):
        self.start_login_calls.append(
            {
                "username": username,
                "password": password,
                "request_context": request_context,
            }
        )
        return AdminAuthStartResult(
            challenge_id=12,
            requires_otp=True,
            requires_password_setup=False,
            requires_password=False,
            dev_otp_hint="123 456",
        )


def test_admin_auth_http_exception_maps_auth_errors() -> None:
    validation_error = admin_auth_http_exception(AdminAuthValidationError("Invalid admin auth payload"))
    unauthorized_error = admin_auth_http_exception(AdminAuthUnauthorizedError("Not authenticated"))
    access_denied_error = admin_auth_http_exception(AdminAuthAccessDeniedError("Access denied"))
    too_many_attempts_error = admin_auth_http_exception(AdminAuthTooManyAttemptsError("Too many attempts"))

    assert validation_error.status_code == 400
    assert validation_error.detail == "Invalid admin auth payload"
    assert unauthorized_error.status_code == 401
    assert unauthorized_error.detail == "Not authenticated"
    assert access_denied_error.status_code == 403
    assert access_denied_error.detail == "Access denied"
    assert too_many_attempts_error.status_code == 429
    assert too_many_attempts_error.detail == "Too many attempts"


def test_admin_auth_start_route_uses_auth_service_context_directly() -> None:
    auth_service = FakeAdminAuthService()
    app = FastAPI()
    app.include_router(
        build_auth_router(
            SimpleNamespace(
                db=SimpleNamespace(
                    settings=SimpleNamespace(
                        app_admin_cookie_secure=False,
                        app_admin_session_hours=12,
                    )
                )
            ),
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: {"telegram_user_id": 1},
                admin_ai_usage_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("ai usage service should not be used")
                ),
                admin_auth_service=lambda: auth_service,
                admin_billing_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("billing service should not be used")
                ),
                admin_bootstrap_service=lambda: (_ for _ in ()).throw(
                    AssertionError("bootstrap service should not be used")
                ),
                admin_dashboard_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dashboard service should not be used")
                ),
                admin_dictionary_action_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary action service should not be used")
                ),
                admin_dictionary_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary read service should not be used")
                ),
                admin_dictionary_service=lambda: (_ for _ in ()).throw(
                    AssertionError("dictionary service should not be used")
                ),
                admin_entity_service=lambda: (_ for _ in ()).throw(
                    AssertionError("entity service should not be used")
                ),
                admin_exercise_text_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text service should not be used")
                ),
                admin_exercise_text_generation_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text generation service should not be used")
                ),
                admin_exercise_text_tts_service=lambda: (_ for _ in ()).throw(
                    AssertionError("exercise text tts service should not be used")
                ),
                admin_import_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("import read service should not be used")
                ),
                admin_log_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("log read service should not be used")
                ),
                admin_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("read service should not be used")
                ),
                admin_settings_service=lambda: (_ for _ in ()).throw(
                    AssertionError("settings service should not be used")
                ),
                admin_user_dictionary_bulk_action=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary bulk action should not be used")
                ),
                admin_user_dictionary_promote_action=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary promote action should not be used")
                ),
                admin_user_dictionary_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user dictionary read service should not be used")
                ),
                admin_user_action_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user action service should not be used")
                ),
                admin_user_read_service=lambda: (_ for _ in ()).throw(
                    AssertionError("user read service should not be used")
                ),
            ),
        )
    )

    response = TestClient(app).post("/auth/start", json={"username": "admin", "password": "Pass1234"})

    assert response.status_code == 200
    assert response.json() == {
        "challenge_id": 12,
        "requires_otp": True,
        "requires_password": False,
        "requires_password_setup": False,
        "dev_otp_hint": "123 456",
    }
    assert auth_service.start_login_calls[0]["username"] == "admin"
    assert auth_service.start_login_calls[0]["password"] == "Pass1234"
    assert auth_service.start_login_calls[0]["request_context"].api_path == "/auth/start"
