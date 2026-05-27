from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.domain.provider_settings import WORD_AUDIO_TASK_KEY
from app.user_import.provider_ports import WordAudioProvider
from app.user_import.providers import (
    read_user_import_provider_task_setting,
)

BuildWordAudioProvider = Callable[[Any, dict[str, Any] | None], WordAudioProvider]


class _DisabledWordAudioProvider:
    provider_name = "disabled"

    def build_audio(
        self,
        *,
        lookup_word: str,
        audio_dir: Path,
    ) -> tuple[str | None, dict[str, Any], str | None]:
        error_text = "User import word audio provider is not configured"
        return None, {"status": "error", "error": error_text}, error_text


def _disabled_word_audio_provider(
    _settings: Any,
    _task_settings: dict[str, Any] | None = None,
) -> WordAudioProvider:
    return _DisabledWordAudioProvider()


class UserImportAudioBuilderService:
    def __init__(
        self,
        db: Any,
        *,
        build_audio_provider: BuildWordAudioProvider = _disabled_word_audio_provider,
    ) -> None:
        self.db = db
        self.build_audio_provider = build_audio_provider

    def build_audio(
        self,
        *,
        lookup_word: str,
        audio_dir: Path,
        **_: Any,
    ) -> tuple[str | None, dict[str, Any], str | None]:
        provider = self.build_audio_provider(
            self.db.settings,
            read_user_import_provider_task_setting(self.db, WORD_AUDIO_TASK_KEY),
        )
        return provider.build_audio(
            lookup_word=lookup_word,
            audio_dir=audio_dir,
        )
