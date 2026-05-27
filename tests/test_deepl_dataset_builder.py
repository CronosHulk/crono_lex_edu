from __future__ import annotations

import json
from pathlib import Path

import pytest

from word_base.deepl_dataset_builder import (
    apply_translations,
    build_context,
    build_diff_rows,
    load_entries,
    summarize_diff,
    write_csv,
)


def test_load_entries_from_txt_user_list_builds_full_word_shape(tmp_path: Path) -> None:
    source = tmp_path / "words.txt"
    source.write_text("abandon\n ability \n\n", encoding="utf-8")

    entries = load_entries(source_full_word=None, input_path=str(source), input_format="txt")

    assert [entry["value"]["word"] for entry in entries] == ["abandon", "ability"]
    assert entries[0]["value"]["us"] == {"mp3": "", "ogg": ""}
    assert entries[0]["value"]["phonetics"] == {"us": "", "uk": ""}
    assert entries[0]["value"]["examples"] == []


def test_build_context_uses_part_of_speech_and_first_example() -> None:
    context = build_context(
        {
            "type": "verb",
            "examples": ["People often abandon their pets.", "Ignored."],
        }
    )

    assert context == "Part of speech: verb. Example: People often abandon their pets."


def test_apply_translations_and_diff_rows_track_changes() -> None:
    entries = [
        {
            "id": 1,
            "value": {
                "word": "abandon",
                "type": "verb",
                "level": "B2",
                "href": "https://example.com/abandon",
                "examples": ["People often abandon their pets."],
                "translate": "відмовитися",
            },
        },
        {
            "id": 2,
            "value": {
                "word": "ability",
                "type": "noun",
                "level": "A2",
                "href": "https://example.com/ability",
                "examples": ["She has the ability to adapt."],
                "translate": "здатність",
            },
        },
    ]

    translated_entries = apply_translations(entries, ["покидати", "здатність"])
    diff_rows = build_diff_rows(original_entries=entries, translated_entries=translated_entries)
    summary = summarize_diff(diff_rows)

    assert translated_entries[0]["value"]["translate"] == "покидати"
    assert diff_rows[0]["is_changed"] is True
    assert diff_rows[1]["is_changed"] is False
    assert summary == {"total": 2, "changed": 1, "unchanged": 1}


def test_write_csv_produces_expected_headers(tmp_path: Path) -> None:
    path = tmp_path / "report.csv"
    rows = [
        {
            "id": 1,
            "word": "abandon",
            "part_of_speech": "verb",
            "level": "B2",
            "current_translate": "відмовитися",
            "deepl_translate": "покидати",
            "is_changed": True,
            "examples_count": 1,
            "href": "https://example.com/abandon",
        }
    ]

    write_csv(path, rows)

    content = path.read_text(encoding="utf-8")
    assert "deepl_translate" in content
    assert "abandon" in content


def test_load_entries_from_json_user_list_accepts_strings_and_objects(tmp_path: Path) -> None:
    path = tmp_path / "user_words.json"
    path.write_text(
        json.dumps(
            [
                "abandon",
                {
                    "word": "ability",
                    "type": "noun",
                    "examples": ["Students must demonstrate ability."],
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    entries = load_entries(source_full_word=None, input_path=str(path), input_format="json")

    assert entries[0]["value"]["word"] == "abandon"
    assert entries[1]["value"]["type"] == "noun"
    assert entries[1]["value"]["examples"] == ["Students must demonstrate ability."]


def test_apply_translations_keeps_original_entries_unchanged() -> None:
    entries = [
        {
            "id": 1,
            "value": {
                "word": "abandon",
                "type": "verb",
                "level": "B2",
                "href": "",
                "examples": [],
                "translate": "відмовитися",
            },
        }
    ]

    translated_entries = apply_translations(entries, ["покидати"])

    assert entries[0]["value"]["translate"] == "відмовитися"
    assert translated_entries[0]["value"]["translate"] == "покидати"


def test_load_entries_rejects_invalid_json_shape(tmp_path: Path) -> None:
    path = tmp_path / "user_words.json"
    path.write_text(json.dumps({"word": "abandon"}), encoding="utf-8")

    with pytest.raises(ValueError, match="list"):
        load_entries(source_full_word=None, input_path=str(path), input_format="json")
