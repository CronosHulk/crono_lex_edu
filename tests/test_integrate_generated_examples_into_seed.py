from __future__ import annotations

import json
from pathlib import Path

from word_base.integrate_generated_examples_into_seed import integrate_generated_examples_into_seed


def test_integrate_generated_examples_into_seed_updates_bundle_and_seed_sql(tmp_path: Path) -> None:
    bundle_path = tmp_path / "normolized_clean_words.json"
    generated_path = tmp_path / "generated.jsonl"
    dictionary_migration_path = tmp_path / "002_seed.sql"
    report_path = tmp_path / "integration.report.json"

    bundle = {
        "entries": [
            {
                "source_ref": "core:7272",
                "entry_key": "superb__adjective__entry",
                "word": "superb",
                "normalized_word": "superb",
                "level_code": "B1",
                "translation_uk": "чудовий",
                "translation_ru": "прекрасный",
                "translation_pl": "znakomity",
                "transcription": "/suːˈpɝːb/",
                "examples": [],
                "parts_of_speech": ["adjective"],
                "audio_path": "word_base/word_audio/5165_superb.mp3",
            },
            {
                "source_ref": "core:1",
                "entry_key": "across__preposition__entry",
                "word": "across",
                "normalized_word": "across",
                "level_code": "A1",
                "translation_uk": "через",
                "translation_ru": "через",
                "translation_pl": "przez",
                "transcription": "/əˈkrɔːs/",
                "examples": ["The bridge stretches across the river."],
                "parts_of_speech": ["preposition"],
                "audio_path": "word_base/word_audio/0064_across.mp3",
            },
        ]
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    generated_path.write_text(
        json.dumps(
            {
                "source_ref": "core:7272",
                "word": "superb",
                "examples": [
                    "The chef prepared a superb meal for the guests.",
                    "Her presentation was superb and impressed everyone there.",
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    dictionary_migration_path.write_text(
        "\n".join(
            [
                "INSERT INTO dictionary_entry (...) VALUES",
                "    (1, 1, 'core', 'across__preposition__entry', '[\"core:1\"]'::jsonb, 'across__preposition__entry', 'across', 'across', (SELECT id FROM language_level WHERE title = 'A1'), '/əˈkrɔːs/', 'через', 'через', 'przez', '[\"The bridge stretches across the river.\"]'::jsonb, FALSE, 'word_base/word_audio/0064_across.mp3', '[0.0]'::vector, 'sentence-model', TRUE),",
                "    (4632, 7272, 'core', 'superb__adjective__entry', '[\"core:7272\"]'::jsonb, 'superb__adjective__entry', 'superb', 'superb', (SELECT id FROM language_level WHERE title = 'B1'), '/suːˈpɝːb/', 'чудовий', 'прекрасный', 'znakomity', '[]'::jsonb, FALSE, 'word_base/word_audio/5165_superb.mp3', '[0.1]'::vector, 'sentence-model', TRUE),",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = integrate_generated_examples_into_seed(
        input_bundle=bundle_path,
        input_jsonl=generated_path,
        dictionary_migration=dictionary_migration_path,
        report_path=report_path,
        overwrite_existing=False,
    )

    updated_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    superb = next(entry for entry in updated_bundle["entries"] if entry["word"] == "superb")
    assert superb["examples"] == [
        "The chef prepared a superb meal for the guests.",
        "Her presentation was superb and impressed everyone there.",
    ]
    across = next(entry for entry in updated_bundle["entries"] if entry["word"] == "across")
    assert across["examples"] == ["The bridge stretches across the river."]

    dictionary_sql = dictionary_migration_path.read_text(encoding="utf-8")
    assert '"The chef prepared a superb meal for the guests."' in dictionary_sql
    assert "'[]'::jsonb" not in dictionary_sql

    assert report["bundle"]["updated_entries"] == 1
    assert report["dictionary_migration"]["updated_lines"] == 1

    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_payload["bundle"]["updated_entries"] == 1


def test_integrate_generated_examples_into_seed_can_overwrite_existing_examples(tmp_path: Path) -> None:
    bundle_path = tmp_path / "normolized_clean_words.json"
    generated_path = tmp_path / "generated.jsonl"
    dictionary_migration_path = tmp_path / "002_seed.sql"
    report_path = tmp_path / "integration.report.json"

    bundle = {
        "entries": [
            {
                "source_ref": "core:7272",
                "entry_key": "superb__adjective__entry",
                "word": "superb",
                "normalized_word": "superb",
                "level_code": "B1",
                "translation_uk": "чудовий",
                "translation_ru": "прекрасный",
                "translation_pl": "znakomity",
                "transcription": "/suːˈpɝːb/",
                "examples": ["Old example for superb."],
                "parts_of_speech": ["adjective"],
                "audio_path": "word_base/word_audio/5165_superb.mp3",
            }
        ]
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    generated_path.write_text(
        json.dumps(
            {
                "source_ref": "core:7272",
                "word": "superb",
                "examples": [
                    "The chef prepared a superb meal for the guests.",
                    "Her presentation was superb and impressed everyone there.",
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    dictionary_migration_path.write_text(
        "INSERT INTO dictionary_entry (...) VALUES\n"
        "    (4632, 7272, 'core', 'superb__adjective__entry', '[\"core:7272\"]'::jsonb, 'superb__adjective__entry', 'superb', 'superb', (SELECT id FROM language_level WHERE title = 'B1'), '/suːˈpɝːb/', 'чудовий', 'прекрасный', 'znakomity', '[\"Old example for superb.\"]'::jsonb, FALSE, 'word_base/word_audio/5165_superb.mp3', '[0.1]'::vector, 'sentence-model', TRUE),\n",
        encoding="utf-8",
    )

    report = integrate_generated_examples_into_seed(
        input_bundle=bundle_path,
        input_jsonl=generated_path,
        dictionary_migration=dictionary_migration_path,
        report_path=report_path,
        overwrite_existing=True,
    )

    updated_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert updated_bundle["entries"][0]["examples"] == [
        "The chef prepared a superb meal for the guests.",
        "Her presentation was superb and impressed everyone there.",
    ]
    assert report["bundle"]["replaced_entries"] == 1
