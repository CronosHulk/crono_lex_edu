from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from app.application.admin.exercise_texts.prompts import build_exercise_text_generation_prompt
from app.application.admin.exercise_texts.providers import (
    ExerciseTextGenerationProvider,
    ExerciseTextGenerationProviderDisabledError,
    ExerciseTextGenerationRequest,
    ExerciseTextGenerationResult,
    ExerciseTextTTSProvider,
    ExerciseTextTTSProviderDisabledError,
    ExerciseTextTTSRequest,
    ExerciseTextTTSResult,
    UnsupportedExerciseTextGenerationProviderError,
    UnsupportedExerciseTextTTSProviderError,
)
from app.domain.provider_settings import (
    EXERCISE_TEXT_GENERATION_TASK_KEY,
    EXERCISE_TEXT_TTS_TASK_KEY,
    get_provider_task,
    resolve_provider_task_setting,
)
from app.external_providers.usage import openai_usage_from_response
from app.external_providers.user_import_google_tts import (
    DEFAULT_GOOGLE_TTS_API_URL,
    resolve_google_tts_api_key,
)
from app.external_providers.user_import_openai import (
    DEFAULT_OPENAI_API_URL,
    DEFAULT_USER_IMPORT_OPENAI_MODEL,
    resolve_openai_api_key,
)


@dataclass(frozen=True)
class OpenAIExerciseTextGenerationProvider:
    model: str = DEFAULT_USER_IMPORT_OPENAI_MODEL
    api_url: str = DEFAULT_OPENAI_API_URL
    provider_key: str = "openai"

    def generate(self, request: ExerciseTextGenerationRequest) -> ExerciseTextGenerationResult:
        prompt = build_exercise_text_generation_prompt(request)
        with httpx.Client(timeout=60) as client:
            response = client.post(
                self.api_url,
                headers={"Authorization": f"Bearer {resolve_openai_api_key()}"},
                json={
                    "model": self.model,
                    "input": [
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": "You generate CronoLex exercise text JSON and return strict JSON only.",
                                }
                            ],
                        },
                        {
                            "role": "user",
                            "content": [{"type": "input_text", "text": prompt}],
                        },
                    ],
                    "text": {"format": {"type": "json_object"}},
                },
            )
            response.raise_for_status()
            response_json = response.json()
        output_text = _extract_openai_text(response_json)
        return ExerciseTextGenerationResult(
            raw_json_text=output_text,
            usage=openai_usage_from_response(
                response_json=response_json,
                model=self.model,
                prompt_text=prompt,
                output_text=output_text,
            ),
        )


def build_exercise_text_generation_provider(
    *,
    settings: Any,
    configured: dict[str, Any] | None,
) -> ExerciseTextGenerationProvider:
    task = get_provider_task(EXERCISE_TEXT_GENERATION_TASK_KEY)
    resolved = resolve_provider_task_setting(
        task,
        configured=configured,
        fallback_config={
            "model": str(getattr(settings, "app_user_import_openai_model", DEFAULT_USER_IMPORT_OPENAI_MODEL)),
            "api_url": str(getattr(settings, "app_user_import_openai_api_url", DEFAULT_OPENAI_API_URL)),
        },
    )
    if not resolved.is_enabled:
        raise ExerciseTextGenerationProviderDisabledError("Exercise text generation provider is disabled")
    if resolved.provider_key == "openai":
        return OpenAIExerciseTextGenerationProvider(
            model=str(resolved.config.get("model") or DEFAULT_USER_IMPORT_OPENAI_MODEL),
            api_url=str(resolved.config.get("api_url") or DEFAULT_OPENAI_API_URL),
        )
    raise UnsupportedExerciseTextGenerationProviderError(resolved.provider_key)


@dataclass(frozen=True)
class GoogleExerciseTextTTSProvider:
    api_url: str = DEFAULT_GOOGLE_TTS_API_URL
    provider_key: str = "google_tts"

    def synthesize(self, request: ExerciseTextTTSRequest) -> ExerciseTextTTSResult:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                self.api_url,
                params={"key": resolve_google_tts_api_key()},
                json={
                    "input": {"text": request.text},
                    "voice": {
                        "languageCode": request.language_code,
                        "name": request.voice_code,
                    },
                    "audioConfig": {
                        "audioEncoding": "MP3",
                        "speakingRate": 0.95,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        audio_content = payload.get("audioContent")
        if not isinstance(audio_content, str) or not audio_content.strip():
            raise RuntimeError("Missing audioContent in Google TTS response")
        return ExerciseTextTTSResult(audio_bytes=base64.b64decode(audio_content), timestamps=[])


def build_exercise_text_tts_provider(*, configured: dict[str, Any] | None) -> ExerciseTextTTSProvider:
    task = get_provider_task(EXERCISE_TEXT_TTS_TASK_KEY)
    resolved = resolve_provider_task_setting(task, configured=configured)
    if not resolved.is_enabled:
        raise ExerciseTextTTSProviderDisabledError("Exercise text TTS provider is disabled")
    if resolved.provider_key == "google_tts":
        return GoogleExerciseTextTTSProvider()
    raise UnsupportedExerciseTextTTSProviderError(resolved.provider_key)


def _extract_openai_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
    output = response_json.get("output")
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict):
                for content in item.get("content") or []:
                    if isinstance(content, dict) and isinstance(content.get("text"), str):
                        return content["text"]
    raise ValueError("OpenAI response does not contain JSON text")
