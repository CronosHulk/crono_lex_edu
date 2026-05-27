from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.api_helpers.audio_response import build_audio_response
from app.api_helpers.request_context import build_request_context
from app.application.client_web.auth_errors import (
    ClientWebAuthError,
    ClientWebAuthNotFoundError,
    ClientWebAuthRateLimitError,
    ClientWebAuthValidationError,
)
from app.application.client_web.auth_service import ClientWebAuthService
from app.application.client_web.import_errors import (
    ClientWebImportError,
    ClientWebImportNotFoundError,
    ClientWebImportProviderUnavailableError,
)
from app.application.client_web.import_service import ClientWebImportService
from app.application.client_web.learning_errors import (
    ClientWebLearningConflictError,
    ClientWebLearningError,
    ClientWebLearningNotFoundError,
    ClientWebLearningPaymentRequiredError,
    ClientWebLearningValidationError,
)
from app.application.client_web.learning_service import ClientWebLearningService
from app.application.client_web.plan_service import (
    ClientWebPlanError,
    ClientWebPlanProfileNotFoundError,
    ClientWebPlanService,
)
from app.application.client_web.settings_service import (
    ClientWebSettingsError,
    ClientWebSettingsService,
)
from app.application.client_web.teacher_students_service import (
    ClientWebTeacherStudentService,
)
from app.billing.services.checkout_service import (
    BillingCheckoutError,
    BillingCheckoutMaintenanceError,
    BillingCheckoutProfileNotFoundError,
    BillingCheckoutProviderUnavailableError,
    BillingCheckoutService,
)
from app.billing.services.history_service import (
    BillingPaymentHistoryProfileNotFoundError,
    BillingPaymentHistoryService,
)
from app.billing.services.status_service import (
    BillingPaymentStatusError,
    BillingPaymentStatusNotFoundError,
    BillingPaymentStatusService,
)
from app.client_api.client_web.schemas import (
    ClientWebAuthOtpRequest,
    ClientWebAuthPasswordRequest,
    ClientWebAuthPasswordUpdateRequest,
    ClientWebAuthStartRequest,
    ClientWebBillingCheckoutRequest,
    ClientWebDictionarySearchLearnRequest,
    ClientWebImportSubmitRequest,
    ClientWebLearningAnswerRequest,
    ClientWebLearningCardActionRequest,
    ClientWebLearningReadyActionRequest,
    ClientWebLearningWordPriorityRequest,
    ClientWebMagicRequest,
    ClientWebPlanSelectRequest,
    ClientWebSettingsUpdateRequest,
)
from app.client_api.client_web.students.router import build_teacher_students_router
from app.marketing.runtime_settings import AnalyticsSettingsValidationError, read_analytics_settings
from app.storage.audio import AudioStorageProvider

CLIENT_WEB_COOKIE_NAME = "cronolex_client_session"


def billing_checkout_error_status_code(error: BillingCheckoutError) -> int:
    if isinstance(error, BillingCheckoutProfileNotFoundError):
        return 404
    if isinstance(error, BillingCheckoutMaintenanceError):
        return 503
    if isinstance(error, BillingCheckoutProviderUnavailableError):
        return 502
    return 400


def client_web_plan_error_status_code(error: ClientWebPlanError) -> int:
    if isinstance(error, ClientWebPlanProfileNotFoundError):
        return 404
    return 400


def client_web_import_error_status_code(_error: ClientWebImportError) -> int:
    if isinstance(_error, ClientWebImportNotFoundError):
        return 404
    if isinstance(_error, ClientWebImportProviderUnavailableError):
        return 502
    return 400


def client_web_auth_error_status_code(error: ClientWebAuthError) -> int:
    if isinstance(error, ClientWebAuthValidationError):
        return 400
    if isinstance(error, ClientWebAuthNotFoundError):
        return 404
    if isinstance(error, ClientWebAuthRateLimitError):
        return 429
    return 401


def client_web_learning_error_status_code(error: ClientWebLearningError) -> int:
    if isinstance(error, ClientWebLearningValidationError):
        return 400
    if isinstance(error, ClientWebLearningPaymentRequiredError):
        return 402
    if isinstance(error, ClientWebLearningNotFoundError):
        return 404
    if isinstance(error, ClientWebLearningConflictError):
        return 409
    return 400


def client_web_learning_http_exception(error: ClientWebLearningError) -> HTTPException:
    return HTTPException(status_code=client_web_learning_error_status_code(error), detail=error.detail)


class ClientWebImportEventStreamer(Protocol):
    def __call__(self, *, telegram_user_id: int, job_id: int) -> Iterator[str]: ...


class ClientWebRouterRuntime(Protocol):
    db: Any
    audio_storage_provider: AudioStorageProvider
    client_web_auth_service: ClientWebAuthService
    client_web_learning_service: ClientWebLearningService
    client_web_import_service: ClientWebImportService
    client_web_settings_service: ClientWebSettingsService
    client_web_plan_service: ClientWebPlanService
    client_web_billing_checkout_service: BillingCheckoutService
    client_web_billing_payment_status_service: BillingPaymentStatusService
    client_web_billing_payment_history_service: BillingPaymentHistoryService
    client_web_teacher_student_service: ClientWebTeacherStudentService
    client_web_import_event_streamer: ClientWebImportEventStreamer


def build_client_web_router(service: ClientWebRouterRuntime) -> APIRouter:
    router = APIRouter(prefix="/client-web")

    def get_auth_service() -> ClientWebAuthService:
        return service.client_web_auth_service

    def get_learning_service() -> ClientWebLearningService:
        return service.client_web_learning_service

    def get_audio_storage_provider() -> AudioStorageProvider:
        return service.audio_storage_provider

    def get_import_service() -> ClientWebImportService:
        return service.client_web_import_service

    def get_settings_service() -> ClientWebSettingsService:
        return service.client_web_settings_service

    def get_plan_service() -> ClientWebPlanService:
        return service.client_web_plan_service

    def get_billing_checkout_service() -> BillingCheckoutService:
        return service.client_web_billing_checkout_service

    def get_billing_payment_status_service() -> BillingPaymentStatusService:
        return service.client_web_billing_payment_status_service

    def get_billing_payment_history_service() -> BillingPaymentHistoryService:
        return service.client_web_billing_payment_history_service

    def current_user(request: Request) -> dict:
        try:
            return get_auth_service().get_session_user(
                request.cookies.get(CLIENT_WEB_COOKIE_NAME),
                request_context=build_request_context(request),
            )
        except ClientWebAuthError as error:
            raise HTTPException(status_code=client_web_auth_error_status_code(error), detail=error.detail) from error

    def optional_current_user(request: Request) -> dict | None:
        try:
            return current_user(request)
        except HTTPException as error:
            if error.status_code == 401:
                return None
            raise

    def set_session_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            CLIENT_WEB_COOKIE_NAME,
            token,
            httponly=True,
            secure=service.db.settings.app_admin_cookie_secure,
            samesite="lax",
            max_age=service.db.settings.app_admin_session_hours * 3600,
            path="/",
        )

    router.include_router(
        build_teacher_students_router(
            get_teacher_student_service=lambda: service.client_web_teacher_student_service,
            current_user=current_user,
        )
    )

    @router.post("/auth/start")
    def auth_start(payload: ClientWebAuthStartRequest) -> dict:
        try:
            result = get_auth_service().start_login(username=payload.username)
        except ClientWebAuthError as error:
            raise HTTPException(status_code=client_web_auth_error_status_code(error), detail=error.detail) from error
        return {
            "challenge_id": result.challenge_id,
            "requires_otp": result.requires_otp,
            "requires_password": result.requires_password,
            "requires_password_setup": result.requires_password_setup,
        }

    @router.get("/analytics-settings")
    def analytics_settings() -> dict:
        try:
            return read_analytics_settings(service.db)
        except AnalyticsSettingsValidationError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @router.post("/auth/verify-password")
    def auth_verify_password(payload: ClientWebAuthPasswordRequest) -> dict:
        try:
            result = get_auth_service().verify_password(
                username=payload.username,
                password=payload.password,
            )
        except ClientWebAuthError as error:
            raise HTTPException(status_code=client_web_auth_error_status_code(error), detail=error.detail) from error
        return {
            "challenge_id": result.challenge_id,
            "requires_otp": result.requires_otp,
            "requires_password": result.requires_password,
            "requires_password_setup": result.requires_password_setup,
        }

    @router.post("/auth/verify-otp")
    def auth_verify_otp(request: Request, payload: ClientWebAuthOtpRequest, response: Response) -> dict:
        try:
            result = get_auth_service().verify_otp(
                challenge_id=payload.challenge_id,
                otp=payload.otp,
                request_context=build_request_context(request),
            )
        except ClientWebAuthError as error:
            raise HTTPException(status_code=client_web_auth_error_status_code(error), detail=error.detail) from error
        set_session_cookie(response, result.session_token)
        return {"user": result.user}

    @router.patch("/auth/password")
    def auth_update_password(request: Request, payload: ClientWebAuthPasswordUpdateRequest) -> dict:
        try:
            user = get_auth_service().update_password(
                user=current_user(request),
                current_password=payload.current_password,
                password=payload.password,
            )
        except ClientWebAuthError as error:
            raise HTTPException(status_code=client_web_auth_error_status_code(error), detail=error.detail) from error
        return {"user": user}

    @router.post("/auth/password-prompted")
    def auth_mark_password_prompted(request: Request) -> dict:
        user = get_auth_service().mark_password_prompted(user=current_user(request))
        return {"user": user}

    @router.post("/auth/magic")
    def auth_magic(request: Request, payload: ClientWebMagicRequest, response: Response) -> dict:
        auth_service = get_auth_service()
        try:
            result = auth_service.consume_magic_link(token=payload.token, request_context=build_request_context(request))
        except ClientWebAuthError as error:
            raise HTTPException(status_code=client_web_auth_error_status_code(error), detail=error.detail) from error
        set_session_cookie(response, result.session_token)
        return {"user": result.user, "target_path": result.target_path}

    @router.get("/auth/me")
    def auth_me(request: Request) -> dict:
        return {"user": optional_current_user(request)}

    @router.post("/auth/logout")
    def auth_logout(request: Request, response: Response) -> dict[str, str]:
        get_auth_service().logout(request.cookies.get(CLIENT_WEB_COOKIE_NAME))
        response.delete_cookie(CLIENT_WEB_COOKIE_NAME, path="/")
        return {"status": "ok"}

    @router.get("/learning/state")
    def learning_state(request: Request) -> dict:
        return get_learning_service().state(current_user(request))

    @router.get("/learning/words")
    def learning_words(
        request: Request,
        mode: str = Query(default="learning", min_length=1, max_length=32),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        word: str = Query(default="", max_length=128),
        topic: list[str] = Query(default=[]),
        level: str = Query(default="", max_length=16),
    ) -> dict:
        try:
            return get_learning_service().words(
                current_user(request),
                mode=mode,
                page=page,
                page_size=page_size,
                word=word,
                topic=topic,
                level=level,
            )
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.get("/learning/word-filters")
    def learning_word_filters(request: Request) -> dict:
        try:
            return get_learning_service().word_filters(current_user(request))
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.get("/learning/dictionary-search")
    def learning_dictionary_search(
        request: Request,
        q: str = Query(default="", max_length=128),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        level: str = Query(default="", max_length=16),
    ) -> dict:
        try:
            return get_learning_service().dictionary_search(
                current_user(request),
                query=q,
                page=page,
                page_size=page_size,
                level=level,
            )
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.post("/learning/dictionary-search/learn")
    def learning_dictionary_search_learn(request: Request, payload: ClientWebDictionarySearchLearnRequest) -> dict:
        try:
            return get_learning_service().learn_dictionary_word(
                current_user(request),
                word_source=payload.word_source,
                word_id=payload.word_id,
            )
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.post("/learning/words/priority")
    def learning_word_priority(request: Request, payload: ClientWebLearningWordPriorityRequest) -> dict:
        try:
            return get_learning_service().prioritize_word(
                current_user(request),
                word_source=payload.word_source,
                word_id=payload.word_id,
            )
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.post("/learning/start")
    def learning_start(request: Request) -> dict:
        try:
            return get_learning_service().start(current_user(request))
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.post("/learning/continue")
    def learning_continue(request: Request) -> dict:
        try:
            return get_learning_service().continue_session(current_user(request))
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.post("/learning/finish")
    def learning_finish(request: Request) -> dict:
        try:
            return get_learning_service().finish(current_user(request))
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.post("/learning/answer")
    def learning_answer(request: Request, payload: ClientWebLearningAnswerRequest) -> dict:
        try:
            return get_learning_service().answer(
                current_user(request),
                session_word_id=payload.session_word_id,
                option_index=payload.option_index,
            )
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.post("/learning/card-action")
    def learning_card_action(request: Request, payload: ClientWebLearningCardActionRequest) -> dict:
        try:
            return get_learning_service().card_action(
                current_user(request),
                session_word_id=payload.session_word_id,
                action=payload.action,
            )
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.post("/learning/ready-action")
    def learning_ready_action(request: Request, payload: ClientWebLearningReadyActionRequest) -> dict:
        try:
            return get_learning_service().ready_action(
                current_user(request),
                expected_stage=payload.expected_stage,
                decision=payload.decision,
            )
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error

    @router.get("/learning/session-words/{session_word_id}/audio")
    def learning_session_word_audio(request: Request, session_word_id: int):
        try:
            audio_path = get_learning_service().audio_path(current_user(request), session_word_id=session_word_id)
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error
        return build_audio_response(
            audio_path,
            storage_provider=get_audio_storage_provider(),
        )

    @router.get("/learning/dictionary-search/{word_source}/{word_id}/audio")
    def learning_dictionary_search_audio(request: Request, word_source: str, word_id: int):
        try:
            audio_path = get_learning_service().dictionary_search_audio_path(
                current_user(request), word_source=word_source, word_id=word_id
            )
        except ClientWebLearningError as error:
            raise client_web_learning_http_exception(error) from error
        return build_audio_response(
            audio_path,
            storage_provider=get_audio_storage_provider(),
        )

    @router.post("/imports")
    def imports_submit(request: Request, payload: ClientWebImportSubmitRequest, background_tasks: BackgroundTasks) -> dict:
        try:
            return get_import_service().submit_import(
                current_user(request),
                source_url=payload.source_url,
                text_content=payload.text_content,
                file_name=payload.file_name,
                background_tasks=background_tasks,
            )
        except ClientWebImportError as error:
            raise HTTPException(status_code=client_web_import_error_status_code(error), detail=error.detail) from error

    @router.get("/imports/items")
    def imports_user_items(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=20, le=100),
        status_category: str = Query(default="all", pattern="^(all|added|queued|rejected)$"),
    ) -> dict:
        try:
            return get_import_service().list_user_results(
                current_user(request),
                page=page,
                page_size=page_size,
                status_category=status_category,
            )
        except ClientWebImportError as error:
            raise HTTPException(status_code=client_web_import_error_status_code(error), detail=error.detail) from error

    @router.get("/imports/events")
    def imports_events(
        request: Request,
        job_id: int = Query(..., ge=1),
    ) -> StreamingResponse:
        user = current_user(request)
        try:
            get_import_service().ensure_job_for_user(user, job_id)
        except ClientWebImportError as error:
            raise HTTPException(status_code=client_web_import_error_status_code(error), detail=error.detail) from error
        telegram_user_id = int(user["telegram_user_id"])
        return StreamingResponse(
            service.client_web_import_event_streamer(
                telegram_user_id=telegram_user_id,
                job_id=job_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get("/imports/{job_id}/items")
    def imports_items(
        request: Request,
        job_id: int,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=20, le=100),
        status_category: str = Query(default="all", pattern="^(all|added|queued|rejected)$"),
    ) -> dict:
        try:
            return get_import_service().list_results(
                current_user(request),
                job_id=job_id,
                page=page,
                page_size=page_size,
                status_category=status_category,
            )
        except ClientWebImportError as error:
            raise HTTPException(status_code=client_web_import_error_status_code(error), detail=error.detail) from error

    @router.delete("/imports/google-doc-binding")
    def imports_google_doc_binding_delete(request: Request) -> dict:
        return get_import_service().clear_google_doc_binding(current_user(request))

    @router.get("/settings")
    def settings_get(request: Request) -> dict:
        try:
            return get_settings_service().get_settings(current_user(request))
        except ClientWebSettingsError as error:
            raise HTTPException(status_code=400, detail=error.detail) from error

    @router.get("/plans")
    def plans_get(request: Request) -> dict:
        try:
            return get_plan_service().list_plans(current_user(request))
        except ClientWebPlanError as error:
            raise HTTPException(status_code=client_web_plan_error_status_code(error), detail=error.detail) from error

    @router.post("/plans/select")
    def plans_select(request: Request, payload: ClientWebPlanSelectRequest) -> dict:
        try:
            return get_plan_service().select_plan(current_user(request), plan_key=payload.plan_key)
        except ClientWebPlanError as error:
            raise HTTPException(status_code=client_web_plan_error_status_code(error), detail=error.detail) from error

    @router.get("/billing/offer")
    def billing_offer_get(request: Request) -> dict:
        current_user(request)
        try:
            return get_billing_checkout_service().get_offer()
        except BillingCheckoutError as error:
            raise HTTPException(status_code=billing_checkout_error_status_code(error), detail=error.detail) from error

    @router.post("/billing/checkout")
    def billing_checkout_create(request: Request, payload: ClientWebBillingCheckoutRequest) -> dict:
        try:
            return get_billing_checkout_service().create_checkout(
                current_user(request),
                plan_key=payload.plan_key,
                period_months=payload.period_months,
                offer_accepted=payload.offer_accepted,
                offer_text_hash=payload.offer_text_hash,
                source_path=payload.source_path,
                request_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        except BillingCheckoutError as error:
            raise HTTPException(status_code=billing_checkout_error_status_code(error), detail=error.detail) from error

    @router.get("/billing/payments/{payment_id}/status")
    def billing_payment_status_get(
        request: Request,
        payment_id: int = Path(..., ge=1),
    ) -> dict:
        try:
            return get_billing_payment_status_service().get_client_payment_status(
                current_user(request),
                payment_id=payment_id,
                request_ip=request.client.host if request.client else None,
            )
        except BillingPaymentStatusError as error:
            status_code = 404 if isinstance(error, BillingPaymentStatusNotFoundError) else 400
            raise HTTPException(status_code=status_code, detail=error.detail) from error

    @router.get("/billing/payments")
    def billing_payments_list(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=50),
    ) -> dict:
        try:
            return get_billing_payment_history_service().list_client_payments(
                current_user(request),
                page=page,
                page_size=page_size,
            )
        except BillingPaymentHistoryProfileNotFoundError as error:
            raise HTTPException(status_code=404, detail=error.detail) from error

    @router.patch("/settings")
    def settings_patch(request: Request, payload: ClientWebSettingsUpdateRequest) -> dict:
        try:
            return get_settings_service().update_settings(
                current_user(request),
                interface_locale=payload.interface_locale,
                language_level=payload.language_level,
                words_per_session=payload.words_per_session,
                daily_reminder_hour=payload.daily_reminder_hour,
                reminder_weekdays=payload.reminder_weekdays,
                reminder_schedule=(
                    [item.model_dump() for item in payload.reminder_schedule]
                    if payload.reminder_schedule is not None
                    else None
                ),
            )
        except ClientWebSettingsError as error:
            raise HTTPException(status_code=400, detail=error.detail) from error

    return router
