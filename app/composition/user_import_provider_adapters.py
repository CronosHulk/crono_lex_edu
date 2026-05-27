from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.composition.audio_storage import build_audio_storage_provider
from app.domain.provider_settings import (
    DEFAULT_OPENAI_API_URL,
    DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
    DEFAULT_USER_IMPORT_OPENAI_MODEL,
    WORD_AUDIO_TASK_KEY,
    WORD_DETAILS_TASK_KEY,
    WORD_VALIDATION_TASK_KEY,
    get_provider_task,
    resolve_provider_task_setting,
)
from app.domain.user_import.text_parser import ParsedImportWord
from app.external_providers.user_import_embeddings import (
    ensure_user_import_embedding as _ensure_user_import_embedding,
)
from app.external_providers.user_import_google_docs import (
    fetch_google_doc_text as _fetch_google_doc_text,
)
from app.external_providers.user_import_google_tts import (
    ensure_user_import_audio as ensure_user_import_audio,
)
from app.external_providers.user_import_openai import (
    refine_user_import_with_openai,
    validate_user_import_candidates_with_openai,
)
from app.storage.audio import AudioStorageProvider
from app.user_import.provider_ports import (
    WordAudioProvider,
    WordDetailsProvider,
    WordValidationProvider,
    WordValidationProviderError,
)
from app.validators.user_import_provider_results import AIImportValidationResult


@dataclass(frozen=True)
class OpenAIWordValidationProvider:
    model: str = DEFAULT_USER_IMPORT_OPENAI_MODEL
    api_url: str = DEFAULT_OPENAI_API_URL
    provider_name: str = "openai_user_import_validation"

    def validate(self, candidates: list[ParsedImportWord]) -> AIImportValidationResult:
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                return validate_user_import_candidates_with_openai(
                    client=client,
                    candidates=candidates,
                    model=self.model,
                    api_url=self.api_url,
                )
        except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as error:
            raise WordValidationProviderError(error) from error


@dataclass(frozen=True)
class OpenAIWordDetailsProvider:
    model: str = DEFAULT_USER_IMPORT_OPENAI_MODEL
    api_url: str = DEFAULT_OPENAI_API_URL
    provider_name: str = "openai_user_import"

    def enrich(
        self,
        *,
        lookup_word: str,
        part_of_speech: str | None,
        translation_uk: str | None,
        translation_ru: str | None,
        translation_pl: str | None,
        phonetic_us: str | None,
        examples_json: list[str],
        details_retry_feedback: str | None = None,
    ) -> tuple[str, str, str, str, str, str, list[str], dict[str, Any]]:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            return refine_user_import_with_openai(
                client=client,
                lookup_word=lookup_word,
                part_of_speech=part_of_speech,
                translation_uk=translation_uk,
                translation_ru=translation_ru,
                translation_pl=translation_pl,
                phonetic_us=phonetic_us,
                examples_json=examples_json,
                model=self.model,
                api_url=self.api_url,
                details_retry_feedback=details_retry_feedback,
            )


@dataclass(frozen=True)
class GoogleTTSWordAudioProvider:
    audio_storage_provider: AudioStorageProvider
    language_code: str = "en-US"
    voice_name: str = "en-US-Neural2-F"
    provider_name: str = "google_tts"

    def build_audio(
        self,
        *,
        lookup_word: str,
        audio_dir: Path,
    ) -> tuple[str | None, dict[str, Any], str | None]:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            return ensure_user_import_audio(
                lookup_word=lookup_word,
                audio_dir=audio_dir,
                language_code=self.language_code,
                voice_name=self.voice_name,
                client=client,
                audio_storage_provider=self.audio_storage_provider,
            )


def build_word_validation_provider(
    settings: Any,
    task_settings: dict[str, Any] | None = None,
) -> WordValidationProvider | None:
    task = get_provider_task(WORD_VALIDATION_TASK_KEY)
    resolved = resolve_provider_task_setting(
        task,
        configured=task_settings,
        fallback_config={
            "model": str(getattr(settings, "app_user_import_openai_model", DEFAULT_USER_IMPORT_OPENAI_MODEL)),
            "api_url": str(getattr(settings, "app_user_import_openai_api_url", DEFAULT_OPENAI_API_URL)),
        },
    )
    if not resolved.is_enabled:
        return None
    if resolved.provider_key == "openai":
        return OpenAIWordValidationProvider(
            model=str(resolved.config.get("model") or DEFAULT_USER_IMPORT_OPENAI_MODEL),
            api_url=str(resolved.config.get("api_url") or DEFAULT_OPENAI_API_URL),
        )
    raise ValueError(f"Unsupported user import word validation provider: {resolved.provider_key}")


def build_word_details_provider(
    settings: Any,
    task_settings: dict[str, Any] | None = None,
) -> WordDetailsProvider | None:
    task = get_provider_task(WORD_DETAILS_TASK_KEY)
    resolved = resolve_provider_task_setting(
        task,
        configured=task_settings,
        fallback_provider_key=getattr(settings, "app_user_import_word_details_provider", "openai"),
        fallback_config={
            "model": str(getattr(settings, "app_user_import_openai_model", DEFAULT_USER_IMPORT_OPENAI_MODEL)),
            "api_url": str(getattr(settings, "app_user_import_openai_api_url", DEFAULT_OPENAI_API_URL)),
        },
    )
    if not resolved.is_enabled:
        return None
    if resolved.provider_key == "openai":
        return OpenAIWordDetailsProvider(
            model=str(resolved.config.get("model") or DEFAULT_USER_IMPORT_OPENAI_MODEL),
            api_url=str(resolved.config.get("api_url") or DEFAULT_OPENAI_API_URL),
        )
    raise ValueError(f"Unsupported user import word details provider: {resolved.provider_key}")


def build_word_audio_provider(
    settings: Any,
    task_settings: dict[str, Any] | None = None,
) -> WordAudioProvider:
    task = get_provider_task(WORD_AUDIO_TASK_KEY)
    resolved = resolve_provider_task_setting(
        task,
        configured=task_settings,
        fallback_provider_key=getattr(settings, "app_user_import_word_audio_provider", "google_tts"),
        fallback_config={
            "language_code": str(getattr(settings, "app_user_import_google_tts_language_code", "en-US")),
            "voice_name": str(getattr(settings, "app_user_import_google_tts_voice_name", "en-US-Neural2-F")),
        },
    )
    if resolved.provider_key == "google_tts" and resolved.is_enabled:
        return GoogleTTSWordAudioProvider(
            language_code=str(resolved.config.get("language_code") or "en-US"),
            voice_name=str(resolved.config.get("voice_name") or "en-US-Neural2-F"),
            audio_storage_provider=build_audio_storage_provider(settings),
        )
    raise ValueError(f"Unsupported user import word audio provider: {resolved.provider_key}")


def fetch_google_doc_text_with_provider(export_url: str) -> str:
    return _fetch_google_doc_text(export_url)


def ensure_user_import_embedding_with_provider(
    *,
    word: str,
    translation_uk: str | None,
    part_of_speech: str | None,
    examples_json: list[str],
    model_name: str = DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
    device: str = "cpu",
) -> tuple[list[float] | None, dict[str, Any], str | None]:
    return _ensure_user_import_embedding(
        word=word,
        translation_uk=translation_uk,
        part_of_speech=part_of_speech,
        examples_json=examples_json,
        model_name=model_name,
        device=device,
    )
