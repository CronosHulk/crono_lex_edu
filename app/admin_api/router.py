from __future__ import annotations

from typing import Any, Protocol

from fastapi import APIRouter, Request

from app.admin_api.ai_usage.router import build_ai_usage_router
from app.admin_api.auth.constants import ADMIN_COOKIE_NAME
from app.admin_api.auth.router import build_auth_router
from app.admin_api.billing.router import build_billing_router
from app.admin_api.bootstrap.router import build_bootstrap_router
from app.admin_api.context import AdminRouterContext
from app.admin_api.dashboard.router import build_dashboard_router
from app.admin_api.dictionary.router import build_dictionary_router
from app.admin_api.entity.router import build_entity_router
from app.admin_api.exercise_texts.router import build_exercise_texts_router
from app.admin_api.imports.router import build_imports_router
from app.admin_api.logs.router import build_logs_router
from app.admin_api.schemas import (
    AdminApiRequest,
    AdminAuthMagicRequest,
    AdminAuthStartRequest,
    AdminAuthVerifyRequest,
    AdminDictionaryEntryUpdateRequest,
    AdminDictionaryVerifyRequest,
    AdminPasswordUpdateRequest,
    AdminSetLearningRoleRequest,
    AdminSetPasswordRequest,
    AdminSetRoleRequest,
    AdminSetSubscriptionRequest,
    AdminSettingsUpdateRequest,
    AdminTeacherAssignmentRequest,
    AdminUserDictionaryBulkActionRequest,
    AdminUserDictionaryPromoteRequest,
)
from app.admin_api.settings.router import build_settings_router
from app.admin_api.user_dictionary.router import build_user_dictionary_router
from app.admin_api.users.router import build_users_router
from app.api_helpers.request_context import build_request_context

__all__ = [
    "AdminApiRequest",
    "AdminAuthMagicRequest",
    "AdminAuthStartRequest",
    "AdminAuthVerifyRequest",
    "AdminDictionaryEntryUpdateRequest",
    "AdminDictionaryVerifyRequest",
    "AdminPasswordUpdateRequest",
    "AdminSettingsUpdateRequest",
    "AdminSetLearningRoleRequest",
    "AdminSetPasswordRequest",
    "AdminSetRoleRequest",
    "AdminSetSubscriptionRequest",
    "AdminUserDictionaryBulkActionRequest",
    "AdminUserDictionaryPromoteRequest",
    "build_admin_router",
    "AdminTeacherAssignmentRequest",
]


class AdminRouterRuntime(Protocol):
    db: Any


def build_admin_router(service: AdminRouterRuntime) -> APIRouter:
    router = APIRouter(prefix="/admin")

    def _admin_dependencies() -> Any:
        return getattr(service, "admin_service_dependencies")

    def _admin_ai_usage_read_service():
        return _admin_dependencies().admin_ai_usage_read_service

    def _admin_auth_service():
        return _admin_dependencies().admin_auth_service

    def _admin_billing_read_service():
        return _admin_dependencies().admin_billing_read_service

    def _admin_bootstrap_service():
        return _admin_dependencies().admin_bootstrap_service

    def _admin_dashboard_service():
        return _admin_dependencies().admin_dashboard_service

    def _admin_dictionary_action_service():
        return _admin_dependencies().admin_dictionary_action_service

    def _admin_dictionary_read_service():
        return _admin_read_service().dictionary_read_service

    def _admin_dictionary_service():
        return _admin_dependencies().admin_dictionary_service

    def _admin_entity_service():
        return _admin_dependencies().admin_entity_service

    def _admin_exercise_text_service():
        return _admin_dependencies().admin_exercise_text_service

    def _admin_exercise_text_generation_service():
        return _admin_dependencies().admin_exercise_text_generation_service

    def _admin_exercise_text_tts_service():
        return _admin_dependencies().admin_exercise_text_tts_service

    def _admin_import_read_service():
        return _admin_read_service().import_read_service

    def _admin_log_read_service():
        return _admin_read_service().log_read_service

    def _admin_read_service():
        return _admin_dependencies().admin_read_service

    def _admin_settings_service():
        return _admin_dependencies().admin_settings_service

    def _admin_user_dictionary_read_service():
        return _admin_read_service().user_dictionary_read_service

    def _admin_user_dictionary_bulk_action():
        return _admin_dependencies().admin_user_dictionary_bulk_action

    def _admin_user_dictionary_promote_action():
        return _admin_dependencies().admin_user_dictionary_promote_action

    def _admin_user_action_service():
        return _admin_dependencies().admin_user_action_service

    def _admin_user_read_service():
        return _admin_read_service().user_read_service

    def _audio_storage_provider():
        return _admin_dependencies().audio_storage_provider

    def _current_admin_user(request: Request) -> dict:
        return _admin_auth_service().get_session_user(
            request.cookies.get(ADMIN_COOKIE_NAME),
            request_context=build_request_context(request),
        )

    context = AdminRouterContext(
        current_admin_user=_current_admin_user,
        admin_ai_usage_read_service=_admin_ai_usage_read_service,
        admin_auth_service=_admin_auth_service,
        admin_billing_read_service=_admin_billing_read_service,
        admin_bootstrap_service=_admin_bootstrap_service,
        admin_dashboard_service=_admin_dashboard_service,
        admin_dictionary_action_service=_admin_dictionary_action_service,
        admin_dictionary_read_service=_admin_dictionary_read_service,
        admin_dictionary_service=_admin_dictionary_service,
        admin_entity_service=_admin_entity_service,
        admin_exercise_text_service=_admin_exercise_text_service,
        admin_exercise_text_generation_service=_admin_exercise_text_generation_service,
        admin_exercise_text_tts_service=_admin_exercise_text_tts_service,
        admin_import_read_service=_admin_import_read_service,
        admin_log_read_service=_admin_log_read_service,
        admin_read_service=_admin_read_service,
        admin_settings_service=_admin_settings_service,
        admin_user_dictionary_bulk_action=_admin_user_dictionary_bulk_action,
        admin_user_dictionary_promote_action=_admin_user_dictionary_promote_action,
        admin_user_dictionary_read_service=_admin_user_dictionary_read_service,
        admin_user_action_service=_admin_user_action_service,
        admin_user_read_service=_admin_user_read_service,
        audio_storage_provider=_audio_storage_provider,
    )
    router.include_router(build_auth_router(service, context))
    router.include_router(build_bootstrap_router(context))
    router.include_router(build_dashboard_router(context))
    router.include_router(build_dictionary_router(context))
    router.include_router(build_exercise_texts_router(context))
    router.include_router(build_users_router(context))
    router.include_router(build_logs_router(context))
    router.include_router(build_ai_usage_router(context))
    router.include_router(build_imports_router(context))
    router.include_router(build_user_dictionary_router(context))
    router.include_router(build_settings_router(context))
    router.include_router(build_billing_router(context))
    router.include_router(build_entity_router(context))
    return router
