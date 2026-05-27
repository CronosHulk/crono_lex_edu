from __future__ import annotations

import json
from pathlib import Path

from word_base.normalize_clean_words_source_refs import normalize_clean_words_source_refs


def test_normalize_clean_words_source_refs_updates_bundle_embeddings_and_synonyms(tmp_path: Path) -> None:
    bundle_path = tmp_path / "clean_words.json"
    embeddings_path = tmp_path / "clean_words.embeddings.jsonl"
    report_path = tmp_path / "normalize.report.json"

    bundle = {
        "source": {"type": "clean_words"},
        "entries": [
            {
                "source_ref": "core:10",
                "source_namespace": "core",
                "source_legacy_id": 10,
                "entry_key": "dog__noun__entry__core-10",
                "word": "dog",
                "normalized_word": "dog",
                "entry_type": "word",
                "level_code": "A1",
                "parts_of_speech": ["noun"],
                "category_tags": ["animals"],
                "translation_uk": "собака",
                "translation_ru": "собака",
                "translation_pl": "pies",
                "transcription": "/dɔːɡ/",
                "examples": ["The dog barked loudly."],
                "synonym_source_refs": ["core:20"],
                "audio_path": "word_base/word_audio/dog.mp3",
            },
            {
                "source_ref": "core:10",
                "source_namespace": "core",
                "source_legacy_id": 10,
                "entry_key": "doll__noun__entry__core-10",
                "word": "doll",
                "normalized_word": "doll",
                "entry_type": "word",
                "level_code": "A1",
                "parts_of_speech": ["noun"],
                "category_tags": ["toys"],
                "translation_uk": "лялька",
                "translation_ru": "кукла",
                "translation_pl": "lalka",
                "transcription": "/dɒl/",
                "examples": ["The doll was on the shelf."],
                "synonym_source_refs": [],
                "audio_path": "word_base/word_audio/doll.mp3",
            },
            {
                "source_ref": "core:20",
                "source_namespace": "core",
                "source_legacy_id": 20,
                "entry_key": "canine__noun__entry__core-20",
                "word": "canine",
                "normalized_word": "canine",
                "entry_type": "word",
                "level_code": "B2",
                "parts_of_speech": ["noun"],
                "category_tags": ["animals"],
                "translation_uk": "пес",
                "translation_ru": "пес",
                "translation_pl": "pies",
                "transcription": "/ˈkeɪnaɪn/",
                "examples": ["The canine waited by the gate."],
                "synonym_source_refs": ["core:10"],
                "audio_path": "word_base/word_audio/canine.mp3",
            },
        ],
        "synonym_pairs": [{"left_source_ref": "core:10", "right_source_ref": "core:20"}],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    embeddings_rows = [
        {
            "source_ref": "core:10",
            "entry_key": "dog__noun__entry__core-10",
            "word": "dog",
            "parts_of_speech": ["noun"],
            "embedding": [0.1, 0.2],
            "embedding_model": "sentence-model",
        },
        {
            "source_ref": "core:10",
            "entry_key": "doll__noun__entry__core-10",
            "word": "doll",
            "parts_of_speech": ["noun"],
            "embedding": [0.3, 0.4],
            "embedding_model": "sentence-model",
        },
        {
            "source_ref": "core:20",
            "entry_key": "canine__noun__entry__core-20",
            "word": "canine",
            "parts_of_speech": ["noun"],
            "embedding": [0.5, 0.6],
            "embedding_model": "sentence-model",
        },
    ]
    embeddings_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in embeddings_rows) + "\n",
        encoding="utf-8",
    )

    report = normalize_clean_words_source_refs(
        bundle_path=bundle_path,
        embeddings_path=embeddings_path,
        report_path=report_path,
    )

    normalized_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    refs_by_word = {entry["word"]: entry["source_ref"] for entry in normalized_bundle["entries"]}
    assert refs_by_word["dog"] == "core:10__dog-noun-entry-core-10"
    assert refs_by_word["doll"] == "core:10__doll-noun-entry-core-10"
    assert refs_by_word["canine"] == "core:20"

    raw_refs_by_word = {entry["word"]: entry["source_raw_refs"] for entry in normalized_bundle["entries"]}
    assert raw_refs_by_word["dog"] == ["core:10__dog-noun-entry-core-10", "core:10"]
    assert raw_refs_by_word["doll"] == ["core:10__doll-noun-entry-core-10", "core:10"]
    assert raw_refs_by_word["canine"] == ["core:20"]

    synonyms_by_word = {entry["word"]: entry["synonym_source_refs"] for entry in normalized_bundle["entries"]}
    assert synonyms_by_word["dog"] == ["core:20"]
    assert synonyms_by_word["canine"] == ["core:10__dog-noun-entry-core-10"]
    assert normalized_bundle["synonym_pairs"] == [
        {"left_source_ref": "core:10__dog-noun-entry-core-10", "right_source_ref": "core:20"}
    ]

    normalized_embeddings = [
        json.loads(line)
        for line in embeddings_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    embedding_refs = {row["word"]: row["source_ref"] for row in normalized_embeddings}
    assert embedding_refs == refs_by_word

    assert report["duplicate_source_refs_before"] == 1
    assert report["duplicate_source_refs_after"] == 0
    assert report["renamed_entries"] == 2
