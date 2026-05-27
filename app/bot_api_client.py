from __future__ import annotations

from app.bot_http_transport import BackendBotApiTransport
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
    TelegramUserContext,
    TextRequest,
)


class BotApiClient:
    def __init__(
        self,
        base_url: str,
        transport: BackendBotApiTransport | None = None,
        *,
        internal_api_token: str = "",
    ) -> None:
        self.transport = transport or BackendBotApiTransport(base_url, internal_api_token=internal_api_token)

    async def bootstrap(self, user: TelegramUserContext, message_text: str | None = None) -> ActionResponse:
        payload = await self.transport.post(
            "/api/v1/bootstrap",
            json=BootstrapRequest(user=user, message_text=message_text).model_dump(mode="json"),
        )
        return ActionResponse.model_validate(payload)

    async def action(self, user: TelegramUserContext, action: str) -> ActionResponse:
        payload = await self.transport.post(
            "/api/v1/action",
            json=ActionRequest(user=user, action=action).model_dump(mode="json"),
        )
        return ActionResponse.model_validate(payload)

    async def text(self, user: TelegramUserContext, text: str) -> ActionResponse:
        payload = await self.transport.post(
            "/api/v1/text",
            json=TextRequest(user=user, text=text).model_dump(mode="json"),
        )
        return ActionResponse.model_validate(payload)

    async def restore_menu(self, telegram_user_id: int) -> ActionResponse:
        payload = await self.transport.post(
            "/api/v1/menu/restore",
            json=MenuRestoreRequest(telegram_user_id=telegram_user_id).model_dump(mode="json"),
        )
        return ActionResponse.model_validate(payload)

    async def dispatch_reminders(self) -> ReminderDispatchResponse:
        payload = await self.transport.post("/api/v1/reminders/dispatch")
        return ReminderDispatchResponse.model_validate(payload)

    async def track_bot_message(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after_hours: int | None = None,
    ) -> BotMessageTrackResponse:
        payload = await self.transport.post(
            "/api/v1/bot/messages/track",
            json=BotMessageTrackRequest(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                message_id=message_id,
                screen_id=screen_id,
                delete_after_hours=delete_after_hours,
            ).model_dump(mode="json"),
        )
        return BotMessageTrackResponse.model_validate(payload)

    async def lookup_bot_message(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
    ) -> BotMessageTrackResponse | None:
        payload = await self.transport.post(
            "/api/v1/bot/messages/lookup",
            json=BotMessageLookupRequest(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                message_id=message_id,
            ).model_dump(mode="json"),
        )
        if payload is None:
            return None
        return BotMessageTrackResponse.model_validate(payload)

    async def list_active_bot_messages(
        self,
        telegram_user_id: int,
        chat_id: int,
    ) -> BotMessageListResponse:
        payload = await self.transport.post(
            "/api/v1/bot/messages/active",
            json=BotMessageListRequest(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
            ).model_dump(mode="json"),
        )
        return BotMessageListResponse.model_validate(payload)

    async def dispatch_bot_message_cleanup(self) -> BotMessageCleanupDispatchResponse:
        payload = await self.transport.post("/api/v1/bot/messages/cleanup/dispatch")
        return BotMessageCleanupDispatchResponse.model_validate(payload)

    async def dispatch_user_imports(self) -> ImportDispatchResponse:
        payload = await self.transport.post("/api/v1/imports/process", timeout=60.0)
        return ImportDispatchResponse.model_validate(payload)

    async def save_bot_message_cleanup_result(
        self,
        message_log_id: int,
        is_deleted: bool,
        error_text: str | None = None,
    ) -> None:
        await self.transport.post(
            f"/api/v1/bot/messages/{message_log_id}/cleanup-result",
            json=BotMessageCleanupResultRequest(
                is_deleted=is_deleted,
                error_text=error_text,
            ).model_dump(mode="json"),
        )

    async def save_billing_notification_delivery_result(
        self,
        notification_id: int,
        *,
        is_sent: bool,
        error_text: str | None = None,
    ) -> None:
        await self.transport.post(
            f"/api/v1/billing/notifications/{notification_id}/delivery-result",
            json=BillingNotificationDeliveryResultRequest(
                is_sent=is_sent,
                error_text=error_text,
            ).model_dump(mode="json"),
        )

    async def save_billing_receipt_delivery_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None = None,
    ) -> None:
        await self.transport.post(
            f"/api/v1/billing/receipts/{receipt_id}/delivery-result",
            json=BillingNotificationDeliveryResultRequest(
                is_sent=is_sent,
                error_text=error_text,
            ).model_dump(mode="json"),
        )

    async def save_billing_receipt_admin_alert_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None = None,
    ) -> None:
        await self.transport.post(
            f"/api/v1/billing/receipts/{receipt_id}/admin-alert-result",
            json=BillingNotificationDeliveryResultRequest(
                is_sent=is_sent,
                error_text=error_text,
            ).model_dump(mode="json"),
        )
