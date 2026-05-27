from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.logs.http_errors import admin_log_read_http_exception
from app.application.admin.logs.errors import AdminLogReadError


def build_logs_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/login-history")
    def admin_login_history(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        user_id: str | None = None,
        interface_context: list[str] | None = Query(default=None),
        result: list[str] | None = Query(default=None),
        api_origin: str = "",
    ) -> dict:
        actor = context.current_admin_user(request)
        try:
            return context.admin_log_read_service().list_login_history(
                actor=actor,
                params={
                    "page": page,
                    "page_size": page_size,
                    "user_id": user_id,
                    "interface_context": interface_context,
                    "result": result,
                    "api_origin": api_origin,
                },
            )
        except AdminLogReadError as error:
            raise admin_log_read_http_exception(error) from error

    @router.get("/task-logs")
    def admin_task_logs(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        search: str = "",
        task_type: list[str] | None = Query(default=None),
        status: list[str] | None = Query(default=None),
        user_id: str | None = None,
        import_job_id: int | None = None,
        scope: str = "operations",
    ) -> dict:
        actor = context.current_admin_user(request)
        try:
            return context.admin_log_read_service().list_task_logs(
                actor=actor,
                params={
                    "page": page,
                    "page_size": page_size,
                    "search": search,
                    "task_type": task_type,
                    "status": status,
                    "user_id": user_id,
                    "import_job_id": import_job_id,
                    "scope": scope,
                },
            )
        except AdminLogReadError as error:
            raise admin_log_read_http_exception(error) from error

    @router.get("/task-logs/{task_log_id}")
    def admin_task_log_detail(task_log_id: int, request: Request) -> dict:
        try:
            return context.admin_log_read_service().get_task_log_detail(
                actor=context.current_admin_user(request),
                task_log_id=task_log_id,
            )
        except AdminLogReadError as error:
            raise admin_log_read_http_exception(error) from error

    @router.get("/error-log")
    def admin_error_logs(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        search: str = "",
        level: list[str] | None = Query(default=None),
    ) -> dict:
        actor = context.current_admin_user(request)
        try:
            return context.admin_log_read_service().list_error_logs(
                actor=actor,
                params={
                    "page": page,
                    "page_size": page_size,
                    "search": search,
                    "level": level,
                },
            )
        except AdminLogReadError as error:
            raise admin_log_read_http_exception(error) from error

    return router
