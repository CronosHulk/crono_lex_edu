from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.exercise_texts.content_jsonb import (
    DIFFICULTY_BANDS,
    EXERCISE_TEXT_STATUSES,
    TEXT_TYPES,
    ExerciseTextContentValidationError,
    validate_content_document,
)
from app.application.admin.exercise_texts.errors import (
    AdminExerciseTextServiceAccessDeniedError,
    AdminExerciseTextServiceConflictError,
    AdminExerciseTextServiceNotFoundError,
    AdminExerciseTextServiceValidationError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.domain.exercise_texts.errors import ExerciseTextVersionConflictError
from app.time_utils import TimeService

LEVEL_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
DIFFICULTY_BAND_MAX_LEVEL = {"A1_A2": "A2", "B1_B2": "B2", "C1_C2": "C2"}
EXERCISE_TEXT_SORT_OPTIONS = ("updated_desc", "created_desc", "title_asc", "id_desc")


class AdminExerciseTextsPort(Protocol):
    def list_page(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        archived: bool = False,
        search: str = "",
        status: list[str] | None = None,
        difficulty_band: list[str] | None = None,
        text_type: list[str] | None = None,
        topic_id: list[int] | None = None,
        has_quiz: bool | None = None,
        has_tts: bool | None = None,
        sort: str = "updated_desc",
    ) -> dict[str, Any]: ...

    def get(self, exercise_text_id: int) -> dict[str, Any] | None: ...

    def create(
        self,
        *,
        title: str | None = None,
        status: str = "draft",
        difficulty_band: str | None = None,
        text_types: list[str] | None = None,
        content_jsonb: dict[str, Any] | None = None,
        topic_ids: list[int] | None = None,
        actor_user_uuid: str | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any]: ...

    def update(
        self,
        exercise_text_id: int,
        *,
        expected_version: int,
        values: dict[str, Any],
        topic_ids: list[int] | None = None,
        actor_user_uuid: str | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any] | None: ...


class AdminExerciseTextGrammarTopicsPort(Protocol):
    def list_active(self) -> list[dict[str, Any]]: ...


class AdminExerciseTextTtsVoicesPort(Protocol):
    def list_active(self, *, provider: str | None = None) -> list[dict[str, Any]]: ...


class AdminExerciseTextDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    exercise_texts: AdminExerciseTextsPort
    grammar_topics: AdminExerciseTextGrammarTopicsPort
    tts_voices: AdminExerciseTextTtsVoicesPort


class AdminExerciseTextService:
    def __init__(self, db: AdminExerciseTextDatabasePort, time_service: TimeService) -> None:
        self.db = db
        self.time_service = time_service

    def list_items(self, *, actor: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/list", detail="Exercise text access is not allowed")
        statuses = _validate_optional_filter_values(params.get("status"), EXERCISE_TEXT_STATUSES, "status")
        difficulty_bands = _validate_optional_filter_values(params.get("difficulty_band"), DIFFICULTY_BANDS, "difficulty_band")
        text_types = _validate_optional_filter_values(params.get("text_type"), TEXT_TYPES, "text_type")
        topic_ids = _validate_optional_topic_ids(params.get("topic_id"))
        has_quiz = _validate_optional_boolean_choice(params.get("has_quiz"), "has_quiz")
        has_tts = _validate_optional_boolean_choice(params.get("has_tts"), "has_tts")
        sort = _validate_sort(params.get("sort"))
        return self.db.exercise_texts.list_page(
            page=params.get("page", 1),
            page_size=params.get("page_size", 50),
            archived=bool(params.get("archived", False)),
            search=str(params.get("search") or ""),
            status=statuses,
            difficulty_band=difficulty_bands,
            text_type=text_types,
            topic_id=topic_ids,
            has_quiz=has_quiz,
            has_tts=has_tts,
            sort=sort,
        )

    def get_item(self, *, actor: dict[str, Any], exercise_text_id: int) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/view", detail="Exercise text access is not allowed")
        return self._require_item(exercise_text_id)

    def create_item(self, *, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/create", detail="Exercise text creation is not allowed")
        content = dict(payload.get("content_jsonb") or {"schema_version": 1})
        self._validate_content(content, require_generated="generated" in content)
        self._ensure_topic_difficulty_allowed(payload)
        return self.db.exercise_texts.create(
            title=payload.get("title"),
            difficulty_band=payload.get("difficulty_band"),
            text_types=payload.get("text_types") or [],
            content_jsonb=content,
            topic_ids=payload.get("topic_ids") or [],
            actor_user_uuid=self._actor_uuid(actor),
            current_time=self.time_service.now(),
        )

    def update_item(self, *, actor: dict[str, Any], exercise_text_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/update", detail="Exercise text update is not allowed")
        item = self._require_item(exercise_text_id)
        if item["status"] == "published":
            raise AdminExerciseTextServiceValidationError("Published exercise text cannot be edited in place")
        self._ensure_topic_difficulty_allowed({**item, **payload})
        values: dict[str, Any] = {}
        for field_name in ("title", "difficulty_band", "text_types"):
            if field_name in payload:
                values[field_name] = payload[field_name]
        if "content_jsonb" in payload and payload["content_jsonb"] is not None:
            content = dict(payload["content_jsonb"])
            self._validate_content(content, require_generated="generated" in content)
            if _changes_generation_inputs(item, payload, content):
                content = _mark_generation_stale(content)
            values["content_jsonb"] = content
        elif _changes_generation_inputs(item, payload, item["content_jsonb"]):
            values["content_jsonb"] = _mark_generation_stale(dict(item["content_jsonb"] or {"schema_version": 1}))
        return self._update_with_version(
            exercise_text_id,
            expected_version=payload["version"],
            values=values,
            topic_ids=payload.get("topic_ids"),
            actor=actor,
        )

    def archive_item(self, *, actor: dict[str, Any], exercise_text_id: int, version: int | None = None) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/archive", detail="Exercise text archive is not allowed")
        item = self._require_item(exercise_text_id)
        expected_version = version or item["version"]
        return self._update_with_version(
            exercise_text_id,
            expected_version=expected_version,
            values={"status": "archived", "archived_at": self.time_service.now()},
            topic_ids=None,
            actor=actor,
        )

    def mark_ready(self, *, actor: dict[str, Any], exercise_text_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/publish", detail="Exercise text publish is not allowed")
        item = self._require_item(exercise_text_id)
        self._ensure_topic_difficulty_allowed({**item, **payload})
        self._validate_content(item["content_jsonb"], require_publishable=True)
        return self._update_with_version(
            exercise_text_id,
            expected_version=payload["version"],
            values={"status": "ready"},
            topic_ids=None,
            actor=actor,
        )

    def publish_item(self, *, actor: dict[str, Any], exercise_text_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/publish", detail="Exercise text publish is not allowed")
        item = self._require_item(exercise_text_id)
        self._ensure_topic_difficulty_allowed({**item, **payload})
        self._validate_content(item["content_jsonb"], require_publishable=True)
        return self._update_with_version(
            exercise_text_id,
            expected_version=payload["version"],
            values={"status": "published", "published_at": self.time_service.now()},
            topic_ids=None,
            actor=actor,
        )

    def unpublish_item(self, *, actor: dict[str, Any], exercise_text_id: int, version: int) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/publish", detail="Exercise text publish is not allowed")
        item = self._require_item(exercise_text_id)
        if item["status"] != "published":
            raise AdminExerciseTextServiceValidationError("Only published exercise text can be unpublished")
        return self._update_with_version(
            exercise_text_id,
            expected_version=version,
            values={"status": "ready", "published_at": None},
            topic_ids=None,
            actor=actor,
        )

    def confirm_paragraph_stage(
        self,
        *,
        actor: dict[str, Any],
        exercise_text_id: int,
        paragraph_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_admin_access(
            actor,
            action="exercise_texts/publish",
            detail="Exercise text paragraph confirmation is not allowed",
        )
        item = self._require_item(exercise_text_id)
        if item["status"] == "published":
            raise AdminExerciseTextServiceValidationError("Published exercise text cannot be edited in place")
        content = deepcopy(item["content_jsonb"] or {"schema_version": 1})
        paragraph = _find_generated_paragraph(content, paragraph_id)
        stage = str(payload["stage"])
        status = paragraph.get("status")
        if not isinstance(status, dict):
            status = {}
        if status.get(stage) not in {"stale", "failed"}:
            raise AdminExerciseTextServiceConflictError("Only stale or failed paragraph stages can be manually confirmed")
        status[stage] = "completed"
        paragraph["status"] = status
        _sync_document_stage_from_paragraphs(content, stage)
        self._validate_content(content, require_generated="generated" in content)
        return self._update_with_version(
            exercise_text_id,
            expected_version=payload["version"],
            values={"content_jsonb": content},
            topic_ids=None,
            actor=actor,
        )

    def list_reference(self, *, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/list", detail="Exercise text access is not allowed")
        return {
            "difficulty_bands": list(DIFFICULTY_BANDS),
            "text_types": list(TEXT_TYPES),
            "statuses": list(EXERCISE_TEXT_STATUSES),
        }

    def list_grammar_topics(self, *, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/list", detail="Exercise text access is not allowed")
        return {"items": self.db.grammar_topics.list_active()}

    def list_tts_voices(self, *, actor: dict[str, Any], provider: str | None = None) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/list", detail="Exercise text access is not allowed")
        return {"items": self.db.tts_voices.list_active(provider=provider)}

    def get_audio_response(self, *, actor: dict[str, Any], exercise_text_id: int):
        self._require_admin_access(actor, action="exercise_texts/play_audio")
        self._require_item(exercise_text_id)
        raise AdminExerciseTextServiceNotFoundError("Audio not found")

    def _require_admin_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminExerciseTextServiceAccessDeniedError(error.detail) from error

    def _require_item(self, exercise_text_id: int) -> dict[str, Any]:
        item = self.db.exercise_texts.get(exercise_text_id)
        if item is None:
            raise AdminExerciseTextServiceNotFoundError("Exercise text not found")
        return item

    def _update_with_version(
        self,
        exercise_text_id: int,
        *,
        expected_version: int,
        values: dict[str, Any],
        topic_ids: list[int] | None,
        actor: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            result = self.db.exercise_texts.update(
                exercise_text_id,
                expected_version=expected_version,
                values=values,
                topic_ids=topic_ids,
                actor_user_uuid=self._actor_uuid(actor),
                current_time=self.time_service.now(),
            )
        except ExerciseTextVersionConflictError as error:
            raise AdminExerciseTextServiceConflictError("Exercise text version conflict") from error
        if result is None:
            raise AdminExerciseTextServiceNotFoundError("Exercise text not found")
        return result

    def _validate_content(
        self,
        content: dict[str, Any],
        *,
        require_generated: bool = False,
        require_publishable: bool = False,
    ) -> None:
        try:
            validate_content_document(content, require_generated=require_generated, require_publishable=require_publishable)
        except ExerciseTextContentValidationError as error:
            raise AdminExerciseTextServiceValidationError({"errors": error.to_payload()}) from error

    def _ensure_topic_difficulty_allowed(self, payload: dict[str, Any]) -> None:
        difficulty_band = payload.get("difficulty_band")
        topic_ids = payload.get("topic_ids") or []
        if not difficulty_band or not topic_ids:
            return
        max_level = DIFFICULTY_BAND_MAX_LEVEL[difficulty_band]
        active_topics = {topic["id"]: topic for topic in self.db.grammar_topics.list_active()}
        missing_ids = [topic_id for topic_id in topic_ids if topic_id not in active_topics]
        if missing_ids:
            raise AdminExerciseTextServiceValidationError(f"Unknown or inactive grammar topic: {missing_ids[0]}")
        conflicting = [
            active_topics[topic_id]
            for topic_id in topic_ids
            if LEVEL_ORDER.get(str(active_topics[topic_id].get("min_level") or active_topics[topic_id].get("level") or ""), 0)
            > LEVEL_ORDER[max_level]
        ]
        if not conflicting:
            return
        force = payload.get("force_topic_difficulty")
        if isinstance(force, dict) and str(force.get("reason") or "").strip():
            return
        raise AdminExerciseTextServiceConflictError(
            {
                "code": "topic_difficulty_conflict",
                "message": "Selected grammar topic is above selected difficulty_band",
                "topic_ids": [topic["id"] for topic in conflicting],
            },
        )

    def _actor_uuid(self, actor: dict[str, Any]) -> str | None:
        value = actor.get("user_uuid") or actor.get("user_id") or actor.get("uuid")
        return str(value) if value else None


def _validate_optional_filter_values(value: list[str] | None, allowed_values: tuple[str, ...], field_name: str) -> list[str] | None:
    if value is None:
        return None
    allowed = set(allowed_values)
    normalized = list(dict.fromkeys(item.strip() for item in value if item.strip()))
    for item in normalized:
        if item not in allowed:
            raise AdminExerciseTextServiceValidationError(f"{field_name} contains unsupported value: {item}")
    return normalized


def _validate_optional_topic_ids(value: list[int] | None) -> list[int] | None:
    if value is None:
        return None
    if len(value) > 200:
        raise AdminExerciseTextServiceValidationError("topic_id accepts at most 200 values")
    try:
        return _positive_id_list(value, "topic_id")
    except (TypeError, ValueError) as error:
        raise AdminExerciseTextServiceValidationError(str(error)) from error


def _positive_id_list(value: list[int], field_name: str) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for item in value:
        resolved = int(item)
        if resolved <= 0:
            raise ValueError(f"{field_name} must be a positive integer")
        if resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    if not result:
        raise ValueError(f"{field_name} must contain at least one id")
    return result


def _validate_optional_boolean_choice(value: Any, field_name: str) -> bool | None:
    normalized = str(value or "all").strip().lower()
    if normalized == "all":
        return None
    if normalized == "yes":
        return True
    if normalized == "no":
        return False
    raise AdminExerciseTextServiceValidationError(f"{field_name} must be all, yes or no")


def _validate_sort(value: Any) -> str:
    normalized = str(value or "updated_desc").strip()
    if normalized in EXERCISE_TEXT_SORT_OPTIONS:
        return normalized
    raise AdminExerciseTextServiceValidationError(f"sort must be one of: {', '.join(EXERCISE_TEXT_SORT_OPTIONS)}")


def _changes_generation_inputs(item: dict[str, Any], payload: dict[str, Any], next_content: dict[str, Any]) -> bool:
    if not isinstance((item.get("content_jsonb") or {}).get("generated"), dict):
        return False
    previous_content = item.get("content_jsonb") or {}
    if previous_content.get("source") != next_content.get("source"):
        return True
    for field_name in ("difficulty_band", "text_types"):
        if field_name in payload and payload[field_name] != item.get(field_name):
            return True
    if "topic_ids" in payload and payload.get("topic_ids") != item.get("topic_ids"):
        return True
    return False


def _mark_generation_stale(content: dict[str, Any]) -> dict[str, Any]:
    next_content = dict(content)
    generated = next_content.get("generated")
    if not isinstance(generated, dict):
        return next_content
    generation_state = next_content.get("generation_state")
    if not isinstance(generation_state, dict):
        generation_state = {}
    for stage in ("content", "translations", "quiz", "tts"):
        if generation_state.get(stage) in {None, "pending"}:
            continue
        generation_state[stage] = "stale"
    next_content["generation_state"] = generation_state
    for paragraph in generated.get("paragraphs") or []:
        if not isinstance(paragraph, dict):
            continue
        status = paragraph.get("status")
        if not isinstance(status, dict):
            continue
        for stage in ("content", "translations", "quiz", "tts"):
            if status.get(stage) in {None, "pending"}:
                continue
            status[stage] = "stale"
    return next_content


def _find_generated_paragraph(content: dict[str, Any], paragraph_id: str) -> dict[str, Any]:
    generated = content.get("generated")
    paragraphs = generated.get("paragraphs") if isinstance(generated, dict) else None
    if not isinstance(paragraphs, list):
        raise AdminExerciseTextServiceValidationError("Exercise text has no generated paragraphs")
    for paragraph in paragraphs:
        if isinstance(paragraph, dict) and paragraph.get("id") == paragraph_id:
            return paragraph
    raise AdminExerciseTextServiceNotFoundError("Exercise text paragraph not found")


def _sync_document_stage_from_paragraphs(content: dict[str, Any], stage: str) -> None:
    generated = content.get("generated")
    paragraphs = generated.get("paragraphs") if isinstance(generated, dict) else None
    if not isinstance(paragraphs, list) or not paragraphs:
        return
    states = []
    for paragraph in paragraphs:
        status = paragraph.get("status") if isinstance(paragraph, dict) else None
        states.append(status.get(stage, "pending") if isinstance(status, dict) else "pending")
    if not states:
        return
    priority = ("running", "failed", "stale", "pending")
    next_state = "completed" if len(states) == len(paragraphs) and all(state == "completed" for state in states) else "pending"
    for state in priority:
        if state in states:
            next_state = state
            break
    generation_state = content.get("generation_state")
    if not isinstance(generation_state, dict):
        generation_state = {}
    generation_state[stage] = next_state
    content["generation_state"] = generation_state
