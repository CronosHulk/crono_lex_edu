from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.admin_api.context import AdminRouterContext
from app.application.admin.permissions import AdminPermissionDeniedError


def build_bootstrap_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/app/bootstrap")
    def admin_bootstrap(request: Request) -> dict:
        user = context.current_admin_user(request)
        try:
            return context.admin_bootstrap_service().bootstrap(user)
        except AdminPermissionDeniedError as error:
            raise HTTPException(status_code=403, detail=error.detail) from error

    return router
