from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.domain.provider_settings import (
    DEFAULT_OPENAI_API_URL,
    DEFAULT_USER_IMPORT_OPENAI_MODEL,
)
from app.storage.user_import_artifacts import UserImportArtifactStorageProvider
from app.user_import.provider_ports import WordDetailsProvider


class UserImportCollectingResolver:
    def __init__(
        self,
        settings: Any,
        *,
        resolve_pending_import_word: Callable[..., Any],
        artifact_storage_provider: UserImportArtifactStorageProvider,
        build_word_details_provider: Callable[[Any], WordDetailsProvider | None],
        language_level_id_by_title: Callable[[], dict[str, int]] | None = None,
    ) -> None:
        self.settings = settings
        self.resolve_pending_import_word = resolve_pending_import_word
        self.artifact_storage_provider = artifact_storage_provider
        self.build_word_details_provider = build_word_details_provider
        self.language_level_id_by_title = language_level_id_by_title or (lambda: {})

    def resolve(
        self,
        *,
        lookup_word: str,
        telegram_user_id: int,
        current_time: datetime,
        part_of_speech: str | None = None,
        translation_uk: str | None = None,
        translation_ru: str | None = None,
        translation_pl: str | None = None,
        details_retry_feedback: str | None = None,
    ) -> Any:
        return self.resolve_pending_import_word(
            lookup_word=lookup_word,
            telegram_user_id=telegram_user_id,
            artifact_storage_provider=self.artifact_storage_provider,
            current_time=current_time,
            openai_refine_enabled=bool(getattr(self.settings, "app_user_import_openai_refine_enabled", True)),
            openai_model=str(getattr(self.settings, "app_user_import_openai_model", DEFAULT_USER_IMPORT_OPENAI_MODEL)),
            openai_api_url=str(getattr(self.settings, "app_user_import_openai_api_url", DEFAULT_OPENAI_API_URL)),
            language_level_id_by_title=self.language_level_id_by_title(),
            part_of_speech=part_of_speech,
            translation_uk=translation_uk,
            translation_ru=translation_ru,
            translation_pl=translation_pl,
            details_retry_feedback=details_retry_feedback,
            word_details_provider=self.build_word_details_provider(self.settings),
        )
