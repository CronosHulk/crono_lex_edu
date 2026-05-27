from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.composition.admin as admin_composition
from app.application.admin.bootstrap_service import AdminBootstrapService
from app.application.admin.permissions import AdminPermissionDeniedError
from app.composition.admin import build_admin_service_dependencies
from app.time_utils import TimeService
from tests.test_admin_service import FakeAdminDb, FakeTelegramGateway, build_pending_row


def test_admin_bootstrap_service_returns_navigation_and_provider_settings() -> None:
    db = FakeAdminDb(build_pending_row())
    db.settings.app_user_import_word_details_provider = "openai"
    db.settings.app_user_import_word_audio_provider = "google_tts"
    service = AdminBootstrapService(db.settings, db.user_learning_settings, db.acl_permissions)

    result = service.bootstrap(db.admin_user)

    assert result["version"] == "0.0.7"
    assert result["user"]["telegram_user_id"] == 1
    assert result["acl"]["environment"] == "web_admin"
    assert [item["id"] for item in result["navigation"]] == [
        "dashboard",
        "dictionary",
        "users",
        "logs",
        "settings",
    ]
    assert result["navigation"][1]["children"] == [
        {"id": "dictionary", "title": "Base"},
        {"id": "user_dictionary", "title": "User Words"},
    ]
    assert result["navigation"][3]["children"] == [
        {"id": "task_logs", "title": "Task Logs"},
        {"id": "ai_usage", "title": "AI Usage"},
        {"id": "error_log", "title": "Error Log"},
    ]
    assert result["settings"]["user_import_providers"]["word_details_provider"] == "openai"
    assert result["settings"]["user_import_providers"]["word_audio_provider"] == "google_tts"


def test_admin_bootstrap_service_preserves_denied_acl_before_payload() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminBootstrapService(db.settings, db.user_learning_settings, db.acl_permissions)

    with pytest.raises(AdminPermissionDeniedError) as error:
        service.bootstrap({"telegram_user_id": 2, "acl_group_title": "student"})

    assert error.value.detail == "Access denied"


def test_admin_dependency_composition_exposes_bootstrap_service(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    audio_storage_provider = object()
    monkeypatch.setattr(
        admin_composition,
        "build_audio_storage_provider",
        lambda _settings: audio_storage_provider,
    )
    dependencies = build_admin_service_dependencies(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())

    result = dependencies.admin_bootstrap_service.bootstrap(db.admin_user)

    assert result["version"] == "0.0.7"
    assert "dictionary/list_words" in result["acl"]["capabilities"]
    assert result["settings"]["user_import_providers"]["google_tts_language_code"] == "en-US"
    assert dependencies.audio_storage_provider is audio_storage_provider
    assert dependencies.admin_settings_service.audio_storage_provider is audio_storage_provider
    assert dependencies.admin_dictionary_service.audio_storage_provider is audio_storage_provider
    assert dependencies.admin_user_dictionary_promote_action.audio_storage_provider is audio_storage_provider
    assert dependencies.admin_exercise_text_tts_service.audio_storage_provider is audio_storage_provider


def test_configure_admin_runtime_attaches_admin_dependencies(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    gateway = FakeTelegramGateway()
    runtime = SimpleNamespace(time_service=TimeService("Europe/Kyiv"))
    gateway_settings = []

    def fake_build_admin_telegram_gateway(settings: object) -> FakeTelegramGateway:
        gateway_settings.append(settings)
        return gateway

    monkeypatch.setattr(
        admin_composition,
        "build_admin_telegram_gateway",
        fake_build_admin_telegram_gateway,
    )

    admin_composition.configure_admin_runtime(runtime, db)

    dependencies = runtime.admin_service_dependencies
    assert gateway_settings == [db.settings]
    assert dependencies.admin_auth_service.db is db
    assert dependencies.admin_auth_service.time_service is runtime.time_service
    assert dependencies.admin_auth_service.telegram_gateway is gateway
    assert dependencies.admin_bootstrap_service.bootstrap(db.admin_user)["version"] == "0.0.7"
