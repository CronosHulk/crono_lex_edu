from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.application.client_learning.display import (
    build_centered_quiz_prompt_text,
    escape_html_text,
)
from app.example_usage import find_usage_form_span
from app.i18n import translate
from app.reference.distractors import has_distractor_conflict


@dataclass(frozen=True)
class QuizPayload:
    exercise_type: str
    prompt_text: str
    correct_answer: str
    options: list[str]


def build_fill_in_gap_example(word: str, examples: list[str]) -> str:
    for example in examples:
        stripped = example.strip()
        if not stripped:
            continue
        span = find_usage_form_span(stripped, word)
        if span is None:
            continue
        start, end = span
        return escape_html_text(stripped[:start]) + "_____" + escape_html_text(stripped[end:])

    for example in examples:
        stripped = example.strip()
        if stripped:
            return escape_html_text(stripped)

    return "_____"


def split_translation_variants(translation: str | None) -> list[str]:
    if not translation:
        return []
    variants: list[str] = []
    for item in translation.split(","):
        candidate = item.strip()
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants


def resolve_translation_for_locale(locale: str, payload: dict[str, Any]) -> str:
    normalized_locale = locale.strip().lower() if locale else "uk"
    locale_chain = {
        "uk": ("translation_uk", "translation_ru", "translation_pl"),
        "ru": ("translation_ru", "translation_uk", "translation_pl"),
        "pl": ("translation_pl", "translation_uk", "translation_ru"),
    }.get(normalized_locale, ("translation_uk", "translation_ru", "translation_pl"))
    for field_name in locale_chain:
        value = str(payload.get(field_name) or "").strip()
        if value:
            return value
    return ""


def select_translation_variant(locale: str, payload: dict[str, Any], *, seed: str) -> str:
    translation = resolve_translation_for_locale(locale, payload)
    variants = split_translation_variants(translation)
    if not variants:
        return translation
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(variants)
    return variants[index]


def build_deterministic_options(
    seed: str,
    correct_value: str,
    distractors: list[str],
    *,
    max_options: int = 4,
) -> list[str]:
    candidates = [correct_value]
    for value in distractors:
        if value not in candidates:
            candidates.append(value)
        if len(candidates) == max(max_options, 1):
            break

    def sort_key(item: str) -> str:
        return hashlib.sha256(f"{seed}:{item}".encode()).hexdigest()

    return sorted(candidates, key=sort_key)


def filter_safe_distractors(source: dict[str, Any], distractors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in distractors
        if not has_distractor_conflict(source, row)
    ]


def build_marks(correct_count: int, total_count: int) -> str:
    return ("✓" * correct_count) + ("✗" * max(total_count - correct_count, 0))


def build_quiz_progress_title(
    locale: str,
    current_position: int,
    total_count: int,
    *,
    total_errors: int = 0,
    repeat_progress_current: int = 0,
    repeat_progress_total: int = 0,
) -> str:
    return translate(
        locale,
        "quiz_word_progress",
        current=current_position,
        total=total_count,
    )


def build_quiz_progress_counts(queue: list[int], position: int) -> tuple[int, int, int, int]:
    unique_queue = list(dict.fromkeys(queue))
    total_count = max(len(unique_queue), 1)
    if not queue:
        return 1, total_count, 0, 0
    clamped_position = min(max(position, 0), len(queue) - 1)
    current_session_word_id = queue[clamped_position]
    try:
        current_position = unique_queue.index(current_session_word_id) + 1
    except ValueError:  # pragma: no cover
        current_position = min(clamped_position + 1, total_count)
    repeat_index = max(sum(1 for value in queue[: clamped_position + 1] if value == current_session_word_id) - 1, 0)
    total_errors = max(len(queue) - len(unique_queue), 0)
    return current_position, total_count, repeat_index, total_errors


def build_quiz_button_row_widths(option_count: int) -> list[int]:
    if option_count == 3:
        return [1, 1, 1, 1]
    return [2, 2, 1]


def build_quiz_error_count(session_word: dict[str, Any], exercise_type: str, *, current_attempts: int | None = None) -> int:
    attempts_field = f"{exercise_type}_attempts"
    attempts = current_attempts if current_attempts is not None else int(session_word.get(attempts_field, 0))
    return max(attempts, 0)


def build_quiz_payload(
    *,
    stage: str,
    session_word: dict[str, Any],
    distractors: list[dict[str, Any]],
    locale: str,
    max_options: int | None = None,
) -> QuizPayload:
    safe_distractors = filter_safe_distractors(session_word, distractors)
    translation_seed = f"{stage}:{session_word['session_word_id']}:translation"
    resolved_translation = resolve_translation_for_locale(locale=locale, payload=session_word)
    selected_translation = select_translation_variant(
        locale=locale,
        payload=session_word,
        seed=translation_seed,
    )
    if stage == "quiz_en_uk":
        return QuizPayload(
            exercise_type="en_uk",
            prompt_text=session_word["word"],
            correct_answer=selected_translation,
            options=build_deterministic_options(
                seed=f"{stage}:{session_word['session_word_id']}",
                correct_value=selected_translation,
                distractors=[
                    select_translation_variant(
                        locale=locale,
                        payload=row,
                        seed=f"{stage}:{session_word['session_word_id']}:distractor:{index}",
                    )
                    for index, row in enumerate(safe_distractors)
                ],
                max_options=max_options or 3,
            ),
        )
    if stage == "quiz_uk_en":
        return QuizPayload(
            exercise_type="uk_en",
            prompt_text=selected_translation or resolved_translation,
            correct_answer=session_word["word"],
            options=build_deterministic_options(
                seed=f"{stage}:{session_word['session_word_id']}",
                correct_value=session_word["word"],
                distractors=[row["word"] for row in safe_distractors],
                max_options=max_options or 3,
            ),
        )
    return QuizPayload(
        exercise_type="gap",
        prompt_text=build_centered_quiz_prompt_text(
            build_fill_in_gap_example(session_word["word"], session_word["examples_json"] or [])
        ),
        correct_answer=session_word["word"],
        options=build_deterministic_options(
            seed=f"{stage}:{session_word['session_word_id']}",
            correct_value=session_word["word"],
            distractors=[row["word"] for row in safe_distractors],
            max_options=max_options or 4,
        ),
    )
