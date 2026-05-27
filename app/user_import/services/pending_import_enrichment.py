from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.provider_settings import DEFAULT_OPENAI_API_URL, DEFAULT_USER_IMPORT_OPENAI_MODEL
from app.domain.user_import.text_parser import is_allowed_lookup_word
from app.helpers.external_error_text import format_word_details_provider_error
from app.reference.dictionary_entries import dictionary_entry_type_from_part_of_speech
from app.storage.user_import_artifacts import UserImportArtifactStorageProvider
from app.user_import.provider_ports import WordDetailsProvider
from app.validators.user_import_provider_results import (
    _normalize_optional_validation_text,
    _normalize_translation_text,
)
from app.word_validation import validate_ascii_word_form


@dataclass(frozen=True)
class ImportEnrichmentResult:
    word: str
    entry_type: str
    translation_uk: str | None
    translation_ru: str | None
    translation_pl: str | None
    part_of_speech: str | None
    phonetic_us: str | None
    phonetic_uk: str | None
    audio_path: str | None
    examples_json: list[str]
    source_payload_refs_json: dict[str, str]
    source_provider_status_json: dict[str, dict[str, Any]]
    status: str
    rejected_reason: str | None = None
    should_retry: bool = False
    level_id: int | None = None
    embedding: list[float] | None = None
    embedding_model: str | None = None
    is_embedding_ready: bool = False


def resolve_pending_import_word(
    *,
    lookup_word: str,
    telegram_user_id: int,
    artifact_storage_provider: UserImportArtifactStorageProvider,
    current_time: datetime,
    openai_refine_enabled: bool = True,
    openai_model: str = DEFAULT_USER_IMPORT_OPENAI_MODEL,
    openai_api_url: str = DEFAULT_OPENAI_API_URL,
    word_details_provider: WordDetailsProvider | None = None,
    language_level_id_by_title: dict[str, int] | None = None,
    part_of_speech: str | None = None,
    translation_uk: str | None = None,
    translation_ru: str | None = None,
    translation_pl: str | None = None,
    details_retry_feedback: str | None = None,
) -> ImportEnrichmentResult:
    lookup_word = validate_ascii_word_form(lookup_word, field_name="lookup_word", source_ref="lookup_word")
    provider_status: dict[str, dict[str, Any]] = {}
    payload_refs: dict[str, str] = {}
    part_of_speech = _normalize_optional_validation_text(part_of_speech, max_length=80)
    phonetic_us: str | None = None
    translation_uk = _normalize_translation_text(translation_uk)
    translation_ru = _normalize_translation_text(translation_ru)
    translation_pl = _normalize_translation_text(translation_pl)
    examples_json: list[str] = []
    audio_path: str | None = None
    level_id: int | None = None

    if openai_refine_enabled and word_details_provider is not None:
        try:
            details_provider_name = getattr(word_details_provider, "provider_name", "word_details_provider")
            (
                refined_pos,
                refined_level,
                refined_phonetic,
                refined_uk,
                refined_ru,
                refined_pl,
                refined_examples,
                provider_payload,
            ) = word_details_provider.enrich(
                lookup_word=lookup_word,
                part_of_speech=part_of_speech,
                translation_uk=translation_uk,
                translation_ru=translation_ru,
                translation_pl=translation_pl,
                phonetic_us=phonetic_us,
                examples_json=examples_json,
                details_retry_feedback=details_retry_feedback,
            )
            payload_refs[details_provider_name] = artifact_storage_provider.write_provider_payload(
                telegram_user_id=telegram_user_id,
                lookup_word=lookup_word,
                provider=details_provider_name,
                created_at=current_time,
                payload=provider_payload,
            )
            part_of_speech = refined_pos
            refined_level = str(refined_level or "").strip().upper()
            if refined_level:
                level_id = (language_level_id_by_title or {}).get(refined_level)
            phonetic_us = refined_phonetic
            translation_uk = refined_uk
            translation_ru = refined_ru
            translation_pl = refined_pl
            examples_json = refined_examples
            details_error: str | None = None
            if not refined_level:
                details_error = "details response missing level"
            elif level_id is None:
                details_error = f"level mapping failed: {refined_level}"
            provider_status[details_provider_name] = {
                "status": "error" if details_error else "ok",
                "part_of_speech": bool(refined_pos),
                "level": refined_level,
                "level_id": level_id,
                "phonetic_us": bool(refined_phonetic),
                "translation_uk": bool(refined_uk),
                "translation_ru": bool(refined_ru),
                "translation_pl": bool(refined_pl),
                "examples_json": len(refined_examples),
                "model": str(getattr(word_details_provider, "model", openai_model)),
            }
            if details_error:
                provider_status[details_provider_name]["error"] = details_error
            if isinstance(provider_payload, dict) and isinstance(provider_payload.get("_cronolex_usage"), dict):
                provider_status[details_provider_name]["usage"] = provider_payload["_cronolex_usage"]
        except Exception as error:
            details_provider_name = getattr(word_details_provider, "provider_name", "word_details_provider")
            provider_status[details_provider_name] = {
                "status": "error",
                "error": format_word_details_provider_error(error),
                "model": str(getattr(word_details_provider, "model", openai_model)),
            }
    elif openai_refine_enabled and word_details_provider is None:
        provider_status["word_details_provider"] = {
            "status": "error",
            "error": "details provider disabled/unavailable",
        }

    rejected_reason: str | None = None
    details_provider_error = next(
        (
            str(value.get("error"))
            for value in provider_status.values()
            if isinstance(value, dict)
            and value.get("status") == "error"
            and value.get("error")
        ),
        None,
    )
    if not is_allowed_lookup_word(lookup_word):
        rejected_reason = "слово не пройшло валідацію формату"
    elif details_provider_error:
        rejected_reason = details_provider_error
    elif not translation_uk:
        rejected_reason = "не знайдено translation_uk"
    elif not part_of_speech:
        rejected_reason = "не знайдено part_of_speech"
    elif level_id is None:
        rejected_reason = "не знайдено level_id"
    elif not phonetic_us:
        rejected_reason = "не знайдено phonetic_us"

    provider_failed = any(value.get("status") == "error" for value in provider_status.values())
    should_retry = provider_failed and rejected_reason is not None

    return ImportEnrichmentResult(
        word=lookup_word,
        entry_type=dictionary_entry_type_from_part_of_speech(part_of_speech),
        translation_uk=translation_uk,
        translation_ru=translation_ru,
        translation_pl=translation_pl,
        part_of_speech=part_of_speech,
        phonetic_us=phonetic_us,
        phonetic_uk=None,
        audio_path=audio_path,
        examples_json=examples_json,
        source_payload_refs_json=payload_refs,
        source_provider_status_json=provider_status,
        status="collecting" if should_retry else ("build_failed" if rejected_reason else "ready_for_attribute_review"),
        rejected_reason=rejected_reason,
        should_retry=should_retry,
        level_id=level_id,
    )
