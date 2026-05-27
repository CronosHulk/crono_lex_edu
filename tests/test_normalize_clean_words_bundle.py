from __future__ import annotations

import json
from pathlib import Path

from word_base.normalize_clean_words_bundle import normalize_clean_words_bundle


def test_normalize_clean_words_bundle_splits_multi_pos_and_prefixes_verbs(tmp_path: Path) -> None:
    input_bundle = tmp_path / "clean_words.json"
    output_bundle = tmp_path / "normolized_clean_words.json"
    input_bundle.write_text(
        json.dumps(
            {
                "source": {"type": "clean_words"},
                "entries": [
                    {
                        "source_ref": "core:1",
                        "source_raw_refs": ["core:1"],
                        "source_namespace": "core",
                        "source_legacy_id": 1,
                        "entry_key": "love__noun-verb__entry",
                        "word": "love",
                        "normalized_word": "love",
                        "entry_type": "word",
                        "level_code": "A1",
                        "parts_of_speech": ["noun", "verb"],
                        "category_tags": ["feelings"],
                        "translation_uk": "любов, кохати",
                        "translation_ru": "любовь, любить",
                        "translation_pl": "miłość, kochać",
                        "transcription": "/lʌv/",
                        "examples": ["Love is complicated.", "I love coffee."],
                        "synonym_source_refs": ["core:2"],
                        "audio_path": "word_base/word_audio/love.mp3",
                    },
                    {
                        "source_ref": "phrasal_verb:2",
                        "source_raw_refs": ["phrasal_verb:2"],
                        "source_namespace": "phrasal_verb",
                        "source_legacy_id": 2,
                        "entry_key": "look-after__phrasal-verb__entry",
                        "word": "look after",
                        "normalized_word": "look after",
                        "entry_type": "phrasal_verb",
                        "level_code": "A2",
                        "parts_of_speech": ["phrasal verb"],
                        "category_tags": ["care"],
                        "translation_uk": "доглядати",
                        "translation_ru": "присматривать",
                        "translation_pl": "opiekować się",
                        "transcription": "/lʊk ˈɑːftər/",
                        "examples": ["She looks after the kids."],
                        "synonym_source_refs": ["core:1"],
                        "audio_path": "word_base/word_audio/look-after.mp3",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = normalize_clean_words_bundle(input_bundle_path=input_bundle, output_bundle_path=output_bundle)

    entries = {(entry["word"], entry["parts_of_speech"][0]): entry for entry in bundle["entries"]}
    assert ("love", "noun") in entries
    assert ("to love", "verb") in entries
    assert ("to look after", "phrasal verb") in entries

    verb_entry = entries[("to love", "verb")]
    assert verb_entry["normalized_word"] == "to love"
    assert verb_entry["source_ref"] == "to-love__verb"
    assert verb_entry["entry_key"] == "to-love__verb__entry"
    assert verb_entry["audio_path"] == "word_base/word_audio/love.mp3"
    assert verb_entry["needs_detail_review"] is True
    assert verb_entry["detail_review_reasons"] == ["split_from_multi_pos"]

    noun_entry = entries[("love", "noun")]
    assert noun_entry["needs_detail_review"] is True
    assert noun_entry["detail_review_reasons"] == ["split_from_multi_pos"]

    phrasal_entry = entries[("to look after", "phrasal verb")]
    assert phrasal_entry["source_ref"] == "to-look-after__phrasal-verb"
    assert sorted(phrasal_entry["synonym_source_refs"]) == [
        "love__noun",
        "to-love__verb",
    ]
    assert phrasal_entry["needs_detail_review"] is False
    assert phrasal_entry["detail_review_reasons"] == []

    report = bundle["normalization_report"]
    assert report["multi_pos_entries_split"] == 1
    assert report["verb_entries_prefixed_with_to"] == 2
    assert report["ambiguous_synonym_expansion_count"] == 1
    assert report["detail_review_entry_count"] == 2
    assert report["detail_review_entries"] == [
        {
            "source_ref": "love__noun",
            "word": "love",
            "pos": "noun",
            "detail_review_reasons": ["split_from_multi_pos"],
        },
        {
            "source_ref": "to-love__verb",
            "word": "to love",
            "pos": "verb",
            "detail_review_reasons": ["split_from_multi_pos"],
        },
    ]

    persisted = json.loads(output_bundle.read_text(encoding="utf-8"))
    assert persisted["source"]["type"] == "normolized_clean_words"


def test_normalize_clean_words_bundle_merges_duplicate_word_pos_groups(tmp_path: Path) -> None:
    input_bundle = tmp_path / "clean_words.json"
    output_bundle = tmp_path / "normolized_clean_words.json"
    input_bundle.write_text(
        json.dumps(
            {
                "source": {"type": "clean_words"},
                "entries": [
                    {
                        "source_ref": "phrasal_verb:10",
                        "source_raw_refs": ["phrasal_verb:10"],
                        "source_namespace": "phrasal_verb",
                        "source_legacy_id": 10,
                        "entry_key": "call-back__phrasal-verb__entry__10",
                        "word": "call back",
                        "normalized_word": "call back",
                        "entry_type": "phrasal_verb",
                        "level_code": "A2",
                        "parts_of_speech": ["phrasal verb"],
                        "category_tags": ["communication"],
                        "translation_uk": "передзвонити",
                        "translation_ru": "перезвонить",
                        "translation_pl": "oddzwonić",
                        "transcription": "/kɔːl bæk/",
                        "examples": ["Please call me back."],
                        "synonym_source_refs": [],
                        "audio_path": "word_base/word_audio/call-back.mp3",
                    },
                    {
                        "source_ref": "phrasal_verb:11",
                        "source_raw_refs": ["phrasal_verb:11"],
                        "source_namespace": "phrasal_verb",
                        "source_legacy_id": 11,
                        "entry_key": "call-back__phrasal-verb__entry__11",
                        "word": "call back",
                        "normalized_word": "call back",
                        "entry_type": "phrasal_verb",
                        "level_code": "A1",
                        "parts_of_speech": ["phrasal verb"],
                        "category_tags": ["phone"],
                        "translation_uk": "передзвонити, відгукнути",
                        "translation_ru": "перезвонить",
                        "translation_pl": "oddzwonić",
                        "transcription": "/kɔːl bæk/",
                        "examples": ["I will call you back tomorrow."],
                        "synonym_source_refs": [],
                        "audio_path": "word_base/word_audio/call-back.mp3",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = normalize_clean_words_bundle(input_bundle_path=input_bundle, output_bundle_path=output_bundle)

    assert len(bundle["entries"]) == 1
    entry = bundle["entries"][0]
    assert entry["word"] == "to call back"
    assert entry["level_code"] == "A1"
    assert entry["translation_uk"] == "передзвонити, відгукнути"
    assert entry["category_tags"] == ["communication", "phone"]
    assert entry["source_raw_refs"] == ["phrasal_verb:10", "phrasal_verb:11"]
    assert bundle["normalization_report"]["merged_duplicate_word_pos_groups"] == 1


def test_normalize_clean_words_bundle_removes_past_form_when_base_verb_exists(tmp_path: Path) -> None:
    input_bundle = tmp_path / "clean_words.json"
    output_bundle = tmp_path / "normolized_clean_words.json"
    input_bundle.write_text(
        json.dumps(
            {
                "source": {"type": "clean_words"},
                "entries": [
                    {
                        "source_ref": "core:20",
                        "source_raw_refs": ["core:20"],
                        "source_namespace": "core",
                        "source_legacy_id": 20,
                        "entry_key": "ask__verb__entry",
                        "word": "ask",
                        "normalized_word": "ask",
                        "entry_type": "word",
                        "level_code": "A1",
                        "parts_of_speech": ["verb"],
                        "category_tags": ["communication"],
                        "translation_uk": "питати",
                        "translation_ru": "спрашивать",
                        "translation_pl": "pytać",
                        "transcription": "/ɑːsk/",
                        "examples": ["Ask a question."],
                        "synonym_source_refs": [],
                    },
                    {
                        "source_ref": "core:21",
                        "source_raw_refs": ["core:21"],
                        "source_namespace": "core",
                        "source_legacy_id": 21,
                        "entry_key": "asked__verb__entry",
                        "word": "asked",
                        "normalized_word": "asked",
                        "entry_type": "word",
                        "level_code": "A1",
                        "parts_of_speech": ["verb"],
                        "category_tags": ["communication"],
                        "translation_uk": "запитав",
                        "translation_ru": "спросил",
                        "translation_pl": "zapytał",
                        "transcription": "/ɑːskt/",
                        "examples": ["He asked for help."],
                        "synonym_source_refs": [],
                    },
                    {
                        "source_ref": "core:22",
                        "source_raw_refs": ["core:22"],
                        "source_namespace": "core",
                        "source_legacy_id": 22,
                        "entry_key": "born__verb__entry",
                        "word": "born",
                        "normalized_word": "born",
                        "entry_type": "word",
                        "level_code": "A1",
                        "parts_of_speech": ["verb"],
                        "category_tags": ["people"],
                        "translation_uk": "народжений",
                        "translation_ru": "рожденный",
                        "translation_pl": "urodzony",
                        "transcription": "/bɔːrn/",
                        "examples": ["She was born in Kyiv."],
                        "synonym_source_refs": [],
                    },
                    {
                        "source_ref": "core:23",
                        "source_raw_refs": ["core:23"],
                        "source_namespace": "core",
                        "source_legacy_id": 23,
                        "entry_key": "be__verb__entry",
                        "word": "be",
                        "normalized_word": "be",
                        "entry_type": "word",
                        "level_code": "A1",
                        "parts_of_speech": ["verb"],
                        "category_tags": ["grammar"],
                        "translation_uk": "бути",
                        "translation_ru": "быть",
                        "translation_pl": "być",
                        "transcription": "/biː/",
                        "examples": ["Be careful."],
                        "synonym_source_refs": [],
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = normalize_clean_words_bundle(input_bundle_path=input_bundle, output_bundle_path=output_bundle)

    words = {(entry["word"], entry["parts_of_speech"][0]) for entry in bundle["entries"]}
    assert ("to ask", "verb") in words
    assert ("to be", "verb") in words
    assert ("to asked", "verb") not in words
    assert ("to born", "verb") not in words

    removed = bundle["normalization_report"]["removed_past_tense_entries"]
    assert removed == [
        {
            "source_ref": "core:21",
            "word": "asked",
            "pos": "verb",
            "suggested_base_word": "to ask",
        },
        {
            "source_ref": "core:22",
            "word": "born",
            "pos": "verb",
            "suggested_base_word": "to be",
        },
    ]
