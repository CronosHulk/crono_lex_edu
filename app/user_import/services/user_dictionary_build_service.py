from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.domain.user_dictionary.constants import (
    USER_DICTIONARY_AUDIO_FAILED,
    USER_DICTIONARY_DETAILS_FAILED,
    USER_DICTIONARY_EMBEDDING_FAILED,
    USER_DICTIONARY_QUEUED_AUDIO,
    USER_DICTIONARY_QUEUED_DETAILS,
    USER_DICTIONARY_QUEUED_EMBEDDING,
    USER_DICTIONARY_READY,
)
from app.helpers.retry import (
    DEFAULT_RETRY_DELAY_SECONDS,
    normalize_retry_attempts,
)
from app.storage.audio import AudioStorageProvider
from app.user_import.providers import read_user_import_provider_task_setting
from app.user_import.runtime_settings import read_user_import_runtime_settings
from app.user_import.services.error_logging import log_user_import_pipeline_error
from app.user_import.services.user_dictionary_audio_build_service import (
    UserDictionaryAudioBuildService,
)
from app.user_import.services.user_dictionary_build_logging import UserDictionaryBuildLogger
from app.user_import.services.user_dictionary_details_build_service import (
    UserDictionaryDetailsBuildService,
)
from app.user_import.services.user_dictionary_embedding_build_service import (
    UserDictionaryEmbeddingBuildService,
)

DETAILS_BUILD_BATCH_SIZE = 100


class _UserImportSettingsPort(Protocol):
    app_user_import_test_mode: bool
    app_user_import_google_tts_language_code: str
    app_user_import_google_tts_voice_name: str
    app_user_import_embeddings_model: str
    app_user_import_embeddings_device: str


class _UserDictionaryRepositoryPort(Protocol):
    def list_entries_by_status(self, status: str, *, limit: int) -> list[dict[str, Any]]: ...

    def update_entry_status(self, entry_id: int, **kwargs: Any) -> dict[str, Any] | None: ...

    def update_entry_details(self, entry_id: int, **kwargs: Any) -> dict[str, Any] | None: ...

    def update_entry_audio(self, entry_id: int, **kwargs: Any) -> dict[str, Any] | None: ...

    def update_entry_embedding(self, entry_id: int, **kwargs: Any) -> dict[str, Any] | None: ...

    def mark_assignments_available_for_entry(
        self, entry_id: int, *, current_time: datetime
    ) -> int: ...


class _UserImportItemsRepositoryPort(Protocol):
    def list_by_user_dictionary_entry(self, entry_id: int) -> list[dict[str, Any]]: ...

    def sync_for_user_dictionary_entry(
        self,
        entry_id: int,
        *,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None: ...


class _UserDictionaryBuildDbPort(Protocol):
    settings: _UserImportSettingsPort
    user_dictionary: _UserDictionaryRepositoryPort
    user_import_items: _UserImportItemsRepositoryPort


class UserDictionaryBuildService:
    def __init__(
        self,
        db: _UserDictionaryBuildDbPort,
        *,
        audio_storage_provider: AudioStorageProvider,
        user_audio_root: Path | str,
        resolver: Any,
        audio_builder: Callable[..., tuple[str | None, dict[str, Any], str | None]],
        embedding_builder: Callable[..., tuple[list[float] | None, dict[str, Any], str | None]],
        error_masker: Callable[[str | None, str], str],
        max_jobs_per_run: int,
        details_batch_size: int = DETAILS_BUILD_BATCH_SIZE,
        retry_attempts: int = 3,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        retry_sleep_func: Callable[[float], None] = time.sleep,
    ) -> None:
        self.db = db
        self.audio_storage_provider = audio_storage_provider
        self.user_audio_root = user_audio_root
        self.resolver = resolver
        self.audio_builder = audio_builder
        self.embedding_builder = embedding_builder
        self.error_masker = error_masker
        self.max_jobs_per_run = max_jobs_per_run
        self.details_batch_size = max(int(details_batch_size), 1)
        self.retry_attempts = normalize_retry_attempts(retry_attempts)
        self.retry_delay_seconds = retry_delay_seconds
        self.retry_sleep_func = retry_sleep_func

        user_dictionary = db.user_dictionary
        user_import_items = db.user_import_items

        def log_pipeline_error(**kwargs: Any) -> None:
            log_user_import_pipeline_error(self.db, **kwargs)

        self._logger = UserDictionaryBuildLogger(
            user_import_items=user_import_items,
            log_pipeline_error=log_pipeline_error,
        )
        self._details_builder = UserDictionaryDetailsBuildService(
            user_dictionary=user_dictionary,
            user_import_items=user_import_items,
            audio_storage_provider=audio_storage_provider,
            user_audio_root=user_audio_root,
            resolver=resolver,
            error_masker=error_masker,
            retry_attempts=self.retry_attempts,
            retry_delay_seconds=retry_delay_seconds,
            retry_sleep_func=retry_sleep_func,
            logger=self._logger,
        )
        self._audio_builder = UserDictionaryAudioBuildService(
            settings=db.settings,
            user_dictionary=user_dictionary,
            user_import_items=user_import_items,
            user_audio_root=user_audio_root,
            audio_builder=audio_builder,
            error_masker=error_masker,
            retry_attempts=self.retry_attempts,
            retry_delay_seconds=retry_delay_seconds,
            retry_sleep_func=retry_sleep_func,
            logger=self._logger,
        )
        self._embedding_builder = UserDictionaryEmbeddingBuildService(
            settings=db.settings,
            user_dictionary=user_dictionary,
            user_import_items=user_import_items,
            read_provider_task_setting=lambda task_key: read_user_import_provider_task_setting(
                self.db,
                task_key,
            ),
            embedding_builder=embedding_builder,
            retry_attempts=self.retry_attempts,
            retry_delay_seconds=retry_delay_seconds,
            retry_sleep_func=retry_sleep_func,
            logger=self._logger,
        )

    def should_run_details_phase(self, current_time: datetime) -> bool:
        if bool(getattr(self.db.settings, "app_user_import_test_mode", False)):
            return True
        runtime_settings = read_user_import_runtime_settings(self.db)
        attribute_weekdays = runtime_settings.get("attribute_build_weekdays")
        if isinstance(attribute_weekdays, list) and current_time.weekday() not in set(
            attribute_weekdays
        ):
            return False
        return current_time.hour == int(runtime_settings["attribute_build_hour"])

    def should_run_audio_phase(self, current_time: datetime) -> bool:
        if bool(getattr(self.db.settings, "app_user_import_test_mode", False)):
            return True
        runtime_settings = read_user_import_runtime_settings(self.db)
        audio_weekdays = runtime_settings.get("audio_build_weekdays")
        if isinstance(audio_weekdays, list) and current_time.weekday() not in set(
            audio_weekdays
        ):
            return False
        return current_time.hour == int(runtime_settings["audio_build_hour"])

    def process_due_details_builds(
        self,
        *,
        current_time: datetime,
        force: bool = False,
    ) -> dict[str, int]:
        if not force and not self.should_run_details_phase(current_time):
            return {"queued_for_audio_count": 0, "details_failed_count": 0}
        queued_for_audio_count = 0
        details_failed_count = 0
        while True:
            entries = self.db.user_dictionary.list_entries_by_status(
                USER_DICTIONARY_QUEUED_DETAILS,
                limit=self.details_batch_size,
            )
            if not entries:
                break
            for entry in entries:
                try:
                    status = self.build_entry_details(
                        entry,
                        current_time=current_time,
                    )
                except Exception as error:
                    status = self._details_builder.mark_failed_after_unhandled_error(
                        entry,
                        error=error,
                        current_time=current_time,
                    )
                if status == USER_DICTIONARY_QUEUED_AUDIO:
                    queued_for_audio_count += 1
                elif status == USER_DICTIONARY_DETAILS_FAILED:
                    details_failed_count += 1
        return {
            "queued_for_audio_count": queued_for_audio_count,
            "details_failed_count": details_failed_count,
        }

    def build_entry_details(
        self,
        entry: dict[str, Any],
        *,
        current_time: datetime,
    ) -> str:
        return self._details_builder.build_entry_details(
            entry,
            current_time=current_time,
        )

    def process_due_audio_builds(
        self, *, current_time: datetime, force: bool = False
    ) -> dict[str, int]:
        if not force and not self.should_run_audio_phase(current_time):
            return {
                "ready_for_rotation_count": 0,
                "queued_for_embedding_count": 0,
                "audio_failed_count": 0,
            }
        ready_count = 0
        queued_for_embedding_count = 0
        audio_failed_count = 0
        while True:
            entries = self.db.user_dictionary.list_entries_by_status(
                USER_DICTIONARY_QUEUED_AUDIO,
                limit=self.max_jobs_per_run,
            )
            if not entries:
                break
            for entry in entries:
                status = self.build_entry_audio(entry, current_time=current_time)
                if status == USER_DICTIONARY_READY:
                    ready_count += 1
                elif status == USER_DICTIONARY_QUEUED_EMBEDDING:
                    queued_for_embedding_count += 1
                elif status == USER_DICTIONARY_AUDIO_FAILED:
                    audio_failed_count += 1
        return {
            "ready_for_rotation_count": ready_count,
            "queued_for_embedding_count": queued_for_embedding_count,
            "audio_failed_count": audio_failed_count,
        }

    def build_entry_audio(self, entry: dict[str, Any], *, current_time: datetime) -> str:
        return self._audio_builder.build_entry_audio(
            entry,
            current_time=current_time,
        )

    def process_due_embedding_builds(
        self, *, current_time: datetime, force: bool = False
    ) -> dict[str, int]:
        runtime_settings = read_user_import_runtime_settings(self.db)
        if not force and not bool(runtime_settings["embedding_build_enabled"]):
            return {
                "ready_for_rotation_count": 0,
                "retry_scheduled_count": 0,
                "embedding_failed_count": 0,
            }
        ready_count = 0
        failed_count = 0
        while True:
            entries = self.db.user_dictionary.list_entries_by_status(
                USER_DICTIONARY_QUEUED_EMBEDDING,
                limit=self.max_jobs_per_run,
            )
            if not entries:
                break
            for entry in entries:
                status = self.build_entry_embedding(entry, current_time=current_time)
                if status == USER_DICTIONARY_READY:
                    ready_count += 1
                elif status == USER_DICTIONARY_EMBEDDING_FAILED:
                    failed_count += 1
                else:
                    failed_count += 1
        return {
            "ready_for_rotation_count": ready_count,
            "retry_scheduled_count": 0,
            "embedding_failed_count": failed_count,
        }

    def build_entry_embedding(self, entry: dict[str, Any], *, current_time: datetime) -> str:
        return self._embedding_builder.build_entry_embedding(entry, current_time=current_time)
