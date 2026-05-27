from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import httpx

from app.helpers.external_error_text import sanitize_external_error_text
from app.helpers.tts_text import build_tts_spoken_text
from app.helpers.user_import_storage import build_user_import_audio_relative_path
from app.storage.audio import AudioStorageProvider

DEFAULT_GOOGLE_TTS_API_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


def resolve_google_tts_api_key() -> str:
    value = os.environ.get("GOOGLE_TTS__API_KEY", "").strip()
    if not value:
        raise RuntimeError("GOOGLE_TTS__API_KEY is not configured.")
    return value


def _format_google_tts_error(error: Exception, *, fallback: str) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code if error.response is not None else "unknown"
        return f"{fallback} (HTTP {status_code})"
    if isinstance(error, httpx.RequestError):
        return f"{fallback} (request error)"
    return sanitize_external_error_text(str(error)) or fallback


def synthesize_google_tts(
    *,
    client: httpx.Client,
    text: str,
    language_code: str,
    voice_name: str,
) -> bytes:
    payload = {
        "input": {"text": build_tts_spoken_text(text)},
        "voice": {
            "languageCode": language_code,
            "name": voice_name,
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 0.95,
        },
    }
    response = client.post(
        DEFAULT_GOOGLE_TTS_API_URL,
        params={"key": resolve_google_tts_api_key()},
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    audio_content = data.get("audioContent")
    if not isinstance(audio_content, str) or not audio_content.strip():
        raise RuntimeError(f"Missing audioContent in Google TTS response for word: {text}")
    return base64.b64decode(audio_content)


def ensure_user_import_audio(
    *,
    lookup_word: str,
    audio_dir: Path,
    language_code: str,
    voice_name: str,
    client: httpx.Client | None = None,
    audio_storage_provider: AudioStorageProvider,
) -> tuple[str | None, dict[str, Any], str | None]:
    local_audio_relative_path = build_user_import_audio_relative_path(audio_dir, lookup_word)
    if audio_storage_provider.exists(local_audio_relative_path):
        return local_audio_relative_path, {"status": "ok", "cached": True}, None

    owns_client = client is None
    request_client = client or httpx.Client(timeout=30.0, follow_redirects=True)
    try:
        audio_bytes = synthesize_google_tts(
            client=request_client,
            text=lookup_word,
            language_code=language_code,
            voice_name=voice_name,
        )
        audio_storage_provider.write_bytes_atomic(local_audio_relative_path, audio_bytes)
        return local_audio_relative_path, {"status": "ok", "cached": False}, None
    except Exception as error:
        audio_error = _format_google_tts_error(error, fallback="Google TTS failed")
        return None, {"status": "error", "error": audio_error}, audio_error
    finally:
        if owns_client:
            request_client.close()
