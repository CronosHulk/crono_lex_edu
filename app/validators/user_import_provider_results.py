from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.domain.user_import.text_parser import ParsedImportWord
from app.example_usage import contains_usage_form
from app.helpers.external_error_text import sanitize_external_error_text
from app.reference.dictionary_entries import normalize_dictionary_part_of_speech
from app.reference.service import LEVEL_ORDER
from app.word_validation import (
    GeneratedWordDetails,
    GeneratedWordValidationRules,
    validate_ascii_word_form,
    validate_generated_word_details,
)

USER_IMPORT_VALIDATION_RULES = GeneratedWordValidationRules(
    expected_example_count=3,
    min_example_words=6,
    max_example_words=14,
    require_part_of_speech=True,
    require_phonetic_us=True,
    require_translations=True,
)


@dataclass(frozen=True)
class AIValidatedImportWord:
    lookup_word: str
    part_of_speech: str | None = None
    translation_uk: str | None = None
    translation_ru: str | None = None
    translation_pl: str | None = None
    translation_hint: str | None = None


@dataclass(frozen=True)
class AIImportValidationResult:
    accepted_lookup_words: set[str]
    rejected_lookup_words: dict[str, str]
    provider_payload: dict[str, Any]
    accepted_items: dict[str, AIValidatedImportWord] = field(default_factory=dict)


def validate_user_import_openai_result(
    *,
    lookup_word: str,
    payload: dict[str, Any],
) -> tuple[str, str, str, str, str, str, list[str]]:
    normalized_lookup_word = validate_ascii_word_form(lookup_word, field_name="lookup_word", source_ref="lookup_word")
    level_title = str(payload.get("level") or "").strip().upper()
    if level_title not in LEVEL_ORDER:
        raise ValueError(f"level must be one of: {', '.join(LEVEL_ORDER)}")
    raw_examples = payload.get("examples")
    if not isinstance(raw_examples, list) or len(raw_examples) != 3:
        raise ValueError("examples must contain exactly three items")
    validated = validate_generated_word_details(
        GeneratedWordDetails(
            source_ref="lookup_word",
            word=normalized_lookup_word,
            usage_form=normalized_lookup_word,
            examples=[str(raw_example) for raw_example in raw_examples],
            part_of_speech=str(payload.get("part_of_speech") or ""),
            phonetic_us=str(payload.get("phonetic_us") or ""),
            translation_uk=str(payload.get("translation_uk") or ""),
            translation_ru=str(payload.get("translation_ru") or ""),
            translation_pl=str(payload.get("translation_pl") or ""),
        ),
        rules=USER_IMPORT_VALIDATION_RULES,
    )
    for index, example in enumerate(validated.examples):
        if not contains_usage_form(example, normalized_lookup_word):
            raise ValueError(f"example {index} does not contain lookup word")
    normalized_part_of_speech = normalize_dictionary_part_of_speech(validated.part_of_speech)
    return (
        normalized_part_of_speech,
        level_title,
        validated.phonetic_us or "",
        _normalize_translation_text(validated.translation_uk) or "",
        _normalize_translation_text(validated.translation_ru) or "",
        _normalize_translation_text(validated.translation_pl) or "",
        validated.examples,
    )


def validate_user_import_validation_result(
    *,
    candidates: list[ParsedImportWord],
    payload: dict[str, Any],
) -> tuple[set[str], dict[str, str], dict[str, AIValidatedImportWord]]:
    candidate_lookup_words = {item.lookup_word for item in candidates}
    candidate_by_lookup_word = {item.lookup_word: item for item in candidates}
    accepted_raw = payload.get("accepted")
    rejected_raw = payload.get("rejected")
    if not isinstance(accepted_raw, list) or not isinstance(rejected_raw, list):
        raise ValueError("validation response must contain accepted and rejected arrays")
    alias_lookup_words = _validation_response_alias_lookup_words(
        accepted_items_raw=payload.get("accepted_items"),
        candidate_lookup_words=candidate_lookup_words,
    )
    accepted = {
        _normalize_validation_response_lookup_word(
            validate_ascii_word_form(str(value), field_name="accepted", source_ref="accepted"),
            candidate_lookup_words=candidate_lookup_words,
            alias_lookup_words=alias_lookup_words,
        )
        for value in accepted_raw
        if str(value).strip()
    }
    rejected: dict[str, str] = {}
    for item in rejected_raw:
        if not isinstance(item, dict):
            raise ValueError("validation rejected item must be an object")
        lookup_word = _normalize_validation_response_lookup_word(
            validate_ascii_word_form(str(item.get("lookup_word") or ""), field_name="lookup_word", source_ref="lookup_word"),
            candidate_lookup_words=candidate_lookup_words,
            alias_lookup_words=alias_lookup_words,
        )
        reason = sanitize_external_error_text(str(item.get("reason") or "")) or "Rejected by import validation"
        rejected[lookup_word] = reason[:240]
    unknown = (accepted | set(rejected)) - candidate_lookup_words
    if unknown:
        raise ValueError("validation response contains unknown lookup words")
    accepted_items: dict[str, AIValidatedImportWord] = {
        lookup_word: AIValidatedImportWord(
            lookup_word=lookup_word,
            translation_hint=candidate_by_lookup_word[lookup_word].translation_hint,
        )
        for lookup_word in accepted
    }
    accepted_items_raw = payload.get("accepted_items")
    if accepted_items_raw is not None:
        if not isinstance(accepted_items_raw, list):
            raise ValueError("validation response accepted_items must be an array")
        for item in accepted_items_raw:
            if not isinstance(item, dict):
                raise ValueError("validation accepted item must be an object")
            lookup_word = validate_ascii_word_form(
                str(item.get("lookup_word") or ""),
                field_name="lookup_word",
                source_ref="lookup_word",
            )
            if lookup_word not in accepted:
                raise ValueError("validation accepted_items contains unknown lookup word")
            normalized_lookup_word = validate_ascii_word_form(
                str(item.get("normalized_lookup_word") or lookup_word),
                field_name="normalized_lookup_word",
                source_ref="normalized_lookup_word",
            ).lower()
            accepted_items[lookup_word] = AIValidatedImportWord(
                lookup_word=normalized_lookup_word,
                part_of_speech=_normalize_validation_part_of_speech(item.get("part_of_speech")),
                translation_uk=_normalize_translation_text(item.get("translation_uk")),
                translation_ru=_normalize_translation_text(item.get("translation_ru")),
                translation_pl=_normalize_translation_text(item.get("translation_pl")),
                translation_hint=candidate_by_lookup_word[lookup_word].translation_hint,
            )
    return accepted, rejected, accepted_items


def _validation_response_alias_lookup_words(
    *,
    accepted_items_raw: Any,
    candidate_lookup_words: set[str],
) -> dict[str, str]:
    if not isinstance(accepted_items_raw, list):
        return {}
    aliases: dict[str, str] = {}
    ambiguous_aliases: set[str] = set()
    for item in accepted_items_raw:
        if not isinstance(item, dict):
            continue
        try:
            lookup_word = validate_ascii_word_form(
                str(item.get("lookup_word") or ""),
                field_name="lookup_word",
                source_ref="lookup_word",
            )
            normalized_lookup_word = validate_ascii_word_form(
                str(item.get("normalized_lookup_word") or ""),
                field_name="normalized_lookup_word",
                source_ref="normalized_lookup_word",
            ).lower()
        except ValueError:
            continue
        if lookup_word not in candidate_lookup_words or normalized_lookup_word in candidate_lookup_words:
            continue
        if normalized_lookup_word in aliases and aliases[normalized_lookup_word] != lookup_word:
            ambiguous_aliases.add(normalized_lookup_word)
            continue
        aliases[normalized_lookup_word] = lookup_word
    for alias in ambiguous_aliases:
        aliases.pop(alias, None)
    return aliases


def _normalize_validation_response_lookup_word(
    lookup_word: str,
    *,
    candidate_lookup_words: set[str],
    alias_lookup_words: dict[str, str],
) -> str:
    if lookup_word in candidate_lookup_words:
        return lookup_word
    aliased_lookup_word = alias_lookup_words.get(lookup_word)
    if aliased_lookup_word is not None:
        return aliased_lookup_word
    return lookup_word


def _normalize_optional_validation_text(value: Any, *, max_length: int = 120) -> str | None:
    candidate = " ".join(str(value or "").strip().split())
    if not candidate:
        return None
    return candidate[:max_length]


def _normalize_translation_text(value: Any, *, max_length: int = 120) -> str | None:
    candidate = _normalize_optional_validation_text(value, max_length=max_length)
    if candidate is None:
        return None
    return re.sub(r"\s*;\s*", ", ", candidate)[:max_length]


def _normalize_validation_part_of_speech(value: Any) -> str | None:
    candidate = _normalize_optional_validation_text(value, max_length=80)
    if candidate is None:
        return None
    return normalize_dictionary_part_of_speech(candidate)
