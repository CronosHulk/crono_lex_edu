from __future__ import annotations

import random
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from app.acl.processor import AclPermissionReader
from app.application.admin.exercise_texts.content_jsonb import PARAGRAPH_ID_RE
from app.application.admin.exercise_texts.errors import (
    AdminExerciseTextTTSAccessDeniedError,
    AdminExerciseTextTTSConflictError,
    AdminExerciseTextTTSNotFoundError,
    AdminExerciseTextTTSValidationError,
)
from app.application.admin.exercise_texts.providers import (
    EXERCISE_TEXT_TTS_TASK_KEY,
    ExerciseTextTTSProvider,
    ExerciseTextTTSProviderDisabledError,
    ExerciseTextTTSProviderFactory,
    ExerciseTextTTSRequest,
    UnsupportedExerciseTextTTSProviderError,
)
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.domain.exercise_texts.errors import ExerciseTextVersionConflictError
from app.helpers.external_error_text import sanitize_external_error_text
from app.storage.audio import AudioStorageProvider
from app.time_utils import TimeService

SAFE_AUDIO_FILENAME_RE = re.compile(r"^[A-Za-z0-9_-]+\.mp3$")


class AdminExerciseTextTTSSettingsPort(Protocol):
    app_exercise_text_audio_dir: str


class AdminExerciseTextTTSExerciseTextsPort(Protocol):
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


class AdminExerciseTextTTSTaskLogsPort(Protocol):
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
        user_uuid: UUID | str | None = None,
        source_type: str | None = None,
        source_identifier: str | None = None,
        import_job_id: int | None = None,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class AdminExerciseTextTTSExternalProviderSettingsPort(Protocol):
    def get_map(self) -> dict[str, dict[str, Any]]: ...


class AdminExerciseTextTTSVoicesPort(Protocol):
    def list_active(self, *, provider: str | None = None) -> list[dict[str, Any]]: ...


class AdminExerciseTextTTSDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    exercise_texts: AdminExerciseTextTTSExerciseTextsPort
    task_logs: AdminExerciseTextTTSTaskLogsPort
    external_provider_settings: AdminExerciseTextTTSExternalProviderSettingsPort
    settings: AdminExerciseTextTTSSettingsPort
    tts_voices: AdminExerciseTextTTSVoicesPort


class AdminExerciseTextTTSService:
    def __init__(
        self,
        db: AdminExerciseTextTTSDatabasePort,
        time_service: TimeService,
        provider: ExerciseTextTTSProvider | None = None,
        provider_factory: ExerciseTextTTSProviderFactory | None = None,
        *,
        audio_storage_provider: AudioStorageProvider,
        random_choice=random.choice,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.provider_override = provider
        self.provider_factory = provider_factory
        self.audio_storage_provider = audio_storage_provider
        self.random_choice = random_choice

    def start_tts_generation(self, *, actor: dict[str, Any], exercise_text_id: int, voice_code: str | None = None) -> dict[str, Any]:
        self._require_admin_access(actor, action="exercise_texts/publish")
        item = self._require_item(exercise_text_id)
        if item["status"] == "published":
            raise AdminExerciseTextTTSValidationError("Published exercise text cannot be generated in place")
        content = deepcopy(item["content_jsonb"] or {"schema_version": 1})
        self._reject_running_tts(content)
        paragraphs = _extract_paragraphs(content)
        if not paragraphs:
            raise AdminExerciseTextTTSValidationError("Exercise text has no generated paragraphs for TTS")
        voice = self._select_voice(voice_code=voice_code)
        task = self._create_task(actor=actor, exercise_text_id=exercise_text_id, voice_code=voice["code"])
        running_content = _with_tts_state(content, "running")
        running_item = self._update_content(exercise_text_id, expected_version=item["version"], content=running_content, actor=actor)
        try:
            provider = self.provider_override or self._build_provider()
            audio_root = Path(str(getattr(self.db.settings, "app_exercise_text_audio_dir", "word_base/exercise_texts/audio")))
            updated_content = self._generate_audio(
                content=running_content,
                exercise_text=running_item,
                audio_root=audio_root,
                provider=provider,
                voice=voice,
                paragraphs=paragraphs,
            )
            saved = self._update_content(
                exercise_text_id,
                expected_version=running_item["version"],
                content=updated_content,
                actor=actor,
                status="generated",
            )
            task = self.db.task_logs.update(
                task["id"],
                status="success",
                current_time=self.time_service.now(),
                description="Exercise text TTS generation completed",
                result_json={"exercise_text_id": exercise_text_id, "stage": "tts", "voice_code": voice["code"]},
            ) or task
            return {"task": task, "exercise_text": saved}
        except Exception as error:
            failed_content = _with_tts_state(running_content, "failed")
            self._update_content(exercise_text_id, expected_version=running_item["version"], content=failed_content, actor=actor)
            task = self.db.task_logs.update(
                task["id"],
                status="error",
                current_time=self.time_service.now(),
                description="Exercise text TTS generation failed",
                error_text=sanitize_external_error_text(str(error))[:500],
                result_json={"exercise_text_id": exercise_text_id, "stage": "tts", "voice_code": voice["code"]},
            ) or task
            return {"task": task, "exercise_text": self._require_item(exercise_text_id)}

    def get_audio_path(self, *, actor: dict[str, Any], exercise_text_id: int, scope: str, paragraph_id: str | None = None) -> str | None:
        self._require_admin_access(actor, action="exercise_texts/play_audio")
        item = self._require_item(exercise_text_id)
        audio_filename = _select_audio_filename(item["content_jsonb"], scope=scope, paragraph_id=paragraph_id)
        audio_root = Path(str(getattr(self.db.settings, "app_exercise_text_audio_dir", "word_base/exercise_texts/audio")))
        audio_path = _audio_file_path(_exercise_audio_dir(audio_root, str(item["uuid"])), audio_filename) if audio_filename else None
        relative_audio_path = _relative_audio_path(audio_path) if audio_path is not None else None
        if relative_audio_path is None or not self.audio_storage_provider.exists(relative_audio_path):
            return None
        return relative_audio_path

    def _build_provider(self) -> ExerciseTextTTSProvider:
        if self.provider_factory is None:
            raise AdminExerciseTextTTSValidationError("Exercise text TTS provider is disabled")
        configured = self.db.external_provider_settings.get_map().get(EXERCISE_TEXT_TTS_TASK_KEY)
        try:
            return self.provider_factory(configured=configured)
        except ExerciseTextTTSProviderDisabledError as error:
            raise AdminExerciseTextTTSValidationError("Exercise text TTS provider is disabled") from error
        except UnsupportedExerciseTextTTSProviderError as error:
            detail = f"Unsupported exercise text TTS provider: {error.provider_key}"
            raise AdminExerciseTextTTSValidationError(detail) from error

    def _require_admin_access(self, actor: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, actor, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminExerciseTextTTSAccessDeniedError(error.detail) from error

    def _generate_audio(
        self,
        *,
        content: dict[str, Any],
        exercise_text: dict[str, Any],
        audio_root: Path,
        provider: ExerciseTextTTSProvider,
        voice: dict[str, Any],
        paragraphs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target_dir = _exercise_audio_dir(audio_root, str(exercise_text["uuid"]))
        next_content = deepcopy(content)
        generated = next_content.setdefault("generated", {})
        files: list[dict[str, Any]] = []
        paragraph_texts: list[str] = []
        paragraphs_by_id = {
            paragraph.get("id"): paragraph
            for paragraph in generated.get("paragraphs", [])
            if isinstance(paragraph, dict) and isinstance(paragraph.get("id"), str)
        }
        for paragraph in paragraphs:
            paragraph_id = paragraph["id"]
            paragraph_texts.append(paragraph["text"])
            path = _audio_file_path(target_dir, f"{paragraph_id}.mp3")
            result = provider.synthesize(
                ExerciseTextTTSRequest(text=paragraph["text"], language_code=voice["language_code"], voice_code=voice["code"])
            )
            relative_path = _relative_audio_path(path)
            self.audio_storage_provider.write_bytes_atomic(relative_path, result.audio_bytes)
            url = _audio_url(int(exercise_text["id"]), paragraph_id=paragraph_id)
            paragraph_payload = {
                "provider": provider.provider_key,
                "voice_code": voice["code"],
                "url": url,
                "duration_sec": None,
                "generated_at": self.time_service.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timestamps": result.timestamps,
            }
            paragraphs_by_id[paragraph_id]["audio"] = paragraph_payload
            files.append({"scope": "paragraph", "paragraph_id": paragraph_id, "path": relative_path, **paragraph_payload})
        full_result = provider.synthesize(
            ExerciseTextTTSRequest(text="\n\n".join(paragraph_texts), language_code=voice["language_code"], voice_code=voice["code"])
        )
        full_path = _audio_file_path(target_dir, "full.mp3")
        full_relative_path = _relative_audio_path(full_path)
        self.audio_storage_provider.write_bytes_atomic(full_relative_path, full_result.audio_bytes)
        files.insert(
            0,
            {
                "scope": "full",
                "path": full_relative_path,
                "provider": provider.provider_key,
                "voice_code": voice["code"],
                "url": _audio_url(int(exercise_text["id"]), paragraph_id=None),
                "duration_sec": None,
                "generated_at": self.time_service.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timestamps": full_result.timestamps,
            },
        )
        generated["audio"] = {
            "provider": provider.provider_key,
            "voice_code": voice["code"],
            "url": _audio_url(int(exercise_text["id"]), paragraph_id=None),
            "storage_prefix": _relative_audio_path(target_dir),
            "duration_sec": None,
            "generated_at": self.time_service.now().strftime("%Y-%m-%d %H:%M:%S"),
            "files": files,
        }
        return _with_tts_state(next_content, "completed")

    def _select_voice(self, *, voice_code: str | None) -> dict[str, Any]:
        voices = self.db.tts_voices.list_active(provider="google_tts")
        if not voices:
            raise AdminExerciseTextTTSValidationError("No active Google TTS voices are configured")
        if voice_code:
            for voice in voices:
                if voice.get("code") == voice_code:
                    return _normalize_voice(voice)
            raise AdminExerciseTextTTSValidationError("Selected TTS voice is not active")
        return _normalize_voice(self.random_choice(voices))

    def _reject_running_tts(self, content: dict[str, Any]) -> None:
        generation_state = content.get("generation_state") if isinstance(content.get("generation_state"), dict) else {}
        if generation_state.get("tts") == "running":
            raise AdminExerciseTextTTSConflictError("tts generation is already running")

    def _require_item(self, exercise_text_id: int) -> dict[str, Any]:
        item = self.db.exercise_texts.get(exercise_text_id)
        if item is None:
            raise AdminExerciseTextTTSNotFoundError("Exercise text not found")
        return item

    def _create_task(self, *, actor: dict[str, Any], exercise_text_id: int, voice_code: str) -> dict[str, Any]:
        return self.db.task_logs.create_for_user_uuid(
            task_type="exercise_texts.tts_generation",
            status="processing",
            current_time=self.time_service.now(),
            user_uuid=actor.get("user_uuid") or actor.get("user_id"),
            source_type="exercise_text",
            source_identifier=str(exercise_text_id),
            description="Exercise text TTS generation started",
            result_json={"exercise_text_id": exercise_text_id, "stage": "tts", "voice_code": voice_code},
        )

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
            raise AdminExerciseTextTTSConflictError("Exercise text version conflict") from error
        if updated is None:
            raise AdminExerciseTextTTSNotFoundError("Exercise text not found")
        return updated


def _extract_paragraphs(content: dict[str, Any]) -> list[dict[str, str]]:
    generated = content.get("generated") if isinstance(content.get("generated"), dict) else {}
    paragraphs = generated.get("paragraphs") if isinstance(generated.get("paragraphs"), list) else []
    payload: list[dict[str, str]] = []
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            continue
        paragraph_id = paragraph.get("id")
        text = ((paragraph.get("text") or {}).get("source") or {}).get("content") if isinstance(paragraph.get("text"), dict) else None
        if isinstance(paragraph_id, str) and PARAGRAPH_ID_RE.match(paragraph_id) and isinstance(text, str) and text.strip():
            payload.append({"id": paragraph_id, "text": text.strip()})
    return payload


def _with_tts_state(content: dict[str, Any], state: str) -> dict[str, Any]:
    next_content = deepcopy(content)
    generation_state = next_content.get("generation_state")
    if not isinstance(generation_state, dict):
        generation_state = {}
    generation_state["tts"] = state
    next_content["generation_state"] = generation_state
    generated = next_content.get("generated")
    if isinstance(generated, dict):
        for paragraph in generated.get("paragraphs") or []:
            if isinstance(paragraph, dict):
                status = paragraph.get("status")
                if not isinstance(status, dict):
                    status = {}
                status["tts"] = state
                paragraph["status"] = status
    return next_content


def _normalize_voice(voice: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(voice.get("code") or "").strip(),
        "language_code": str(voice.get("language_code") or "en-US").strip() or "en-US",
    }


def _exercise_audio_dir(audio_root: Path, exercise_uuid: str) -> Path:
    root = _project_path(audio_root)
    target = (root / exercise_uuid).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise AdminExerciseTextTTSValidationError("Invalid exercise text audio path") from error
    return target


def _audio_file_path(target_dir: Path, filename: str) -> Path:
    if not SAFE_AUDIO_FILENAME_RE.match(filename):
        raise AdminExerciseTextTTSValidationError("Invalid exercise text audio filename")
    path = (target_dir / filename).resolve()
    try:
        path.relative_to(target_dir)
    except ValueError as error:
        raise AdminExerciseTextTTSValidationError("Invalid exercise text audio filename") from error
    return path


def _project_path(value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (Path.cwd() / value).resolve()


def _relative_audio_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError as error:
        raise AdminExerciseTextTTSValidationError("Exercise text audio path must stay inside project root") from error


def _audio_url(exercise_text_id: int, *, paragraph_id: str | None) -> str:
    if paragraph_id:
        return f"/api/v1/admin/exercise-texts/{exercise_text_id}/audio?paragraph_id={paragraph_id}"
    return f"/api/v1/admin/exercise-texts/{exercise_text_id}/audio?scope=full"


def _select_audio_filename(content: dict[str, Any], *, scope: str, paragraph_id: str | None) -> str | None:
    if paragraph_id is not None and not PARAGRAPH_ID_RE.match(paragraph_id):
        raise AdminExerciseTextTTSValidationError("Invalid paragraph_id")
    normalized_scope = str(scope or "full").strip()
    if normalized_scope not in {"full", "paragraph"}:
        raise AdminExerciseTextTTSValidationError("scope must be full or paragraph")
    if normalized_scope == "paragraph" and not paragraph_id:
        raise AdminExerciseTextTTSValidationError("paragraph_id is required for paragraph audio")
    generated = content.get("generated") if isinstance(content.get("generated"), dict) else {}
    audio = generated.get("audio") if isinstance(generated.get("audio"), dict) else {}
    files = audio.get("files") if isinstance(audio.get("files"), list) else []
    target_scope = "paragraph" if paragraph_id else normalized_scope
    for item in files:
        if not isinstance(item, dict) or item.get("scope") != target_scope:
            continue
        if paragraph_id and item.get("paragraph_id") != paragraph_id:
            continue
        return f"{paragraph_id}.mp3" if paragraph_id else "full.mp3"
    return None
