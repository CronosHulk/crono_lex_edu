from __future__ import annotations

import re
import unicodedata
from typing import Any

TRANSLATION_FIELDS = ("translation_uk", "translation_ru", "translation_pl")


def normalize_distractor_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(normalized.strip().split())


def split_distractor_translation_variants(value: str | None) -> set[str]:
    variants: set[str] = set()
    for item in re.split(r"[,;/\n]+", str(value or "")):
        candidate = normalize_distractor_text(item).strip(" .!?()[]{}\"'")
        if candidate:
            variants.add(candidate)
    return variants


def distractor_translation_variants(payload: dict[str, Any]) -> set[str]:
    variants: set[str] = set()
    for field_name in TRANSLATION_FIELDS:
        variants.update(split_distractor_translation_variants(payload.get(field_name)))
    return variants


def has_distractor_conflict(source: dict[str, Any], candidate: dict[str, Any]) -> bool:
    source_word = normalize_distractor_text(source.get("word"))
    candidate_word = normalize_distractor_text(candidate.get("word"))
    if source_word and source_word == candidate_word:
        return True

    source_translations = distractor_translation_variants(source)
    candidate_translations = distractor_translation_variants(candidate)
    return bool(source_translations & candidate_translations)
