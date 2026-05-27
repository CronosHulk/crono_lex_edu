from __future__ import annotations

import json
from pathlib import Path

from app.word_validation import count_words, supports_gap_example
from word_base.generate_missing_examples_openai import (
    MissingEntry,
    build_prompt,
    load_entries,
    load_source_ref_filter,
    validate_examples_for_entry,
)


def build_entry(word: str) -> MissingEntry:
    return MissingEntry(
        source_ref=f"core:{word}",
        word=word,
        normalized_word=word.lower(),
        level_code="A1",
        parts_of_speech=["noun"],
        translation_uk="тест",
    )


def test_count_words_counts_simple_sentence() -> None:
    assert count_words("The bridge can withstand heavy wind and rain.") == 8


def test_supports_gap_example_handles_phrasal_verb() -> None:
    assert supports_gap_example("check in", "Please check in before the morning meeting starts.") is True


def test_validate_examples_for_entry_accepts_short_natural_sentences() -> None:
    examples = [
        "Morning fog covered the sea beyond the empty harbor.",
        "Rough sea waves shook the small fishing boat.",
    ]
    assert validate_examples_for_entry(build_entry("sea"), examples) == examples


def test_build_prompt_includes_usage_form_guidance_for_phrasal_verbs() -> None:
    prompt = build_prompt(
        [
            MissingEntry(
                source_ref="to-run-into__phrasal-verb",
                word="to run into",
                normalized_word="to run into",
                level_code="B1",
                parts_of_speech=["phrasal verb"],
                translation_uk="випадково зустріти",
            )
        ]
    )

    assert "usage_form" in prompt
    assert "\"usage_form\": \"run into\"" in prompt
    assert "omit the infinitive marker 'to'" in prompt


def test_validate_examples_for_entry_rejects_too_short_sentence() -> None:
    examples = [
        "Sea views matter.",
        "Morning fog covered the sea beyond the empty harbor.",
    ]
    try:
        validate_examples_for_entry(build_entry("sea"), examples)
    except ValueError as error:
        assert "word count" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_validate_examples_for_entry_rejects_example_that_gap_builder_cannot_blank() -> None:
    examples = [
        "This sentence mentions nothing relevant at all.",
        "Morning fog covered the sea beyond the empty harbor.",
    ]
    try:
        validate_examples_for_entry(build_entry("sea"), examples)
    except ValueError as error:
        assert "gap builder could not blank target word" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_load_source_ref_filter_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    source_ref_path = tmp_path / "source_refs.txt"
    source_ref_path.write_text("\n# comment\ncore:one\n\n core:two \n", encoding="utf-8")

    assert load_source_ref_filter(source_ref_path) == {"core:one", "core:two"}


def test_load_entries_filters_to_requested_source_refs_and_keeps_existing_examples(tmp_path: Path) -> None:
    bundle_path = tmp_path / "clean_words.json"
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "core:one",
                        "word": "superb",
                        "normalized_word": "superb",
                        "level_code": "B1",
                        "parts_of_speech": ["adjective"],
                        "translation_uk": "чудовий",
                        "examples": ["Her idea was superb from the first draft."],
                    },
                    {
                        "source_ref": "core:two",
                        "word": "shed",
                        "normalized_word": "shed",
                        "level_code": "A2",
                        "parts_of_speech": ["noun"],
                        "translation_uk": "сарай",
                        "examples": [],
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    entries = load_entries(
        bundle_path,
        limit=0,
        source_ref_filter={"core:one"},
        include_with_examples=True,
    )

    assert [entry.source_ref for entry in entries] == ["core:one"]
    assert entries[0].word == "superb"


def test_load_entries_raises_when_requested_source_ref_is_missing(tmp_path: Path) -> None:
    bundle_path = tmp_path / "clean_words.json"
    bundle_path.write_text(json.dumps({"entries": []}), encoding="utf-8")

    try:
        load_entries(bundle_path, limit=0, source_ref_filter={"core:missing"}, include_with_examples=True)
    except ValueError as error:
        assert "core:missing" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_load_entries_rejects_non_ascii_word_forms(tmp_path: Path) -> None:
    bundle_path = tmp_path / "clean_words.json"
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "core:bad",
                        "word": "ennuyé",
                        "normalized_word": "ennuyé",
                        "level_code": "C2",
                        "parts_of_speech": ["adjective"],
                        "translation_uk": "знуджений",
                        "examples": [],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    try:
        load_entries(bundle_path, limit=0, source_ref_filter=None, include_with_examples=True)
    except ValueError as error:
        assert "non-ascii word" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")
