from __future__ import annotations

import json
from pathlib import Path

from app.word_validation import supports_gap_example
from word_base.review_normolized_clean_words_openai import (
    apply_review_rows,
    build_prompt,
    load_review_entries,
    validate_review,
)


def test_load_review_entries_builds_usage_form_and_context(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    candidates_path = tmp_path / "candidates.json"
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "to-love__verb",
                        "word": "to love",
                        "parts_of_speech": ["verb"],
                        "level_code": "A1",
                        "translation_uk": "любити",
                        "translation_ru": "любить",
                        "translation_pl": "kochać",
                        "examples": ["They love quiet evenings together."],
                    },
                    {
                        "source_ref": "love__noun",
                        "word": "love",
                        "parts_of_speech": ["noun"],
                        "level_code": "A1",
                        "translation_uk": "любов",
                        "translation_ru": "любовь",
                        "translation_pl": "miłość",
                        "examples": ["Love can change everything."],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    candidates_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "source_ref": "to-love__verb",
                        "reasons": ["same_translation_uk_across_split_pos"],
                        "evidence": [
                            {
                                "type": "split_group",
                                "base_word": "love",
                                "poses": ["noun", "verb"],
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    entries = load_review_entries(bundle_path=bundle_path, candidates_path=candidates_path, source_ref_filter=None)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.word == "to love"
    assert entry.usage_form == "love"
    assert entry.context_entries == [
        {
            "source_ref": "love__noun",
            "word": "love",
            "usage_form": "love",
            "pos": "noun",
            "translation_uk": "любов",
            "translation_ru": "любовь",
            "translation_pl": "miłość",
            "examples": ["Love can change everything."],
        }
    ]


def test_load_review_entries_rejects_non_ascii_word_forms(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    candidates_path = tmp_path / "candidates.json"
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "ennuy__adjective",
                        "word": "ennuyé",
                        "parts_of_speech": ["adjective"],
                        "level_code": "C2",
                        "translation_uk": "знуджений",
                        "translation_ru": "скучающий",
                        "translation_pl": "znudzony",
                        "examples": ["He looked ennuyé during the lecture."],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidates_path.write_text(
        json.dumps({"candidates": [{"source_ref": "ennuy__adjective", "reasons": [], "evidence": []}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    try:
        load_review_entries(bundle_path=bundle_path, candidates_path=candidates_path, source_ref_filter=None)
    except ValueError as error:
        assert "non-ascii word" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_validate_review_accepts_usage_form_without_to_prefix() -> None:
    class Entry:
        source_ref = "to-look-after__phrasal-verb"
        usage_form = "look after"

    row = validate_review(
        Entry(),
        {
            "translation_uk": "доглядати",
            "translation_ru": "присматривать",
            "translation_pl": "opiekować się",
            "sense_hint_uk": "піклуватися про когось",
            "examples": [
                "She looks after her younger brother every weekend.",
                "Good nurses look after patients with great patience.",
                "Neighbors look after the house during winter trips.",
            ],
        },
    )
    assert row["translation_uk"] == "доглядати"
    assert len(row["examples"]) == 3


def test_validate_review_accepts_examples_that_blank_inflected_usage_form() -> None:
    class Entry:
        source_ref = "to-pace__verb"
        usage_form = "pace"

    row = validate_review(
        Entry(),
        {
            "translation_uk": "крокувати туди-сюди",
            "translation_ru": "мерить шагами",
            "translation_pl": "krążyć tam i z powrotem",
            "sense_hint_uk": "ходити туди-сюди короткими кроками",
            "examples": [
                "She kept pacing across the narrow room.",
                "He paced outside the office for ten minutes.",
                "They were pacing near the locked gate.",
            ],
        },
    )

    assert len(row["examples"]) == 3


def test_validate_review_accepts_silent_e_past_forms() -> None:
    class Entry:
        source_ref = "to-pause__verb"
        usage_form = "to pause"

    row = validate_review(
        Entry(),
        {
            "translation_uk": "робити паузу",
            "translation_ru": "делать паузу",
            "translation_pl": "zatrzymywać się na chwilę",
            "sense_hint_uk": "ненадовго зупинятися перед продовженням",
            "examples": [
                "She paused briefly before answering the question.",
                "He paused near the door after the noise.",
                "The speaker paused to check the final slide.",
            ],
        },
    )

    assert len(row["examples"]) == 3


def test_validate_review_accepts_to_prefixed_usage_form_for_single_word_verbs() -> None:
    class Entry:
        source_ref = "to-puncture__verb"
        usage_form = "to puncture"

    row = validate_review(
        Entry(),
        {
            "translation_uk": "проколювати",
            "translation_ru": "прокалывать",
            "translation_pl": "przebijać",
            "sense_hint_uk": "робити отвір гострим предметом",
            "examples": [
                "The sharp nail punctured the rear tire.",
                "A thorn punctured his glove during work.",
                "The falling branch punctured the tent roof.",
            ],
        },
    )

    assert len(row["examples"]) == 3


def test_supports_gap_example_matches_quiz_gap_behavior() -> None:
    assert supports_gap_example("to puncture", "The sharp nail punctured the rear tire.") is True
    assert supports_gap_example("pace", "This sentence mentions nothing relevant.") is False


def test_apply_review_rows_updates_bundle_entries() -> None:
    bundle = {
        "entries": [
            {
                "source_ref": "love__noun",
                "translation_uk": "любов, кохати",
                "translation_ru": "любовь, любить",
                "translation_pl": "miłość, kochać",
                "examples": ["Love is complicated.", "I love coffee.", "They spoke about love yesterday."],
            }
        ]
    }
    rows = {
        "love__noun": {
            "translation_uk": "любов",
            "translation_ru": "любовь",
            "translation_pl": "miłość",
            "sense_hint_uk": "почуття любові",
            "examples": [
                "Their love survived many difficult years.",
                "A mother's love can comfort a frightened child.",
                "His first poem was about lost love.",
            ],
            "reviewed_at": "2026-04-22 12:00:00",
            "review_scope": "translations_examples_details",
            "review_reasons": ["same_translation_uk_across_split_pos"],
        }
    }

    updated = apply_review_rows(bundle, rows, model="gpt-5.4-mini")
    entry = updated["entries"][0]
    assert entry["translation_uk"] == "любов"
    assert entry["sense_hint_uk"] == "почуття любові"
    assert entry["details_review"]["model"] == "gpt-5.4-mini"


def test_build_prompt_emphasizes_sentence_length_checks() -> None:
    prompt = build_prompt(
        [
            type(
                "Entry",
                (),
                {
                    "source_ref": "both__determiner",
                    "word": "both",
                    "usage_form": "both",
                    "pos": "determiner",
                    "level_code": "A1",
                    "translation_uk": "",
                    "translation_ru": "",
                    "translation_pl": "",
                    "examples": [],
                    "reasons": ["same_examples_across_split_pos"],
                    "context_entries": [],
                },
            )()
        ]
    )

    assert "Aim for 8 to 12 words per sentence" in prompt
    assert "rewrite any sentence shorter than 6 words" in prompt
    assert "For very short usage_form values" in prompt
    assert "make this entry contrastive" in prompt
    assert "Do not reuse or lightly paraphrase example sentences from context entries." in prompt
    assert "Choose a syntactic frame that proves the requested part of speech" in prompt
    assert "For adverbs, do not give the target word a direct noun-phrase object" in prompt
    assert "For numerals, use the target word to count or quantify" in prompt
    assert "sense_hint_uk must briefly explain the specific role or meaning" in prompt
