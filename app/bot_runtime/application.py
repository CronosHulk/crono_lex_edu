from __future__ import annotations

import asyncio
import logging
import traceback
from collections.abc import Awaitable, Callable

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.bot_api_client import BotApiClient
from app.config import Settings
from app.storage.audio import AudioStorageProvider

LOGGER = logging.getLogger(__name__)

PollingLoop = Callable[[Application], Awaitable[None]]
UpdateHandler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
ErrorHandler = Callable[[object, ContextTypes.DEFAULT_TYPE], Awaitable[None]]

POLLING_TASK_KEYS = ("reminder_task", "cleanup_task", "user_import_task")


def schedule_polling_tasks(
    application: Application,
    *,
    reminder_polling_loop_func: PollingLoop,
    bot_message_cleanup_loop_func: PollingLoop,
    user_import_polling_loop_func: PollingLoop,
) -> None:
    application.bot_data["reminder_task"] = application.create_task(reminder_polling_loop_func(application))
    application.bot_data["cleanup_task"] = application.create_task(bot_message_cleanup_loop_func(application))
    application.bot_data["user_import_task"] = application.create_task(user_import_polling_loop_func(application))


async def cancel_polling_tasks(application: Application) -> None:
    for task_key in POLLING_TASK_KEYS:
        task = application.bot_data.get(task_key)
        if task is None:
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def build_application(
    api_client: BotApiClient,
    token: str,
    settings: Settings,
    *,
    audio_storage_provider: AudioStorageProvider,
    start_handler_func: UpdateHandler,
    menu_handler_func: UpdateHandler,
    text_handler_func: UpdateHandler,
    callback_handler_func: UpdateHandler,
    reminder_polling_loop_func: PollingLoop,
    bot_message_cleanup_loop_func: PollingLoop,
    user_import_polling_loop_func: PollingLoop,
    error_handler_func: ErrorHandler,
) -> Application:
    async def post_init(application: Application) -> None:
        schedule_polling_tasks(
            application,
            reminder_polling_loop_func=reminder_polling_loop_func,
            bot_message_cleanup_loop_func=bot_message_cleanup_loop_func,
            user_import_polling_loop_func=user_import_polling_loop_func,
        )

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(cancel_polling_tasks)
        .build()
    )
    application.bot_data["api_client"] = api_client
    application.bot_data["settings"] = settings
    application.bot_data["audio_storage_provider"] = audio_storage_provider
    application.add_handler(CommandHandler("start", start_handler_func))
    application.add_handler(CommandHandler("menu", menu_handler_func))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler_func))
    application.add_handler(CallbackQueryHandler(callback_handler_func))
    application.add_error_handler(error_handler_func)
    return application


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled telegram bot error. Update=%s", update, exc_info=context.error)
    LOGGER.error("%s", traceback.format_exception(type(context.error), context.error, context.error.__traceback__))
