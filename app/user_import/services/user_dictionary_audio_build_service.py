from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.domain.user_dictionary.constants import (
    USER_DICTIONARY_AUDIO_FAILED,
    USER_DICTIONARY_QUEUED_EMBEDDING,
)
from app.helpers.retry import sleep_before_retry
from app.user_import.providers import WORD_AUDIO_TASK_KEY
from app.user_import.services.audio_paths import build_pos_audio_dir
from app.user_import.services.user_dictionary_build_logging import UserDictionaryBuildLogger


class _UserImportAudioSettingsPort(Protocol):
    app_user_import_google_tts_language_code: str
    app_user_import_google_tts_voice_name: str


class _UserDictionaryAudioRepositoryPort(Protocol):
    def update_entry_audio(
        self,
        entry_id: int,
        *,
        audio_path: str | None,
        source_provider_status_json: dict[str, Any],
        status: str,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...


class _UserImportItemsSyncRepositoryPort(Protocol):
    def sync_for_user_dictionary_entry(
        self,
        entry_id: int,
        *,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None: ...


class UserDictionaryAudioBuildService:
    def __init__(
        self,
        *,
        settings: _UserImportAudioSettingsPort,
        user_dictionary: _UserDictionaryAudioRepositoryPort,
        user_import_items: _UserImportItemsSyncRepositoryPort,
        user_audio_root: Path | str,
        audio_builder: Callable[..., tuple[str | None, dict[str, Any], str | None]],
        error_masker: Callable[[str | None, str], str],
        retry_attempts: int,
        retry_delay_seconds: float,
        retry_sleep_func: Callable[[float], None],
        logger: UserDictionaryBuildLogger,
    ) -> None:
        self.settings = settings
        self.user_dictionary = user_dictionary
        self.user_import_items = user_import_items
        self.user_audio_root = user_audio_root
        self.audio_builder = audio_builder
        self.error_masker = error_masker
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.retry_sleep_func = retry_sleep_func
        self.logger = logger

    def build_entry_audio(self, entry: dict[str, Any], *, current_time: datetime) -> str:
        generated_audio_path = None
        google_tts_status: dict[str, Any] = {}
        audio_error = None
        attempt_count = 0
        for attempt_index in range(self.retry_attempts):
            attempt_count = attempt_index + 1
            try:
                generated_audio_path, google_tts_status, audio_error = self.audio_builder(
                    lookup_word=str(entry["word"]),
                    audio_dir=build_pos_audio_dir(self.user_audio_root, entry),
                    language_code=str(
                        getattr(self.settings, "app_user_import_google_tts_language_code")
                    ),
                    voice_name=str(
                        getattr(self.settings, "app_user_import_google_tts_voice_name")
                    ),
                )
            except Exception as error:
                audio_error = str(error)
                google_tts_status = {"status": "error", "error_type": type(error).__name__}
                sleep_before_retry(
                    attempt_index=attempt_index,
                    attempts=self.retry_attempts,
                    delay_seconds=self.retry_delay_seconds,
                    sleep_func=self.retry_sleep_func,
                )
                continue
            if generated_audio_path is not None:
                break
            sleep_before_retry(
                attempt_index=attempt_index,
                attempts=self.retry_attempts,
                delay_seconds=self.retry_delay_seconds,
                sleep_func=self.retry_sleep_func,
            )
        provider_status = dict(entry.get("source_provider_status_json") or {})
        provider_status["google_tts"] = {**google_tts_status, "attempt_count": attempt_count}
        if generated_audio_path is None:
            error_text = self.error_masker(audio_error, "не вдалося отримати audio_path")
            self.logger.log_pipeline_error(
                entry,
                stage="audio",
                error_text=error_text,
                attempt_count=attempt_count,
                current_time=current_time,
                task_key=WORD_AUDIO_TASK_KEY,
                provider_key="google_tts",
            )
            self.user_dictionary.update_entry_audio(
                int(entry["id"]),
                audio_path=None,
                source_provider_status_json=provider_status,
                status=USER_DICTIONARY_AUDIO_FAILED,
                current_time=current_time,
            )
            self.user_import_items.sync_for_user_dictionary_entry(
                int(entry["id"]),
                status="audio_failed",
                error_text=error_text,
                current_time=current_time,
            )
            return USER_DICTIONARY_AUDIO_FAILED
        next_status = USER_DICTIONARY_QUEUED_EMBEDDING
        self.user_dictionary.update_entry_audio(
            int(entry["id"]),
            audio_path=generated_audio_path,
            source_provider_status_json=provider_status,
            status=next_status,
            current_time=current_time,
        )
        self.user_import_items.sync_for_user_dictionary_entry(
            int(entry["id"]),
            status="queued_for_embedding",
            error_text=None,
            current_time=current_time,
        )
        return next_status
