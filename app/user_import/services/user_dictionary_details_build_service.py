from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.domain.user_dictionary.constants import (
    USER_DICTIONARY_DETAILS_FAILED,
    USER_DICTIONARY_QUEUED_AUDIO,
)
from app.helpers.retry import sleep_before_retry
from app.storage.audio import AudioStorageProvider
from app.user_import.providers import WORD_DETAILS_TASK_KEY
from app.user_import.services.user_dictionary_build_logging import UserDictionaryBuildLogger


class _UserDictionaryDetailsRepositoryPort(Protocol):
    def update_entry_status(
        self,
        entry_id: int,
        *,
        status: str,
        current_time: datetime,
        source_provider_status_json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...

    def update_entry_details(
        self,
        entry_id: int,
        *,
        audio_storage_provider: AudioStorageProvider,
        word: str,
        entry_type: str | None,
        part_of_speech: str,
        level_id: int | None,
        transcription: str | None,
        translation_uk: str | None,
        translation_ru: str | None,
        translation_pl: str | None,
        examples_json: list[str],
        source_provider_status_json: dict[str, Any],
        status: str,
        audio_roots: list[Path | str] | None = None,
        queue_audio_on_spelling_change: bool = True,
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


class UserDictionaryDetailsBuildService:
    def __init__(
        self,
        *,
        user_dictionary: _UserDictionaryDetailsRepositoryPort,
        user_import_items: _UserImportItemsSyncRepositoryPort,
        audio_storage_provider: AudioStorageProvider,
        user_audio_root: Path | str,
        resolver: Any,
        error_masker: Callable[[str | None, str], str],
        retry_attempts: int,
        retry_delay_seconds: float,
        retry_sleep_func: Callable[[float], None],
        logger: UserDictionaryBuildLogger,
    ) -> None:
        self.user_dictionary = user_dictionary
        self.user_import_items = user_import_items
        self.audio_storage_provider = audio_storage_provider
        self.user_audio_root = user_audio_root
        self.resolver = resolver
        self.error_masker = error_masker
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.retry_sleep_func = retry_sleep_func
        self.logger = logger

    def build_entry_details(
        self,
        entry: dict[str, Any],
        *,
        current_time: datetime,
    ) -> str:
        resolution = None
        validation_error = None
        provider_status: dict[str, Any] = {}
        error_text = None
        attempt_count = 0
        details_retry_feedback: str | None = None
        for attempt_index in range(self.retry_attempts):
            attempt_count = attempt_index + 1
            import_context = self.logger.entry_import_context(int(entry["id"]))
            try:
                resolution = self.resolver.resolve(
                    lookup_word=str(entry["word"]),
                    telegram_user_id=int(import_context.get("telegram_user_id") or 0),
                    current_time=current_time,
                    part_of_speech=entry.get("part_of_speech"),
                    translation_uk=entry.get("translation_uk"),
                    translation_ru=entry.get("translation_ru"),
                    translation_pl=entry.get("translation_pl"),
                    details_retry_feedback=details_retry_feedback,
                )
            except Exception as error:
                error_text = self.error_masker(str(error), "не вдалося отримати деталі слова")
                self.logger.log_pipeline_error(
                    entry,
                    stage="details",
                    error_text=error_text,
                    error=error,
                    attempt_count=attempt_count,
                    current_time=current_time,
                    import_context=import_context,
                    task_key=WORD_DETAILS_TASK_KEY,
                    provider_key=self.logger.provider_key_from_status(provider_status, "openai"),
                )
                sleep_before_retry(
                    attempt_index=attempt_index,
                    attempts=self.retry_attempts,
                    delay_seconds=self.retry_delay_seconds,
                    sleep_func=self.retry_sleep_func,
                )
                continue
            validation_error = self._details_validation_error(resolution)
            provider_status = dict(getattr(resolution, "source_provider_status_json", None) or {})
            if not validation_error:
                break
            error_text = validation_error
            details_retry_feedback = self._details_retry_feedback(
                lookup_word=str(entry.get("word") or ""),
                validation_error=validation_error,
            )
            sleep_before_retry(
                attempt_index=attempt_index,
                attempts=self.retry_attempts,
                delay_seconds=self.retry_delay_seconds,
                sleep_func=self.retry_sleep_func,
            )

        if resolution is None:
            provider_status = dict(entry.get("source_provider_status_json") or {})
            provider_status["details_phase"] = {
                "status": "error",
                "error": error_text or "не вдалося отримати деталі слова",
                "attempt_count": attempt_count,
                "last_attempted_at": current_time.isoformat(),
            }
            self.user_dictionary.update_entry_status(
                int(entry["id"]),
                status=USER_DICTIONARY_DETAILS_FAILED,
                source_provider_status_json=provider_status,
                current_time=current_time,
            )
            self.user_import_items.sync_for_user_dictionary_entry(
                int(entry["id"]),
                status="details_failed",
                error_text=provider_status["details_phase"]["error"],
                current_time=current_time,
            )
            return USER_DICTIONARY_DETAILS_FAILED

        next_status = (
            USER_DICTIONARY_DETAILS_FAILED if validation_error else USER_DICTIONARY_QUEUED_AUDIO
        )
        if validation_error:
            provider_status["details_validation"] = {
                "status": "error",
                "error": validation_error,
                "attempt_count": attempt_count,
            }
            self.logger.log_pipeline_error(
                entry,
                stage="details_validation",
                error_text=validation_error,
                attempt_count=attempt_count,
                current_time=current_time,
                task_key=WORD_DETAILS_TASK_KEY,
                provider_key=self.logger.provider_key_from_status(provider_status, "openai"),
            )
        else:
            provider_status["details_validation"] = {"status": "ok", "attempt_count": attempt_count}
        self.user_dictionary.update_entry_details(
            int(entry["id"]),
            word=str(resolution.word),
            entry_type=getattr(resolution, "entry_type", None),
            part_of_speech=str(resolution.part_of_speech or entry.get("part_of_speech") or ""),
            level_id=resolution.level_id,
            transcription=resolution.phonetic_us,
            translation_uk=resolution.translation_uk,
            translation_ru=getattr(resolution, "translation_ru", None),
            translation_pl=getattr(resolution, "translation_pl", None),
            examples_json=list(resolution.examples_json or []),
            source_provider_status_json=provider_status,
            status=next_status,
            audio_storage_provider=self.audio_storage_provider,
            audio_roots=[self.user_audio_root],
            queue_audio_on_spelling_change=False,
            current_time=current_time,
        )
        self.user_import_items.sync_for_user_dictionary_entry(
            int(entry["id"]),
            status="queued_for_audio"
            if next_status == USER_DICTIONARY_QUEUED_AUDIO
            else "details_failed",
            error_text=validation_error,
            current_time=current_time,
        )
        return next_status

    @staticmethod
    def _details_retry_feedback(*, lookup_word: str, validation_error: str) -> str:
        normalized_lookup_word = " ".join(str(lookup_word or "").split())
        base = f"Previous details response failed validation: {validation_error}."
        if "gap builder could not blank usage form" in validation_error and normalized_lookup_word:
            return (
                f'{base} Regenerate all examples so each sentence contains the exact lookup_word phrase '
                f'"{normalized_lookup_word}" contiguously and unchanged. Do not inflect, split, reorder, '
                "replace, or omit that phrase."
            )
        return f"{base} Return corrected JSON that satisfies all validation rules."

    def mark_failed_after_unhandled_error(
        self,
        entry: dict[str, Any],
        *,
        error: Exception,
        current_time: datetime,
    ) -> str:
        error_text = self.error_masker(str(error), "не вдалося отримати деталі слова")
        provider_status = dict(entry.get("source_provider_status_json") or {})
        provider_status["details_phase"] = {
            "status": "error",
            "error": error_text,
            "attempt_count": self.retry_attempts,
            "last_attempted_at": current_time.isoformat(),
        }
        try:
            self.logger.log_pipeline_error(
                entry,
                stage="details",
                error_text=error_text,
                error=error,
                attempt_count=self.retry_attempts,
                current_time=current_time,
                task_key=WORD_DETAILS_TASK_KEY,
                provider_key=self.logger.provider_key_from_status(provider_status, "openai"),
            )
        except Exception as log_error:
            self.logger.log_logging_failure(
                entry,
                stage="details",
                error=log_error,
                current_time=current_time,
            )
        self.user_dictionary.update_entry_status(
            int(entry["id"]),
            status=USER_DICTIONARY_DETAILS_FAILED,
            source_provider_status_json=provider_status,
            current_time=current_time,
        )
        self.user_import_items.sync_for_user_dictionary_entry(
            int(entry["id"]),
            status="details_failed",
            error_text=error_text,
            current_time=current_time,
        )
        return USER_DICTIONARY_DETAILS_FAILED

    @staticmethod
    def _details_validation_error(resolution: Any) -> str | None:
        if getattr(resolution, "rejected_reason", None):
            return str(resolution.rejected_reason)
        if not getattr(resolution, "translation_uk", None):
            return "не знайдено translation_uk"
        if not getattr(resolution, "part_of_speech", None):
            return "не знайдено part_of_speech"
        if getattr(resolution, "level_id", None) is None:
            return "не знайдено level_id"
        if not getattr(resolution, "phonetic_us", None):
            return "не знайдено phonetic_us"
        if not list(getattr(resolution, "examples_json", None) or []):
            return "не знайдено examples_json"
        return None
