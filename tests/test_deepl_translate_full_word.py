from __future__ import annotations

import json
from pathlib import Path

from word_base.deepl_translate_full_word import (
    append_jsonl,
    build_context,
    build_output_snapshot,
    finalize_status,
    load_processed_ids,
    update_status,
)


def test_build_context_uses_part_of_speech_and_first_example() -> None:
    context = build_context(
        {
            "type": "verb",
            "examples": ["People often abandon their pets.", "Ignored."],
        }
    )

    assert context == "Part of speech: verb. Example: People often abandon their pets."


def test_append_jsonl_and_load_processed_ids_roundtrip(tmp_path: Path) -> None:
    journal_path = tmp_path / "dataset.jsonl"
    append_jsonl(journal_path, {"id": 1, "translate": "покинути"})
    append_jsonl(journal_path, {"id": 2, "translate": "здатність"})

    assert load_processed_ids(journal_path) == {1, 2}


def test_build_output_snapshot_creates_full_word_like_json(tmp_path: Path) -> None:
    source_entries = [
        {"id": 1, "value": {"word": "abandon", "translate": "відмовитися"}},
        {"id": 2, "value": {"word": "ability", "translate": "здатність"}},
    ]
    journal_path = tmp_path / "dataset.jsonl"
    output_path = tmp_path / "full-word.deepl.json"

    append_jsonl(journal_path, {"id": 1, "translate": "покинути"})

    processed = build_output_snapshot(source_entries, journal_path, output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert processed == 1
    assert payload == [{"id": 1, "value": {"word": "abandon", "translate": "покинути"}}]


def test_update_status_writes_progress_file(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    output_path = tmp_path / "output.json"
    journal_path = tmp_path / "output.jsonl"

    update_status(
        status_path=status_path,
        started_at="2026-04-07T12:00:00+00:00",
        total=100,
        processed=25,
        last_word="abandon",
        output_path=output_path,
        journal_path=journal_path,
        is_completed=False,
    )

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["processed"] == 25
    assert payload["last_word"] == "abandon"
    assert payload["is_completed"] is False


def test_finalize_status_marks_partial_run_as_not_completed(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    output_path = tmp_path / "output.json"
    journal_path = tmp_path / "output.jsonl"

    finalize_status(
        status_path=status_path,
        started_at="2026-04-07T12:00:00+00:00",
        total=100,
        processed=25,
        last_word="abandon",
        output_path=output_path,
        journal_path=journal_path,
    )

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["processed"] == 25
    assert payload["last_word"] == "abandon"
    assert payload["is_completed"] is False
