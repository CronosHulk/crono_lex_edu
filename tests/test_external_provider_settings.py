from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.application.admin.settings.errors import (
    AdminSettingsAccessDeniedError,
    AdminSettingsUnauthorizedError,
    AdminSettingsValidationError,
)
from app.application.admin.settings.settings_service import AdminSettingsService
from app.application.admin.settings.validators import (
    normalize_provider_settings_payload,
    normalize_settings_payload,
)
from app.time_utils import TimeService

ACTOR = {"telegram_user_id": 42, "acl_group_title": "super_admin", "interface_locale": "uk"}
ADMIN_ACTOR = {"telegram_user_id": 42, "acl_group_title": "admin", "interface_locale": "uk"}
DENIED_ACTOR = {"telegram_user_id": 42, "acl_group_title": "student", "interface_locale": "uk"}


class FakeAudioStorageProvider:
    def delete_if_under_roots(self, audio_path, audio_roots) -> bool:
        return False


class FakeExternalProviderSettingsRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def get_map(self) -> dict[str, dict[str, Any]]:
        return dict(self.rows)

    def upsert(self, **kwargs: Any) -> dict[str, Any]:
        row = {
            "task_key": kwargs["task_key"],
            "provider_key": kwargs["provider_key"],
            "is_enabled": kwargs["is_enabled"],
            "config_json": kwargs["config_json"],
            "last_status_json": {},
            "created": kwargs["current_time"],
            "updated": kwargs["current_time"],
        }
        self.rows[kwargs["task_key"]] = row
        return row


class FakeAppSettingsRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def get_value(self, key: str) -> dict[str, Any] | None:
        return self.rows.get(key)

    def upsert_value(
        self, key: str, value_json: dict[str, Any], current_time: datetime
    ) -> dict[str, Any]:
        self.rows[key] = dict(value_json)
        return {
            "key": key,
            "value_json": dict(value_json),
            "created": current_time,
            "updated": current_time,
        }


class FakeAclPermissions:
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        if action in self.list_group_capabilities(group_title=group_title, environment=environment):
            return "enabled"
        return "disabled"

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        if environment != "web_admin":
            return []
        if group_title == "super_admin":
            return ["acl/manage", "settings/view"]
        if group_title == "admin":
            return ["settings/view"]
        return []


class FakeActionOtpVerifier:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def verify_action_otp(self, *, user, action_key, challenge_id, otp) -> None:
        self.calls.append(
            {
                "user": user,
                "action_key": action_key,
                "challenge_id": challenge_id,
                "otp": otp,
            }
        )
        if self.error is not None:
            raise self.error


class FakeProviderSettingsDb:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            app_user_import_word_details_provider="openai",
            app_user_import_openai_model="gpt-5.4-mini",
            app_user_import_openai_api_url="https://api.example.test/responses",
            app_user_import_word_audio_provider="google_tts",
            app_user_import_google_tts_language_code="en-US",
            app_user_import_google_tts_voice_name="en-US-Neural2-F",
            app_user_import_embeddings_model="sentence-model",
            app_user_import_embeddings_device="cpu",
        )
        self.external_provider_settings = FakeExternalProviderSettingsRepository()
        self.app_settings = FakeAppSettingsRepository()
        self.current_app_version = "0.0.7"
        self.user_learning_settings = SimpleNamespace(
            get_current_app_version=lambda: self.current_app_version,
            set_current_app_version=self._set_current_app_version,
        )
        self.user_profiles = SimpleNamespace(
            set_interface_locale=lambda _telegram_user_id, _locale: None
        )
        self.admin_users = SimpleNamespace(get_by_id=lambda _telegram_user_id: None)
        self.acl_permissions = FakeAclPermissions()

    def _set_current_app_version(self, version: str, *, current_time: str) -> str:
        _ = current_time
        self.current_app_version = version
        return self.current_app_version


def build_settings_service(
    db: FakeProviderSettingsDb | None = None,
    *,
    action_otp_verifier: FakeActionOtpVerifier | None = None,
) -> AdminSettingsService:
    return AdminSettingsService(
        db or FakeProviderSettingsDb(),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
        action_otp_verifier=action_otp_verifier,
    )


def test_provider_settings_service_lists_env_backed_defaults() -> None:
    service = build_settings_service()

    result = service.list_provider_settings(user=ACTOR)

    word_details = _task(result, "user_import.word_details")
    assert word_details["provider_key"] == "openai"
    assert word_details["is_enabled"] is True
    assert word_details["config"]["model"] == "gpt-5.4-mini"
    assert word_details["config"]["api_url"] == "https://api.example.test/responses"
    assert word_details["config_options"]["model"] == ["gpt-5.4", "gpt-5.4-mini"]
    assert word_details["config_options_by_provider"]["openai"]["model"] == [
        "gpt-5.4",
        "gpt-5.4-mini",
    ]
    word_validation = _task(result, "user_import.word_validation")
    assert word_validation["config"]["model"] == "gpt-5.4-mini"
    assert word_validation["config_options_by_provider"]["openai"]["model"] == [
        "gpt-5.4",
        "gpt-5.4-mini",
    ]
    embeddings = _task(result, "user_import.embeddings")
    assert embeddings["provider_key"] == "local_sentence_transformers"
    assert embeddings["is_enabled"] is True
    assert embeddings["config"]["model"] == "sentence-model"
    assert embeddings["config_options"]["device"] == ["cpu", "cuda"]


def test_provider_settings_service_persists_task_selection() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    result = service.update_provider_settings(
        user=ACTOR,
        payload={
            "tasks": [
                {
                    "task_key": "user_import.word_details",
                    "provider_key": "disabled",
                    "is_enabled": False,
                    "config": {},
                }
            ]
        }
    )

    word_details = _task(result, "user_import.word_details")
    assert word_details["provider_key"] == "disabled"
    assert word_details["is_enabled"] is False
    assert (
        db.external_provider_settings.rows["user_import.word_details"]["provider_key"] == "disabled"
    )


def test_provider_settings_service_rejects_write_without_acl_manage() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsAccessDeniedError) as error:
        service.update_provider_settings(
            user=ADMIN_ACTOR,
            payload={
                "tasks": [
                    {
                        "task_key": "user_import.word_details",
                        "provider_key": "disabled",
                        "is_enabled": False,
                        "config": {},
                    }
                ]
            },
        )

    assert error.value.detail == "Access denied"
    assert db.external_provider_settings.rows == {}


def test_settings_service_returns_default_import_settings() -> None:
    service = build_settings_service()

    result = service.get_settings(user=ACTOR)

    assert result["settings"]["import_settings"] == {
        "enrich_after_google_doc_import_enabled": False,
        "embedding_build_enabled": False,
        "attribute_build_hour": 2,
        "attribute_build_weekdays": None,
        "audio_build_hour": 2,
        "audio_build_weekdays": None,
        "google_doc_sync_hour": 0,
        "google_doc_sync_interval_days": 3,
        "google_doc_sync_weekdays": None,
        "max_import_entries_per_submission": 100,
        "scheduler_tick_minutes": 10,
        "validation_batch_size": 10,
    }
    assert result["settings"]["subscription_settings"] == {"trial_duration_days": 7}
    assert result["settings"]["billing_settings"]["monobank_mode"] == "disabled"
    assert result["settings"]["billing_settings"]["plan_prices_uah"]["premium"]["1"] == 10
    assert result["settings"]["support_settings"] == {
        "is_enabled": True,
        "support_url": "https://send.monobank.ua/jar/7E7wGkzHJr",
    }


def test_settings_service_rejects_denied_settings_read() -> None:
    service = build_settings_service()

    with pytest.raises(AdminSettingsAccessDeniedError) as error:
        service.get_settings(user=DENIED_ACTOR)

    assert error.value.detail == "Access denied"


def test_settings_service_rejects_denied_provider_settings_read() -> None:
    service = build_settings_service()

    with pytest.raises(AdminSettingsAccessDeniedError) as error:
        service.list_provider_settings(user=DENIED_ACTOR)

    assert error.value.detail == "Access denied"


def test_settings_service_rejects_denied_settings_update_before_payload_validation() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsAccessDeniedError) as error:
        service.update_settings(
            user=DENIED_ACTOR,
            payload={"billing_settings": {"monobank_mode": "test"}},
        )

    assert error.value.detail == "Access denied"
    assert "billing.runtime_settings" not in db.app_settings.rows


def test_settings_service_rejects_app_version_update_without_acl_manage() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsAccessDeniedError) as error:
        service.update_settings(user=ADMIN_ACTOR, payload={"app_version": "0.0.8"})

    assert error.value.detail == "Access denied"
    assert db.current_app_version == "0.0.7"


def test_settings_service_persists_import_settings() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    result = service.update_settings(
        user=ACTOR,
        payload={
            "import_settings": {
                "enrich_after_google_doc_import_enabled": True,
                "attribute_build_hour": 4,
                "attribute_build_weekdays": [1, 3, 5],
                "audio_build_hour": 2,
                "audio_build_weekdays": [0, 1, 2, 3, 4, 5, 6],
                "google_doc_sync_hour": 5,
                "google_doc_sync_interval_days": 7,
                "google_doc_sync_weekdays": [0, 2, 4],
                "max_import_entries_per_submission": 50,
                "scheduler_tick_minutes": 5,
                "validation_batch_size": 5,
            }
        },
    )

    assert result["settings"]["import_settings"]["enrich_after_google_doc_import_enabled"] is True
    assert db.app_settings.rows["user_import.runtime_settings"]["attribute_build_hour"] == 4
    assert db.app_settings.rows["user_import.runtime_settings"]["attribute_build_weekdays"] == [
        1,
        3,
        5,
    ]
    assert db.app_settings.rows["user_import.runtime_settings"]["audio_build_hour"] == 2
    assert db.app_settings.rows["user_import.runtime_settings"]["audio_build_weekdays"] == [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert db.app_settings.rows["user_import.runtime_settings"]["google_doc_sync_weekdays"] == [
        0,
        2,
        4,
    ]
    assert (
        db.app_settings.rows["user_import.runtime_settings"]["max_import_entries_per_submission"]
        == 50
    )
    assert db.app_settings.rows["user_import.runtime_settings"]["scheduler_tick_minutes"] == 5
    assert db.app_settings.rows["user_import.runtime_settings"]["validation_batch_size"] == 5


def test_settings_service_persists_subscription_settings() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    result = service.update_settings(
        user=ACTOR,
        payload={"subscription_settings": {"trial_duration_days": 14}},
    )

    assert result["settings"]["subscription_settings"]["trial_duration_days"] == 14
    assert db.app_settings.rows["subscriptions.runtime_settings"]["trial_duration_days"] == 14


def test_settings_service_persists_billing_settings() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    result = service.update_settings(
        user=ACTOR,
        payload={"billing_settings": {"plan_prices_uah": {"premium": {"1": 15}}}},
    )

    assert result["settings"]["billing_settings"]["monobank_mode"] == "disabled"
    assert result["settings"]["billing_settings"]["plan_prices_uah"]["premium"]["1"] == 15
    assert db.app_settings.rows["billing.runtime_settings"]["monobank_mode"] == "disabled"


def test_settings_service_partial_billing_settings_update_preserves_runtime_provider_and_custom_fields() -> None:
    db = FakeProviderSettingsDb()
    db.app_settings.rows["billing.runtime_settings"] = {
        "billing_provider": "monobank",
        "monobank_mode": "production",
        "plan_prices_uah": {
            "premium": {"1": 19, "3": 49},
            "premium_plus": {"1": 39, "12": 320},
        },
        "enabled_period_months": [1, 3, 6, 12],
        "frontend_poll_interval_seconds": 17,
        "frontend_poll_timeout_seconds": 123,
        "offer_text": "Custom offer text for partial update regression coverage.",
        "premium_plus_checkout_enabled": False,
        "double_time_for_project_support_enabled": True,
    }
    service = build_settings_service(db)

    result = service.update_settings(
        user=ACTOR,
        payload={"billing_settings": {"frontend_poll_interval_seconds": 29}},
    )

    stored = db.app_settings.rows["billing.runtime_settings"]
    assert stored["billing_provider"] == "monobank"
    assert stored["monobank_mode"] == "production"
    assert stored["plan_prices_uah"]["premium"]["1"] == 19
    assert stored["plan_prices_uah"]["premium_plus"]["12"] == 320
    assert stored["enabled_period_months"] == [1, 3, 6, 12]
    assert stored["frontend_poll_interval_seconds"] == 29
    assert stored["frontend_poll_timeout_seconds"] == 123
    assert stored["offer_text"] == "Custom offer text for partial update regression coverage."
    assert stored["premium_plus_checkout_enabled"] is False
    assert stored["double_time_for_project_support_enabled"] is True
    assert result["settings"]["billing_settings"]["billing_provider"] == "monobank"
    assert result["settings"]["billing_settings"]["frontend_poll_interval_seconds"] == 29


def test_settings_service_provider_only_update_with_valid_otp_preserves_existing_billing_runtime_settings() -> None:
    db = FakeProviderSettingsDb()
    db.app_settings.rows["billing.runtime_settings"] = {
        "billing_provider": "monobank",
        "monobank_mode": "production",
        "plan_prices_uah": {
            "premium": {"1": 19, "3": 49},
            "premium_plus": {"1": 39},
        },
        "enabled_period_months": [1, 3, 6],
        "frontend_poll_interval_seconds": 17,
        "frontend_poll_timeout_seconds": 123,
        "offer_text": "Custom offer text for provider regression coverage.",
        "premium_plus_checkout_enabled": False,
        "double_time_for_project_support_enabled": True,
    }
    otp_verifier = FakeActionOtpVerifier()
    service = build_settings_service(db, action_otp_verifier=otp_verifier)

    result = service.update_billing_provider_settings_with_otp(
        user=ACTOR,
        payload={"billing_provider": "instant", "challenge_id": 10, "otp": "123456"},
    )

    stored = db.app_settings.rows["billing.runtime_settings"]
    assert stored["billing_provider"] == "instant"
    assert stored["monobank_mode"] == "production"
    assert stored["plan_prices_uah"]["premium"]["1"] == 19
    assert stored["plan_prices_uah"]["premium_plus"]["1"] == 39
    assert stored["enabled_period_months"] == [1, 3, 6]
    assert stored["frontend_poll_interval_seconds"] == 17
    assert stored["frontend_poll_timeout_seconds"] == 123
    assert stored["offer_text"] == "Custom offer text for provider regression coverage."
    assert stored["premium_plus_checkout_enabled"] is False
    assert stored["double_time_for_project_support_enabled"] is True
    assert result["settings"]["billing_settings"]["billing_provider"] == "instant"
    assert result["settings"]["billing_settings"]["plan_prices_uah"]["premium"]["1"] == 19
    assert result["settings"]["billing_settings"]["frontend_poll_interval_seconds"] == 17
    assert otp_verifier.calls == [
        {
            "user": ACTOR,
            "action_key": "billing_provider_settings",
            "challenge_id": 10,
            "otp": "123456",
        }
    ]


def test_settings_service_provider_only_payload_missing_otp_does_not_persist_provider_switch() -> None:
    db = FakeProviderSettingsDb()
    db.app_settings.rows["billing.runtime_settings"] = {
        "billing_provider": "monobank",
        "monobank_mode": "production",
        "plan_prices_uah": {"premium": {"1": 19}},
    }
    before = deepcopy(db.app_settings.rows["billing.runtime_settings"])
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsValidationError) as error:
        service.update_billing_provider_settings_with_otp(
            user=ACTOR,
            payload={"billing_provider": "instant"},
        )

    assert "challenge_id" in str(error.value.detail)
    assert "otp" in str(error.value.detail)
    assert db.app_settings.rows["billing.runtime_settings"] == before


def test_settings_service_provider_only_payload_invalid_otp_does_not_persist_provider_switch() -> None:
    db = FakeProviderSettingsDb()
    db.app_settings.rows["billing.runtime_settings"] = {
        "billing_provider": "monobank",
        "monobank_mode": "production",
        "plan_prices_uah": {"premium": {"1": 19}},
    }
    before = deepcopy(db.app_settings.rows["billing.runtime_settings"])
    otp_verifier = FakeActionOtpVerifier(AdminSettingsUnauthorizedError("Invalid OTP"))
    service = build_settings_service(db, action_otp_verifier=otp_verifier)

    with pytest.raises(AdminSettingsUnauthorizedError) as error:
        service.update_billing_provider_settings_with_otp(
            user=ACTOR,
            payload={
                "billing_provider": "instant",
                "challenge_id": 10,
                "otp": "123456",
            },
        )

    assert error.value.detail == "Invalid OTP"
    assert db.app_settings.rows["billing.runtime_settings"] == before
    assert otp_verifier.calls == [
        {
            "user": ACTOR,
            "action_key": "billing_provider_settings",
            "challenge_id": 10,
            "otp": "123456",
        }
    ]


def test_settings_service_combined_provider_and_monobank_mode_update_persists_both_with_valid_otp() -> None:
    db = FakeProviderSettingsDb()
    db.settings.monobank_token_test = "test-token"
    db.app_settings.rows["billing.runtime_settings"] = {
        "billing_provider": "instant",
        "monobank_mode": "disabled",
        "plan_prices_uah": {"premium": {"1": 15}},
    }
    otp_verifier = FakeActionOtpVerifier()
    service = build_settings_service(db, action_otp_verifier=otp_verifier)

    result = service.update_billing_provider_settings_with_otp(
        user=ACTOR,
        payload={
            "billing_provider": "monobank",
            "monobank_mode": "test",
            "challenge_id": 10,
            "otp": "123456",
        },
    )

    assert db.app_settings.rows["billing.runtime_settings"]["billing_provider"] == "monobank"
    assert db.app_settings.rows["billing.monobank_mode"] == {"monobank_mode": "test"}
    assert result["settings"]["billing_settings"]["billing_provider"] == "monobank"
    assert result["settings"]["billing_settings"]["monobank_mode"] == "test"
    assert otp_verifier.calls == [
        {
            "user": ACTOR,
            "action_key": "billing_provider_settings",
            "challenge_id": 10,
            "otp": "123456",
        }
    ]


def test_settings_service_combined_provider_payload_missing_otp_does_not_partially_persist_provider() -> None:
    db = FakeProviderSettingsDb()
    db.app_settings.rows["billing.runtime_settings"] = {
        "billing_provider": "monobank",
        "monobank_mode": "production",
        "plan_prices_uah": {"premium": {"1": 19}},
    }
    before = dict(db.app_settings.rows["billing.runtime_settings"])
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsValidationError) as error:
        service.update_billing_provider_settings_with_otp(
            user=ACTOR,
            payload={"billing_provider": "instant", "monobank_mode": "test"},
        )

    assert "challenge_id" in str(error.value.detail)
    assert "otp" in str(error.value.detail)
    assert db.app_settings.rows["billing.runtime_settings"] == before
    assert "billing.monobank_mode" not in db.app_settings.rows


def test_settings_service_combined_provider_payload_invalid_otp_does_not_partially_persist_provider() -> None:
    db = FakeProviderSettingsDb()
    db.settings.monobank_token_test = "test-token"
    db.app_settings.rows["billing.runtime_settings"] = {
        "billing_provider": "monobank",
        "monobank_mode": "production",
        "plan_prices_uah": {"premium": {"1": 19}},
    }
    before = dict(db.app_settings.rows["billing.runtime_settings"])
    otp_verifier = FakeActionOtpVerifier(
        AdminSettingsUnauthorizedError("Invalid OTP"),
    )
    service = build_settings_service(db, action_otp_verifier=otp_verifier)

    with pytest.raises(AdminSettingsUnauthorizedError) as error:
        service.update_billing_provider_settings_with_otp(
            user=ACTOR,
            payload={
                "billing_provider": "instant",
                "monobank_mode": "test",
                "challenge_id": 10,
                "otp": "123456",
            },
        )

    assert error.value.detail == "Invalid OTP"
    assert db.app_settings.rows["billing.runtime_settings"] == before
    assert "billing.monobank_mode" not in db.app_settings.rows


def test_settings_service_rejects_direct_monobank_mode_update() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsValidationError) as error:
        service.update_settings(
            user=ACTOR,
            payload={"billing_settings": {"monobank_mode": "test"}},
        )

    assert str(error.value.detail) == "Use OTP-protected billing provider settings endpoint"
    assert "billing.runtime_settings" not in db.app_settings.rows


def test_settings_service_rejects_direct_billing_provider_update_and_does_not_persist() -> None:
    db = FakeProviderSettingsDb()
    db.app_settings.rows["billing.runtime_settings"] = {
        "billing_provider": "monobank",
        "monobank_mode": "production",
        "plan_prices_uah": {"premium": {"1": 19}},
    }
    before = dict(db.app_settings.rows["billing.runtime_settings"])
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsValidationError) as error:
        service.update_settings(
            user=ACTOR,
            payload={"billing_settings": {"billing_provider": "instant"}},
        )

    assert str(error.value.detail) == "Use OTP-protected billing provider settings endpoint"
    assert db.app_settings.rows["billing.runtime_settings"] == before
    assert "billing.monobank_mode" not in db.app_settings.rows


def test_settings_service_rejects_non_object_billing_settings_as_type_error() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsValidationError) as error:
        service.update_settings(
            user=ACTOR,
            payload={"billing_settings": "monobank_mode"},
        )

    assert str(error.value.detail) == "billing_settings must be an object"
    assert "billing.runtime_settings" not in db.app_settings.rows


def test_settings_service_persists_monobank_mode_separately() -> None:
    db = FakeProviderSettingsDb()
    db.app_settings.rows["billing.runtime_settings"] = {
        "monobank_mode": "disabled",
        "plan_prices_uah": {"premium": {"1": 15}},
    }
    service = build_settings_service(db)

    result = service.update_billing_monobank_mode(
        user={"telegram_user_id": 42, "interface_locale": "uk"},
        monobank_mode="test",
    )

    assert result["settings"]["billing_settings"]["monobank_mode"] == "test"
    assert result["settings"]["billing_settings"]["plan_prices_uah"]["premium"]["1"] == 15
    assert db.app_settings.rows["billing.runtime_settings"]["monobank_mode"] == "disabled"
    assert db.app_settings.rows["billing.monobank_mode"] == {"monobank_mode": "test"}


def test_settings_service_rejects_invalid_monobank_mode() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    with pytest.raises(AdminSettingsValidationError) as error:
        service.update_billing_monobank_mode(
            user={"telegram_user_id": 42, "interface_locale": "uk"},
            monobank_mode="live",
        )

    assert "monobank_mode" in str(error.value.detail)
    assert "billing.monobank_mode" not in db.app_settings.rows


def test_settings_service_persists_support_settings() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    result = service.update_settings(
        user=ACTOR,
        payload={
            "support_settings": {
                "is_enabled": True,
                "support_url": "https://send.monobank.ua/jar/custom",
            }
        },
    )

    assert result["settings"]["support_settings"] == {
        "is_enabled": True,
        "support_url": "https://send.monobank.ua/jar/custom",
    }
    assert (
        db.app_settings.rows["project.support_settings"]["support_url"]
        == "https://send.monobank.ua/jar/custom"
    )


def test_normalize_provider_settings_payload_rejects_unknown_config_field() -> None:
    try:
        normalize_provider_settings_payload(
            {
                "tasks": [
                    {
                        "task_key": "user_import.word_details",
                        "provider_key": "openai",
                        "is_enabled": True,
                        "config": {"temperature": "1"},
                    }
                ]
            }
        )
    except AdminSettingsValidationError as error:
        assert "Unsupported config fields" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_normalize_settings_payload_rejects_invalid_import_settings() -> None:
    try:
        normalize_settings_payload({"import_settings": {"google_doc_sync_interval_days": 8}})
    except AdminSettingsValidationError as error:
        assert "google_doc_sync_interval_days" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_normalize_settings_payload_rejects_unknown_google_doc_weekday_preset() -> None:
    try:
        normalize_settings_payload({"import_settings": {"google_doc_sync_weekdays": [0, 1]}})
    except AdminSettingsValidationError as error:
        assert "google_doc_sync_weekdays" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_normalize_settings_payload_rejects_invalid_import_limits() -> None:
    for field, value in (
        ("max_import_entries_per_submission", 500),
        ("scheduler_tick_minutes", 15),
        ("validation_batch_size", 25),
    ):
        try:
            normalize_settings_payload({"import_settings": {field: value}})
        except AdminSettingsValidationError as error:
            assert field in str(error.detail)
        else:  # pragma: no cover
            raise AssertionError("AdminSettingsValidationError was expected")


def test_normalize_settings_payload_rejects_invalid_subscription_settings() -> None:
    try:
        normalize_settings_payload({"subscription_settings": {"trial_duration_days": 99}})
    except AdminSettingsValidationError as error:
        assert "trial_duration_days" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_normalize_settings_payload_rejects_invalid_support_url() -> None:
    try:
        normalize_settings_payload({"support_settings": {"support_url": "http://example.test/jar"}})
    except AdminSettingsValidationError as error:
        assert "support_url" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_normalize_settings_payload_rejects_invalid_analytics_id() -> None:
    try:
        normalize_settings_payload({"analytics_settings": {"google_analytics_id": "UA-123"}})
    except AdminSettingsValidationError as error:
        assert "google_analytics_id" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_settings_service_rejects_enabled_support_without_url() -> None:
    db = FakeProviderSettingsDb()
    service = build_settings_service(db)

    try:
        service.update_settings(
            user=ACTOR,
            payload={"support_settings": {"support_url": ""}},
        )
    except AdminSettingsValidationError as error:
        assert "support_url" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_normalize_provider_settings_payload_rejects_unknown_openai_model() -> None:
    try:
        normalize_provider_settings_payload(
            {
                "tasks": [
                    {
                        "task_key": "user_import.word_validation",
                        "provider_key": "openai",
                        "is_enabled": True,
                        "config": {"model": "gpt-whatever"},
                    }
                ]
            }
        )
    except AdminSettingsValidationError as error:
        assert "model" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_fake_repository_uses_current_time() -> None:
    repository = FakeExternalProviderSettingsRepository()
    current_time = datetime(2026, 5, 1, 12, 0, 0)

    row = repository.upsert(
        task_key="user_import.word_audio",
        provider_key="google_tts",
        is_enabled=True,
        config_json={"voice_name": "en-US-Neural2-F"},
        current_time=current_time,
    )

    assert row["updated"] == current_time


def _task(payload: dict[str, Any], task_key: str) -> dict[str, Any]:
    for item in payload["tasks"]:
        if item["task_key"] == task_key:
            return item
    raise AssertionError(f"Missing task: {task_key}")
