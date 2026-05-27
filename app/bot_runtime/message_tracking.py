from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram.ext import Application

from app.bot_api_client import BotApiClient
from app.bot_runtime.state import (
    ActiveScreenMessage,
    build_message_log_refs,
    clear_auxiliary_screen_message_state,
    get_auxiliary_screen_message,
    read_int,
)

LOGGER = logging.getLogger(__name__)


async def is_tracked_message_still_active(
    *,
    api_client: BotApiClient,
    telegram_user_id: int,
    chat_id: int,
    message_id: int,
) -> bool:
    try:
        response = await api_client.list_active_bot_messages(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
        )
    except Exception:
        LOGGER.exception(
            "Failed to verify active tracked message telegram_user_id=%s chat_id=%s message_id=%s",
            telegram_user_id,
            chat_id,
            message_id,
        )
        return True
    return any(row.message_id == message_id for row in response.messages)


async def clear_messages(
    chat_id: int,
    application: Application,
    message_ids: list[int],
    message_log_refs: list[dict[str, int]] | None = None,
) -> None:
    refs_by_message_id = {
        item["message_id"]: item["message_log_id"]
        for item in (message_log_refs or [])
        if "message_id" in item and "message_log_id" in item
    }
    api_client: BotApiClient | None = application.bot_data.get("api_client")
    for message_id in message_ids:
        message_log_id = refs_by_message_id.get(message_id)
        try:
            await application.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if is_message_already_deleted_error(error):
                if api_client is not None and message_log_id is not None:
                    await save_cleanup_deleted_result(api_client, message_log_id)
                continue
            LOGGER.debug("Failed to delete message_id=%s in chat_id=%s", message_id, chat_id)
            if api_client is not None and message_log_id is not None:
                await save_cleanup_failure(api_client, message_log_id, error)
            continue
        if api_client is not None and message_log_id is not None:
            await save_cleanup_deleted_result(api_client, message_log_id)


async def clear_tracked_messages(chat_id: int, context: Any) -> None:
    message_ids = list(context.user_data.get("bot_message_ids", []))
    message_log_refs = list(context.user_data.get("bot_message_log_refs", []))
    auxiliary_message = get_auxiliary_screen_message(context.user_data)
    if auxiliary_message is not None:
        message_ids.append(auxiliary_message.message_id)
        message_log_refs.extend(build_message_log_refs([auxiliary_message]))
    context.user_data["bot_message_ids"] = []
    context.user_data["bot_message_log_refs"] = []
    context.user_data["active_screen_message_id"] = None
    context.user_data["active_screen_message_log_id"] = None
    context.user_data["active_screen_has_audio"] = False
    context.user_data["active_screen_screen_id"] = None
    clear_auxiliary_screen_message_state(context.user_data)
    await clear_messages(chat_id, context.application, message_ids, message_log_refs)


async def resolve_callback_active_screen_message(
    update: Any,
    user_data: dict | None,
    api_client: BotApiClient | None,
    telegram_user_id: int | None,
    chat_id: int | None,
) -> ActiveScreenMessage | None:
    callback_query = update.callback_query
    callback_message = getattr(callback_query, "message", None) if callback_query is not None else None
    if callback_message is None:
        return None
    message_id = getattr(callback_message, "message_id", None)
    if not isinstance(message_id, int):
        return None
    message_log_id = None
    screen_id = None
    if user_data is not None:
        for item in user_data.get("bot_message_log_refs", []):
            if item.get("message_id") == message_id:
                message_log_id = read_int(item.get("message_log_id"))
                break
    if message_log_id is None and api_client is not None and telegram_user_id is not None and chat_id is not None:
        try:
            tracked_row = await api_client.lookup_bot_message(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                message_id=message_id,
            )
            message_log_id = getattr(tracked_row, "id", None)
            screen_id = getattr(tracked_row, "screen_id", None)
        except Exception:
            LOGGER.exception(
                "Failed to lookup tracked callback message telegram_user_id=%s chat_id=%s message_id=%s",
                telegram_user_id,
                chat_id,
                message_id,
            )
    return ActiveScreenMessage(
        message_id=message_id,
        message_log_id=message_log_id,
        has_audio=bool(getattr(callback_message, "audio", None)),
        screen_id=screen_id,
    )


async def list_chat_tracked_messages(
    api_client: BotApiClient | None,
    telegram_user_id: int | None,
    chat_id: int,
) -> list[ActiveScreenMessage]:
    if api_client is None or telegram_user_id is None:
        return []
    try:
        response = await api_client.list_active_bot_messages(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
        )
    except Exception:
        LOGGER.exception(
            "Failed to list tracked bot messages telegram_user_id=%s chat_id=%s",
            telegram_user_id,
            chat_id,
        )
        return []
    return [
        ActiveScreenMessage(
            message_id=row.message_id,
            message_log_id=row.id,
            has_audio=row.screen_id.startswith("card:"),
            screen_id=row.screen_id,
        )
        for row in response.messages
    ]


async def sweep_chat_tracked_messages(
    *,
    application: Application,
    api_client: BotApiClient | None,
    chat_id: int,
    telegram_user_id: int | None,
    keep_messages: list[ActiveScreenMessage | None],
    user_data: dict | None,
) -> None:
    tracked_messages = await list_chat_tracked_messages(api_client, telegram_user_id, chat_id)
    if not tracked_messages:
        return
    keep_ids = {message.message_id for message in keep_messages if message is not None}
    sticky_reports = [message for message in tracked_messages if is_sticky_import_report_screen_id(message.screen_id)]
    current_sticky_report = next(
        (message for message in keep_messages if message is not None and is_sticky_import_report_screen_id(message.screen_id)),
        None,
    )
    latest_tracked_sticky_report = max(
        sticky_reports,
        key=lambda message: (message.message_id, message.message_log_id or -1),
        default=None,
    )
    sticky_keep_ids = (
        {current_sticky_report.message_id}
        if current_sticky_report is not None
        else ({latest_tracked_sticky_report.message_id} if latest_tracked_sticky_report is not None else set())
    )
    messages_to_delete = [
        message
        for message in tracked_messages
        if message.message_id not in keep_ids and (not is_sticky_import_report_screen_id(message.screen_id) or message.message_id not in sticky_keep_ids)
    ]
    if messages_to_delete:
        await clear_messages(
            chat_id,
            application,
            [message.message_id for message in messages_to_delete],
            build_message_log_refs(messages_to_delete),
        )
    if user_data is None:
        return
    active_message = next((message for message in keep_messages if message is not None and message.message_id == read_int(user_data.get("active_screen_message_id"))), None)
    if active_message is None:
        active_message = next((message for message in keep_messages if message is not None), None)
    auxiliary_message_id = read_int(user_data.get("auxiliary_screen_message_id"))
    user_messages = [
        message
        for message in keep_messages
        if message is not None and message.message_id != auxiliary_message_id
    ]
    user_data["bot_message_ids"] = [message.message_id for message in user_messages]
    user_data["bot_message_log_refs"] = build_message_log_refs([message for message in keep_messages if message is not None])


async def track_sent_bot_message(
    api_client: BotApiClient | None,
    telegram_user_id: int | None,
    chat_id: int,
    screen_id: str,
    message_id: int,
    delete_after_hours: int | None = None,
) -> object | None:
    if api_client is None or telegram_user_id is None:
        return None
    try:
        return await api_client.track_bot_message(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            message_id=message_id,
            screen_id=screen_id,
            delete_after_hours=delete_after_hours,
        )
    except Exception:
        LOGGER.exception(
            "Failed to persist sent bot message telegram_user_id=%s chat_id=%s message_id=%s",
            telegram_user_id,
            chat_id,
            message_id,
        )
        return None


async def save_cleanup_failure(api_client: BotApiClient, message_log_id: int, error: Exception) -> None:
    try:
        await api_client.save_bot_message_cleanup_result(
            message_log_id=message_log_id,
            is_deleted=False,
            error_text=str(error),
        )
    except Exception:
        LOGGER.exception("Failed to persist cleanup failure for bot_message_log id=%s", message_log_id)


async def save_cleanup_deleted_result(api_client: BotApiClient, message_log_id: int) -> None:
    try:
        await api_client.save_bot_message_cleanup_result(
            message_log_id=message_log_id,
            is_deleted=True,
        )
    except Exception:
        LOGGER.exception("Failed to persist deleted cleanup result for bot_message_log id=%s", message_log_id)


def is_message_already_deleted_error(error: Exception) -> bool:
    error_text = str(error).lower()
    return "message to delete not found" in error_text


def is_sticky_import_report_screen_id(screen_id: str | None) -> bool:
    if not isinstance(screen_id, str):
        return False
    return screen_id.startswith("import_words:summary:") or screen_id.startswith("import_words:failed:")
