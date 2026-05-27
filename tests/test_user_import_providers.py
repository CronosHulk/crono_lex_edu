from __future__ import annotations

from types import SimpleNamespace

import app.composition.user_import_provider_adapters as user_import_provider_adapters
from app.composition.user_import_provider_adapters import (
    GoogleTTSWordAudioProvider,
    OpenAIWordDetailsProvider,
    OpenAIWordValidationProvider,
    build_word_audio_provider,
    build_word_details_provider,
    build_word_validation_provider,
)
from app.user_import.providers import (
    WORD_DETAILS_TASK_KEY,
    WORD_VALIDATION_TASK_KEY,
    describe_user_import_providers,
    read_user_import_provider_task_setting,
    read_user_import_provider_task_settings,
)


class FakeProviderSettingsRepository:
    def __init__(self, values):
        self.values = values

    def get_map(self):
        return self.values


def test_build_word_details_provider_returns_openai_provider() -> None:
    settings = SimpleNamespace(
        app_user_import_word_details_provider="openai",
        app_user_import_openai_model="gpt-test",
        app_user_import_openai_api_url="https://api.example.test/responses",
    )

    provider = build_word_details_provider(settings)

    assert isinstance(provider, OpenAIWordDetailsProvider)
    assert provider.model == "gpt-test"
    assert provider.api_url == "https://api.example.test/responses"


def test_build_word_validation_provider_returns_openai_provider() -> None:
    settings = SimpleNamespace(
        app_user_import_openai_model="gpt-fallback",
        app_user_import_openai_api_url="https://api.example.test/fallback",
    )

    provider = build_word_validation_provider(
        settings,
        {
            "provider_key": "openai",
            "config": {
                "model": "gpt-validation",
                "api_url": "https://api.example.test/validation",
            },
        },
    )

    assert isinstance(provider, OpenAIWordValidationProvider)
    assert provider.model == "gpt-validation"
    assert provider.api_url == "https://api.example.test/validation"


def test_build_word_validation_provider_returns_none_when_disabled() -> None:
    settings = SimpleNamespace(
        app_user_import_openai_model="gpt-validation",
        app_user_import_openai_api_url="https://api.example.test/validation",
    )

    provider = build_word_validation_provider(
        settings,
        {
            "provider_key": "disabled",
            "is_enabled": False,
            "config": {"model": "gpt-validation"},
        },
    )

    assert provider is None


def test_build_word_audio_provider_returns_google_tts_provider(monkeypatch) -> None:
    storage_provider = object()
    settings = SimpleNamespace(
        app_user_import_word_audio_provider="google_tts",
        app_user_import_google_tts_language_code="en-GB",
        app_user_import_google_tts_voice_name="en-GB-Neural2-A",
    )

    monkeypatch.setattr(
        user_import_provider_adapters,
        "build_audio_storage_provider",
        lambda _settings: storage_provider,
    )

    provider = build_word_audio_provider(settings)

    assert isinstance(provider, GoogleTTSWordAudioProvider)
    assert provider.language_code == "en-GB"
    assert provider.voice_name == "en-GB-Neural2-A"
    assert provider.audio_storage_provider is storage_provider


def test_describe_user_import_providers_returns_admin_safe_settings() -> None:
    settings = SimpleNamespace(
        app_user_import_word_details_provider="openai",
        app_user_import_word_audio_provider="google_tts",
        app_user_import_openai_refine_enabled=True,
        app_user_import_openai_model="gpt-test",
        app_user_import_google_tts_language_code="en-US",
        app_user_import_google_tts_voice_name="en-US-Neural2-F",
    )

    description = describe_user_import_providers(settings)

    assert description == {
        "word_details_provider": "openai",
        "word_audio_provider": "google_tts",
        "openai_refine_enabled": True,
        "openai_model": "gpt-test",
        "google_tts_language_code": "en-US",
        "google_tts_voice_name": "en-US-Neural2-F",
    }


def test_read_user_import_provider_task_settings_uses_repository_map() -> None:
    values = {
        WORD_DETAILS_TASK_KEY: {
            "provider_key": "openai",
            "config": {"model": "gpt-test"},
        },
        WORD_VALIDATION_TASK_KEY: {
            "provider_key": "openai",
            "config": {"model": "gpt-validation"},
        }
    }
    db = SimpleNamespace(external_provider_settings=FakeProviderSettingsRepository(values))

    assert read_user_import_provider_task_settings(db) is values
    assert read_user_import_provider_task_setting(db, WORD_DETAILS_TASK_KEY) == values[
        WORD_DETAILS_TASK_KEY
    ]


def test_read_user_import_provider_task_setting_handles_missing_repository() -> None:
    db = SimpleNamespace()

    assert read_user_import_provider_task_settings(db) == {}
    assert read_user_import_provider_task_setting(db, WORD_DETAILS_TASK_KEY) is None
