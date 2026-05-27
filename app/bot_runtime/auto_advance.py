from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from telegram.ext import ContextTypes

from app.bot_api_client import BotApiClient
from app.bot_runtime.message_tracking import is_tracked_message_still_active
from app.bot_runtime.state import read_int
from app.contracts import ScreenModel, TelegramUserContext
from app.reference.telegram_timing import TELEGRAM_SCHEDULER_INTERVAL_MINUTES
from app.screen_delivery_policy import read_screen_delivery_policy
from app.time_utils import round_datetime_up_to_minutes

LOGGER = logging.getLogger(__name__)

SendScreenToChat = Callable[..., Awaitable[None]]
REMINDER_AUTO_RETURN_TASKS_KEY = "reminder_auto_return_tasks"


def calculate_reminder_poll_sleep_seconds(current_time: datetime) -> float:
    next_poll_time = round_datetime_up_to_minutes(current_time, TELEGRAM_SCHEDULER_INTERVAL_MINUTES)
    if next_poll_time <= current_time:
        next_poll_time = next_poll_time + timedelta(minutes=TELEGRAM_SCHEDULER_INTERVAL_MINUTES)
    return max((next_poll_time - current_time).total_seconds(), 0.0)


def cancel_auto_advance_task(user_data: dict | None) -> None:
    if user_data is None:
        return
    task = user_data.pop("auto_advance_task", None)
    if task is not None:
        task.cancel()


def cancel_reminder_auto_return_task(
    bot_data: dict | None,
    telegram_user_id: int | None = None,
    chat_id: int | None = None,
) -> None:
    if bot_data is None:
        return
    tasks = bot_data.get(REMINDER_AUTO_RETURN_TASKS_KEY)
    if not isinstance(tasks, dict):
        return
    for key, task in list(tasks.items()):
        if not _is_matching_reminder_auto_return_key(key, telegram_user_id, chat_id):
            continue
        if task is not None:
            task.cancel()
        tasks.pop(key, None)


def schedule_reminder_auto_return_task(
    application,
    reminder,
    *,
    send_screen_to_chat: SendScreenToChat,
    sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    policy = read_screen_delivery_policy(reminder.screen)
    delay_ms = policy.auto_return_after_ms
    if delay_ms is None:
        return
    bot_data = application.bot_data
    key = _reminder_auto_return_key(reminder.telegram_user_id, reminder.chat_id)
    cancel_reminder_auto_return_task(bot_data, reminder.telegram_user_id, reminder.chat_id)

    async def auto_return() -> None:
        try:
            await sleep_func(delay_ms / 1000)
            api_client: BotApiClient = bot_data["api_client"]
            response = await api_client.restore_menu(reminder.telegram_user_id)
            await send_screen_to_chat(
                application,
                reminder.chat_id,
                response.screen,
                telegram_user_id=reminder.telegram_user_id,
                disable_notification=True,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception(
                "Reminder auto-return failed for telegram_user_id=%s chat_id=%s",
                reminder.telegram_user_id,
                reminder.chat_id,
            )
        finally:
            tasks = bot_data.get(REMINDER_AUTO_RETURN_TASKS_KEY)
            if isinstance(tasks, dict) and tasks.get(key) is task:
                tasks.pop(key, None)

    task_factory = getattr(application, "create_task", None)
    task = task_factory(auto_return()) if callable(task_factory) else asyncio.create_task(auto_return())
    bot_data.setdefault(REMINDER_AUTO_RETURN_TASKS_KEY, {})[key] = task


def schedule_auto_advance_task(
    context: ContextTypes.DEFAULT_TYPE,
    user: TelegramUserContext,
    chat_id: int | None,
    screen: ScreenModel,
    *,
    send_screen_to_chat: SendScreenToChat,
) -> None:
    if chat_id is None:
        return
    policy = read_screen_delivery_policy(screen)
    delay_ms = policy.auto_advance_after_ms
    next_action = policy.next_action
    if delay_ms is None or next_action is None:
        return
    expected_message_id = read_int(context.user_data.get("active_screen_message_id"))

    async def auto_advance() -> None:
        try:
            await asyncio.sleep(delay_ms / 1000)
            api_client: BotApiClient = context.application.bot_data["api_client"]
            if expected_message_id is not None:
                is_source_message_active = await is_tracked_message_still_active(
                    api_client=api_client,
                    telegram_user_id=user.telegram_user_id,
                    chat_id=chat_id,
                    message_id=expected_message_id,
                )
                if not is_source_message_active:
                    return
            response = await api_client.action(user, next_action)
            await send_screen_to_chat(
                context.application,
                chat_id,
                response.screen,
                user_data=context.user_data,
                telegram_user_id=user.telegram_user_id,
                disable_notification=True,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception(
                "Auto-advance failed for telegram_user_id=%s next_action=%s",
                user.telegram_user_id,
                next_action,
            )
        finally:
            if context.user_data.get("auto_advance_task") is task:
                context.user_data.pop("auto_advance_task", None)

    task = context.application.create_task(auto_advance())
    context.user_data["auto_advance_task"] = task


def _reminder_auto_return_key(telegram_user_id: int, chat_id: int) -> str:
    return f"{telegram_user_id}:{chat_id}"


def _is_matching_reminder_auto_return_key(key: object, telegram_user_id: int | None, chat_id: int | None) -> bool:
    if not isinstance(key, str):
        return False
    if telegram_user_id is None:
        return True
    prefix = f"{telegram_user_id}:"
    if not key.startswith(prefix):
        return False
    return chat_id is None or key == _reminder_auto_return_key(telegram_user_id, chat_id)
