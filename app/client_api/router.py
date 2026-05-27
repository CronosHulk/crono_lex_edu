from __future__ import annotations

import traceback
from typing import Any, Protocol

from fastapi import APIRouter, Depends

from app.client_api.internal_auth import build_internal_api_guard
from app.contracts import (
    ActionRequest,
    ActionResponse,
    BillingNotificationDeliveryResultRequest,
    BootstrapRequest,
    BotMessageCleanupDispatchResponse,
    BotMessageCleanupResultRequest,
    BotMessageListRequest,
    BotMessageListResponse,
    BotMessageLookupRequest,
    BotMessageTrackRequest,
    BotMessageTrackResponse,
    ImportDispatchResponse,
    MenuRestoreRequest,
    ReminderDispatchResponse,
    SubscriptionMaintenanceResponse,
    TelegramUserContext,
    TextRequest,
)


class ClientImportNotificationRuntime(Protocol):
    def process_due_import_notifications(self) -> list[Any]: ...


class ClientSubscriptionMaintenanceRuntime(Protocol):
    def process_due_subscription_maintenance(self) -> Any: ...


class ClientBillingNotificationRuntime(Protocol):
    def save_bot_notification_delivery_result(
        self,
        notification_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None: ...

    def save_receipt_delivery_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None: ...

    def save_receipt_admin_alert_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None,
    ) -> None: ...


class ClientRuntimeBootstrapService(Protocol):
    def bootstrap(self, user: TelegramUserContext, message_text: str | None) -> Any: ...

    def build_main_menu_restore_screen(self, telegram_user_id: int) -> Any: ...

    def build_unexpected_error_screen(self, user: TelegramUserContext) -> Any: ...

    def log_unexpected_error(
        self,
        *,
        route: str,
        user: TelegramUserContext | None,
        error: Exception,
        details: str,
    ) -> None: ...


class ClientRuntimeInputService(Protocol):
    def handle_action(self, user: TelegramUserContext, action: str) -> Any: ...

    def handle_text_input(self, user: TelegramUserContext, text: str) -> Any: ...


class ClientBotMessageRuntime(Protocol):
    def track_bot_message(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after_hours: int | None = None,
    ) -> dict[str, Any]: ...

    def get_bot_message_log(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
    ) -> dict[str, Any] | None: ...

    def list_active_bot_messages(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
    ) -> list[dict[str, Any]]: ...

    def dispatch_due_bot_message_cleanup(self) -> list[dict[str, Any]]: ...

    def save_bot_message_cleanup_result(
        self,
        *,
        message_log_id: int,
        is_deleted: bool,
        error_text: str | None,
    ) -> None: ...


class ClientReminderRuntime(Protocol):
    def dispatch_due_reminders(self) -> list[Any]: ...


class ClientRouterRuntime(Protocol):
    db: Any
    client_runtime_bootstrap_service: ClientRuntimeBootstrapService
    client_runtime_input_service: ClientRuntimeInputService
    client_runtime_bot_message_service: ClientBotMessageRuntime
    client_runtime_reminder_service: ClientReminderRuntime
    client_import_notification_service: ClientImportNotificationRuntime
    subscription_maintenance_runtime_service: ClientSubscriptionMaintenanceRuntime
    billing_notification_service: ClientBillingNotificationRuntime


class _ClientRouterRuntimeAdapter:
    def __init__(self, runtime: ClientRouterRuntime) -> None:
        self.bootstrap_service = runtime.client_runtime_bootstrap_service
        self.input_service = runtime.client_runtime_input_service
        self.bot_message_service = runtime.client_runtime_bot_message_service
        self.reminder_dispatch_service = runtime.client_runtime_reminder_service
        self.import_notification_service = runtime.client_import_notification_service
        self.subscription_maintenance_runtime_service = (
            runtime.subscription_maintenance_runtime_service
        )
        self.billing_notification_service = runtime.billing_notification_service

    def bootstrap(self, user: TelegramUserContext, message_text: str | None) -> Any:
        return self.bootstrap_service.bootstrap(user, message_text)

    def handle_action(self, user: TelegramUserContext, action: str) -> Any:
        return self.input_service.handle_action(user, action)

    def handle_text_input(self, user: TelegramUserContext, text: str) -> Any:
        return self.input_service.handle_text_input(user, text)

    def restore_menu(self, telegram_user_id: int) -> Any:
        return self.bootstrap_service.build_main_menu_restore_screen(telegram_user_id)

    def build_unexpected_error_screen(self, user: TelegramUserContext) -> Any:
        return self.bootstrap_service.build_unexpected_error_screen(user)

    def log_unexpected_error(
        self,
        *,
        route: str,
        user: TelegramUserContext | None,
        error: Exception,
        details: str,
    ) -> None:
        self.bootstrap_service.log_unexpected_error(
            route=route,
            user=user,
            error=error,
            details=details,
        )

    def dispatch_due_reminders(self) -> list[Any]:
        return self.reminder_dispatch_service.dispatch_due_reminders()

    def track_bot_message(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after_hours: int | None = None,
    ) -> dict[str, Any]:
        return self.bot_message_service.track_bot_message(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            message_id=message_id,
            screen_id=screen_id,
            delete_after_hours=delete_after_hours,
        )

    def lookup_bot_message(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
    ) -> dict[str, Any] | None:
        return self.bot_message_service.get_bot_message_log(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            message_id=message_id,
        )

    def list_active_bot_messages(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        return self.bot_message_service.list_active_bot_messages(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
        )

    def dispatch_due_bot_message_cleanup(self) -> list[dict[str, Any]]:
        return self.bot_message_service.dispatch_due_bot_message_cleanup()

    def process_due_import_notifications(self) -> list[Any]:
        return self.import_notification_service.process_due_import_notifications()

    def process_due_subscription_maintenance(self) -> Any:
        return self.subscription_maintenance_runtime_service.process_due_subscription_maintenance()

    def save_bot_message_cleanup_result(
        self,
        *,
        message_log_id: int,
        is_deleted: bool,
        error_text: str | None,
    ) -> None:
        self.bot_message_service.save_bot_message_cleanup_result(
            message_log_id=message_log_id,
            is_deleted=is_deleted,
            error_text=error_text,
        )

    def save_billing_notification_delivery_result(
        self,
        *,
        notification_id: int,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        self.billing_notification_service.save_bot_notification_delivery_result(
            notification_id,
            is_sent=is_sent,
            error_text=error_text,
        )

    def save_billing_receipt_delivery_result(
        self,
        *,
        receipt_id: int,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        self.billing_notification_service.save_receipt_delivery_result(
            receipt_id,
            is_sent=is_sent,
            error_text=error_text,
        )

    def save_billing_receipt_admin_alert_result(
        self,
        *,
        receipt_id: int,
        is_sent: bool,
        error_text: str | None,
    ) -> None:
        self.billing_notification_service.save_receipt_admin_alert_result(
            receipt_id,
            is_sent=is_sent,
            error_text=error_text,
        )


def _build_unexpected_error_response(
    client_adapter: _ClientRouterRuntimeAdapter,
    *,
    route: str,
    user: Any,
    error: Exception,
) -> ActionResponse:
    details = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    client_adapter.log_unexpected_error(route=route, user=user, error=error, details=details)
    return ActionResponse(screen=client_adapter.build_unexpected_error_screen(user))


def build_client_router(service: ClientRouterRuntime) -> APIRouter:
    router = APIRouter(dependencies=[Depends(build_internal_api_guard(service))])
    client_adapter = _ClientRouterRuntimeAdapter(service)

    @router.post("/bootstrap", response_model=ActionResponse)
    def bootstrap(request: BootstrapRequest) -> ActionResponse:
        try:
            screen = client_adapter.bootstrap(request.user, request.message_text)
            return ActionResponse(screen=screen)
        except Exception as error:
            return _build_unexpected_error_response(
                client_adapter,
                route="bootstrap",
                user=request.user,
                error=error,
            )

    @router.post("/action", response_model=ActionResponse)
    def action(request: ActionRequest) -> ActionResponse:
        try:
            screen = client_adapter.handle_action(request.user, request.action)
            return ActionResponse(screen=screen)
        except Exception as error:
            return _build_unexpected_error_response(
                client_adapter,
                route=f"action:{request.action}",
                user=request.user,
                error=error,
            )

    @router.post("/text", response_model=ActionResponse)
    def text(request: TextRequest) -> ActionResponse:
        try:
            screen = client_adapter.handle_text_input(request.user, request.text)
            return ActionResponse(screen=screen)
        except Exception as error:
            return _build_unexpected_error_response(
                client_adapter,
                route="text",
                user=request.user,
                error=error,
            )

    @router.post("/menu/restore", response_model=ActionResponse)
    def restore_menu(request: MenuRestoreRequest) -> ActionResponse:
        return ActionResponse(screen=client_adapter.restore_menu(request.telegram_user_id))

    @router.post("/reminders/dispatch", response_model=ReminderDispatchResponse)
    def dispatch_reminders() -> ReminderDispatchResponse:
        return ReminderDispatchResponse(reminders=client_adapter.dispatch_due_reminders())

    @router.post("/bot/messages/track", response_model=BotMessageTrackResponse)
    def track_bot_message(request: BotMessageTrackRequest) -> BotMessageTrackResponse:
        return BotMessageTrackResponse.model_validate(
            client_adapter.track_bot_message(
                telegram_user_id=request.telegram_user_id,
                chat_id=request.chat_id,
                message_id=request.message_id,
                screen_id=request.screen_id,
                delete_after_hours=request.delete_after_hours,
            )
        )

    @router.post("/bot/messages/lookup", response_model=BotMessageTrackResponse | None)
    def lookup_bot_message(request: BotMessageLookupRequest) -> BotMessageTrackResponse | None:
        row = client_adapter.lookup_bot_message(
            telegram_user_id=request.telegram_user_id,
            chat_id=request.chat_id,
            message_id=request.message_id,
        )
        return BotMessageTrackResponse.model_validate(row) if row is not None else None

    @router.post("/bot/messages/active", response_model=BotMessageListResponse)
    def list_active_bot_messages(request: BotMessageListRequest) -> BotMessageListResponse:
        return BotMessageListResponse(
            messages=client_adapter.list_active_bot_messages(
                telegram_user_id=request.telegram_user_id,
                chat_id=request.chat_id,
            )
        )

    @router.post("/bot/messages/cleanup/dispatch", response_model=BotMessageCleanupDispatchResponse)
    def dispatch_bot_message_cleanup() -> BotMessageCleanupDispatchResponse:
        return BotMessageCleanupDispatchResponse(messages=client_adapter.dispatch_due_bot_message_cleanup())

    @router.post("/imports/process", response_model=ImportDispatchResponse)
    def dispatch_user_imports() -> ImportDispatchResponse:
        return ImportDispatchResponse(notifications=client_adapter.process_due_import_notifications())

    @router.post("/subscriptions/maintenance/process", response_model=SubscriptionMaintenanceResponse)
    def process_subscription_maintenance() -> SubscriptionMaintenanceResponse:
        return SubscriptionMaintenanceResponse(summary=client_adapter.process_due_subscription_maintenance())

    @router.post("/bot/messages/{message_log_id}/cleanup-result")
    def save_bot_message_cleanup_result(
        message_log_id: int,
        request: BotMessageCleanupResultRequest,
    ) -> dict[str, str]:
        client_adapter.save_bot_message_cleanup_result(
            message_log_id=message_log_id,
            is_deleted=request.is_deleted,
            error_text=request.error_text,
        )
        return {"status": "ok"}

    @router.post("/billing/notifications/{notification_id}/delivery-result")
    def save_billing_notification_delivery_result(
        notification_id: int,
        request: BillingNotificationDeliveryResultRequest,
    ) -> dict[str, str]:
        client_adapter.save_billing_notification_delivery_result(
            notification_id=notification_id,
            is_sent=request.is_sent,
            error_text=request.error_text,
        )
        return {"status": "ok"}

    @router.post("/billing/receipts/{receipt_id}/delivery-result")
    def save_billing_receipt_delivery_result(
        receipt_id: int,
        request: BillingNotificationDeliveryResultRequest,
    ) -> dict[str, str]:
        client_adapter.save_billing_receipt_delivery_result(
            receipt_id=receipt_id,
            is_sent=request.is_sent,
            error_text=request.error_text,
        )
        return {"status": "ok"}

    @router.post("/billing/receipts/{receipt_id}/admin-alert-result")
    def save_billing_receipt_admin_alert_result(
        receipt_id: int,
        request: BillingNotificationDeliveryResultRequest,
    ) -> dict[str, str]:
        client_adapter.save_billing_receipt_admin_alert_result(
            receipt_id=receipt_id,
            is_sent=request.is_sent,
            error_text=request.error_text,
        )
        return {"status": "ok"}

    return router
