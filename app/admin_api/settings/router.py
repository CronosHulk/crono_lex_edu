from __future__ import annotations

from fastapi import APIRouter, Request

from app.admin_api.context import AdminRouterContext
from app.admin_api.schemas import (
    AdminActionOtpConfirmRequest,
    AdminBillingMonobankModeUpdateRequest,
    AdminBillingProviderSettingsUpdateRequest,
    AdminProviderSettingsUpdateRequest,
    AdminSettingsUpdateRequest,
)
from app.admin_api.settings.http_errors import admin_settings_http_exception
from app.application.admin.settings.errors import AdminSettingsError


def build_settings_router(context: AdminRouterContext) -> APIRouter:
    router = APIRouter()

    @router.get("/settings")
    def admin_get_settings(request: Request) -> dict:
        try:
            return context.admin_settings_service().get_settings(user=context.current_admin_user(request))
        except AdminSettingsError as error:
            raise admin_settings_http_exception(error) from error

    @router.patch("/settings")
    def admin_update_settings(request: Request, payload: AdminSettingsUpdateRequest) -> dict:
        try:
            return context.admin_settings_service().update_settings(
                user=context.current_admin_user(request),
                payload=payload.model_dump(exclude_unset=True),
            )
        except AdminSettingsError as error:
            raise admin_settings_http_exception(error) from error

    @router.patch("/settings/billing/monobank-mode")
    def admin_update_billing_monobank_mode(request: Request, payload: AdminBillingMonobankModeUpdateRequest) -> dict:
        try:
            return context.admin_settings_service().update_billing_monobank_mode_with_otp(
                user=context.current_admin_user(request),
                monobank_mode=payload.monobank_mode,
                challenge_id=payload.challenge_id,
                otp=payload.otp,
                action_key="billing_monobank_mode",
            )
        except AdminSettingsError as error:
            raise admin_settings_http_exception(error) from error

    @router.patch("/settings/billing/provider")
    @router.patch("/settings/billing/provider-settings")
    def admin_update_billing_provider_settings(request: Request, payload: AdminBillingProviderSettingsUpdateRequest) -> dict:
        try:
            return context.admin_settings_service().update_billing_provider_settings_with_otp(
                user=context.current_admin_user(request),
                payload=payload.model_dump(exclude_unset=True),
                action_key="billing_provider_settings",
            )
        except AdminSettingsError as error:
            raise admin_settings_http_exception(error) from error

    @router.get("/settings/providers")
    def admin_get_provider_settings(request: Request) -> dict:
        try:
            return context.admin_settings_service().list_provider_settings(user=context.current_admin_user(request))
        except AdminSettingsError as error:
            raise admin_settings_http_exception(error) from error

    @router.patch("/settings/providers")
    def admin_update_provider_settings(request: Request, payload: AdminProviderSettingsUpdateRequest) -> dict:
        try:
            return context.admin_settings_service().update_provider_settings(
                user=context.current_admin_user(request),
                payload=payload.model_dump(),
            )
        except AdminSettingsError as error:
            raise admin_settings_http_exception(error) from error

    @router.delete("/settings/import-data")
    def admin_delete_import_data(request: Request, payload: AdminActionOtpConfirmRequest) -> dict:
        try:
            return context.admin_settings_service().delete_all_import_data_with_otp(
                user=context.current_admin_user(request),
                challenge_id=payload.challenge_id,
                otp=payload.otp,
            )
        except AdminSettingsError as error:
            raise admin_settings_http_exception(error) from error

    return router
