from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.read.http_errors import admin_read_http_exception
from app.admin_api.schemas import (
    AdminSetLearningRoleRequest,
    AdminSetRoleRequest,
    AdminSetSubscriptionRequest,
    AdminSetSubscriptionTrialRequest,
)
from app.admin_api.users.http_errors import (
    admin_user_action_http_exception,
    admin_user_read_http_exception,
)
from app.application.admin.read.errors import AdminReadError
from app.application.admin.users.errors import (
    AdminUserActionError,
    AdminUserReadError,
)


def build_users_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/users")
    def admin_users(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        archived: bool = False,
        search: str = "",
        user_type: str = Query(default="student"),
        user_id: str = "",
        role: list[str] | None = Query(default=None),
        status: list[str] | None = Query(default=None),
    ) -> dict:
        actor = context.current_admin_user(request)
        try:
            return context.admin_user_read_service().list_users(
                actor=actor,
                params={
                    "page": page,
                    "page_size": page_size,
                    "archived": str(archived).lower(),
                    "search": search,
                    "user_type": user_type,
                    "user_id": user_id,
                    "role": role,
                    "status": status,
                }
            )
        except AdminUserReadError as error:
            raise admin_user_read_http_exception(error) from error

    @router.get("/users/filter-metadata")
    def admin_user_filter_metadata(request: Request) -> dict:
        try:
            return context.admin_read_service().get_filter_metadata(
                actor=context.current_admin_user(request),
                entity_type="users",
            )
        except AdminReadError as error:
            raise admin_read_http_exception(error) from error

    @router.get("/users/{user_id}")
    def admin_user_detail(user_id: str, request: Request) -> dict:
        try:
            return context.admin_user_read_service().get_user_detail(
                actor=context.current_admin_user(request),
                user_id=user_id,
            )
        except AdminUserReadError as error:
            raise admin_user_read_http_exception(error) from error

    @router.get("/users/{user_id}/login-history")
    def admin_user_login_history(
        user_id: str,
        request: Request,
        limit: int = Query(default=10, ge=1, le=100),
    ) -> dict:
        try:
            return context.admin_user_read_service().list_latest_login_history_for_user(
                actor=context.current_admin_user(request),
                user_id=user_id,
                limit=limit,
            )
        except AdminUserReadError as error:
            raise admin_user_read_http_exception(error) from error

    @router.post("/users/{user_id}/roles")
    def admin_set_user_role(user_id: str, request: Request, payload: AdminSetRoleRequest) -> dict:
        try:
            return context.admin_user_action_service().set_role(
                actor=context.current_admin_user(request),
                target_user_id=user_id,
                role=payload.role,
            )
        except AdminUserActionError as error:
            raise admin_user_action_http_exception(error) from error

    @router.post("/users/{user_id}/learning-role")
    def admin_set_user_learning_role(user_id: str, request: Request, payload: AdminSetLearningRoleRequest) -> dict:
        try:
            return context.admin_user_action_service().set_learning_role(
                actor=context.current_admin_user(request),
                target_user_id=user_id,
                learning_role=payload.learning_role,
            )
        except AdminUserActionError as error:
            raise admin_user_action_http_exception(error) from error

    @router.post("/users/{user_id}/subscription")
    def admin_set_user_subscription(user_id: str, request: Request, payload: AdminSetSubscriptionRequest) -> dict:
        try:
            return context.admin_user_action_service().set_subscription(
                actor=context.current_admin_user(request),
                target_user_id=user_id,
                plan_key=payload.plan_key,
            )
        except AdminUserActionError as error:
            raise admin_user_action_http_exception(error) from error

    @router.post("/users/{user_id}/subscription-trial")
    def admin_set_user_subscription_trial(user_id: str, request: Request, payload: AdminSetSubscriptionTrialRequest) -> dict:
        try:
            return context.admin_user_action_service().set_subscription_trial(
                actor=context.current_admin_user(request),
                target_user_id=user_id,
                is_trial_enabled=payload.is_trial_enabled,
            )
        except AdminUserActionError as error:
            raise admin_user_action_http_exception(error) from error

    @router.post("/users/{user_id}/password-reset")
    def admin_reset_user_password(user_id: str, request: Request) -> dict:
        try:
            return context.admin_user_action_service().reset_password(
                actor=context.current_admin_user(request),
                user_id=user_id,
            )
        except AdminUserActionError as error:
            raise admin_user_action_http_exception(error) from error

    return router
