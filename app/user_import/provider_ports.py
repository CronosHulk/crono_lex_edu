from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from app.domain.user_import.text_parser import ParsedImportWord
from app.validators.user_import_provider_results import AIImportValidationResult


class WordDetailsProvider(Protocol):
    provider_name: str

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
        ...


class WordAudioProvider(Protocol):
    provider_name: str

    def build_audio(
        self,
        *,
        lookup_word: str,
        audio_dir: Path,
    ) -> tuple[str | None, dict[str, Any], str | None]:
        ...


class WordValidationProvider(Protocol):
    provider_name: str

    def validate(
        self,
        candidates: list[ParsedImportWord],
    ) -> AIImportValidationResult:
        ...


class WordValidationProviderError(Exception):
    def __init__(self, original_error: Exception) -> None:
        super().__init__(str(original_error))
        self.original_error = original_error
