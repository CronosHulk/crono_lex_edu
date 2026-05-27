from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.domain.provider_settings import (
    DEFAULT_OPENAI_API_URL as DEFAULT_OPENAI_API_URL,
)
from app.domain.provider_settings import (
    DEFAULT_USER_IMPORT_OPENAI_MODEL as DEFAULT_USER_IMPORT_OPENAI_MODEL,
)
from app.domain.user_import.prompts import (
    build_user_import_openai_prompt,
    build_user_import_validation_prompt,
)
from app.domain.user_import.text_parser import MAX_IMPORT_ITEM_CHARS, ParsedImportWord
from app.external_providers.usage import openai_usage_from_response
from app.reference.dictionary_entries import DICTIONARY_PART_OF_SPEECH_TYPES
from app.reference.service import LEVEL_ORDER
from app.validators.user_import_provider_results import (
    AIImportValidationResult,
    validate_user_import_openai_result,
    validate_user_import_validation_result,
)
from app.word_validation import validate_ascii_word_form


def resolve_openai_api_key() -> str:
    value = os.environ.get("OPENAI__API_KEY", "").strip() or os.environ.get("OPENAI__API", "").strip()
    if not value:
        raise RuntimeError("OPENAI__API_KEY is not configured.")
    return value


def validate_user_import_candidates_with_openai(
    *,
    client: httpx.Client,
    candidates: list[ParsedImportWord],
    model: str,
    api_url: str,
) -> AIImportValidationResult:
    normalized_candidates = [
        ParsedImportWord(
            raw_value=str(candidate.raw_value or "").strip()[:MAX_IMPORT_ITEM_CHARS],
            lookup_word=validate_ascii_word_form(candidate.lookup_word, field_name="lookup_word", source_ref="lookup_word"),
            translation_hint=candidate.translation_hint,
        )
        for candidate in candidates
    ]
    if not normalized_candidates:
        return AIImportValidationResult(accepted_lookup_words=set(), rejected_lookup_words={}, provider_payload={})
    prompt_text = build_user_import_validation_prompt(normalized_candidates)
    candidate_lookup_word_enum = [item.lookup_word for item in normalized_candidates]
    request_payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": "You validate English vocabulary import candidates and return strict JSON."}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt_text}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "user_import_word_validation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "accepted": {"type": "array", "items": {"type": "string", "enum": candidate_lookup_word_enum}},
                        "accepted_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "lookup_word": {"type": "string", "enum": candidate_lookup_word_enum},
                                    "normalized_lookup_word": {"type": "string"},
                                    "part_of_speech": {
                                        "type": "string",
                                        "enum": list(DICTIONARY_PART_OF_SPEECH_TYPES),
                                    },
                                    "translation_uk": {"type": "string"},
                                    "translation_ru": {"type": "string"},
                                    "translation_pl": {"type": "string"},
                                },
                                "required": [
                                    "lookup_word",
                                    "normalized_lookup_word",
                                    "part_of_speech",
                                    "translation_uk",
                                    "translation_ru",
                                    "translation_pl",
                                ],
                            },
                        },
                        "rejected": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "lookup_word": {"type": "string", "enum": candidate_lookup_word_enum},
                                    "reason": {"type": "string"},
                                },
                                "required": ["lookup_word", "reason"],
                            },
                        },
                    },
                    "required": ["accepted", "accepted_items", "rejected"],
                },
            }
        },
    }
    response = client.post(
        api_url,
        headers={
            "Authorization": f"Bearer {resolve_openai_api_key()}",
            "Content-Type": "application/json",
        },
        json=request_payload,
    )
    response.raise_for_status()
    response_json = response.json()
    output_text = _extract_openai_output_text(response_json)
    parsed = json.loads(output_text)
    accepted, rejected, accepted_items = validate_user_import_validation_result(
        candidates=normalized_candidates,
        payload=parsed,
    )
    usage = openai_usage_from_response(
        response_json=response_json,
        model=model,
        prompt_text=prompt_text,
        output_text=output_text,
    )
    response_json["_cronolex_usage"] = usage.to_status_json()
    return AIImportValidationResult(
        accepted_lookup_words=accepted,
        rejected_lookup_words=rejected,
        provider_payload=response_json,
        accepted_items=accepted_items,
    )


def _extract_openai_output_text(response_json: dict[str, Any]) -> str:
    output_text = response_json.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    for item in response_json.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    raise ValueError("OpenAI response did not contain output_text message")


def refine_user_import_with_openai(
    *,
    client: httpx.Client,
    lookup_word: str,
    part_of_speech: str | None,
    translation_uk: str | None,
    translation_ru: str | None,
    translation_pl: str | None,
    phonetic_us: str | None,
    examples_json: list[str],
    model: str,
    api_url: str,
    details_retry_feedback: str | None = None,
) -> tuple[str, str, str, str, str, str, list[str], dict[str, Any]]:
    normalized_lookup_word = validate_ascii_word_form(lookup_word, field_name="lookup_word", source_ref="lookup_word")
    request_payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You refine user-import vocabulary details and return strict JSON.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "",
                    }
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "user_import_word_details",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "part_of_speech": {"type": "string"},
                        "level": {"type": "string", "enum": list(LEVEL_ORDER)},
                        "phonetic_us": {"type": "string"},
                        "translation_uk": {"type": "string"},
                        "translation_ru": {"type": "string"},
                        "translation_pl": {"type": "string"},
                        "examples": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "part_of_speech",
                        "level",
                        "phonetic_us",
                        "translation_uk",
                        "translation_ru",
                        "translation_pl",
                        "examples",
                    ],
                },
            }
        },
    }
    prompt_text = build_user_import_openai_prompt(
        lookup_word=normalized_lookup_word,
        part_of_speech=part_of_speech,
        translation_uk=translation_uk,
        translation_ru=translation_ru,
        translation_pl=translation_pl,
        phonetic_us=phonetic_us,
        examples_json=examples_json,
        details_retry_feedback=details_retry_feedback,
    )
    request_payload["input"][1]["content"][0]["text"] = prompt_text
    response = client.post(
        api_url,
        headers={
            "Authorization": f"Bearer {resolve_openai_api_key()}",
            "Content-Type": "application/json",
        },
        json=request_payload,
    )
    response.raise_for_status()
    response_json = response.json()
    output_text = _extract_openai_output_text(response_json)
    parsed = json.loads(output_text)
    refined_pos, refined_level, refined_phonetic, refined_uk, refined_ru, refined_pl, refined_examples = validate_user_import_openai_result(
        lookup_word=normalized_lookup_word,
        payload=parsed,
    )
    usage = openai_usage_from_response(
        response_json=response_json,
        model=model,
        prompt_text=prompt_text,
        output_text=output_text,
    )
    response_json["_cronolex_usage"] = usage.to_status_json()
    return refined_pos, refined_level, refined_phonetic, refined_uk, refined_ru, refined_pl, refined_examples, response_json
