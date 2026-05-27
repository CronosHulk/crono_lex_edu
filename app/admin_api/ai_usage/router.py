from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.admin_api.ai_usage.http_errors import admin_ai_usage_read_error_status_code
from app.admin_api.context import AdminRouterContext
from app.admin_api.schemas import AdminActionOtpConfirmRequest
from app.application.admin.ai_usage.errors import AdminAIUsageReadError


def build_ai_usage_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/ai-usage/summary")
    def admin_ai_usage_summary(
        request: Request,
        period: str = Query(default="week"),
    ) -> dict:
        try:
            return context.admin_ai_usage_read_service().summarize(
                actor=context.current_admin_user(request),
                period=period,
            )
        except AdminAIUsageReadError as error:
            raise HTTPException(
                status_code=admin_ai_usage_read_error_status_code(error),
                detail=error.detail,
            ) from error

    @router.get("/ai-usage/sessions")
    def admin_ai_usage_sessions(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        period: str = Query(default="week"),
        search: str = "",
        task_scope: list[str] | None = Query(default=None),
        task_key: list[str] | None = Query(default=None),
        provider_key: list[str] | None = Query(default=None),
        model: list[str] | None = Query(default=None),
        user_id: str | None = None,
    ) -> dict:
        try:
            return context.admin_ai_usage_read_service().list_sessions(
                actor=context.current_admin_user(request),
                params={
                    "page": page,
                    "page_size": page_size,
                    "period": period,
                    "search": search,
                    "task_scope": task_scope,
                    "task_key": task_key,
                    "provider_key": provider_key,
                    "model": model,
                    "actor_user_id": user_id,
                },
            )
        except AdminAIUsageReadError as error:
            raise HTTPException(
                status_code=admin_ai_usage_read_error_status_code(error),
                detail=error.detail,
            ) from error

    @router.delete("/ai-usage/sessions")
    def admin_delete_ai_usage_sessions(request: Request, payload: AdminActionOtpConfirmRequest) -> dict:
        try:
            return context.admin_ai_usage_read_service().delete_all_sessions_with_otp(
                actor=context.current_admin_user(request),
                challenge_id=payload.challenge_id,
                otp=payload.otp,
            )
        except AdminAIUsageReadError as error:
            raise HTTPException(
                status_code=admin_ai_usage_read_error_status_code(error),
                detail=error.detail,
            ) from error

    return router
