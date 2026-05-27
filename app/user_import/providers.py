from __future__ import annotations

from typing import Any

from app.domain.provider_settings import (
    DEFAULT_OPENAI_API_URL,
    DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
    DEFAULT_USER_IMPORT_OPENAI_MODEL,
    WORD_AUDIO_TASK_KEY,
    WORD_DETAILS_TASK_KEY,
    WORD_EMBEDDINGS_TASK_KEY,
    WORD_VALIDATION_TASK_KEY,
    get_provider_task,
    normalize_provider_key,
    resolve_provider_task_setting,
)

__all__ = [
    "DEFAULT_OPENAI_API_URL",
    "DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL",
    "DEFAULT_USER_IMPORT_OPENAI_MODEL",
    "WORD_AUDIO_TASK_KEY",
    "WORD_DETAILS_TASK_KEY",
    "WORD_EMBEDDINGS_TASK_KEY",
    "WORD_VALIDATION_TASK_KEY",
    "describe_user_import_providers",
    "normalize_provider_name",
    "read_user_import_provider_task_setting",
    "read_user_import_provider_task_settings",
    "resolve_word_embedding_provider_setting",
]


def read_user_import_provider_task_settings(db: Any) -> dict[str, dict[str, Any]]:
    repository = getattr(db, "external_provider_settings", None)
    if repository is None:
        if not callable(getattr(db, "session", None)):
            return {}
        try:
            from app.data_access.external_provider_settings import (
                ExternalProviderSettingsRepository,
            )
            repository = ExternalProviderSettingsRepository(db)
        except ImportError:
            return {}
    return repository.get_map()


def read_user_import_provider_task_setting(
    db: Any,
    task_key: str,
) -> dict[str, Any] | None:
    return read_user_import_provider_task_settings(db).get(task_key)


def normalize_provider_name(value: str | None) -> str:
    return normalize_provider_key(value)


def resolve_word_embedding_provider_setting(
    settings: Any,
    task_settings: dict[str, Any] | None = None,
) -> Any:
    return resolve_provider_task_setting(
        get_provider_task(WORD_EMBEDDINGS_TASK_KEY),
        configured=task_settings,
        fallback_provider_key="local_sentence_transformers",
        fallback_config={
            "model": str(
                getattr(
                    settings,
                    "app_user_import_embeddings_model",
                    DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
                )
            ),
            "device": str(getattr(settings, "app_user_import_embeddings_device", "cpu")),
        },
    )


def describe_user_import_providers(settings: Any, provider_task_settings: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    provider_task_settings = provider_task_settings or {}
    details = resolve_provider_task_setting(
        get_provider_task(WORD_DETAILS_TASK_KEY),
        configured=provider_task_settings.get(WORD_DETAILS_TASK_KEY),
        fallback_provider_key=getattr(settings, "app_user_import_word_details_provider", "openai"),
        fallback_config={
            "model": str(getattr(settings, "app_user_import_openai_model", DEFAULT_USER_IMPORT_OPENAI_MODEL)),
            "api_url": str(getattr(settings, "app_user_import_openai_api_url", DEFAULT_OPENAI_API_URL)),
        },
    )
    audio = resolve_provider_task_setting(
        get_provider_task(WORD_AUDIO_TASK_KEY),
        configured=provider_task_settings.get(WORD_AUDIO_TASK_KEY),
        fallback_provider_key=getattr(settings, "app_user_import_word_audio_provider", "google_tts"),
        fallback_config={
            "language_code": str(getattr(settings, "app_user_import_google_tts_language_code", "en-US")),
            "voice_name": str(getattr(settings, "app_user_import_google_tts_voice_name", "en-US-Neural2-F")),
        },
    )
    return {
        "word_details_provider": details.provider_key,
        "word_audio_provider": audio.provider_key,
        "openai_refine_enabled": details.is_enabled,
        "openai_model": str(details.config.get("model") or DEFAULT_USER_IMPORT_OPENAI_MODEL),
        "google_tts_language_code": str(audio.config.get("language_code") or "en-US"),
        "google_tts_voice_name": str(audio.config.get("voice_name") or "en-US-Neural2-F"),
    }
