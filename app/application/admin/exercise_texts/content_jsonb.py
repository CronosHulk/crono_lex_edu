from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

DIFFICULTY_BANDS = ("A1_A2", "B1_B2", "C1_C2")
EXERCISE_TEXT_STATUSES = ("draft", "generated", "ready", "published", "archived")
GENERATION_STAGE_STATES = ("pending", "running", "completed", "failed", "stale")
BLOCKING_GENERATION_STAGE_STATES = {"pending", "running", "failed", "stale"}
PUBLISH_REQUIRED_GENERATION_STAGES = ("content", "translations", "quiz")
TEXT_TYPES = ("science", "it", "law", "news", "article", "book_excerpt", "nature")
TRANSLATION_LANGUAGES = ("uk", "ru", "pl")
PROMPT_VERSION_STAGES = ("content", "translations", "quiz")
QUESTION_OPTION_COUNT = 3
PARAGRAPH_ID_RE = re.compile(r"^pg_[A-Za-z0-9][A-Za-z0-9_-]{4,}$")
QUESTION_ID_RE = re.compile(r"^qz_[A-Za-z0-9][A-Za-z0-9_-]{4,}$")
OPTION_ID_RE = re.compile(r"^op_[A-Za-z0-9][A-Za-z0-9_-]{4,}$")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+")


@dataclass(frozen=True)
class ContentValidationErrorItem:
    field: str
    message: str


class ExerciseTextContentValidationError(ValueError):
    def __init__(self, errors: list[ContentValidationErrorItem]) -> None:
        self.errors = errors
        super().__init__(errors[0].message if errors else "exercise_text_content_invalid")

    def to_payload(self) -> list[dict[str, str]]:
        return [{"field": error.field, "message": error.message} for error in self.errors]


def validate_content_document(
    document: dict[str, Any],
    *,
    require_generated: bool = False,
    require_quiz: bool = False,
    require_publishable: bool = False,
) -> None:
    errors = collect_content_validation_errors(
        document,
        require_generated=require_generated or require_publishable,
        require_quiz=require_quiz or require_publishable,
        require_publishable=require_publishable,
    )
    if errors:
        raise ExerciseTextContentValidationError(errors)


def collect_content_validation_errors(
    document: dict[str, Any],
    *,
    require_generated: bool = False,
    require_quiz: bool = False,
    require_publishable: bool = False,
) -> list[ContentValidationErrorItem]:
    errors: list[ContentValidationErrorItem] = []
    if not isinstance(document, dict):
        return [_error("content_jsonb", "content_jsonb must be an object")]
    _require_equal(document.get("schema_version"), 1, "schema_version", errors)
    _validate_source(document.get("source"), errors)
    _validate_generation_state(document.get("generation_state"), "generation_state", errors)
    generated = document.get("generated")
    if require_generated and not isinstance(generated, dict):
        errors.append(_error("generated", "generated must be an object"))
        return errors
    if isinstance(generated, dict):
        _validate_generated(
            generated,
            errors,
            require_generated=require_generated,
            require_quiz=require_quiz,
            require_publishable=require_publishable,
        )
    if require_publishable:
        for field in find_blocking_generation_statuses(document):
            errors.append(_error(field, "generation status must be completed before ready or published"))
    return errors


def find_blocking_generation_statuses(document: dict[str, Any]) -> list[str]:
    blocked: list[str] = []
    generation_state = document.get("generation_state")
    if not isinstance(generation_state, dict):
        blocked.append("generation_state")
    else:
        for stage in PUBLISH_REQUIRED_GENERATION_STAGES:
            if generation_state.get(stage) != "completed":
                _append_once(blocked, f"generation_state.{stage}")
        for key, value in generation_state.items():
            if value in BLOCKING_GENERATION_STAGE_STATES:
                _append_once(blocked, f"generation_state.{key}")
    generated = document.get("generated")
    if not isinstance(generated, dict):
        return blocked
    for index, paragraph in enumerate(_list_value(generated.get("paragraphs"))):
        status = paragraph.get("status") if isinstance(paragraph, dict) else None
        paragraph_id = paragraph.get("id") or str(index)
        if not isinstance(status, dict):
            blocked.append(f"generated.paragraphs.{paragraph_id}.status")
            continue
        for stage in PUBLISH_REQUIRED_GENERATION_STAGES:
            if status.get(stage) != "completed":
                _append_once(blocked, f"generated.paragraphs.{paragraph_id}.status.{stage}")
        for key, value in status.items():
            if value in BLOCKING_GENERATION_STAGE_STATES:
                _append_once(blocked, f"generated.paragraphs.{paragraph_id}.status.{key}")
    return blocked


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _validate_source(source: Any, errors: list[ContentValidationErrorItem]) -> None:
    if source is None:
        return
    if not isinstance(source, dict):
        errors.append(_error("source", "source must be an object"))
        return
    constraints = source.get("generation_constraints")
    if constraints is None:
        return
    if not isinstance(constraints, dict):
        errors.append(_error("source.generation_constraints", "generation_constraints must be an object"))
        return
    _validate_optional_allowed(constraints.get("difficulty_band"), DIFFICULTY_BANDS, "source.generation_constraints.difficulty_band", errors)
    _validate_allowed_list(constraints.get("text_types"), TEXT_TYPES, "source.generation_constraints.text_types", errors, required=False)


def _validate_generated(
    generated: dict[str, Any],
    errors: list[ContentValidationErrorItem],
    *,
    require_generated: bool,
    require_quiz: bool,
    require_publishable: bool,
) -> None:
    if require_publishable and (not isinstance(generated.get("title"), str) or not generated.get("title")):
        errors.append(_error("generated.title", "title is required before ready or published"))
    if require_generated:
        _validate_prompt_versions(generated.get("ai_metadata"), errors)
    difficulty = generated.get("difficulty")
    if difficulty is not None:
        if not isinstance(difficulty, dict):
            errors.append(_error("generated.difficulty", "difficulty must be an object"))
        else:
            _validate_optional_allowed(difficulty.get("band"), DIFFICULTY_BANDS, "generated.difficulty.band", errors)
    _validate_allowed_list(generated.get("text_types"), TEXT_TYPES, "generated.text_types", errors, required=require_generated)
    _validate_target_vocabulary(generated.get("target_vocabulary"), errors, required=require_generated)
    paragraphs = _validate_paragraphs(generated.get("paragraphs"), errors, required=require_generated)
    paragraph_text_by_id = {
        paragraph["id"]: paragraph["text"]["source"]["content"]
        for paragraph in paragraphs
        if _has_paragraph_source_text(paragraph)
    }
    if require_quiz:
        _validate_questions(generated.get("questions"), paragraph_text_by_id, errors)


def _validate_prompt_versions(value: Any, errors: list[ContentValidationErrorItem]) -> None:
    if not isinstance(value, dict):
        errors.append(_error("generated.ai_metadata", "ai_metadata must be an object"))
        return
    prompt_versions = value.get("prompt_versions")
    if not isinstance(prompt_versions, dict):
        errors.append(_error("generated.ai_metadata.prompt_versions", "prompt_versions must be an object"))
        return
    for stage in PROMPT_VERSION_STAGES:
        if not isinstance(prompt_versions.get(stage), str) or not prompt_versions.get(stage):
            errors.append(
                _error(
                    f"generated.ai_metadata.prompt_versions.{stage}",
                    f"{stage} prompt version is required for generated content",
                )
            )


def _validate_paragraphs(value: Any, errors: list[ContentValidationErrorItem], *, required: bool) -> list[dict[str, Any]]:
    if value is None and not required:
        return []
    if not isinstance(value, list):
        errors.append(_error("generated.paragraphs", "paragraphs must be a list"))
        return []
    if required and not 3 <= len(value) <= 4:
        errors.append(_error("generated.paragraphs", "paragraphs must contain 3-4 items"))
    paragraphs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, paragraph in enumerate(value):
        field = f"generated.paragraphs[{index}]"
        if not isinstance(paragraph, dict):
            errors.append(_error(field, "paragraph must be an object"))
            continue
        paragraph_id = _validate_id(paragraph.get("id"), PARAGRAPH_ID_RE, f"{field}.id", "paragraph id", errors)
        if paragraph_id in seen_ids:
            errors.append(_error(f"{field}.id", "paragraph id must be unique"))
        seen_ids.add(paragraph_id)
        _validate_generation_state(paragraph.get("status"), f"{field}.status", errors)
        _validate_localized_text(paragraph.get("text"), f"{field}.text", errors, required_translations=TRANSLATION_LANGUAGES)
        if _has_paragraph_source_text(paragraph):
            sentence_count = _count_sentences(paragraph["text"]["source"]["content"])
            if not 3 <= sentence_count <= 4:
                errors.append(_error(f"{field}.text.source.content", "English paragraph must contain 3-4 sentences"))
        paragraphs.append(paragraph)
    return paragraphs


def _validate_questions(value: Any, paragraph_text_by_id: dict[str, str], errors: list[ContentValidationErrorItem]) -> None:
    if not isinstance(value, list):
        errors.append(_error("generated.questions", "questions must be a list"))
        return
    seen_question_ids: set[str] = set()
    question_count_by_paragraph = {paragraph_id: 0 for paragraph_id in paragraph_text_by_id}
    for index, question in enumerate(value):
        field = f"generated.questions[{index}]"
        if not isinstance(question, dict):
            errors.append(_error(field, "question must be an object"))
            continue
        question_id = _validate_id(question.get("id"), QUESTION_ID_RE, f"{field}.id", "question id", errors)
        if question_id in seen_question_ids:
            errors.append(_error(f"{field}.id", "question id must be unique"))
        seen_question_ids.add(question_id)
        paragraph_ids = question.get("paragraph_ids")
        if not isinstance(paragraph_ids, list) or len(paragraph_ids) != 1:
            errors.append(_error(f"{field}.paragraph_ids", "question must reference exactly one paragraph"))
            linked_paragraph_id = None
        else:
            linked_paragraph_id = str(paragraph_ids[0])
            if linked_paragraph_id not in paragraph_text_by_id:
                errors.append(_error(f"{field}.paragraph_ids", "question references unknown paragraph"))
            else:
                question_count_by_paragraph[linked_paragraph_id] += 1
        _validate_localized_text(question.get("question"), f"{field}.question", errors, required_translations=TRANSLATION_LANGUAGES)
        _validate_options(question.get("options"), field, linked_paragraph_id, paragraph_text_by_id, errors)
    for paragraph_id, count in question_count_by_paragraph.items():
        if count != 1:
            errors.append(_error(f"generated.questions.{paragraph_id}", "each paragraph must have exactly one question"))


def _validate_options(
    value: Any,
    question_field: str,
    linked_paragraph_id: str | None,
    paragraph_text_by_id: dict[str, str],
    errors: list[ContentValidationErrorItem],
) -> None:
    if not isinstance(value, list):
        errors.append(_error(f"{question_field}.options", "options must be a list"))
        return
    if len(value) != QUESTION_OPTION_COUNT:
        errors.append(_error(f"{question_field}.options", "question must have exactly 3 options"))
    correct_count = 0
    seen_option_ids: set[str] = set()
    for index, option in enumerate(value):
        field = f"{question_field}.options[{index}]"
        if not isinstance(option, dict):
            errors.append(_error(field, "option must be an object"))
            continue
        option_id = _validate_id(option.get("id"), OPTION_ID_RE, f"{field}.id", "option id", errors)
        if option_id in seen_option_ids:
            errors.append(_error(f"{field}.id", "option id must be unique"))
        seen_option_ids.add(option_id)
        if option.get("is_correct") is True:
            correct_count += 1
        _validate_localized_text(option.get("text"), f"{field}.text", errors, required_translations=TRANSLATION_LANGUAGES)
        _validate_localized_text(option.get("explanation"), f"{field}.explanation", errors, required_translations=TRANSLATION_LANGUAGES)
        _validate_evidence(option, field, linked_paragraph_id, paragraph_text_by_id, errors)
    if correct_count != 1:
        errors.append(_error(f"{question_field}.options", "question must have exactly one correct option"))


def _validate_evidence(
    option: dict[str, Any],
    field: str,
    linked_paragraph_id: str | None,
    paragraph_text_by_id: dict[str, str],
    errors: list[ContentValidationErrorItem],
) -> None:
    quote = option.get("evidence_quote")
    if not isinstance(quote, str) or not quote:
        errors.append(_error(f"{field}.evidence_quote", "evidence_quote is required"))
        return
    span = option.get("evidence_span")
    if not isinstance(span, dict):
        errors.append(_error(f"{field}.evidence_span", "evidence_span must be an object"))
        return
    paragraph_id = span.get("paragraph_id")
    if not isinstance(paragraph_id, str) or paragraph_id not in paragraph_text_by_id:
        errors.append(_error(f"{field}.evidence_span.paragraph_id", "evidence_span paragraph_id is unknown"))
        return
    if linked_paragraph_id is not None and paragraph_id != linked_paragraph_id:
        errors.append(_error(f"{field}.evidence_span.paragraph_id", "evidence_span must point to the question paragraph"))
    start_char = span.get("start_char")
    end_char = span.get("end_char")
    if not isinstance(start_char, int) or not isinstance(end_char, int) or start_char < 0 or end_char <= start_char:
        errors.append(_error(f"{field}.evidence_span", "evidence_span must have valid start_char and end_char"))
        return
    paragraph_text = paragraph_text_by_id[paragraph_id]
    if end_char > len(paragraph_text) or paragraph_text[start_char:end_char] != quote:
        errors.append(_error(f"{field}.evidence_span", "evidence_quote must match evidence_span substring exactly"))


def _validate_localized_text(
    value: Any,
    field: str,
    errors: list[ContentValidationErrorItem],
    *,
    required_translations: tuple[str, ...],
) -> None:
    if not isinstance(value, dict):
        errors.append(_error(field, "localized text must be an object"))
        return
    source = value.get("source")
    if not isinstance(source, dict):
        errors.append(_error(f"{field}.source", "source must be an object"))
    else:
        if source.get("lang") != "en":
            errors.append(_error(f"{field}.source.lang", "source language must be en"))
        if not isinstance(source.get("content"), str) or not source.get("content"):
            errors.append(_error(f"{field}.source.content", "source content is required"))
    translations = value.get("translations")
    if not isinstance(translations, list):
        errors.append(_error(f"{field}.translations", "translations must be a list"))
        return
    by_lang = {item.get("lang"): item for item in translations if isinstance(item, dict)}
    for lang in required_translations:
        item = by_lang.get(lang)
        if item is None:
            errors.append(_error(f"{field}.translations.{lang}", f"{lang} translation is required"))
            continue
        if not isinstance(item.get("content"), str) or not item.get("content"):
            errors.append(_error(f"{field}.translations.{lang}.content", f"{lang} translation content is required"))


def _validate_target_vocabulary(value: Any, errors: list[ContentValidationErrorItem], *, required: bool) -> None:
    if value is None and not required:
        return
    if not isinstance(value, list) or not value:
        errors.append(_error("generated.target_vocabulary", "target_vocabulary must be a non-empty list"))
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(_error(f"generated.target_vocabulary[{index}]", "target vocabulary item must be an object"))
            continue
        if not isinstance(item.get("lemma"), str) or not item.get("lemma"):
            errors.append(_error(f"generated.target_vocabulary[{index}].lemma", "target vocabulary lemma is required"))


def _validate_generation_state(value: Any, field: str, errors: list[ContentValidationErrorItem]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(_error(field, "generation state must be an object"))
        return
    for key, state in value.items():
        if state not in GENERATION_STAGE_STATES:
            errors.append(_error(f"{field}.{key}", f"generation state must be one of: {', '.join(GENERATION_STAGE_STATES)}"))


def _validate_allowed_list(
    value: Any,
    allowed_values: tuple[str, ...],
    field: str,
    errors: list[ContentValidationErrorItem],
    *,
    required: bool,
) -> None:
    if value is None and not required:
        return
    if not isinstance(value, list) or not value:
        errors.append(_error(field, "must be a non-empty list"))
        return
    allowed = set(allowed_values)
    for item in value:
        if item not in allowed:
            errors.append(_error(field, f"contains unsupported value: {item}"))


def _validate_optional_allowed(value: Any, allowed_values: tuple[str, ...], field: str, errors: list[ContentValidationErrorItem]) -> None:
    if value is None:
        return
    if value not in set(allowed_values):
        errors.append(_error(field, f"must be one of: {', '.join(allowed_values)}"))


def _validate_id(value: Any, pattern: re.Pattern[str], field: str, label: str, errors: list[ContentValidationErrorItem]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        errors.append(_error(field, f"{label} must use a stable prefixed id"))
        return ""
    return value


def _has_paragraph_source_text(paragraph: dict[str, Any]) -> bool:
    text = paragraph.get("text")
    return isinstance(text, dict) and isinstance(text.get("source"), dict) and isinstance(text["source"].get("content"), str)


def _count_sentences(value: str) -> int:
    matches = SENTENCE_RE.findall(value.strip())
    return len(matches)


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _require_equal(value: Any, expected: Any, field: str, errors: list[ContentValidationErrorItem]) -> None:
    if value != expected:
        errors.append(_error(field, f"{field} must be {expected}"))


def _error(field: str, message: str) -> ContentValidationErrorItem:
    return ContentValidationErrorItem(field=field, message=message)
