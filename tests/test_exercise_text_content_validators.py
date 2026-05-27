from __future__ import annotations

import pytest

from app.application.admin.exercise_texts.content_jsonb import (
    ExerciseTextContentValidationError,
    collect_content_validation_errors,
    find_blocking_generation_statuses,
    validate_content_document,
)


def localized(content: str) -> dict:
    return {
        "source": {"lang": "en", "content": content},
        "translations": [
            {"lang": "uk", "content": f"uk {content}"},
            {"lang": "ru", "content": f"ru {content}"},
            {"lang": "pl", "content": f"pl {content}"},
        ],
    }


PARAGRAPH_TEXTS = [
    "One small robot opens the museum door. It greets every child. The children smile.",
    "A guide shows a bright computer room. Students touch old keyboards. They learn about early games.",
    "In the last hall, a drone flies slowly. It carries a tiny camera. Everyone watches the screen.",
]


def valid_generated_document() -> dict:
    paragraphs = [
        {
            "id": f"pg_valid_{index}",
            "status": {"content": "completed", "translations": "completed", "quiz": "completed", "tts": "pending"},
            "text": localized(text),
        }
        for index, text in enumerate(PARAGRAPH_TEXTS, start=1)
    ]
    questions = []
    for index, paragraph in enumerate(paragraphs, start=1):
        paragraph_text = paragraph["text"]["source"]["content"]
        quote = paragraph_text.split(".")[0] + "."
        questions.append(
            {
                "id": f"qz_valid_{index}",
                "paragraph_ids": [paragraph["id"]],
                "question": localized(f"What happens in paragraph {index}?"),
                "options": [
                    {
                        "id": f"op_valid_{index}_a",
                        "text": localized("Correct answer."),
                        "is_correct": True,
                        "evidence_quote": quote,
                        "evidence_span": {"paragraph_id": paragraph["id"], "start_char": 0, "end_char": len(quote)},
                        "explanation": localized("The quote supports this answer."),
                    },
                    {
                        "id": f"op_valid_{index}_b",
                        "text": localized("Wrong answer."),
                        "is_correct": False,
                        "evidence_quote": quote,
                        "evidence_span": {"paragraph_id": paragraph["id"], "start_char": 0, "end_char": len(quote)},
                        "explanation": localized("The quote does not support this answer."),
                    },
                    {
                        "id": f"op_valid_{index}_c",
                        "text": localized("Another wrong answer."),
                        "is_correct": False,
                        "evidence_quote": quote,
                        "evidence_span": {"paragraph_id": paragraph["id"], "start_char": 0, "end_char": len(quote)},
                        "explanation": localized("The paragraph says something else."),
                    },
                ],
            }
        )
    return {
        "schema_version": 1,
        "source": {
            "provided_by_admin": True,
            "generation_constraints": {"difficulty_band": "A1_A2", "text_types": ["it", "article"]},
        },
        "generated": {
            "title": "A Day at the Tech Museum",
            "ai_metadata": {"prompt_versions": {"content": "content-v1", "translations": "translations-v1", "quiz": "quiz-v1"}},
            "difficulty": {"band": "A1_A2", "min": "A1", "max": "A2"},
            "text_types": ["it", "article"],
            "target_vocabulary": [{"text": "museum", "lemma": "museum", "paragraph_ids": ["pg_valid_1"]}],
            "paragraphs": paragraphs,
            "questions": questions,
        },
        "generation_state": {"content": "completed", "translations": "completed", "quiz": "completed", "tts": "pending"},
    }


def error_fields(document: dict, **kwargs) -> list[str]:
    return [error.field for error in collect_content_validation_errors(document, **kwargs)]


def test_minimal_draft_content_passes_schema_validation() -> None:
    validate_content_document({"schema_version": 1})


def test_invalid_schema_version_returns_safe_error() -> None:
    with pytest.raises(ExerciseTextContentValidationError) as exc_info:
        validate_content_document({"schema_version": 2})

    assert exc_info.value.to_payload() == [{"field": "schema_version", "message": "schema_version must be 1"}]


def test_generated_content_rejects_invalid_allowlist_value() -> None:
    document = valid_generated_document()
    document["generated"]["text_types"] = ["unsupported"]

    assert "generated.text_types" in error_fields(document, require_generated=True)


def test_generated_content_rejects_malformed_localized_text() -> None:
    document = valid_generated_document()
    document["generated"]["paragraphs"][0]["text"]["translations"] = [{"lang": "uk", "content": "тільки українська"}]

    fields = error_fields(document, require_generated=True)

    assert "generated.paragraphs[0].text.translations.ru" in fields
    assert "generated.paragraphs[0].text.translations.pl" in fields


def test_generated_content_requires_prompt_versions() -> None:
    document = valid_generated_document()
    document["generated"]["ai_metadata"]["prompt_versions"]["quiz"] = ""

    fields = error_fields(document, require_generated=True)

    assert "generated.ai_metadata.prompt_versions.quiz" in fields


def test_valid_generated_quiz_content_passes_validation() -> None:
    validate_content_document(valid_generated_document(), require_generated=True, require_quiz=True)


def test_quiz_requires_three_options_and_one_correct_answer() -> None:
    document = valid_generated_document()
    options = document["generated"]["questions"][0]["options"]
    options.pop()
    options[0]["is_correct"] = False

    fields = error_fields(document, require_generated=True, require_quiz=True)

    assert "generated.questions[0].options" in fields


def test_evidence_span_must_match_english_paragraph_substring() -> None:
    document = valid_generated_document()
    document["generated"]["questions"][0]["options"][0]["evidence_span"]["end_char"] = 4

    fields = error_fields(document, require_generated=True, require_quiz=True)

    assert "generated.questions[0].options[0].evidence_span" in fields


def test_publishable_content_blocks_stale_failed_or_running_statuses() -> None:
    document = valid_generated_document()
    document["generated"]["paragraphs"][0]["status"]["tts"] = "stale"
    document["generation_state"]["quiz"] = "running"

    blocked = find_blocking_generation_statuses(document)
    fields = error_fields(document, require_publishable=True)

    assert "generation_state.quiz" in blocked
    assert "generated.paragraphs.pg_valid_1.status.tts" in blocked
    assert "generation_state.quiz" in fields
    assert "generated.paragraphs.pg_valid_1.status.tts" in fields


def test_publishable_content_requires_completed_required_generation_stages() -> None:
    document = valid_generated_document()
    del document["generation_state"]["quiz"]
    del document["generated"]["paragraphs"][1]["status"]["translations"]

    blocked = find_blocking_generation_statuses(document)
    fields = error_fields(document, require_publishable=True)

    assert "generation_state.quiz" in blocked
    assert "generated.paragraphs.pg_valid_2.status.translations" in blocked
    assert "generation_state.quiz" in fields
    assert "generated.paragraphs.pg_valid_2.status.translations" in fields


def test_publishable_content_requires_generated_title() -> None:
    document = valid_generated_document()
    document["generated"]["title"] = ""

    fields = error_fields(document, require_publishable=True)

    assert "generated.title" in fields
