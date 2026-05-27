from __future__ import annotations

from app.user_import.services.helpers import (
    build_invalid_import_notice,
    format_failed_import_item,
    format_import_count_text,
    format_import_task_status,
    format_invalid_import_fragments,
    format_numbered_import_item_list,
    normalize_import_document_lines,
    normalize_nonempty_strings,
    write_text_atomic,
)


def test_format_import_count_text_uses_project_plural_rules() -> None:
    assert format_import_count_text("uk", 1) == "1 елемент"
    assert format_import_count_text("uk", 5) == "5 елементів"


def test_normalize_nonempty_strings_accepts_only_nonempty_list_values() -> None:
    assert normalize_nonempty_strings(None) == []
    assert normalize_nonempty_strings([" word ", "", 42]) == ["word", "42"]


def test_normalize_import_document_lines_collapses_whitespace() -> None:
    assert normalize_import_document_lines(["  hello   world  ", "", "next\tline"]) == ["hello world", "next line"]


def test_write_text_atomic_creates_parent_and_replaces_file(tmp_path) -> None:
    target = tmp_path / "nested" / "document.txt"

    write_text_atomic(target, "first")
    write_text_atomic(target, "second")

    assert target.read_text(encoding="utf-8") == "second"
    assert not (target.parent / ".document.txt.tmp").exists()


def test_format_numbered_import_item_list_escapes_and_limits_items() -> None:
    result = format_numbered_import_item_list("uk", ["<one>", "two", "three"], limit=2)

    assert "1. &lt;one&gt;" in result
    assert "2. two" in result
    assert "та ще 1 елемент" in result


def test_format_numbered_import_item_list_returns_empty_without_items() -> None:
    assert format_numbered_import_item_list("uk", []) == ""


def test_format_failed_import_item_appends_reason_marker_when_error_exists() -> None:
    assert format_failed_import_item({"lookup_word": "plain", "error_text": ""}) == "plain"
    assert format_failed_import_item({"lookup_word": "plain", "error_text": "broken"}).startswith("plain\n")


def test_format_import_task_status_translates_and_falls_back() -> None:
    assert format_import_task_status("uk", None) == "-"
    assert format_import_task_status("uk", "unknown-status") == "unknown-status"


def test_format_invalid_import_fragments_escapes_and_limits_items() -> None:
    result = format_invalid_import_fragments("uk", ["<bad>", "wrong", "skip"], limit=2)

    assert "&lt;bad&gt;" in result
    assert "wrong" in result
    assert "та ще 1 елемент" in result


def test_build_invalid_import_notice_returns_none_without_fragments() -> None:
    assert build_invalid_import_notice("uk", []) is None


def test_build_invalid_import_notice_includes_formatted_fragments() -> None:
    result = build_invalid_import_notice("uk", ["<bad>"])

    assert result is not None
    assert "&lt;bad&gt;" in result
