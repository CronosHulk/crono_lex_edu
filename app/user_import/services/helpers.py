from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from app.i18n import translate
from app.plurals import format_import_item_count


def format_import_count_text(locale: str, count: int) -> str:
    return format_import_item_count(locale, count)


def normalize_nonempty_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            result.append(text)
    return result


def normalize_import_document_lines(values: list[str]) -> list[str]:
    lines: list[str] = []
    for value in values:
        candidate = " ".join(str(value).split()).strip()
        if not candidate:
            continue
        lines.append(candidate)
    return lines


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def format_numbered_import_item_list(locale: str, items: list[str], *, limit: int = 20) -> str:
    escaped = [html.escape(item) for item in items if item]
    if not escaped:
        return ""
    lines = [f"{index}. {item}" for index, item in enumerate(escaped[:limit], start=1)]
    if len(escaped) > limit:
        lines.append(
            translate(
                locale,
                "import_words_summary_more_suffix",
                count_text=format_import_item_count(locale, len(escaped) - limit),
            )
        )
    return "\n".join(lines)


def format_failed_import_item(item: dict[str, Any]) -> str:
    word = str(item.get("lookup_word") or "")
    error_text = str(item.get("error_text") or "").strip()
    if not error_text:
        return word
    return f"{word}\n{translate('uk', 'import_words_failed_item_reason')}"


def format_import_task_status(locale: str, status: str | None) -> str:
    normalized_status = str(status or "").strip().lower()
    if not normalized_status:
        return "-"
    translation_key = f"import_words_task_status_{normalized_status}"
    try:
        return translate(locale, translation_key)
    except KeyError:
        return normalized_status


def format_invalid_import_fragments(locale: str, fragments: list[str], *, limit: int = 20) -> str:
    escaped = [html.escape(fragment) for fragment in fragments if fragment]
    if not escaped:
        return ""
    if len(escaped) <= limit:
        return ", ".join(escaped)
    shown = ", ".join(escaped[:limit])
    return (
        f"{shown}, "
        f"{translate(locale, 'import_words_summary_more_suffix', count_text=format_import_item_count(locale, len(escaped) - limit))}"
    )


def build_invalid_import_notice(locale: str, fragments: list[str]) -> str | None:
    formatted = format_invalid_import_fragments(locale, fragments)
    if not formatted:
        return None
    return translate(locale, "import_words_invalid_items_notice", items=formatted)
