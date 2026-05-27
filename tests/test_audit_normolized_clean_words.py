from __future__ import annotations

import json
from pathlib import Path

from word_base.audit_normolized_clean_words import audit_normolized_clean_words


def test_audit_normolized_clean_words_builds_local_report_and_api_candidates(tmp_path: Path) -> None:
    input_bundle = tmp_path / "normolized_clean_words.json"
    audit_report = tmp_path / "local_audit.json"
    api_candidates = tmp_path / "api_candidates.json"
    input_bundle.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "love__noun",
                        "word": "love",
                        "parts_of_speech": ["noun"],
                        "translation_uk": "любов, кохати",
                        "translation_ru": "любовь, любить",
                        "translation_pl": "miłość, kochać",
                        "examples": ["Love is complicated.", "I love coffee."],
                        "synonym_source_refs": ["to-love__verb", "fondness__noun"],
                        "needs_detail_review": True,
                    },
                    {
                        "source_ref": "to-love__verb",
                        "word": "to love",
                        "parts_of_speech": ["verb"],
                        "translation_uk": "любов, кохати",
                        "translation_ru": "любовь, любить",
                        "translation_pl": "miłość, kochać",
                        "examples": ["Love is complicated.", "I love coffee."],
                        "synonym_source_refs": ["love__noun"],
                        "needs_detail_review": True,
                    },
                    {
                        "source_ref": "fondness__noun",
                        "word": "fondness",
                        "parts_of_speech": ["noun"],
                        "translation_uk": "ніжність",
                        "translation_ru": "нежность",
                        "translation_pl": "czułość",
                        "examples": ["Her fondness for music was obvious."],
                        "synonym_source_refs": ["to-adore__verb"],
                        "needs_detail_review": False,
                    },
                    {
                        "source_ref": "respect__noun",
                        "word": "respect",
                        "parts_of_speech": ["noun"],
                        "translation_uk": "повага",
                        "translation_ru": "уважение",
                        "translation_pl": "szacunek",
                        "examples": ["Mutual respect matters."],
                        "synonym_source_refs": [],
                        "needs_detail_review": False,
                    },
                    {
                        "source_ref": "to-respect__verb",
                        "word": "to respect",
                        "parts_of_speech": ["verb"],
                        "translation_uk": "поважати",
                        "translation_ru": "уважать",
                        "translation_pl": "szanować",
                        "examples": ["Please respect the rules."],
                        "synonym_source_refs": [],
                        "needs_detail_review": False,
                    },
                    {
                        "source_ref": "to-adore__verb",
                        "word": "to adore",
                        "parts_of_speech": ["verb"],
                        "translation_uk": "обожнювати",
                        "translation_ru": "обожать",
                        "translation_pl": "uwielbiać",
                        "examples": ["They adore their child."],
                        "synonym_source_refs": ["fondness__noun"],
                        "needs_detail_review": False,
                    },
                ],
                "normalization_report": {
                    "ambiguous_synonym_expansions": [
                        {
                            "entry_source_ref": "fondness__noun",
                            "original_target_source_ref": "core:123",
                            "expanded_target_source_refs": [
                                "respect__noun",
                                "to-respect__verb",
                            ],
                        }
                    ]
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = audit_normolized_clean_words(
        input_bundle_path=input_bundle,
        audit_report_path=audit_report,
        api_candidates_path=api_candidates,
    )

    report = result["audit_report"]
    assert report["split_word_group_count"] == 1
    assert report["ambiguous_synonym_case_count"] == 1
    assert report["cross_pos_synonym_case_count"] == 1
    assert report["api_candidate_high_priority_count"] >= 1

    split_group = report["split_groups"][0]
    assert split_group["base_word"] == "love"
    assert "same_translation_uk_across_split_pos" in split_group["reasons"]
    assert "same_examples_across_split_pos" in split_group["reasons"]

    ambiguous_case = report["ambiguous_synonym_cases"][0]
    assert ambiguous_case["entry_source_ref"] == "fondness__noun"
    assert "ambiguous_synonym_target_after_split" in ambiguous_case["reasons"]
    assert "expanded_targets_span_multiple_pos" in ambiguous_case["reasons"]

    candidate_rows = {item["source_ref"]: item for item in result["api_candidates"]["candidates"]}
    assert candidate_rows["fondness__noun"]["priority"] == "high"
    assert "ambiguous_synonym_target_after_split" in candidate_rows["fondness__noun"]["reasons"]
    assert "love__noun" in candidate_rows
    assert "to-love__verb" in candidate_rows

    persisted_report = json.loads(audit_report.read_text(encoding="utf-8"))
    persisted_candidates = json.loads(api_candidates.read_text(encoding="utf-8"))
    assert persisted_report["api_candidate_count"] == len(persisted_candidates["candidates"])
