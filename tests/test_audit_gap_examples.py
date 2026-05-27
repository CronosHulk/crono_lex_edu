from __future__ import annotations

import json
from pathlib import Path

from word_base.audit_gap_examples import audit_gap_examples, classify_gap_result


def test_classify_gap_result_marks_missing_word_as_example_issue() -> None:
    result = classify_gap_result(
        word="pace",
        example="This sentence mentions nothing relevant.",
        gap_output="This sentence mentions nothing relevant.",
    )

    assert result["issue_type"] == "example_issue"
    assert result["issue_reason"] == "target_word_missing_from_example"


def test_classify_gap_result_marks_detected_but_unchanged_example_as_module_issue() -> None:
    result = classify_gap_result(
        word="to pace",
        example="She kept pacing across the narrow room.",
        gap_output="She kept pacing across the narrow room.",
    )

    assert result["issue_type"] == "module_issue"
    assert result["exact_match"] is True


def test_audit_gap_examples_reports_problem_examples(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    report_path = tmp_path / "report.json"
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "to-pace__verb",
                        "word": "to pace",
                        "parts_of_speech": ["verb"],
                        "examples": [
                            "She kept pacing across the narrow room.",
                            "This sentence mentions nothing relevant.",
                        ],
                    },
                    {
                        "source_ref": "calm__adjective",
                        "word": "calm",
                        "parts_of_speech": ["adjective"],
                        "examples": ["The sea stayed calm throughout the morning."],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = audit_gap_examples(input_bundle_path=bundle_path, report_json_path=report_path)

    assert report["stats"]["total_examples"] == 3
    assert report["stats"]["ok_examples"] == 2
    assert report["stats"]["issue_examples"] == 1
    assert report["stats"]["example_issue_examples"] == 1
    assert report["stats"]["module_issue_examples"] == 0
    assert report["issues"] == [
        {
            "source_ref": "to-pace__verb",
            "word": "to pace",
            "part_of_speech": "verb",
            "example_index": 1,
            "example": "This sentence mentions nothing relevant.",
            "gap_output": "This sentence mentions nothing relevant.",
            "issue_type": "example_issue",
            "issue_reason": "target_word_missing_from_example",
            "word_count": 5,
            "exact_match": False,
            "likely_match": False,
        }
    ]

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved_report["stats"]["affected_entries"] == 1


def test_audit_gap_examples_treats_to_prefixed_phrasal_verbs_via_usage_form(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    report_path = tmp_path / "report.json"
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "to-check-in__phrasal-verb",
                        "word": "to check in",
                        "parts_of_speech": ["phrasal verb"],
                        "examples": ["Please check in before the morning meeting starts."],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = audit_gap_examples(input_bundle_path=bundle_path, report_json_path=report_path)

    assert report["stats"]["issue_examples"] == 0
    assert report["stats"]["ok_examples"] == 1
