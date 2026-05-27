from __future__ import annotations

import json
from pathlib import Path

from word_base.build_clean_word_embeddings import build_clean_word_embeddings


def test_build_clean_word_embeddings_writes_separate_jsonl(tmp_path: Path, monkeypatch) -> None:
    input_bundle = tmp_path / "normolized_clean_words.json"
    output_jsonl = tmp_path / "normolized_clean_words.embeddings.jsonl"
    status_json = tmp_path / "normolized_clean_words.embeddings.status.json"
    report_json = tmp_path / "normolized_clean_words.embeddings.report.json"
    input_bundle.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "core:1",
                        "entry_key": "abandon__verb__entry",
                        "word": "abandon",
                        "parts_of_speech": ["verb"],
                        "level_code": "B2",
                        "translation_uk": "покидати",
                        "translation_ru": "покидать",
                        "translation_pl": "porzucać",
                        "category_tags": ["general"],
                        "examples": ["Abandon ship."],
                    },
                    {
                        "source_ref": "core:2",
                        "entry_key": "ability__noun__entry",
                        "word": "ability",
                        "parts_of_speech": ["noun"],
                        "level_code": "A2",
                        "translation_uk": "здатність",
                        "translation_ru": "способность",
                        "translation_pl": "zdolność",
                        "category_tags": ["general"],
                        "examples": ["She has ability."],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "word_base.build_clean_word_embeddings.build_local_encoder",
        lambda model_name, device: object(),
    )
    monkeypatch.setattr(
        "word_base.build_clean_word_embeddings.encode_texts",
        lambda **kwargs: [[0.1, 0.2], [0.3, 0.4]],
    )

    report = build_clean_word_embeddings(
        input_bundle=input_bundle,
        output_jsonl=output_jsonl,
        status_json=status_json,
        report_json=report_json,
        embeddings_model="text-embedding-3-small",
        device="cpu",
        batch_size=10,
        checkpoint_every=1,
        limit=0,
    )

    rows = [json.loads(line) for line in output_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["source_ref"] == "core:1"
    assert rows[0]["embedding_model"] == "text-embedding-3-small"
    assert rows[1]["embedding"] == [0.3, 0.4]
    assert report["stats"]["generated_entries"] == 2


def test_build_clean_word_embeddings_reuses_existing_rows_when_source_ref_changes(tmp_path: Path, monkeypatch) -> None:
    input_bundle = tmp_path / "normolized_clean_words.json"
    output_jsonl = tmp_path / "normolized_clean_words.embeddings.jsonl"
    status_json = tmp_path / "normolized_clean_words.embeddings.status.json"
    report_json = tmp_path / "normolized_clean_words.embeddings.report.json"
    input_bundle.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "core:1__abandon-verb-entry",
                        "entry_key": "abandon__verb__entry",
                        "word": "abandon",
                        "parts_of_speech": ["verb"],
                        "level_code": "B2",
                        "translation_uk": "покидати",
                        "translation_ru": "покидать",
                        "translation_pl": "porzucać",
                        "category_tags": ["general"],
                        "examples": ["Abandon ship."],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    output_jsonl.write_text(
        json.dumps(
            {
                "source_ref": "core:1",
                "entry_key": "abandon__verb__entry",
                "word": "abandon",
                "parts_of_speech": ["verb"],
                "embedding": [0.1, 0.2],
                "embedding_model": "text-embedding-3-small",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "word_base.build_clean_word_embeddings.build_local_encoder",
        lambda model_name, device: object(),
    )
    monkeypatch.setattr(
        "word_base.build_clean_word_embeddings.encode_texts",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("encode_texts should not be called")),
    )

    report = build_clean_word_embeddings(
        input_bundle=input_bundle,
        output_jsonl=output_jsonl,
        status_json=status_json,
        report_json=report_json,
        embeddings_model="text-embedding-3-small",
        device="cpu",
        batch_size=10,
        checkpoint_every=1,
        limit=0,
    )

    rows = [json.loads(line) for line in output_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["source_ref"] == "core:1__abandon-verb-entry"
    assert rows[0]["embedding"] == [0.1, 0.2]
    assert report["stats"]["generated_entries"] == 0
    assert report["stats"]["skipped_existing_entries"] == 1
