from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import RedirectResponse

from app.application.client_web.teacher_students_errors import (
    ClientWebTeacherStudentConfigurationError,
    ClientWebTeacherStudentConflictError,
    ClientWebTeacherStudentError,
    ClientWebTeacherStudentForbiddenError,
    ClientWebTeacherStudentNotFoundError,
    ClientWebTeacherStudentUpstreamError,
    ClientWebTeacherStudentValidationError,
)
from app.application.client_web.teacher_students_service import (
    ClientWebTeacherStudentService,
)
from app.client_api.client_web.schemas import (
    ClientWebTeacherStudentAliasRequest,
    ClientWebTeacherStudentGroupRequest,
    ClientWebTeacherStudentGroupSaveRequest,
    ClientWebTeacherStudentLevelRequest,
)


def client_web_teacher_student_error_status_code(error: ClientWebTeacherStudentError) -> int:
    if isinstance(error, ClientWebTeacherStudentValidationError):
        return 400
    if isinstance(error, ClientWebTeacherStudentForbiddenError):
        return 403
    if isinstance(error, ClientWebTeacherStudentNotFoundError):
        return 404
    if isinstance(error, ClientWebTeacherStudentConflictError):
        return 409
    if isinstance(error, ClientWebTeacherStudentUpstreamError):
        return 502
    if isinstance(error, ClientWebTeacherStudentConfigurationError):
        return 503
    return 400


def client_web_teacher_student_http_exception(error: ClientWebTeacherStudentError) -> HTTPException:
    return HTTPException(status_code=client_web_teacher_student_error_status_code(error), detail=error.detail)


def build_teacher_students_router(
    *,
    get_teacher_student_service: Callable[[], ClientWebTeacherStudentService],
    current_user: Callable[[Request], dict],
) -> APIRouter:
    router = APIRouter()

    @router.get("/students")
    def teacher_students_list(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=100),
        name: str = Query(default="", max_length=128),
        login: str = Query(default="", max_length=64),
        level: str = Query(default="", max_length=16),
        group_id: int | None = Query(default=None, ge=1),
    ) -> dict:
        try:
            return get_teacher_student_service().list_students(
                current_user(request),
                page=page,
                page_size=page_size,
                name=name,
                login=login,
                level=level,
                group_id=group_id,
            )
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.get("/students/groups")
    def teacher_student_groups_list(request: Request) -> dict:
        try:
            return get_teacher_student_service().list_groups(current_user(request))
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.post("/students/groups")
    def teacher_student_groups_create(request: Request, payload: ClientWebTeacherStudentGroupSaveRequest) -> dict:
        try:
            return get_teacher_student_service().create_group(current_user(request), title=payload.title)
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.patch("/students/groups/{group_id}")
    def teacher_student_groups_update(
        request: Request,
        payload: ClientWebTeacherStudentGroupSaveRequest,
        group_id: int = Path(..., ge=1),
    ) -> dict:
        try:
            return get_teacher_student_service().update_group(current_user(request), group_id=group_id, title=payload.title)
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.delete("/students/groups/{group_id}")
    def teacher_student_groups_delete(request: Request, group_id: int = Path(..., ge=1)) -> dict:
        try:
            return get_teacher_student_service().delete_group(current_user(request), group_id=group_id)
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.patch("/students/{student_user_id}/alias")
    def teacher_student_alias_update(
        request: Request,
        payload: ClientWebTeacherStudentAliasRequest,
        student_user_id: UUID = Path(...),
    ) -> dict:
        try:
            return get_teacher_student_service().update_student_alias(
                current_user(request),
                student_user_id=str(student_user_id),
                teacher_alias=payload.teacher_alias,
            )
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.patch("/students/{student_user_id}/level")
    def teacher_student_level_update(
        request: Request,
        payload: ClientWebTeacherStudentLevelRequest,
        student_user_id: UUID = Path(...),
    ) -> dict:
        try:
            return get_teacher_student_service().update_student_level(
                current_user(request),
                student_user_id=str(student_user_id),
                language_level=payload.language_level,
            )
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.patch("/students/{student_user_id}/group")
    def teacher_student_group_update(
        request: Request,
        payload: ClientWebTeacherStudentGroupRequest,
        student_user_id: UUID = Path(...),
    ) -> dict:
        try:
            return get_teacher_student_service().update_student_group(
                current_user(request),
                student_user_id=str(student_user_id),
                group_id=payload.group_id,
            )
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.post("/students/{student_user_id}/meet-session")
    def teacher_student_meet_session_create(
        request: Request,
        student_user_id: UUID = Path(...),
    ) -> dict:
        try:
            return get_teacher_student_service().create_meet_session(current_user(request), student_user_id=str(student_user_id))
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error

    @router.get("/google/oauth/start")
    def google_oauth_start(
        request: Request,
        return_to: str = Query(default="/students", max_length=512),
        pending_action: str | None = Query(default=None, max_length=64),
        student_id: UUID | None = Query(default=None),
    ) -> RedirectResponse:
        try:
            redirect_url = get_teacher_student_service().create_google_oauth_redirect(
                current_user(request),
                return_to=return_to,
                pending_action=pending_action,
                student_user_id=str(student_id) if student_id is not None else None,
            )
        except ClientWebTeacherStudentError as error:
            raise client_web_teacher_student_http_exception(error) from error
        return RedirectResponse(redirect_url)

    @router.get("/google/oauth/callback")
    def google_oauth_callback(
        request: Request,
        code: str | None = Query(default=None, min_length=1, max_length=2048),
        state: str = Query(..., min_length=1, max_length=2048),
        error: str | None = Query(default=None, max_length=256),
    ) -> RedirectResponse:
        try:
            redirect_url = get_teacher_student_service().complete_google_oauth(
                current_user(request),
                code=code,
                state=state,
                oauth_error=error,
            )
        except ClientWebTeacherStudentError as service_error:
            raise client_web_teacher_student_http_exception(service_error) from service_error
        return RedirectResponse(redirect_url)

    return router
