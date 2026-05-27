from __future__ import annotations

import json
from pathlib import Path

from word_base.generate_phrase_entries_openai import (
    GenerationSlot,
    build_slots,
    normalize_phrase,
    validate_generated_row,
)


def test_build_slots_uses_supported_levels_and_entry_types() -> None:
    slots = build_slots(20)

    assert len(slots) == 20
    assert slots[0].source_ref == "generated_phrases:000001"
    assert {slot.level_code for slot in slots} <= {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert {slot.entry_type for slot in slots} <= {"idiom", "phrase_pattern"}


def test_normalize_phrase_uses_project_placeholders() -> None:
    assert normalize_phrase("Make Somebody Do Something") == "make smb do smth"
    assert normalize_phrase("be supposed to do sth") == "be supposed to do smth"


def test_validate_generated_row_builds_normalized_bundle_entry() -> None:
    slot = GenerationSlot(
        source_ref="generated_phrases:000001",
        entry_type="phrase_pattern",
        level_code="B1",
    )

    row = validate_generated_row(
        slot,
        {
            "source_ref": "generated_phrases:000001",
            "word": "make smb do smth",
            "entry_type": "phrase_pattern",
            "level_code": "B1",
            "translation_uk": "змусити когось щось зробити",
            "translation_ru": "заставить кого-то что-то сделать",
            "translation_pl": "sprawić, że ktoś coś zrobi",
            "transcription": "/meɪk ˈsʌmbədi duː ˈsʌmθɪŋ/",
            "examples": [
                "The coach made every player run after practice.",
                "Her story made me think about my choices.",
                "That noise made the baby cry all night.",
            ],
        },
        seen_phrase_keys=set(),
    )

    assert row["entry_key"] == "make-smb-do-smth__phrase-pattern__entry"
    assert row["parts_of_speech"] == ["phrase pattern"]
    assert row["audio_path"] is None


def test_validate_generated_row_rejects_phrase_pattern_without_placeholder() -> None:
    slot = GenerationSlot(
        source_ref="generated_phrases:000001",
        entry_type="phrase_pattern",
        level_code="B1",
    )

    try:
        validate_generated_row(
            slot,
            {
                "source_ref": "generated_phrases:000001",
                "word": "make a difference",
                "entry_type": "phrase_pattern",
                "level_code": "B1",
                "translation_uk": "мати значення",
                "translation_ru": "иметь значение",
                "translation_pl": "mieć znaczenie",
                "transcription": "/meɪk ə ˈdɪfərəns/",
                "examples": [
                    "Small changes can make a difference at work.",
                    "Your support made a difference during the crisis.",
                    "Clear rules make a difference for new teams.",
                ],
            },
            seen_phrase_keys=set(),
        )
    except ValueError as error:
        assert "missing smb/smth" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_validate_generated_row_rejects_bad_placeholder_grammar() -> None:
    slot = GenerationSlot(
        source_ref="generated_phrases:000001",
        entry_type="phrase_pattern",
        level_code="A1",
    )

    try:
        validate_generated_row(
            slot,
            {
                "source_ref": "generated_phrases:000001",
                "word": "there is a smth on the table",
                "entry_type": "phrase_pattern",
                "level_code": "A1",
                "translation_uk": "щось є на столі",
                "translation_ru": "что-то есть на столе",
                "translation_pl": "coś jest na stole",
                "transcription": "/ðer ɪz ə ˈsʌmθɪŋ ɑn ðə ˈteɪbəl/",
                "examples": [
                    "There is a book on the table.",
                    "There is a phone near the lamp.",
                    "There is a bag under the chair.",
                ],
            },
            seen_phrase_keys=set(),
        )
    except ValueError as error:
        assert "existential template" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_validate_generated_row_rejects_weak_idiom_phrase() -> None:
    slot = GenerationSlot(source_ref="generated_phrases:000002", entry_type="idiom", level_code="A2")

    try:
        validate_generated_row(
            slot,
            {
                "source_ref": "generated_phrases:000002",
                "word": "in time",
                "entry_type": "idiom",
                "level_code": "A2",
                "translation_uk": "вчасно",
                "translation_ru": "вовремя",
                "translation_pl": "na czas",
                "transcription": "/ɪn taɪm/",
                "examples": [
                    "We arrived in time for lunch.",
                    "She came in time for class.",
                    "The letter arrived in time today.",
                ],
            },
            seen_phrase_keys=set(),
        )
    except ValueError as error:
        assert "weak idiom phrase" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_generated_phrase_bundle_fixture_shape_is_json_serializable(tmp_path: Path) -> None:
    slot = GenerationSlot(source_ref="generated_phrases:000002", entry_type="idiom", level_code="B2")
    row = validate_generated_row(
        slot,
        {
            "source_ref": "generated_phrases:000002",
            "word": "break the ice",
            "entry_type": "idiom",
            "level_code": "B2",
            "translation_uk": "розтопити лід у спілкуванні",
            "translation_ru": "растопить лёд в общении",
            "translation_pl": "przełamać pierwsze lody",
            "transcription": "/breɪk ði aɪs/",
            "examples": [
                "A simple joke helped break the ice quickly.",
                "The game broke the ice at the meeting.",
                "Music can break the ice between strangers.",
            ],
        },
        seen_phrase_keys=set(),
    )

    output_path = tmp_path / "normolized_phrase_entries.json"
    output_path.write_text(json.dumps({"entries": [row]}, ensure_ascii=False), encoding="utf-8")

    assert json.loads(output_path.read_text(encoding="utf-8"))["entries"][0]["entry_type"] == "idiom"
