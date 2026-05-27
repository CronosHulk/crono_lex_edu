from __future__ import annotations

import re
from dataclasses import dataclass

NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")
WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


@dataclass(frozen=True, slots=True)
class GeneratedWordDetails:
    source_ref: str
    word: str
    usage_form: str
    examples: list[str]
    part_of_speech: str | None = None
    phonetic_us: str | None = None
    translation_uk: str | None = None
    translation_ru: str | None = None
    translation_pl: str | None = None


@dataclass(frozen=True, slots=True)
class GeneratedWordValidationRules:
    expected_example_count: int
    min_example_words: int
    max_example_words: int
    require_gap_support: bool = True
    require_part_of_speech: bool = False
    require_phonetic_us: bool = False
    require_translations: bool = False
    max_translation_length: int = 120


def has_non_ascii_characters(value: str) -> bool:
    return bool(NON_ASCII_RE.search(value))


def validate_ascii_word_form(value: str, *, field_name: str, source_ref: str) -> str:
    candidate = " ".join(value.split()).strip()
    if not candidate:
        raise ValueError(f"{source_ref}: empty {field_name}")
    if has_non_ascii_characters(candidate):
        raise ValueError(f"{source_ref}: non-ascii {field_name}")
    return candidate


def validate_translation_text(value: str | None, *, field_name: str, source_ref: str, max_length: int = 120) -> str:
    candidate = " ".join(str(value or "").strip().split())
    if not candidate:
        raise ValueError(f"{source_ref}: empty {field_name}")
    if len(candidate) > max_length:
        raise ValueError(f"{source_ref}: {field_name} too long")
    return candidate


def usage_form_for_word(word: str, pos: str) -> str:
    candidate = " ".join(word.strip().split())
    if pos in {"verb", "phrasal verb"} and candidate.lower().startswith("to "):
        return candidate[3:].strip()
    return candidate


def normalize_sentence(value: str) -> str:
    return " ".join(value.strip().split())


def count_words(value: str) -> int:
    return len(WORD_TOKEN_RE.findall(value))


def supports_gap_example(word: str, example: str) -> bool:
    from app.application.client_learning.content import build_fill_in_gap_example

    gap_output = build_fill_in_gap_example(word, [example])
    return "_____" in gap_output


def validate_generated_word_details(
    details: GeneratedWordDetails,
    *,
    rules: GeneratedWordValidationRules,
) -> GeneratedWordDetails:
    source_ref = details.source_ref.strip() or "<generated>"
    word = validate_ascii_word_form(details.word, field_name="word", source_ref=source_ref)
    usage_form = validate_ascii_word_form(details.usage_form, field_name="usage_form", source_ref=source_ref)

    part_of_speech = details.part_of_speech.strip() if details.part_of_speech else None
    if rules.require_part_of_speech and not part_of_speech:
        raise ValueError(f"{source_ref}: empty part_of_speech")

    phonetic_us = details.phonetic_us.strip() if details.phonetic_us else None
    if rules.require_phonetic_us and not phonetic_us:
        raise ValueError(f"{source_ref}: empty phonetic_us")

    translation_uk = details.translation_uk
    translation_ru = details.translation_ru
    translation_pl = details.translation_pl
    if rules.require_translations:
        translation_uk = validate_translation_text(
            translation_uk,
            field_name="translation_uk",
            source_ref=source_ref,
            max_length=rules.max_translation_length,
        )
        translation_ru = validate_translation_text(
            translation_ru,
            field_name="translation_ru",
            source_ref=source_ref,
            max_length=rules.max_translation_length,
        )
        translation_pl = validate_translation_text(
            translation_pl,
            field_name="translation_pl",
            source_ref=source_ref,
            max_length=rules.max_translation_length,
        )

    examples = list(details.examples)
    if len(examples) != rules.expected_example_count:
        raise ValueError(f"{source_ref}: expected {rules.expected_example_count} examples, got {len(examples)}")

    normalized_examples: list[str] = []
    seen_examples: set[str] = set()
    for raw_example in examples:
        candidate = normalize_sentence(raw_example)
        if not candidate:
            raise ValueError(f"{source_ref}: empty example")
        if has_non_ascii_characters(candidate):
            raise ValueError(f"{source_ref}: non-ascii example")
        if candidate in seen_examples:
            raise ValueError(f"{source_ref}: duplicate examples")
        word_count = count_words(candidate)
        if word_count < rules.min_example_words or word_count > rules.max_example_words:
            raise ValueError(f"{source_ref}: word count {word_count} out of range")
        if rules.require_gap_support and not supports_gap_example(usage_form, candidate):
            raise ValueError(f"{source_ref}: gap builder could not blank usage form")
        if not re.search(r"[.!?]$", candidate):
            raise ValueError(f"{source_ref}: missing sentence punctuation")
        seen_examples.add(candidate)
        normalized_examples.append(candidate)

    return GeneratedWordDetails(
        source_ref=source_ref,
        word=word,
        usage_form=usage_form,
        examples=normalized_examples,
        part_of_speech=part_of_speech,
        phonetic_us=phonetic_us,
        translation_uk=translation_uk,
        translation_ru=translation_ru,
        translation_pl=translation_pl,
    )
