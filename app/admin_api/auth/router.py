from __future__ import annotations

from typing import Any, Protocol

from fastapi import APIRouter, HTTPException, Request, Response

from app.admin_api.auth.constants import ADMIN_COOKIE_NAME
from app.admin_api.auth.http_errors import admin_auth_error_status_code
from app.admin_api.context import AdminRouterContext
from app.admin_api.schemas import (
    AdminActionOtpStartRequest,
    AdminAuthMagicRequest,
    AdminAuthStartRequest,
    AdminAuthVerifyRequest,
    AdminPasswordUpdateRequest,
    AdminSetPasswordRequest,
)
from app.api_helpers.request_context import build_request_context
from app.application.admin.auth.errors import AdminAuthError


class AdminAuthRouterRuntime(Protocol):
    db: Any


def admin_auth_http_exception(error: AdminAuthError) -> HTTPException:
    return HTTPException(status_code=admin_auth_error_status_code(error), detail=error.detail)


def build_auth_router(service: AdminAuthRouterRuntime, context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/start")
    def admin_auth_start(request: Request, payload: AdminAuthStartRequest) -> dict:
        try:
            result = context.admin_auth_service().start_login(
                username=payload.username,
                password=payload.password,
                request_context=build_request_context(request),
            )
        except AdminAuthError as error:
            raise admin_auth_http_exception(error) from error
        return {
            "challenge_id": result.challenge_id,
            "requires_otp": result.requires_otp,
            "requires_password": result.requires_password,
            "requires_password_setup": result.requires_password_setup,
            "dev_otp_hint": result.dev_otp_hint,
        }

    @router.post("/auth/verify-otp")
    def admin_auth_verify_otp(request: Request, payload: AdminAuthVerifyRequest, response: Response) -> dict:
        try:
            result = context.admin_auth_service().verify_otp(
                challenge_id=payload.challenge_id,
                otp=payload.otp,
                request_context=build_request_context(request),
            )
        except AdminAuthError as error:
            raise admin_auth_http_exception(error) from error
        response.set_cookie(
            ADMIN_COOKIE_NAME,
            result.session_token,
            httponly=True,
            secure=service.db.settings.app_admin_cookie_secure,
            samesite="lax",
            max_age=service.db.settings.app_admin_session_hours * 3600,
            path="/",
        )
        return {"user": result.user, "requires_password_setup": result.requires_password_setup}

    @router.post("/auth/magic")
    def admin_auth_magic(request: Request, payload: AdminAuthMagicRequest, response: Response) -> dict:
        try:
            result = context.admin_auth_service().consume_magic_link(
                token=payload.token,
                request_context=build_request_context(request),
            )
        except AdminAuthError as error:
            raise admin_auth_http_exception(error) from error
        response.set_cookie(
            ADMIN_COOKIE_NAME,
            result.session_token,
            httponly=True,
            secure=service.db.settings.app_admin_cookie_secure,
            samesite="lax",
            max_age=service.db.settings.app_admin_session_hours * 3600,
            path="/",
        )
        return {
            "user": result.user,
            "requires_password_setup": result.requires_password_setup,
            "target_path": result.target_path,
        }

    @router.post("/auth/action-otp")
    def admin_action_otp(request: Request, payload: AdminActionOtpStartRequest) -> dict:
        try:
            return context.admin_auth_service().start_action_otp(
                user=context.current_admin_user(request),
                action_key=payload.action_key,
            )
        except AdminAuthError as error:
            raise admin_auth_http_exception(error) from error

    @router.post("/auth/set-password")
    def admin_set_password(request: Request, payload: AdminSetPasswordRequest) -> dict[str, str]:
        user = context.current_admin_user(request)
        try:
            context.admin_auth_service().set_password(user=user, password=payload.password)
        except AdminAuthError as error:
            raise admin_auth_http_exception(error) from error
        return {"status": "ok"}

    @router.patch("/auth/password")
    def admin_update_password(request: Request, payload: AdminPasswordUpdateRequest) -> dict:
        try:
            user = context.admin_auth_service().update_password(
                user=context.current_admin_user(request),
                current_password=payload.current_password,
                password=payload.password,
            )
        except AdminAuthError as error:
            raise admin_auth_http_exception(error) from error
        return {"user": user}

    @router.post("/auth/password-prompted")
    def admin_mark_password_prompted(request: Request) -> dict:
        try:
            user = context.admin_auth_service().mark_password_prompted(user=context.current_admin_user(request))
        except AdminAuthError as error:
            raise admin_auth_http_exception(error) from error
        return {"user": user}

    @router.post("/auth/logout")
    def admin_logout(request: Request, response: Response) -> dict[str, str]:
        context.admin_auth_service().logout(
            request.cookies.get(ADMIN_COOKIE_NAME),
            request_context=build_request_context(request),
        )
        response.delete_cookie(ADMIN_COOKIE_NAME, path="/")
        return {"status": "ok"}

    @router.get("/auth/me")
    def admin_me(request: Request) -> dict:
        return {"user": context.current_admin_user(request)}

    return router
