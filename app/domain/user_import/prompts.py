from __future__ import annotations

import json

from app.domain.user_import.text_parser import ParsedImportWord
from app.reference.dictionary_entries import DICTIONARY_PART_OF_SPEECH_TYPES
from app.reference.service import LEVEL_ORDER


def build_user_import_openai_prompt(
    *,
    lookup_word: str,
    part_of_speech: str | None,
    translation_uk: str | None,
    translation_ru: str | None,
    translation_pl: str | None,
    phonetic_us: str | None,
    examples_json: list[str],
    details_retry_feedback: str | None = None,
) -> str:
    return "PROMPT"


def build_user_import_validation_prompt(candidates: list[ParsedImportWord]) -> str:
    return "PROMPT"

