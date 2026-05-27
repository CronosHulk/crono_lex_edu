from __future__ import annotations

import hashlib
import html
from typing import Any

from app.i18n import translate
from app.reference.labels import format_category_labels, format_part_of_speech_labels

CARD_CAPTION_MAX_LENGTH = 900
SECTION_SEPARATOR = "────────────"
PROGRESS_BAR_PADDING_SYMBOL = "⋯"
PROGRESS_BAR_ROW_SLOTS = 20
WORD_JOINER = "\u2060"
FIGURE_SPACE = "\u2007"


def escape_html_text(value: str) -> str:
    return html.escape(value, quote=False)


def build_quote_block(examples: list[str]) -> str:
    escaped_lines = [escape_html_text(example.strip()) for example in examples if example.strip()]
    if not escaped_lines:
        return ""
    content = "<br/>".join(escaped_lines)
    return f"<blockquote>{content}</blockquote>"


def pick_single_example(seed: str, examples: list[str]) -> list[str]:
    normalized = [example.strip() for example in examples if example.strip()]
    if not normalized:
        return []
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(normalized)
    return [normalized[index]]


def normalize_phonetic(phonetic: str | None) -> str:
    if not phonetic:
        return "—"
    stripped = phonetic.strip()
    if stripped.startswith("/") and stripped.endswith("/") and len(stripped) >= 2:
        return stripped[1:-1]
    return stripped


def build_card_caption(
    locale: str,
    word: str,
    parts_of_speech: list[str] | None,
    phonetic: str,
    translation: str,
    examples: list[str],
    categories: list[str] | None = None,
    progress_bar: str | None = None,
) -> str:
    word_line = f"<b>{html.escape(word)}</b>"
    part_of_speech_label = format_part_of_speech_labels(locale, parts_of_speech)
    if part_of_speech_label:
        word_line = f"{word_line} <i>({html.escape(part_of_speech_label)})</i>"
    base_lines = [
        word_line,
        f"[{html.escape(phonetic)}]",
        html.escape(translation),
    ]
    visible_lines = [line for line in base_lines if line]
    current_text = "\n".join(visible_lines)
    category_line = ""
    category_labels = format_category_labels(locale, categories)
    if category_labels:
        category_line = f"Категорії: {html.escape(category_labels)}"
    progress_bar_markup = build_progress_bar_markup(progress_bar) if progress_bar else ""
    selected_example = pick_single_example(f"card:{word}:{translation}", examples)
    if not selected_example:
        tail_lines = [line for line in [category_line, progress_bar_markup] if line]
        return "\n".join([current_text, *tail_lines]) if tail_lines else current_text

    candidate_lines = [*visible_lines, "", build_quote_block(selected_example)]
    if category_line:
        candidate_lines.append(category_line)
    if progress_bar_markup:
        candidate_lines.append(progress_bar_markup)
    candidate_text = "\n".join(candidate_lines)
    if len(candidate_text) <= CARD_CAPTION_MAX_LENGTH:
        return candidate_text
    tail_lines = [line for line in [category_line, progress_bar_markup] if line]
    return "\n".join([current_text, *tail_lines]) if tail_lines else current_text


def build_section_title(title: str) -> str:
    return f"<i>{html.escape(title)}</i>\n{SECTION_SEPARATOR}"


def build_progress_bar_markup(progress_bar: str) -> str:
    return html.escape(progress_bar).replace(" ", "\u00A0")


def build_quiz_prompt_text(
    value: str,
    *,
    progress_bar: str | None = None,
    center: bool = False,
    total_width: int = 22,
) -> str:
    candidate = value.strip()
    if not candidate:
        candidate = WORD_JOINER
    if center and len(candidate) <= total_width:
        padding = total_width - len(candidate)
        left_padding = FIGURE_SPACE * (padding // 2)
        right_padding = FIGURE_SPACE * (padding - (padding // 2))
        candidate = f"{left_padding}{candidate}{right_padding}"
    if progress_bar:
        lines = [build_progress_bar_markup(progress_bar), "", ""]
    else:
        lines = [WORD_JOINER, "", ""]
    lines.extend([f"<b>{html.escape(candidate)}</b>", "", "", WORD_JOINER])
    return "\n".join(lines)


def build_centered_quiz_prompt_text(value: str, total_width: int = 22) -> str:
    return build_quiz_prompt_text(value, center=True, total_width=total_width)


def prepend_progress_bar_to_prompt_text(prompt_text: str, *, progress_bar: str) -> str:
    return "\n".join([build_progress_bar_markup(progress_bar), "", "", prompt_text])


def build_card_hint_text_for_count(locale: str, selected_words_count: int) -> str:
    return "\n".join(
        [
            translate(locale, "card_hint_title"),
            translate(locale, "card_hint_known"),
        ]
    )


def build_card_auxiliary_text(
    locale: str,
    *,
    selected_words_count: int,
    progress_bar: str,
) -> str:
    return build_hint_with_progress_text(
        build_card_hint_text_for_count(locale, selected_words_count),
        progress_bar=progress_bar,
    )


def build_quiz_hint_text(locale: str, stage_title: str) -> str:
    return "\n".join(
        [
            translate(locale, "card_hint_title"),
            stage_title,
        ]
    )


def build_hint_with_progress_text(hint_text: str, *, progress_bar: str) -> str:
    return "\n".join(
        [
            hint_text,
            "",
            "",
            build_progress_bar_markup(progress_bar),
        ]
    )


def build_quiz_auxiliary_text(
    locale: str,
    *,
    stage_title: str,
    progress_bar: str,
    current_position: int,
    total_count: int,
    total_errors: int = 0,
    repeat_progress_current: int = 0,
    repeat_progress_total: int = 0,
) -> str:
    return build_quiz_hint_text(locale, stage_title)


def build_centered_progress_bar(
    symbols: list[str], total_slots: int | None = None, *, max_row_slots: int = PROGRESS_BAR_ROW_SLOTS
) -> str:
    normalized_total_slots = (
        total_slots
        if total_slots is not None
        else _default_progress_total_slots(len([symbol for symbol in symbols if symbol]))
    )
    normalized_total_slots = max(int(normalized_total_slots or 1), 1)
    normalized_max_row_slots = max(int(max_row_slots or 1), 1)
    normalized_symbols = [symbol for symbol in symbols if symbol][:normalized_total_slots]
    if not normalized_symbols:
        normalized_symbols = ["○"]
    rows: list[str] = []
    remaining_slots = normalized_total_slots
    offset = 0
    is_multiline = normalized_total_slots > normalized_max_row_slots
    while remaining_slots > 0:
        row_slots = min(remaining_slots, normalized_max_row_slots)
        row_symbols = normalized_symbols[offset : offset + row_slots]
        rows.append(
            _build_centered_progress_bar_row(
                row_symbols,
                row_slots,
                normalized_max_row_slots,
                use_full_width=is_multiline,
            )
        )
        offset += row_slots
        remaining_slots -= row_slots
    return "\n".join(rows)


def _build_centered_progress_bar_row(
    symbols: list[str], row_slots: int, max_row_slots: int, *, use_full_width: bool
) -> str:
    display_slots = max_row_slots if use_full_width and row_slots < max_row_slots else row_slots
    if len(symbols) >= display_slots:
        return f"[{''.join(symbols[:display_slots])}]"
    padding = display_slots - len(symbols)
    left_padding = padding // 2
    right_padding = padding - left_padding
    return (
        f"[{PROGRESS_BAR_PADDING_SYMBOL * left_padding}"
        f"{''.join(symbols)}"
        f"{PROGRESS_BAR_PADDING_SYMBOL * right_padding}]"
    )


def build_card_progress_bar(current_position: int, total_count: int, total_slots: int | None = None) -> str:
    normalized_total = max(int(total_count or 1), 1)
    normalized_total_slots = max(
        int(total_slots) if total_slots is not None else _default_progress_total_slots(normalized_total),
        1,
    )
    normalized_total = min(normalized_total, normalized_total_slots)
    normalized_position = min(max(current_position, 1), normalized_total)
    symbols = ["✓"] * (normalized_position - 1) + ["●"] + ["○"] * (normalized_total - normalized_position)
    return build_centered_progress_bar(symbols, total_slots=normalized_total_slots)


def build_quiz_progress_bar(
    queue: list[int],
    position: int,
    session_words_by_id: dict[int, dict[str, Any]],
    exercise_type: str,
    total_slots: int | None = None,
) -> str:
    unique_queue = list(dict.fromkeys(queue))
    normalized_total_slots = max(
        int(total_slots) if total_slots is not None else _default_progress_total_slots(len(unique_queue)),
        1,
    )
    if not unique_queue:
        return build_centered_progress_bar(["●"], total_slots=normalized_total_slots)

    clamped_position = min(max(position, 0), len(queue) - 1)
    current_session_word_id = queue[clamped_position]
    attempts_field = f"{exercise_type}_attempts"
    correct_field = f"{exercise_type}_correct"
    symbols: list[str] = []
    for session_word_id in unique_queue:
        if session_word_id == current_session_word_id:
            symbols.append("●")
            continue
        session_word = session_words_by_id.get(session_word_id) or {}
        attempts = int(session_word.get(attempts_field) or 0)
        is_correct = bool(session_word.get(correct_field))
        if is_correct:
            symbols.append("✓")
        elif attempts > 0:
            symbols.append("✗")
        else:
            symbols.append("○")
    return build_centered_progress_bar(symbols, total_slots=normalized_total_slots)


def _default_progress_total_slots(symbol_count: int) -> int:
    normalized_count = max(int(symbol_count or 1), 1)
    return normalized_count if normalized_count > PROGRESS_BAR_ROW_SLOTS else PROGRESS_BAR_ROW_SLOTS
