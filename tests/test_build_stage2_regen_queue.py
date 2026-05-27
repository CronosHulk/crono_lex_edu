from __future__ import annotations

import json
from pathlib import Path

from word_base.build_stage2_regen_queue import build_queue


def test_build_queue_collects_consistency_and_manual_items(tmp_path: Path) -> None:
    consistency_path = tmp_path / "consistency.json"
    reviewed_path = tmp_path / "reviewed.json"
    consistency_path.write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "word": "one",
                        "issue_types": ["shared_examples_across_split_pos", "same_translation_uk_across_split_pos"],
                        "shared_examples": ["Which one do you prefer?"],
                        "entries": [
                            {"source_ref": "one__numeral"},
                            {"source_ref": "one__pronoun"},
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
    reviewed_path.write_text(
        json.dumps(
            {
                "entries": [
                    {"source_ref": "one__numeral", "word": "one", "parts_of_speech": ["numeral"]},
                    {"source_ref": "one__pronoun", "word": "one", "parts_of_speech": ["pronoun"]},
                    {"source_ref": "on__preposition", "word": "on", "parts_of_speech": ["preposition"]},
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    queue = build_queue(consistency_audit_path=consistency_path, reviewed_bundle_path=reviewed_path)

    refs = [item["source_ref"] for item in queue["items"]]
    assert "one__numeral" in refs
    assert "one__pronoun" in refs
    assert "on__preposition" in refs
    assert queue["stats"]["queued_source_refs"] >= 3
    one_item = next(item for item in queue["items"] if item["source_ref"] == "one__numeral")
    assert one_item["priority"] == "high"
    assert "split_pos_consistency_issue" in one_item["reasons"]
