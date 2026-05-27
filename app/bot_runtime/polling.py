from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol

from telegram.ext import Application

from app.bot_api_client import BotApiClient
from app.bot_runtime.auto_advance import (
    calculate_reminder_poll_sleep_seconds,
    schedule_reminder_auto_return_task,
)
from app.bot_runtime.message_tracking import (
    is_message_already_deleted_error,
    save_cleanup_deleted_result,
    save_cleanup_failure,
)
from app.config import Settings
from app.contracts import ScreenModel

LOGGER = logging.getLogger(__name__)

SleepFunc = Callable[[float], Awaitable[None]]


class SendScreenToChat(Protocol):
    def __call__(
        self,
        application: Application,
        chat_id: int,
        screen: ScreenModel,
        *,
        user_data: dict[str, object] | None = None,
        telegram_user_id: int | None = None,
        disable_notification: bool = True,
    ) -> Awaitable[None]: ...


def bot_message_cleanup_interval_seconds(settings: Settings) -> int:
    configured_seconds = getattr(settings, "app_bot_message_cleanup_poll_seconds", None)
    if configured_seconds is not None:
        return max(int(configured_seconds), 1)
    return max(settings.app_bot_message_cleanup_poll_minutes, 1) * 60


async def reminder_polling_loop(
    application: Application,
    *,
    send_screen_to_chat_func: SendScreenToChat,
    sleep_func: SleepFunc = asyncio.sleep,
    now_func: Callable[[], datetime] = lambda: datetime.now().astimezone(),
) -> None:
    api_client: BotApiClient = application.bot_data["api_client"]
    while True:
        try:
            response = await api_client.dispatch_reminders()
            for reminder in response.reminders:
                await send_screen_to_chat_func(
                    application,
                    reminder.chat_id,
                    reminder.screen,
                    telegram_user_id=reminder.telegram_user_id,
                    disable_notification=False,
                )
                schedule_reminder_auto_return_task(
                    application,
                    reminder,
                    send_screen_to_chat=send_screen_to_chat_func,
                    sleep_func=sleep_func,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Reminder polling failed")
        await sleep_func(calculate_reminder_poll_sleep_seconds(now_func()))


async def bot_message_cleanup_loop(
    application: Application,
    *,
    sleep_func: SleepFunc = asyncio.sleep,
) -> None:
    api_client: BotApiClient = application.bot_data["api_client"]
    settings: Settings = application.bot_data["settings"]
    interval_seconds = bot_message_cleanup_interval_seconds(settings)
    while True:
        try:
            response = await api_client.dispatch_bot_message_cleanup()
            if response.messages:
                LOGGER.info("Bot message cleanup claimed %s due messages", len(response.messages))
            deleted_count = 0
            failed_count = 0
            for row in response.messages:
                try:
                    await application.bot.delete_message(chat_id=row.chat_id, message_id=row.message_id)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    if is_message_already_deleted_error(error):
                        await save_cleanup_deleted_result(api_client, row.id)
                        deleted_count += 1
                        continue
                    LOGGER.debug(
                        "Failed to cleanup tracked bot message id=%s chat_id=%s message_id=%s",
                        row.id,
                        row.chat_id,
                        row.message_id,
                    )
                    await save_cleanup_failure(api_client, row.id, error)
                    failed_count += 1
                    continue
                await save_cleanup_deleted_result(api_client, row.id)
                deleted_count += 1
            if response.messages:
                LOGGER.info(
                    "Bot message cleanup finished: claimed=%s deleted=%s failed=%s",
                    len(response.messages),
                    deleted_count,
                    failed_count,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Bot message cleanup polling failed")
        await sleep_func(interval_seconds)


async def user_import_polling_loop(
    application: Application,
    *,
    send_screen_to_chat_func: SendScreenToChat,
    sleep_func: SleepFunc = asyncio.sleep,
) -> None:
    api_client: BotApiClient = application.bot_data["api_client"]
    settings: Settings = application.bot_data["settings"]
    interval_seconds = max(settings.app_bot_user_import_poll_minutes, 1) * 60
    while True:
        try:
            response = await api_client.dispatch_user_imports()
            for notification in response.notifications:
                try:
                    await send_screen_to_chat_func(
                        application,
                        notification.chat_id,
                        notification.screen,
                        telegram_user_id=notification.telegram_user_id,
                        disable_notification=notification.disable_notification,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    await save_import_notification_delivery_failure(api_client, notification, error)
                    LOGGER.exception(
                        "Import notification delivery failed for telegram_user_id=%s chat_id=%s",
                        notification.telegram_user_id,
                        notification.chat_id,
                    )
                    continue
                await save_import_notification_delivery_success(api_client, notification)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("User import polling failed")
        await sleep_func(interval_seconds)


async def save_import_notification_delivery_success(api_client: BotApiClient, notification: object) -> None:
    delivery_kind = getattr(notification, "delivery_kind", None)
    if delivery_kind not in {"billing_bot_notification", "billing_receipt_delivery", "billing_receipt_admin_alert"}:
        return
    delivery_id = getattr(notification, "delivery_id", None)
    if delivery_id is None:
        return
    if delivery_kind == "billing_receipt_delivery":
        await api_client.save_billing_receipt_delivery_result(int(delivery_id), is_sent=True)
        return
    if delivery_kind == "billing_receipt_admin_alert":
        await api_client.save_billing_receipt_admin_alert_result(int(delivery_id), is_sent=True)
        return
    await api_client.save_billing_notification_delivery_result(int(delivery_id), is_sent=True)


async def save_import_notification_delivery_failure(api_client: BotApiClient, notification: object, error: Exception) -> None:
    delivery_kind = getattr(notification, "delivery_kind", None)
    if delivery_kind not in {"billing_bot_notification", "billing_receipt_delivery", "billing_receipt_admin_alert"}:
        return
    delivery_id = getattr(notification, "delivery_id", None)
    if delivery_id is None:
        return
    error_text = f"{type(error).__name__}: {error}"[:1000]
    if delivery_kind == "billing_receipt_delivery":
        await api_client.save_billing_receipt_delivery_result(
            int(delivery_id),
            is_sent=False,
            error_text=error_text,
        )
        return
    if delivery_kind == "billing_receipt_admin_alert":
        await api_client.save_billing_receipt_admin_alert_result(
            int(delivery_id),
            is_sent=False,
            error_text=error_text,
        )
        return
    await api_client.save_billing_notification_delivery_result(
        int(delivery_id),
        is_sent=False,
        error_text=error_text,
    )
