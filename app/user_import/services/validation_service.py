from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.provider_settings import WORD_VALIDATION_TASK_KEY
from app.domain.user_import.text_parser import ParsedImportWord
from app.helpers.external_error_text import format_external_error
from app.user_import.provider_ports import (
    WordValidationProvider,
    WordValidationProviderError,
)
from app.user_import.providers import (
    read_user_import_provider_task_setting,
)
from app.user_import.runtime_settings import (
    DEFAULT_IMPORT_RUNTIME_SETTINGS,
    read_user_import_runtime_settings,
)
from app.user_import.services.error_logging import log_user_import_pipeline_error
from app.validators.user_import_provider_results import (
    AIImportValidationResult,
    AIValidatedImportWord,
)


@dataclass(frozen=True)
class UserImportValidationOutcome:
    valid_words: list[ParsedImportWord]
    rejected_items: list[dict[str, str]]
    validation_result: AIImportValidationResult | None


BuildWordValidationProvider = Callable[[Any, dict[str, Any] | None], WordValidationProvider | None]


def _disabled_word_validation_provider(
    _settings: Any,
    _task_settings: dict[str, Any] | None = None,
) -> WordValidationProvider | None:
    return None


class UserImportValidationService:
    def __init__(
        self,
        db: Any,
        *,
        build_validation_provider: BuildWordValidationProvider = _disabled_word_validation_provider,
    ) -> None:
        self.db = db
        self.build_validation_provider = build_validation_provider

    def validate_words(self, candidates: list[ParsedImportWord]) -> UserImportValidationOutcome:
        if not candidates:
            return UserImportValidationOutcome([], [], None)
        provider = self.build_validation_provider(
            self.db.settings,
            read_user_import_provider_task_setting(self.db, WORD_VALIDATION_TASK_KEY),
        )
        if provider is None:
            return UserImportValidationOutcome(candidates, [], None)

        validation_results: list[AIImportValidationResult] = []
        skipped_candidates: list[ParsedImportWord] = []
        batch_size = self._validation_batch_size()
        for candidate_batch in _chunk_candidates(candidates, batch_size):
            try:
                validation_results.append(provider.validate(candidate_batch))
            except WordValidationProviderError as error:
                self._log_validation_skip(error.original_error)
                skipped_candidates.extend(candidate_batch)
        if not validation_results:
            return UserImportValidationOutcome(candidates, [], None)
        validation_result = _merge_validation_results(validation_results, skipped_candidates)

        rejected = validation_result.rejected_lookup_words
        accepted = validation_result.accepted_lookup_words
        valid_words: list[ParsedImportWord] = []
        for item in candidates:
            if item.lookup_word not in accepted or item.lookup_word in rejected:
                continue
            validated = validation_result.accepted_items.get(item.lookup_word)
            if validated is None:
                valid_words.append(item)
                continue
            valid_words.append(
                ParsedImportWord(
                    raw_value=item.raw_value,
                    lookup_word=item.lookup_word,
                    translation_hint=validated.translation_hint or item.translation_hint,
                    validated_lookup_word=validated.lookup_word if validated.lookup_word != item.lookup_word else None,
                    validated_part_of_speech=validated.part_of_speech,
                    validated_translation_uk=validated.translation_uk,
                    validated_translation_ru=validated.translation_ru,
                    validated_translation_pl=validated.translation_pl,
                )
            )

        rejected_items = [
            {
                "raw_value": item.raw_value,
                "lookup_word": item.lookup_word,
                "status": "rejected",
                "error_text": rejected.get(item.lookup_word) or "Rejected by import validation",
            }
            for item in candidates
            if item.lookup_word in rejected or item.lookup_word not in accepted
        ]
        return UserImportValidationOutcome(valid_words, rejected_items, validation_result)

    def record_usage(
        self,
        validation_result: AIImportValidationResult | None,
        *,
        task_scope: str,
        actor_user_uuid: str,
        source_type: str | None,
        source_identifier: str | None,
        import_job_id: int | None,
        task_log_id: int | None,
        batch_key: str,
        current_time: datetime,
    ) -> None:
        if validation_result is None:
            return
        repository = getattr(self.db, "ai_usage_sessions", None)
        usage = validation_result.provider_payload.get("_cronolex_usage")
        if repository is None or not isinstance(usage, dict):
            return
        repository.accumulate(
            task_key=WORD_VALIDATION_TASK_KEY,
            task_scope=task_scope,
            provider_key=str(usage.get("provider_key") or "openai"),
            model=str(usage.get("model") or "unknown"),
            actor_type="telegram_user",
            actor_user_uuid=actor_user_uuid,
            actor_group_title=None,
            source_type=source_type,
            source_identifier=source_identifier,
            import_job_id=import_job_id,
            task_log_id=task_log_id,
            batch_key=batch_key,
            request_count=int(usage.get("request_count") or 0),
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
            estimated_cost_usd=usage.get("estimated_cost_usd") or "0",
            pricing_source=usage.get("pricing_source"),
            status="success",
            summary="User import word validation",
            metadata_json={
                "accepted_count": len(validation_result.accepted_lookup_words),
                "rejected_count": len(validation_result.rejected_lookup_words),
            },
            started=current_time,
            finished=current_time,
            created=current_time,
            updated=current_time,
        )

    def _validation_batch_size(self) -> int:
        try:
            runtime_settings = read_user_import_runtime_settings(self.db)
        except Exception:
            runtime_settings = DEFAULT_IMPORT_RUNTIME_SETTINGS
        return max(int(runtime_settings["validation_batch_size"]), 1)

    def _log_validation_skip(self, error: Exception) -> None:
        log_user_import_pipeline_error(
            self.db,
            stage="word_validation",
            error=error,
            error_text=format_external_error(error, fallback="AI import validation skipped"),
            task_key=WORD_VALIDATION_TASK_KEY,
            provider_key="openai",
            context_json={"optional_validation_skipped": True},
        )


def _chunk_candidates(candidates: list[ParsedImportWord], batch_size: int) -> list[list[ParsedImportWord]]:
    return [candidates[index : index + batch_size] for index in range(0, len(candidates), batch_size)]


def _merge_validation_results(
    validation_results: list[AIImportValidationResult],
    skipped_candidates: list[ParsedImportWord],
) -> AIImportValidationResult:
    accepted_lookup_words = {item.lookup_word for item in skipped_candidates}
    rejected_lookup_words: dict[str, str] = {}
    accepted_items: dict[str, AIValidatedImportWord] = {}
    usage_items: list[dict[str, Any]] = []
    for result in validation_results:
        accepted_lookup_words.update(result.accepted_lookup_words)
        rejected_lookup_words.update(result.rejected_lookup_words)
        accepted_items.update(result.accepted_items)
        usage = result.provider_payload.get("_cronolex_usage")
        if isinstance(usage, dict):
            usage_items.append(usage)
    provider_payload: dict[str, Any] = {"validation_batch_count": len(validation_results)}
    usage = _merge_usage_items(usage_items)
    if usage is not None:
        provider_payload["_cronolex_usage"] = usage
    return AIImportValidationResult(
        accepted_lookup_words=accepted_lookup_words,
        rejected_lookup_words=rejected_lookup_words,
        provider_payload=provider_payload,
        accepted_items=accepted_items,
    )


def _merge_usage_items(usage_items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not usage_items:
        return None
    first = usage_items[0]
    estimated_cost = sum((_decimal_value(item.get("estimated_cost_usd")) for item in usage_items), Decimal("0"))
    pricing_sources = {
        str(item.get("pricing_source"))
        for item in usage_items
        if item.get("pricing_source") is not None
    }
    return {
        "provider_key": str(first.get("provider_key") or "openai"),
        "model": str(first.get("model") or "unknown"),
        "request_count": sum(_int_value(item.get("request_count")) for item in usage_items),
        "input_tokens": sum(_int_value(item.get("input_tokens")) for item in usage_items),
        "output_tokens": sum(_int_value(item.get("output_tokens")) for item in usage_items),
        "total_tokens": sum(_int_value(item.get("total_tokens")) for item in usage_items),
        "estimated_cost_usd": str(estimated_cost),
        "pricing_source": ", ".join(sorted(pricing_sources)) if pricing_sources else None,
    }


def _int_value(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0")
