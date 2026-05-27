from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.domain.provider_settings import DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL
from app.domain.user_dictionary.constants import (
    USER_DICTIONARY_EMBEDDING_FAILED,
    USER_DICTIONARY_READY,
)
from app.helpers.retry import sleep_before_retry
from app.user_import.providers import (
    WORD_EMBEDDINGS_TASK_KEY,
    resolve_word_embedding_provider_setting,
)
from app.user_import.services.user_dictionary_build_logging import UserDictionaryBuildLogger

_ProviderTaskSettingReader = Callable[[str], dict[str, Any] | None]


class _UserImportEmbeddingSettingsPort(Protocol):
    app_user_import_embeddings_model: str
    app_user_import_embeddings_device: str


class _UserDictionaryEmbeddingRepositoryPort(Protocol):
    def update_entry_embedding(
        self,
        entry_id: int,
        *,
        embedding: list[float] | None,
        embedding_model: str | None,
        is_embedding_ready: bool,
        source_provider_status_json: dict[str, Any],
        status: str,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...

    def mark_assignments_available_for_entry(
        self, entry_id: int, *, current_time: datetime
    ) -> int: ...


class _UserImportItemsSyncRepositoryPort(Protocol):
    def sync_for_user_dictionary_entry(
        self,
        entry_id: int,
        *,
        status: str,
        error_text: str | None,
        current_time: datetime,
    ) -> None: ...


class UserDictionaryEmbeddingBuildService:
    def __init__(
        self,
        *,
        settings: _UserImportEmbeddingSettingsPort,
        user_dictionary: _UserDictionaryEmbeddingRepositoryPort,
        user_import_items: _UserImportItemsSyncRepositoryPort,
        read_provider_task_setting: _ProviderTaskSettingReader,
        embedding_builder: Callable[..., tuple[list[float] | None, dict[str, Any], str | None]],
        retry_attempts: int,
        retry_delay_seconds: float,
        retry_sleep_func: Callable[[float], None],
        logger: UserDictionaryBuildLogger,
    ) -> None:
        self.settings = settings
        self.user_dictionary = user_dictionary
        self.user_import_items = user_import_items
        self.read_provider_task_setting = read_provider_task_setting
        self.embedding_builder = embedding_builder
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.retry_sleep_func = retry_sleep_func
        self.logger = logger

    def build_entry_embedding(self, entry: dict[str, Any], *, current_time: datetime) -> str:
        embedding = None
        embedding_status: dict[str, Any] = {}
        embedding_error = None
        attempt_count = 0
        provider_setting = self._embedding_provider_setting()
        if not provider_setting.is_enabled:
            embedding_error = "Embedding provider is disabled"
            provider_status = dict(entry.get("source_provider_status_json") or {})
            provider_status["embedding_phase"] = {
                "status": "error",
                "error_type": "ProviderDisabled",
                "last_error": embedding_error,
                "attempt_count": 0,
            }
            self.logger.log_pipeline_error(
                entry,
                stage="embedding",
                error_text=embedding_error,
                attempt_count=0,
                current_time=current_time,
                task_key=WORD_EMBEDDINGS_TASK_KEY,
                provider_key=provider_setting.provider_key,
            )
            self.user_dictionary.update_entry_embedding(
                int(entry["id"]),
                embedding=None,
                embedding_model=entry.get("embedding_model"),
                is_embedding_ready=False,
                source_provider_status_json=provider_status,
                status=USER_DICTIONARY_EMBEDDING_FAILED,
                current_time=current_time,
            )
            self.user_import_items.sync_for_user_dictionary_entry(
                int(entry["id"]),
                status="embedding_failed",
                error_text=embedding_error,
                current_time=current_time,
            )
            return USER_DICTIONARY_EMBEDDING_FAILED
        embedding_model = str(
            provider_setting.config.get("model")
            or getattr(
                self.settings,
                "app_user_import_embeddings_model",
                DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
            )
        )
        embedding_device = str(
            provider_setting.config.get("device")
            or getattr(self.settings, "app_user_import_embeddings_device", "cpu")
        )
        for attempt_index in range(self.retry_attempts):
            attempt_count = attempt_index + 1
            try:
                embedding, embedding_status, embedding_error = self.embedding_builder(
                    word=str(entry["word"]),
                    translation_uk=entry.get("translation_uk"),
                    part_of_speech=entry.get("part_of_speech"),
                    examples_json=entry.get("examples_json") or [],
                    model_name=embedding_model,
                    device=embedding_device,
                )
            except Exception as error:
                embedding_error = str(error)
                embedding_status = {"status": "error", "error_type": type(error).__name__}
                sleep_before_retry(
                    attempt_index=attempt_index,
                    attempts=self.retry_attempts,
                    delay_seconds=self.retry_delay_seconds,
                    sleep_func=self.retry_sleep_func,
                )
                continue
            if embedding is not None:
                break
            sleep_before_retry(
                attempt_index=attempt_index,
                attempts=self.retry_attempts,
                delay_seconds=self.retry_delay_seconds,
                sleep_func=self.retry_sleep_func,
            )
        provider_status = dict(entry.get("source_provider_status_json") or {})
        provider_status["embedding_phase"] = {
            **embedding_status,
            "last_error": None if embedding is not None else embedding_error,
            "attempt_count": attempt_count,
        }
        if embedding is None:
            self.logger.log_pipeline_error(
                entry,
                stage="embedding",
                error_text=embedding_error,
                attempt_count=attempt_count,
                current_time=current_time,
                task_key=WORD_EMBEDDINGS_TASK_KEY,
                provider_key=provider_setting.provider_key,
                context_json={"embedding_model": embedding_model, "embedding_device": embedding_device},
            )
            self.user_dictionary.update_entry_embedding(
                int(entry["id"]),
                embedding=None,
                embedding_model=entry.get("embedding_model"),
                is_embedding_ready=False,
                source_provider_status_json=provider_status,
                status=USER_DICTIONARY_EMBEDDING_FAILED,
                current_time=current_time,
            )
            self.user_import_items.sync_for_user_dictionary_entry(
                int(entry["id"]),
                status="embedding_failed",
                error_text=embedding_error,
                current_time=current_time,
            )
            return USER_DICTIONARY_EMBEDDING_FAILED
        self.user_dictionary.update_entry_embedding(
            int(entry["id"]),
            embedding=embedding,
            embedding_model=embedding_status.get("model") or entry.get("embedding_model"),
            is_embedding_ready=True,
            source_provider_status_json=provider_status,
            status=USER_DICTIONARY_READY,
            current_time=current_time,
        )
        self._mark_ready(int(entry["id"]), current_time=current_time)
        return USER_DICTIONARY_READY

    def _mark_ready(self, entry_id: int, *, current_time: datetime) -> None:
        self.user_dictionary.mark_assignments_available_for_entry(
            entry_id, current_time=current_time
        )
        self.user_import_items.sync_for_user_dictionary_entry(
            entry_id,
            status="ready_for_rotation",
            error_text=None,
            current_time=current_time,
        )

    def _embedding_provider_setting(self):
        return resolve_word_embedding_provider_setting(
            self.settings,
            task_settings=self.read_provider_task_setting(WORD_EMBEDDINGS_TASK_KEY),
        )
