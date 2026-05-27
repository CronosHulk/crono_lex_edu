from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Protocol, cast
from uuid import UUID

from app.acl.processor import AclPermissionReader
from app.application.admin.exercise_texts.content_jsonb import (
    ExerciseTextContentValidationError,
    validate_content_document,
)
from app.application.admin.exercise_texts.errors import (
    AdminExerciseTextGenerationAccessDeniedError,
    AdminExerciseTextGenerationConflictError,
    AdminExerciseTextGenerationNotFoundError,
    AdminExerciseTextGenerationValidationError,
)
from app.application.admin.exercise_texts.providers import (
    EXERCISE_TEXT_GENERATION_TASK_KEY,
    ExerciseTextGenerationProvider,
    ExerciseTextGenerationProviderDisabledError,
    ExerciseTextGenerationProviderFactory,
    ExerciseTextGenerationRequest,
    UnsupportedExerciseTextGenerationProviderError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.domain.exercise_texts.errors import ExerciseTextVersionConflictError
from app.helpers.external_error_text import sanitize_external_error_text
from app.time_utils import TimeService

EXERCISE_TEXT_GENERATION_STAGES = ("content", "translations", "quiz")


class AdminExerciseTextGenerationExerciseTextsPort(Protocol):
    def get(self, exercise_text_id: int) -> dict[str, Any] | None: ...

    def update(
        self,
        exercise_text_id: int,
        *,
        expected_version: int,
        values: dict[str, Any],
        topic_ids: list[int] | None = None,
        actor_user_uuid: UUID | str | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any] | None: ...


class AdminExerciseTextGenerationTaskLogsPort(Protocol):
    def get(self, task_log_id: int) -> dict[str, Any] | None: ...

    def update(
        self,
        task_log_id: int,
        *,
        status: str,
        current_time: datetime,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
        import_job_id: int | None = None,
    ) -> dict[str, Any] | None: ...

    def create_for_user_uuid(
        self,
        *,
        task_type: str,
        status: str,
        current_time: datetime,
        user_uuid: str | UUID | None = None,
        source_type: str | None = None,
        source_identifier: str | None = None,
        import_job_id: int | None = None,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class AdminExerciseTextGenerationExternalProviderSettingsPort(Protocol):
    def get_map(self) -> dict[str, dict[str, Any]]: ...


class AdminExerciseTextGenerationAIUsageSessionsPort(Protocol):
    def accumulate(self, **kwargs: Any) -> dict[str, Any]: ...


class AdminExerciseTextGenerationUsageDatabasePort(Protocol):
    ai_usage_sessions: AdminExerciseTextGenerationAIUsageSessionsPort


class AdminExerciseTextGenerationDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    task_logs: AdminExerciseTextGenerationTaskLogsPort
    exercise_texts: AdminExerciseTextGenerationExerciseTextsPort
    external_provider_settings: AdminExerciseTextGenerationExternalProviderSettingsPort
    settings: Any


class AdminExerciseTextGenerationService:
    def __init__(
        self,
        db: AdminExerciseTextGenerationDatabasePort,
        time_service: TimeService,
        provider: ExerciseTextGenerationProvider | None = None,
        provider_factory: ExerciseTextGenerationProviderFactory | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.provider_override = provider
        self.provider_factory = provider_factory

    def start_generation(self, *, actor: dict[str, Any], exercise_text_id: int, stage: str) -> dict[str, Any]:
        self._require_publish_access(actor)
        return self._start_generation(actor=actor, exercise_text_id=exercise_text_id, stage=stage)

    def generate_all(self, *, actor: dict[str, Any], exercise_text_id: int) -> dict[str, Any]:
        self._require_publish_access(actor)
        results = []
        for stage in EXERCISE_TEXT_GENERATION_STAGES:
            result = self._start_generation(actor=actor, exercise_text_id=exercise_text_id, stage=stage)
            results.append(result["task"])
            if result["task"]["status"] != "success":
                break
        return {"tasks": results, "exercise_text": self._require_item(exercise_text_id)}

    def get_generation_task(self, *, actor: dict[str, Any], exercise_text_id: int, task_id: int) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/view")
        item = self._require_item(exercise_text_id)
        task = self.db.task_logs.get(task_id)
        if task is None:
            raise AdminExerciseTextGenerationNotFoundError("Exercise text generation task not found")
        if task.get("source_type") != "exercise_text" or str(task.get("source_identifier")) != str(exercise_text_id):
            raise AdminExerciseTextGenerationNotFoundError("Exercise text generation task not found")
        generation_task_types = {f"exercise_texts.{stage}_generation" for stage in EXERCISE_TEXT_GENERATION_STAGES}
        generation_task_types.add("exercise_texts.tts_generation")
        if str(task.get("task_type") or "") not in generation_task_types:
            raise AdminExerciseTextGenerationNotFoundError("Exercise text generation task not found")
        return {"task": task, "exercise_text": item}

    def _require_publish_access(self, actor: dict[str, Any]) -> None:
        self._require_admin_access(actor, action="exercise_texts/publish")

    def _require_admin_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminExerciseTextGenerationAccessDeniedError(error.detail) from error

    def _start_generation(self, *, actor: dict[str, Any], exercise_text_id: int, stage: str) -> dict[str, Any]:
        normalized_stage = _normalize_generation_stage(stage)
        item = self._require_item(exercise_text_id)
        if item["status"] == "published":
            raise AdminExerciseTextGenerationValidationError("Published exercise text cannot be generated in place")
        content = deepcopy(item["content_jsonb"] or {"schema_version": 1})
        self._reject_running_stage(content, normalized_stage)
        task = self._create_task(actor=actor, exercise_text_id=exercise_text_id, stage=normalized_stage)
        running_content = self._with_stage_state(content, normalized_stage, "running")
        running_item = self._update_content(exercise_text_id, expected_version=item["version"], content=running_content, actor=actor)
        try:
            provider = self.provider_override or self._build_provider()
            result = provider.generate(ExerciseTextGenerationRequest(stage=normalized_stage, exercise_text=running_item))
            parsed = _parse_strict_json_object(result.raw_json_text)
            validate_content_document(parsed, require_generated=True, require_quiz=normalized_stage == "quiz")
            parsed = self._with_stage_state(parsed, normalized_stage, "completed")
            saved = self._update_content(
                exercise_text_id,
                expected_version=running_item["version"],
                content=parsed,
                actor=actor,
                status="generated",
            )
            self._record_usage(actor=actor, exercise_text_id=exercise_text_id, stage=normalized_stage, task_id=task["id"], provider=provider, usage=result.usage)
            task = self.db.task_logs.update(
                task["id"],
                status="success",
                current_time=self.time_service.now(),
                description=f"Exercise text {normalized_stage} generation completed",
                result_json={"exercise_text_id": exercise_text_id, "stage": normalized_stage},
            ) or task
            return {"task": task, "exercise_text": saved}
        except Exception as error:
            failed_content = self._with_stage_state(running_content, normalized_stage, "failed")
            self._update_content(exercise_text_id, expected_version=running_item["version"], content=failed_content, actor=actor)
            task = self.db.task_logs.update(
                task["id"],
                status="error",
                current_time=self.time_service.now(),
                description=f"Exercise text {normalized_stage} generation failed",
                error_text=_safe_error_text(error),
                result_json={"exercise_text_id": exercise_text_id, "stage": normalized_stage},
            ) or task
            return {"task": task, "exercise_text": self._require_item(exercise_text_id)}

    def _build_provider(self) -> ExerciseTextGenerationProvider:
        if self.provider_factory is None:
            raise AdminExerciseTextGenerationValidationError("Exercise text generation provider is disabled")
        configured = self.db.external_provider_settings.get_map().get(EXERCISE_TEXT_GENERATION_TASK_KEY)
        try:
            return self.provider_factory(settings=self.db.settings, configured=configured)
        except ExerciseTextGenerationProviderDisabledError as error:
            raise AdminExerciseTextGenerationValidationError("Exercise text generation provider is disabled") from error
        except UnsupportedExerciseTextGenerationProviderError as error:
            detail = f"Unsupported exercise text generation provider: {error.provider_key}"
            raise AdminExerciseTextGenerationValidationError(detail) from error

    def _require_item(self, exercise_text_id: int) -> dict[str, Any]:
        item = self.db.exercise_texts.get(exercise_text_id)
        if item is None:
            raise AdminExerciseTextGenerationNotFoundError("Exercise text not found")
        return item

    def _update_content(
        self,
        exercise_text_id: int,
        *,
        expected_version: int,
        content: dict[str, Any],
        actor: dict[str, Any],
        status: str | None = None,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {"content_jsonb": content}
        if status is not None:
            values["status"] = status
        try:
            updated = self.db.exercise_texts.update(
                exercise_text_id,
                expected_version=expected_version,
                values=values,
                actor_user_uuid=str(actor.get("user_uuid") or actor.get("user_id") or "") or None,
                current_time=self.time_service.now(),
            )
        except ExerciseTextVersionConflictError as error:
            raise AdminExerciseTextGenerationConflictError("Exercise text version conflict") from error
        if updated is None:
            raise AdminExerciseTextGenerationNotFoundError("Exercise text not found")
        return updated

    def _create_task(self, *, actor: dict[str, Any], exercise_text_id: int, stage: str) -> dict[str, Any]:
        return self.db.task_logs.create_for_user_uuid(
            task_type=f"exercise_texts.{stage}_generation",
            status="processing",
            current_time=self.time_service.now(),
            user_uuid=actor.get("user_uuid") or actor.get("user_id"),
            source_type="exercise_text",
            source_identifier=str(exercise_text_id),
            description=f"Exercise text {stage} generation started",
            result_json={"exercise_text_id": exercise_text_id, "stage": stage},
        )

    def _record_usage(
        self,
        *,
        actor: dict[str, Any],
        exercise_text_id: int,
        stage: str,
        task_id: int,
        provider: ExerciseTextGenerationProvider,
        usage: Any,
    ) -> None:
        if usage is None or not hasattr(self.db, "ai_usage_sessions"):
            return
        usage_db = cast(AdminExerciseTextGenerationUsageDatabasePort, self.db)
        usage_db.ai_usage_sessions.accumulate(
            task_key=EXERCISE_TEXT_GENERATION_TASK_KEY,
            task_scope="exercise_texts",
            provider_key=provider.provider_key,
            model=provider.model,
            actor_type="admin",
            actor_user_uuid=actor.get("user_uuid") or actor.get("user_id"),
            actor_group_title=actor.get("acl_group_title"),
            source_type="exercise_text",
            source_identifier=str(exercise_text_id),
            task_log_id=task_id,
            batch_key=f"exercise_text:{exercise_text_id}:{stage}:{task_id}",
            request_count=usage.request_count,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            estimated_cost_usd=usage.estimated_cost_usd,
            pricing_source=usage.pricing_source,
            status="success",
            summary=f"Exercise text {stage} generation",
            metadata_json={"stage": stage},
            started=self.time_service.now(),
            finished=self.time_service.now(),
            created=self.time_service.now(),
            updated=self.time_service.now(),
        )

    def _reject_running_stage(self, content: dict[str, Any], stage: str) -> None:
        generation_state = content.get("generation_state") if isinstance(content.get("generation_state"), dict) else {}
        if generation_state.get(stage) == "running":
            raise AdminExerciseTextGenerationConflictError(f"{stage} generation is already running")

    def _with_stage_state(self, content: dict[str, Any], stage: str, state: str) -> dict[str, Any]:
        next_content = deepcopy(content)
        next_content.setdefault("schema_version", 1)
        generation_state = next_content.get("generation_state")
        if not isinstance(generation_state, dict):
            generation_state = {}
        generation_state[stage] = state
        next_content["generation_state"] = generation_state
        return next_content


def _normalize_generation_stage(stage: str) -> str:
    normalized = str(stage or "").strip()
    if normalized not in EXERCISE_TEXT_GENERATION_STAGES:
        raise AdminExerciseTextGenerationValidationError("Unsupported exercise text generation stage")
    return normalized


def _parse_strict_json_object(value: str) -> dict[str, Any]:
    if value.lstrip().startswith("```"):
        raise ValueError("Provider response must be strict JSON, not markdown")
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Provider response JSON must be an object")
    return parsed


def _safe_error_text(error: Exception) -> str:
    if isinstance(error, ExerciseTextContentValidationError):
        return "Exercise text provider response failed schema validation"
    if isinstance(error, json.JSONDecodeError):
        return "Exercise text provider response was not valid JSON"
    return sanitize_external_error_text(str(error))[:500]
