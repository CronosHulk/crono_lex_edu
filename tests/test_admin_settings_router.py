from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_api.context import AdminRouterContext
from app.admin_api.settings.router import build_settings_router
from app.application.admin.settings.errors import (
    AdminSettingsAccessDeniedError,
    AdminSettingsTooManyAttemptsError,
    AdminSettingsUnauthorizedError,
    AdminSettingsValidationError,
)


class FakeAdminSettingsService:
    def __init__(self) -> None:
        self.get_settings_calls = []
        self.update_settings_calls = []
        self.update_billing_monobank_mode_with_otp_calls = []
        self.update_billing_provider_settings_with_otp_calls = []

    def get_settings(self, *, user):
        self.get_settings_calls.append({"user": user})
        return {"user": user, "settings": {"interface_locale": "uk"}}

    def update_settings(self, *, user, payload):
        self.update_settings_calls.append({"user": user, "payload": payload})
        return {"user": user, "settings": payload}

    def update_billing_monobank_mode_with_otp(self, *, user, monobank_mode, challenge_id, otp, action_key):
        self.update_billing_monobank_mode_with_otp_calls.append(
            {
                "user": user,
                "monobank_mode": monobank_mode,
                "challenge_id": challenge_id,
                "otp": otp,
                "action_key": action_key,
            }
        )
        return {"user": user, "settings": {"billing_settings": {"monobank_mode": monobank_mode}}, "action_key": action_key}

    def update_billing_provider_settings_with_otp(self, *, user, payload, action_key):
        self.update_billing_provider_settings_with_otp_calls.append(
            {
                "user": user,
                "payload": payload,
                "action_key": action_key,
            }
        )
        return {"user": user, "settings": {"billing_settings": payload}, "action_key": action_key}


class InvalidUpdateAdminSettingsService(FakeAdminSettingsService):
    def update_settings(self, *, user, payload):
        self.update_settings_calls.append({"user": user, "payload": payload})
        raise AdminSettingsValidationError("interface_locale must be one of: pl, ru, uk")


class InvalidGenericBillingProviderUpdateAdminSettingsService(FakeAdminSettingsService):
    def update_settings(self, *, user, payload):
        self.update_settings_calls.append({"user": user, "payload": payload})
        raise AdminSettingsValidationError("Use OTP-protected billing provider settings endpoint")


class ErrorGetAdminSettingsService(FakeAdminSettingsService):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    def get_settings(self, *, user):
        self.get_settings_calls.append({"user": user})
        raise self.error


def _unused_service(name: str):
    return lambda: (_ for _ in ()).throw(AssertionError(f"{name} should not be used"))


def build_settings_test_client(*, settings_service, actor: dict | None = None) -> TestClient:
    actor = actor or {"telegram_user_id": 1, "acl_group_title": "admin"}
    app = FastAPI()
    app.include_router(
        build_settings_router(
            AdminRouterContext(audio_storage_provider=lambda: object(),
                current_admin_user=lambda request: actor,
                admin_ai_usage_read_service=_unused_service("ai usage service"),
                admin_auth_service=_unused_service("auth service"),
                admin_billing_read_service=_unused_service("billing service"),
                admin_bootstrap_service=_unused_service("bootstrap service"),
                admin_dashboard_service=_unused_service("dashboard service"),
                admin_dictionary_action_service=_unused_service("dictionary action service"),
                admin_dictionary_read_service=_unused_service("dictionary read service"),
                admin_dictionary_service=_unused_service("dictionary service"),
                admin_entity_service=_unused_service("entity service"),
                admin_exercise_text_service=_unused_service("exercise text service"),
                admin_exercise_text_generation_service=_unused_service("exercise text generation service"),
                admin_exercise_text_tts_service=_unused_service("exercise text tts service"),
                admin_import_read_service=_unused_service("import read service"),
                admin_log_read_service=_unused_service("log read service"),
                admin_read_service=_unused_service("read service"),
                admin_settings_service=lambda: settings_service,
                admin_user_dictionary_bulk_action=_unused_service("user dictionary bulk action"),
                admin_user_dictionary_promote_action=_unused_service("user dictionary promote action"),
                admin_user_dictionary_read_service=_unused_service("user dictionary read service"),
                admin_user_action_service=_unused_service("user action service"),
                admin_user_read_service=_unused_service("user read service"),
            )
        )
    )
    return TestClient(app)


def test_admin_settings_route_uses_settings_service_context_directly() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)

    response = client.get("/settings")

    assert response.status_code == 200
    assert response.json() == {"user": actor, "settings": {"interface_locale": "uk"}}
    assert settings_service.get_settings_calls == [{"user": actor}]


def test_admin_settings_router_maps_settings_validation_errors() -> None:
    settings_service = InvalidUpdateAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)

    response = client.patch("/settings", json={"interface_locale": "en"})

    assert response.status_code == 400
    assert response.json() == {"detail": "interface_locale must be one of: pl, ru, uk"}
    assert settings_service.update_settings_calls == [
        {
            "user": actor,
            "payload": {"interface_locale": "en"},
        }
    ]


def test_admin_settings_router_updates_generic_settings_with_partial_billing_settings() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)
    payload = {"billing_settings": {"plan_prices_uah": {"premium": {"1": 15}}}}

    response = client.patch("/settings", json=payload)

    assert response.status_code == 200
    assert settings_service.update_settings_calls == [
        {
            "user": actor,
            "payload": payload,
        }
    ]
    assert settings_service.update_billing_provider_settings_with_otp_calls == []


def test_admin_settings_router_rejects_generic_settings_patch_with_billing_provider() -> None:
    settings_service = InvalidGenericBillingProviderUpdateAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)
    payload = {"billing_settings": {"billing_provider": "monobank"}}

    response = client.patch("/settings", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "Use OTP-protected billing provider settings endpoint"}
    assert settings_service.update_settings_calls == [{"user": actor, "payload": payload}]
    assert settings_service.update_billing_provider_settings_with_otp_calls == []


def test_admin_settings_router_maps_settings_access_denied_errors() -> None:
    settings_service = ErrorGetAdminSettingsService(AdminSettingsAccessDeniedError("Access denied"))
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)

    response = client.get("/settings")

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied"}
    assert settings_service.get_settings_calls == [{"user": actor}]


def test_admin_settings_router_maps_settings_unauthorized_errors() -> None:
    settings_service = ErrorGetAdminSettingsService(AdminSettingsUnauthorizedError("Invalid OTP"))
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)

    response = client.get("/settings")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid OTP"}
    assert settings_service.get_settings_calls == [{"user": actor}]


def test_admin_settings_router_maps_settings_too_many_attempts_errors() -> None:
    settings_service = ErrorGetAdminSettingsService(AdminSettingsTooManyAttemptsError("Too many attempts"))
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)

    response = client.get("/settings")

    assert response.status_code == 429
    assert response.json() == {"detail": "Too many attempts"}
    assert settings_service.get_settings_calls == [{"user": actor}]


def test_admin_settings_router_updates_provider_settings_route_aliases_for_provider_payload_with_otp() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)
    for route in ("/settings/billing/provider-settings", "/settings/billing/provider"):
        for billing_provider in ("instant", "monobank"):
            payload = {"billing_provider": billing_provider, "challenge_id": 10, "otp": "123456"}
            response = client.patch(route, json=payload)
            assert response.status_code == 200

    assert settings_service.update_billing_provider_settings_with_otp_calls == [
        {
            "user": actor,
            "payload": {"billing_provider": "instant", "challenge_id": 10, "otp": "123456"},
            "action_key": "billing_provider_settings",
        },
        {
            "user": actor,
            "payload": {"billing_provider": "monobank", "challenge_id": 10, "otp": "123456"},
            "action_key": "billing_provider_settings",
        },
        {
            "user": actor,
            "payload": {"billing_provider": "instant", "challenge_id": 10, "otp": "123456"},
            "action_key": "billing_provider_settings",
        },
        {
            "user": actor,
            "payload": {"billing_provider": "monobank", "challenge_id": 10, "otp": "123456"},
            "action_key": "billing_provider_settings",
        },
    ]


def test_admin_settings_router_rejects_provider_settings_route_aliases_for_provider_without_otp() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)

    for route in ("/settings/billing/provider-settings", "/settings/billing/provider"):
        for billing_provider in ("instant", "monobank"):
            response = client.patch(route, json={"billing_provider": billing_provider})
            assert response.status_code in {400, 422}

    assert settings_service.update_billing_provider_settings_with_otp_calls == []


def test_admin_settings_router_updates_provider_settings_route_with_monobank_mode_and_otp() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)
    payload = {"monobank_mode": "test", "challenge_id": 10, "otp": "123456"}

    response = client.patch("/settings/billing/provider-settings", json=payload)

    assert response.status_code == 200
    assert settings_service.update_billing_provider_settings_with_otp_calls == [
        {
            "user": actor,
            "payload": {
                "monobank_mode": "test",
                "challenge_id": 10,
                "otp": "123456",
            },
            "action_key": "billing_provider_settings",
        }
    ]


def test_admin_settings_router_updates_provider_settings_route_with_combined_provider_and_monobank_mode() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)
    payload = {
        "billing_provider": "instant",
        "monobank_mode": "test",
        "challenge_id": 10,
        "otp": "123456",
    }

    response = client.patch("/settings/billing/provider-settings", json=payload)

    assert response.status_code == 200
    assert settings_service.update_billing_provider_settings_with_otp_calls == [
        {
            "user": actor,
            "payload": payload,
            "action_key": "billing_provider_settings",
        }
    ]


def test_admin_settings_router_rejects_provider_settings_monobank_mode_without_otp() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)

    response = client.patch("/settings/billing/provider-settings", json={"monobank_mode": "test"})

    assert response.status_code == 422
    assert settings_service.update_billing_provider_settings_with_otp_calls == []


def test_admin_settings_router_rejects_combined_provider_settings_monobank_mode_without_otp() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)

    response = client.patch(
        "/settings/billing/provider-settings",
        json={"billing_provider": "instant", "monobank_mode": "test"},
    )

    assert response.status_code == 422
    assert settings_service.update_billing_provider_settings_with_otp_calls == []


def test_admin_settings_router_keeps_legacy_monobank_mode_route_action_key() -> None:
    settings_service = FakeAdminSettingsService()
    actor = {"telegram_user_id": 1, "acl_group_title": "admin"}
    client = build_settings_test_client(settings_service=settings_service, actor=actor)
    payload = {"monobank_mode": "test", "challenge_id": 10, "otp": "123456"}

    response = client.patch("/settings/billing/monobank-mode", json=payload)

    assert response.status_code == 200
    assert settings_service.update_billing_monobank_mode_with_otp_calls == [
        {
            "user": actor,
            "monobank_mode": "test",
            "challenge_id": 10,
            "otp": "123456",
            "action_key": "billing_monobank_mode",
        }
    ]
