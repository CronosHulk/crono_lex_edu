from __future__ import annotations

import json
from pathlib import Path

from word_base.regenerate_seed_migrations import regenerate_seed_migrations


def test_regenerate_seed_migrations_builds_split_stack_from_bundle_and_embeddings(tmp_path: Path) -> None:
    bundle_path = tmp_path / "normolized_clean_words.json"
    embeddings_path = tmp_path / "normolized_clean_words.embeddings.jsonl"
    migrations_dir = tmp_path / "migrations"

    bundle = {
        "entries": [
            {
                "source_ref": "core:1",
                "source_namespace": "core",
                "source_legacy_id": 1,
                "entry_key": "across__preposition__entry",
                "word": "across",
                "normalized_word": "across",
                "entry_type": "word",
                "level_code": "A1",
                "parts_of_speech": ["preposition"],
                "category_tags": ["position", "movement"],
                "translation_uk": "через",
                "translation_ru": "через",
                "translation_pl": "przez",
                "transcription": "/əˈkrɔːs/",
                "examples": ["The bridge stretches across the river."],
                "audio_path": "word_base/word_audio/0064_across.mp3",
            },
            {
                "source_ref": "core:2__pick-up-phrasal-verb-entry",
                "source_raw_refs": ["core:2__pick-up-phrasal-verb-entry", "core:2"],
                "source_namespace": "core",
                "source_legacy_id": 2,
                "entry_key": "pick-up__phrasal verb__entry",
                "word": "pick up",
                "normalized_word": "pick up",
                "entry_type": "phrasal_verb",
                "level_code": "B1",
                "parts_of_speech": ["phrasal verb"],
                "category_tags": ["general"],
                "translation_uk": "підбирати",
                "translation_ru": "подбирать",
                "translation_pl": "odebrać",
                "transcription": "/pɪk ʌp/",
                "examples": ["Please pick up milk on your way home."],
                "audio_path": "word_base/word_audio/pick-up.mp3",
            },
        ],
        "synonym_pairs": [{"left_source_ref": "core:1", "right_source_ref": "core:2__pick-up-phrasal-verb-entry"}],
        "part_of_speech_catalog": [
            {"code": "preposition", "title": "preposition"},
            {"code": "phrasal verb", "title": "phrasal verb"},
        ],
        "category_catalog": [
            {"code": "position", "title": "position"},
            {"code": "movement", "title": "movement"},
            {"code": "general", "title": "general"},
        ],
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    embedding_rows = [
        {
            "source_ref": "core:1",
            "entry_key": "across__preposition__entry",
            "word": "across",
            "parts_of_speech": ["preposition"],
            "embedding": [0.1, 0.2],
            "embedding_model": "sentence-model",
        },
        {
            "source_ref": "core:2__pick-up-phrasal-verb-entry",
            "entry_key": "pick-up__phrasal verb__entry",
            "word": "pick up",
            "parts_of_speech": ["phrasal verb"],
            "embedding": [0.3, 0.4],
            "embedding_model": "sentence-model",
        },
    ]
    embeddings_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in embedding_rows) + "\n",
        encoding="utf-8",
    )

    stats = regenerate_seed_migrations(
        bundle_path=bundle_path,
        embeddings_path=embeddings_path,
        migrations_dir=migrations_dir,
    )

    assert stats["dictionary_entry_count"] == 2
    assert stats["dictionary_pos_link_count"] == 2
    assert stats["dictionary_category_link_count"] == 3
    assert stats["dictionary_synonym_count"] == 1
    assert stats["embedding_row_count"] == 2
    init_sql = (migrations_dir / "001_init.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS dictionary_entry" in init_sql
    assert "INSERT INTO dictionary_part_of_speech" not in init_sql

    dictionary_sql = (migrations_dir / "002_seed.sql").read_text(encoding="utf-8")
    assert "INSERT INTO dictionary_part_of_speech" in dictionary_sql
    assert "'across__preposition__entry'" in dictionary_sql
    assert "'pick-up__phrasal verb__entry'" in dictionary_sql
    assert '\'["core:2__pick-up-phrasal-verb-entry", "core:2"]\'::jsonb' in dictionary_sql
    assert "embedding_model" not in dictionary_sql

    embeddings_sql = (migrations_dir / "003_embeddings.sql").read_text(encoding="utf-8")
    assert "UPDATE dictionary_entry AS entry" in embeddings_sql
    assert "'sentence-model'" in embeddings_sql
    assert "'[0.1, 0.2]'::vector" in embeddings_sql


def test_regenerate_seed_migrations_can_merge_phrase_bundle_and_embeddings(tmp_path: Path) -> None:
    bundle_path = tmp_path / "normolized_clean_words.json"
    embeddings_path = tmp_path / "normolized_clean_words.embeddings.jsonl"
    phrase_bundle_path = tmp_path / "normolized_phrase_entries.json"
    phrase_embeddings_path = tmp_path / "normolized_phrase_entries.embeddings.jsonl"
    migrations_dir = tmp_path / "migrations"

    base_bundle = {
        "entries": [
            {
                "source_ref": "core:1",
                "source_namespace": "core",
                "source_legacy_id": 1,
                "entry_key": "learn__verb__entry",
                "word": "learn",
                "normalized_word": "learn",
                "entry_type": "word",
                "level_code": "A1",
                "parts_of_speech": ["verb"],
                "category_tags": ["education"],
                "translation_uk": "вчити",
                "translation_ru": "учить",
                "translation_pl": "uczyć się",
                "transcription": "/lɜːrn/",
                "examples": ["I learn English."],
                "audio_path": "word_base/word_audio/learn.mp3",
            }
        ],
        "synonym_pairs": [],
        "part_of_speech_catalog": [{"code": "verb", "title": "verb"}],
        "category_catalog": [{"code": "education", "title": "education"}],
    }
    phrase_bundle = {
        "entries": [
            {
                "source_ref": "phrase:1",
                "source_namespace": "phrase",
                "source_legacy_id": None,
                "entry_key": "break-the-ice__idiom__entry",
                "word": "break the ice",
                "normalized_word": "break the ice",
                "entry_type": "idiom",
                "level_code": "B2",
                "parts_of_speech": ["idiom"],
                "category_tags": ["general"],
                "translation_uk": "розрядити атмосферу",
                "translation_ru": "разрядить обстановку",
                "translation_pl": "przełamać lody",
                "transcription": "/breɪk ði aɪs/",
                "examples": ["A joke helped break the ice."],
                "audio_path": "word_base/phrase_audio/break-the-ice.mp3",
            }
        ],
        "synonym_pairs": [],
        "part_of_speech_catalog": [{"code": "idiom", "title": "idiom"}],
        "category_catalog": [{"code": "general", "title": "general"}],
    }
    bundle_path.write_text(json.dumps(base_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    phrase_bundle_path.write_text(json.dumps(phrase_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    embeddings_path.write_text(
        json.dumps(
            {
                "source_ref": "core:1",
                "entry_key": "learn__verb__entry",
                "word": "learn",
                "parts_of_speech": ["verb"],
                "embedding": [0.1, 0.2],
                "embedding_model": "sentence-model",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    phrase_embeddings_path.write_text(
        json.dumps(
            {
                "source_ref": "phrase:1",
                "entry_key": "break-the-ice__idiom__entry",
                "word": "break the ice",
                "parts_of_speech": ["idiom"],
                "embedding": [0.3, 0.4],
                "embedding_model": "sentence-model",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    stats = regenerate_seed_migrations(
        bundle_path=bundle_path,
        embeddings_path=embeddings_path,
        extra_bundle_paths=(phrase_bundle_path,),
        extra_embeddings_paths=(phrase_embeddings_path,),
        migrations_dir=migrations_dir,
    )

    assert stats["dictionary_entry_count"] == 2
    assert stats["embedding_row_count"] == 2
    dictionary_sql = (migrations_dir / "002_seed.sql").read_text(encoding="utf-8")
    assert "'idiom', 'idiom'" in dictionary_sql
    assert "'break the ice'" in dictionary_sql
    assert "'word_base/phrase_audio/break-the-ice.mp3'" in dictionary_sql
