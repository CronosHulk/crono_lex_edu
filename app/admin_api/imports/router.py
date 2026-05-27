from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.imports.http_errors import admin_import_read_error_status_code
from app.application.admin.imports.errors import AdminImportReadError


def build_imports_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/import-jobs")
    def admin_import_jobs(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        search: str = "",
        status: list[str] | None = Query(default=None),
        source_type: list[str] | None = Query(default=None),
        user_id: str | None = None,
    ) -> dict:
        try:
            return context.admin_import_read_service().list_import_jobs(
                actor=context.current_admin_user(request),
                params={
                    "page": page,
                    "page_size": page_size,
                    "search": search,
                    "status": status,
                    "source_type": source_type,
                    "user_id": user_id,
                },
            )
        except AdminImportReadError as error:
            raise HTTPException(
                status_code=admin_import_read_error_status_code(error),
                detail=error.detail,
            ) from error

    @router.get("/import-items")
    def admin_import_items(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        search: str = "",
        status: list[str] | None = Query(default=None),
        import_job_id: int | None = None,
        user_id: str | None = None,
    ) -> dict:
        try:
            return context.admin_import_read_service().list_import_items(
                actor=context.current_admin_user(request),
                params={
                    "page": page,
                    "page_size": page_size,
                    "search": search,
                    "status": status,
                    "import_job_id": import_job_id,
                    "user_id": user_id,
                },
            )
        except AdminImportReadError as error:
            raise HTTPException(
                status_code=admin_import_read_error_status_code(error),
                detail=error.detail,
            ) from error

    @router.get("/import-jobs/{import_job_id}")
    def admin_import_job_detail(import_job_id: int, request: Request) -> dict:
        try:
            return context.admin_import_read_service().get_import_job_detail(
                actor=context.current_admin_user(request),
                import_job_id=import_job_id,
            )
        except AdminImportReadError as error:
            raise HTTPException(
                status_code=admin_import_read_error_status_code(error),
                detail=error.detail,
            ) from error

    return router
