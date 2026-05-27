from __future__ import annotations

import json
from pathlib import Path

from word_base.fix_normolized_clean_words_translations_deepl import (
    append_jsonl,
    build_context,
    build_issue_rows,
    build_multi_pos_word_set,
    build_output_snapshot,
    build_targets_report,
    detect_translation_issues,
    load_journal_rows,
    parse_target_langs,
)


def test_build_multi_pos_word_set_detects_words_with_multiple_parts_of_speech() -> None:
    clean_entries = [
        {"word": "trace", "parts_of_speech": ["noun", "verb"]},
        {"word": "light", "parts_of_speech": ["noun"]},
        {"word": "light", "parts_of_speech": ["verb"]},
        {"word": "only", "parts_of_speech": ["adverb"]},
    ]

    result = build_multi_pos_word_set(clean_entries)

    assert result == {"trace", "light"}


def test_build_targets_report_selects_multi_pos_entries_and_all_to_entries() -> None:
    normalized_entries = [
        {"source_ref": "trace__noun", "word": "trace", "parts_of_speech": ["noun"]},
        {"source_ref": "to-trace__verb", "word": "to trace", "parts_of_speech": ["verb"]},
        {"source_ref": "table__noun", "word": "table", "parts_of_speech": ["noun"]},
        {"source_ref": "to-agree__verb", "word": "to agree", "parts_of_speech": ["verb"]},
    ]

    report = build_targets_report(normalized_entries, multi_pos_words={"trace"})

    assert report["target_entry_count"] == 3
    assert report["multi_pos_only_count"] == 1
    assert report["to_only_count"] == 1
    assert report["multi_pos_and_to_count"] == 1
    assert [target["source_ref"] for target in report["targets"]] == [
        "trace__noun",
        "to-trace__verb",
        "to-agree__verb",
    ]


def test_parse_target_langs_validates_and_deduplicates() -> None:
    assert parse_target_langs("UK, RU, PL, UK") == ["UK", "RU", "PL"]


def test_build_context_uses_part_of_speech_and_first_example() -> None:
    entry = {
        "parts_of_speech": ["noun"],
        "examples": [
            "Police found a faint trace near the window.",
            "Ignored example.",
        ],
    }

    assert build_context(entry) == "Part of speech: noun. Example: Police found a faint trace near the window."


def test_build_output_snapshot_updates_only_journaled_entries(tmp_path: Path) -> None:
    bundle = {
        "entries": [
            {
                "source_ref": "trace__noun",
                "word": "trace",
                "translation_uk": "відстежувати, слід",
                "translation_ru": "отслеживать, след",
                "translation_pl": "śledzić, ślad",
            },
            {
                "source_ref": "to-trace__verb",
                "word": "to trace",
                "translation_uk": "відстежувати, слід",
                "translation_ru": "отслеживать, след",
                "translation_pl": "śledzić, ślad",
            },
        ]
    }
    journal_path = tmp_path / "fixed.jsonl"
    output_path = tmp_path / "normolized_clean_words_fixed.json"

    append_jsonl(
        journal_path,
        {
            "source_ref": "trace__noun",
            "translation_uk": "слід, слідок",
            "translation_ru": "след, следок",
            "translation_pl": "ślad",
        },
    )

    processed_count = build_output_snapshot(
        bundle,
        output_path=output_path,
        journal_rows=load_journal_rows(journal_path),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert processed_count == 1
    assert payload["entries"][0]["translation_uk"] == "слід, слідок"
    assert payload["entries"][1]["translation_uk"] == "відстежувати, слід"
    assert output_path.read_text(encoding="utf-8").startswith('{\n  "entries": [\n')


def test_detect_translation_issues_flags_echo_translation_for_cyrillic_target() -> None:
    assert detect_translation_issues(
        word="advance",
        target_lang="RU",
        translated_text="advance",
    ) == ["same_as_source", "latin_only_for_cyrillic_target"]


def test_build_issue_rows_collects_flagged_translations() -> None:
    rows = build_issue_rows(
        source_ref="advance__noun",
        entry={"word": "advance", "parts_of_speech": ["noun"]},
        translations={
            "translation_uk": "прогрес",
            "translation_ru": "advance",
            "translation_pl": "postęp",
        },
        target_langs=["UK", "RU", "PL"],
    )

    assert rows == [
        {
            "source_ref": "advance__noun",
            "word": "advance",
            "parts_of_speech": ["noun"],
            "target_lang": "RU",
            "field_name": "translation_ru",
            "translated_text": "advance",
            "issues": ["same_as_source", "latin_only_for_cyrillic_target"],
        }
    ]
