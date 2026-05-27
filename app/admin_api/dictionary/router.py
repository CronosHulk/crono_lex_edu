from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.dictionary.http_errors import (
    admin_dictionary_action_http_exception,
    admin_dictionary_read_http_exception,
    admin_dictionary_service_http_exception,
)
from app.admin_api.schemas import AdminDictionaryEntryUpdateRequest, AdminDictionaryVerifyRequest
from app.api_helpers.audio_response import build_audio_response
from app.application.admin.dictionary.errors import (
    AdminDictionaryActionError,
    AdminDictionaryReadError,
    AdminDictionaryServiceError,
)


def build_dictionary_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/dictionary/entries")
    def admin_dictionary_entries(
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50),
        archived: bool = False,
        search: str = "",
        part_of_speech: list[str] | None = Query(default=None),
        category: list[str] | None = Query(default=None),
        entry_type: list[str] | None = Query(default=None),
        verified: str = Query(default="all"),
    ) -> dict:
        actor = context.current_admin_user(request)
        try:
            return context.admin_dictionary_read_service().list_dictionary_entries(
                actor=actor,
                params={
                    "page": page,
                    "page_size": page_size,
                    "archived": str(archived).lower(),
                    "search": search,
                    "part_of_speech": part_of_speech,
                    "category": category,
                    "entry_type": entry_type,
                    "verified": verified,
                },
            )
        except AdminDictionaryReadError as error:
            raise admin_dictionary_read_http_exception(error) from error

    @router.post("/dictionary/entries/verify")
    def admin_dictionary_entries_verify(request: Request, payload: AdminDictionaryVerifyRequest) -> dict:
        actor = context.current_admin_user(request)
        try:
            return context.admin_dictionary_action_service().verify_entries(actor=actor, entry_ids=payload.entry_ids)
        except AdminDictionaryActionError as error:
            raise admin_dictionary_action_http_exception(error) from error

    @router.get("/dictionary/entries/{entry_id}")
    def admin_dictionary_entry_detail(entry_id: int, request: Request) -> dict:
        try:
            return context.admin_dictionary_read_service().get_dictionary_entry(
                actor=context.current_admin_user(request),
                entry_id=entry_id,
            )
        except AdminDictionaryReadError as error:
            raise admin_dictionary_read_http_exception(error) from error

    @router.patch("/dictionary/entries/{entry_id}")
    def admin_dictionary_entry_update(
        entry_id: int,
        request: Request,
        payload: AdminDictionaryEntryUpdateRequest,
    ) -> dict:
        actor = context.current_admin_user(request)
        update_payload: dict[str, Any] = payload.model_dump(exclude_unset=True)
        try:
            return context.admin_dictionary_service().update_dictionary_entry(
                actor=actor,
                entry_id=entry_id,
                payload=update_payload,
            )
        except AdminDictionaryServiceError as error:
            raise admin_dictionary_service_http_exception(error) from error

    @router.get("/dictionary/entries/{entry_id}/audio")
    def admin_dictionary_audio(entry_id: int, request: Request):
        user = context.current_admin_user(request)
        try:
            audio_path = context.admin_dictionary_service().get_audio_path(actor=user, entry_id=entry_id)
        except AdminDictionaryServiceError as error:
            raise admin_dictionary_service_http_exception(error) from error
        return build_audio_response(
            audio_path,
            storage_provider=context.audio_storage_provider(),
        )

    return router
