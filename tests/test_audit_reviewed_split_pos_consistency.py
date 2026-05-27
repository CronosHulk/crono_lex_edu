from __future__ import annotations

import json
from pathlib import Path

from word_base.audit_reviewed_split_pos_consistency import audit_reviewed_split_pos_consistency


def test_audit_reviewed_split_pos_consistency_flags_shared_examples_and_translations(tmp_path: Path) -> None:
    bundle_path = tmp_path / "reviewed.json"
    report_path = tmp_path / "report.json"
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "one__numeral",
                        "word": "one",
                        "parts_of_speech": ["numeral"],
                        "translation_uk": "один",
                        "translation_ru": "один",
                        "translation_pl": "jeden",
                        "sense_hint_uk": "числівник",
                        "examples": ["I bought one apple today.", "Which one do you prefer?"],
                    },
                    {
                        "source_ref": "one__pronoun",
                        "word": "one",
                        "parts_of_speech": ["pronoun"],
                        "translation_uk": "один",
                        "translation_ru": "один",
                        "translation_pl": "jeden",
                        "sense_hint_uk": "займенник",
                        "examples": ["I bought one apple today.", "Which one do you prefer?"],
                    },
                    {
                        "source_ref": "outside__adverb",
                        "word": "outside",
                        "parts_of_speech": ["adverb"],
                        "translation_uk": "зовні",
                        "translation_ru": "снаружи",
                        "translation_pl": "na zewnątrz",
                        "sense_hint_uk": "прислівник",
                        "examples": ["Please wait outside the station."],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = audit_reviewed_split_pos_consistency(input_bundle_path=bundle_path, report_json_path=report_path)

    assert report["stats"]["suspicious_word_groups"] == 1
    assert report["issue_type_counts"]["shared_examples_across_split_pos"] == 1
    assert report["issue_type_counts"]["same_translation_uk_across_split_pos"] == 1
    assert report["groups"][0]["word"] == "one"
    assert len(report["groups"][0]["shared_examples"]) == 2

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved_report["groups"][0]["entries"][0]["source_ref"] == "one__numeral"
