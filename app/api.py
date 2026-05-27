from __future__ import annotations

from typing import Any, Protocol

from fastapi import APIRouter

from app.admin_api.router import build_admin_router
from app.billing_api import build_billing_router
from app.client_api.client_web.router import build_client_web_router
from app.client_api.router import build_client_router


class ApiRouterRuntime(Protocol):
    db: Any
    time_service: Any
    reference: Any
    user_import_preparation_service: Any
    user_import_bound_google_doc_sync_service: Any
    user_import_scheduled_runtime_service: Any
    client_learning_card_action_service: Any
    client_learning_quiz_action_service: Any
    client_learning_ready_action_service: Any
    client_learning_session_completion_service: Any
    client_learning_summary_service: Any
    client_runtime_bootstrap_service: Any
    client_runtime_input_service: Any
    client_runtime_bot_message_service: Any
    client_runtime_reminder_service: Any
    client_import_notification_service: Any
    client_learning_start_service: Any
    subscription_maintenance_runtime_service: Any
    billing_notification_service: Any
    billing_webhook_service: Any
    client_web_auth_service: Any
    client_web_learning_service: Any
    client_web_import_service: Any
    client_web_settings_service: Any
    client_web_plan_service: Any
    client_web_billing_checkout_service: Any
    client_web_billing_payment_status_service: Any
    client_web_billing_payment_history_service: Any
    client_web_teacher_student_service: Any
    client_web_import_event_streamer: Any
    audio_storage_provider: Any


def build_api_router(service: ApiRouterRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    router.include_router(build_admin_router(service))
    router.include_router(build_client_router(service))
    router.include_router(build_client_web_router(service))
    router.include_router(build_billing_router(service))
    return router
