from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.entity.http_errors import admin_entity_error_status_code
from app.admin_api.read.http_errors import admin_read_http_exception
from app.application.admin.entity.errors import AdminEntityError
from app.application.admin.read.errors import AdminReadError


def build_entity_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/{entity_type}/filter-metadata")
    def admin_filter_metadata(entity_type: str, request: Request, scope: str = Query(default="operations")) -> dict:
        try:
            return context.admin_read_service().get_filter_metadata(
                actor=context.current_admin_user(request),
                entity_type=entity_type,
                params={"scope": scope},
            )
        except AdminReadError as error:
            raise admin_read_http_exception(error) from error

    @router.post("/{entity_type}/{entity_id}/archive")
    def admin_archive_entity(entity_type: str, entity_id: str, request: Request) -> dict[str, str]:
        try:
            return context.admin_entity_service().archive_entity(
                actor=context.current_admin_user(request),
                entity_type=entity_type,
                entity_id=entity_id,
            )
        except AdminEntityError as error:
            raise HTTPException(status_code=admin_entity_error_status_code(error), detail=error.detail) from error

    @router.delete("/{entity_type}/{entity_id}")
    def admin_delete_entity(entity_type: str, entity_id: str, request: Request) -> dict[str, str]:
        try:
            return context.admin_entity_service().delete_entity(
                actor=context.current_admin_user(request),
                entity_type=entity_type,
                entity_id=entity_id,
            )
        except AdminEntityError as error:
            raise HTTPException(status_code=admin_entity_error_status_code(error), detail=error.detail) from error

    return router
