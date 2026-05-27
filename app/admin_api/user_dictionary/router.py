from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.schemas import (
    AdminUserDictionaryBulkActionRequest,
    AdminUserDictionaryPromoteRequest,
)
from app.admin_api.user_dictionary.http_errors import (
    admin_user_dictionary_action_http_exception,
    admin_user_dictionary_read_http_exception,
)
from app.api_helpers.audio_response import build_audio_response
from app.application.admin.user_dictionary.errors import (
    AdminUserDictionaryActionError,
    AdminUserDictionaryReadError,
)


def build_user_dictionary_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/user-dictionary/entries")
    def admin_user_dictionary_entries(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        search: str = "",
        status: list[str] | None = Query(default=None),
        part_of_speech: list[str] | None = Query(default=None),
        level_id: list[str] | None = Query(default=None),
    ) -> dict:
        try:
            return context.admin_user_dictionary_read_service().list_entries(
                actor=context.current_admin_user(request),
                params={
                    "page": page,
                    "page_size": page_size,
                    "search": search,
                    "status": status,
                    "part_of_speech": part_of_speech,
                    "level_id": level_id,
                },
            )
        except AdminUserDictionaryReadError as error:
            raise admin_user_dictionary_read_http_exception(error) from error

    @router.get("/user-dictionary/entries/{entry_id}/audio")
    def admin_user_dictionary_audio(entry_id: int, request: Request):
        try:
            audio_path = context.admin_user_dictionary_read_service().get_audio_path(
                actor=context.current_admin_user(request),
                entry_id=entry_id,
            )
        except AdminUserDictionaryReadError as error:
            raise admin_user_dictionary_read_http_exception(error) from error
        return build_audio_response(
            audio_path,
            storage_provider=context.audio_storage_provider(),
        )

    @router.get("/user-dictionary/entries/{entry_id}")
    def admin_user_dictionary_entry_detail(entry_id: int, request: Request) -> dict:
        try:
            return context.admin_user_dictionary_read_service().get_entry_detail(
                actor=context.current_admin_user(request),
                entry_id=entry_id,
            )
        except AdminUserDictionaryReadError as error:
            raise admin_user_dictionary_read_http_exception(error) from error

    @router.post("/user-dictionary/entries/promote")
    def admin_user_dictionary_entries_promote(request: Request, payload: AdminUserDictionaryPromoteRequest) -> dict:
        try:
            return context.admin_user_dictionary_promote_action().promote_entries(
                actor=context.current_admin_user(request),
                entry_ids=payload.entry_ids,
            )
        except AdminUserDictionaryActionError as error:
            raise admin_user_dictionary_action_http_exception(error) from error

    @router.post("/user-dictionary/entries/bulk-action")
    def admin_user_dictionary_entries_bulk_action(request: Request, payload: AdminUserDictionaryBulkActionRequest) -> dict:
        try:
            return context.admin_user_dictionary_bulk_action().execute(
                actor=context.current_admin_user(request),
                action=payload.action,
                entry_ids=payload.entry_ids,
            )
        except AdminUserDictionaryActionError as error:
            raise admin_user_dictionary_action_http_exception(error) from error

    @router.post("/user-dictionary/entries/{entry_id}/promote")
    def admin_user_dictionary_promote(entry_id: int, request: Request) -> dict:
        try:
            return context.admin_user_dictionary_promote_action().promote_entry(
                actor=context.current_admin_user(request),
                entry_id=entry_id,
            )
        except AdminUserDictionaryActionError as error:
            raise admin_user_dictionary_action_http_exception(error) from error

    return router
