from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Query, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.exercise_texts.http_errors import (
    admin_exercise_text_generation_http_exception,
    admin_exercise_text_service_http_exception,
    admin_exercise_text_tts_http_exception,
)
from app.admin_api.exercise_texts.schemas import (
    ExerciseTextCreateRequest,
    ExerciseTextParagraphConfirmRequest,
    ExerciseTextPublishRequest,
    ExerciseTextTTSGenerationRequest,
    ExerciseTextUpdateRequest,
    ExerciseTextVersionedActionRequest,
)
from app.api_helpers.audio_response import build_audio_response
from app.application.admin.exercise_texts.errors import (
    AdminExerciseTextGenerationError,
    AdminExerciseTextServiceError,
    AdminExerciseTextTTSError,
)


def _call_core_service[T](call: Callable[[], T]) -> T:
    try:
        return call()
    except AdminExerciseTextServiceError as error:
        raise admin_exercise_text_service_http_exception(error) from error


def _call_generation_service[T](call: Callable[[], T]) -> T:
    try:
        return call()
    except AdminExerciseTextGenerationError as error:
        raise admin_exercise_text_generation_http_exception(error) from error


def _call_tts_service[T](call: Callable[[], T]) -> T:
    try:
        return call()
    except AdminExerciseTextTTSError as error:
        raise admin_exercise_text_tts_http_exception(error) from error


def build_exercise_texts_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/exercise-texts")
    def admin_exercise_texts(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=100),
        archived: bool = False,
        search: str = "",
        sort: str = "updated_desc",
        status: list[str] | None = Query(default=None),
        difficulty_band: list[str] | None = Query(default=None),
        text_type: list[str] | None = Query(default=None),
        topic_id: list[int] | None = Query(default=None),
        has_quiz: str = "all",
        has_tts: str = "all",
    ) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().list_items(
                actor=context.current_admin_user(request),
                params={
                    "page": page,
                    "page_size": page_size,
                    "archived": archived,
                    "search": search,
                    "sort": sort,
                    "status": status,
                    "difficulty_band": difficulty_band,
                    "text_type": text_type,
                    "topic_id": topic_id,
                    "has_quiz": has_quiz,
                    "has_tts": has_tts,
                },
            )
        )

    @router.post("/exercise-texts")
    def admin_exercise_text_create(request: Request, payload: ExerciseTextCreateRequest) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().create_item(
                actor=context.current_admin_user(request),
                payload=payload.model_dump(exclude_unset=True),
            )
        )

    @router.get("/exercise-texts/{exercise_text_id}")
    def admin_exercise_text_detail(exercise_text_id: int, request: Request) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().get_item(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
            )
        )

    @router.put("/exercise-texts/{exercise_text_id}")
    def admin_exercise_text_update(exercise_text_id: int, request: Request, payload: ExerciseTextUpdateRequest) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().update_item(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                payload=payload.model_dump(exclude_unset=True),
            )
        )

    @router.delete("/exercise-texts/{exercise_text_id}")
    def admin_exercise_text_delete(exercise_text_id: int, request: Request, version: int = Query(ge=1)) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().archive_item(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                version=version,
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/archive")
    def admin_exercise_text_archive(
        exercise_text_id: int,
        request: Request,
        payload: ExerciseTextVersionedActionRequest,
    ) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().archive_item(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                version=payload.version,
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/ready")
    def admin_exercise_text_ready(exercise_text_id: int, request: Request, payload: ExerciseTextPublishRequest) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().mark_ready(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                payload=payload.model_dump(exclude_unset=True),
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/generate-content")
    def admin_exercise_text_generate_content(exercise_text_id: int, request: Request) -> dict:
        return _call_generation_service(
            lambda: context.admin_exercise_text_generation_service().start_generation(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                stage="content",
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/generate-translations")
    def admin_exercise_text_generate_translations(exercise_text_id: int, request: Request) -> dict:
        return _call_generation_service(
            lambda: context.admin_exercise_text_generation_service().start_generation(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                stage="translations",
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/generate-quiz")
    def admin_exercise_text_generate_quiz(exercise_text_id: int, request: Request) -> dict:
        return _call_generation_service(
            lambda: context.admin_exercise_text_generation_service().start_generation(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                stage="quiz",
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/generate-all")
    def admin_exercise_text_generate_all(exercise_text_id: int, request: Request) -> dict:
        return _call_generation_service(
            lambda: context.admin_exercise_text_generation_service().generate_all(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/generate-tts")
    def admin_exercise_text_generate_tts(
        exercise_text_id: int,
        request: Request,
        payload: ExerciseTextTTSGenerationRequest | None = None,
    ) -> dict:
        return _call_tts_service(
            lambda: context.admin_exercise_text_tts_service().start_tts_generation(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                voice_code=payload.voice_code if payload is not None else None,
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/paragraphs/{paragraph_id}/confirm-stage")
    def admin_exercise_text_confirm_paragraph_stage(
        exercise_text_id: int,
        paragraph_id: str,
        request: Request,
        payload: ExerciseTextParagraphConfirmRequest,
    ) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().confirm_paragraph_stage(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                paragraph_id=paragraph_id,
                payload=payload.model_dump(exclude_unset=True),
            )
        )

    @router.get("/exercise-texts/{exercise_text_id}/generation-tasks/{task_id}")
    def admin_exercise_text_generation_task(exercise_text_id: int, task_id: int, request: Request) -> dict:
        return _call_generation_service(
            lambda: context.admin_exercise_text_generation_service().get_generation_task(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                task_id=task_id,
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/publish")
    def admin_exercise_text_publish(exercise_text_id: int, request: Request, payload: ExerciseTextPublishRequest) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().publish_item(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                payload=payload.model_dump(exclude_unset=True),
            )
        )

    @router.post("/exercise-texts/{exercise_text_id}/unpublish")
    def admin_exercise_text_unpublish(
        exercise_text_id: int,
        request: Request,
        payload: ExerciseTextVersionedActionRequest,
    ) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().unpublish_item(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                version=payload.version,
            )
        )

    @router.get("/exercise-texts/{exercise_text_id}/audio")
    def admin_exercise_text_audio(
        exercise_text_id: int,
        request: Request,
        scope: str = "full",
        paragraph_id: str | None = None,
    ):
        audio_path = _call_tts_service(
            lambda: context.admin_exercise_text_tts_service().get_audio_path(
                actor=context.current_admin_user(request),
                exercise_text_id=exercise_text_id,
                scope=scope,
                paragraph_id=paragraph_id,
            )
        )
        return build_audio_response(
            audio_path,
            storage_provider=context.audio_storage_provider(),
        )

    @router.get("/reference/exercise-text-options")
    def admin_exercise_text_options(request: Request) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().list_reference(
                actor=context.current_admin_user(request),
            )
        )

    @router.get("/reference/grammar-topics")
    def admin_grammar_topics(request: Request) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().list_grammar_topics(
                actor=context.current_admin_user(request),
            )
        )

    @router.get("/reference/tts-voices")
    def admin_tts_voices(request: Request, provider: str | None = None) -> dict:
        return _call_core_service(
            lambda: context.admin_exercise_text_service().list_tts_voices(
                actor=context.current_admin_user(request),
                provider=provider,
            )
        )

    return router
