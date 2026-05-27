from __future__ import annotations

import argparse
import asyncio
import logging
import os
from dataclasses import replace

from telegram import Update
from telegram.ext import ContextTypes

import app.bot_runtime.application as runtime_application
import app.bot_runtime.handlers as runtime_handlers
import app.bot_runtime.polling as runtime_polling
from app.bot_api_client import BotApiClient
from app.bot_runtime.auto_advance import (
    schedule_auto_advance_task as schedule_runtime_auto_advance_task,
)
from app.bot_runtime.screen_delivery import render_screen, send_screen_to_chat
from app.composition.audio_storage import build_audio_storage_provider
from app.config import Settings, load_settings
from app.contracts import ScreenModel, TelegramUserContext
from app.storage.audio import AudioStorageProvider

ALLOWED_UPDATES = ["message", "callback_query"]


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CronoLex Telegram bot update transport.")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use LOCAL_BOT_TOKEN from the environment and process updates with local polling.",
    )
    return parser.parse_args(argv)


def apply_local_bot_credentials(settings):
    local_token = os.getenv("LOCAL_BOT_TOKEN", "").strip()
    if not local_token:
        raise RuntimeError("LOCAL_BOT_TOKEN is required when running bot_main.py with --local.")
    return replace(settings, bot_token=local_token, app_env="local")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await runtime_handlers.start_handler(update, context, render_screen_func=render_screen)


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await runtime_handlers.menu_handler(update, context, render_screen_func=render_screen)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await runtime_handlers.text_handler(update, context, render_screen_func=render_screen)


def schedule_auto_advance_task(
    context: ContextTypes.DEFAULT_TYPE,
    user: TelegramUserContext,
    chat_id: int | None,
    screen: ScreenModel,
) -> None:
    schedule_runtime_auto_advance_task(
        context,
        user,
        chat_id,
        screen,
        send_screen_to_chat=send_screen_to_chat,
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await runtime_handlers.callback_handler(
        update,
        context,
        render_screen_func=render_screen,
        schedule_auto_advance_func=schedule_auto_advance_task,
    )


async def reminder_polling_loop(application) -> None:
    await runtime_polling.reminder_polling_loop(
        application,
        send_screen_to_chat_func=send_screen_to_chat,
        sleep_func=asyncio.sleep,
    )


async def bot_message_cleanup_loop(application) -> None:
    await runtime_polling.bot_message_cleanup_loop(application, sleep_func=asyncio.sleep)


async def user_import_polling_loop(application) -> None:
    await runtime_polling.user_import_polling_loop(
        application,
        send_screen_to_chat_func=send_screen_to_chat,
        sleep_func=asyncio.sleep,
    )


def build_application(
    api_client: BotApiClient,
    token: str,
    settings: Settings,
    *,
    audio_storage_provider: AudioStorageProvider,
):
    return runtime_application.build_application(
        api_client,
        token,
        settings,
        audio_storage_provider=audio_storage_provider,
        start_handler_func=start_handler,
        menu_handler_func=menu_handler,
        text_handler_func=text_handler,
        callback_handler_func=callback_handler,
        reminder_polling_loop_func=reminder_polling_loop,
        bot_message_cleanup_loop_func=bot_message_cleanup_loop,
        user_import_polling_loop_func=user_import_polling_loop,
        error_handler_func=runtime_application.error_handler,
    )


def normalize_webhook_path(path: str) -> str:
    return path.strip().strip("/")


def build_webhook_url(settings) -> str:
    configured_url = settings.app_bot_webhook_url.strip()
    if configured_url:
        return configured_url
    return f"{settings.app_web_base_url.rstrip('/')}/{normalize_webhook_path(settings.app_bot_webhook_path)}"


def validate_enabled_webhook_settings(settings: Settings) -> None:
    if not settings.app_bot_webhook_secret_token.strip():
        raise RuntimeError(
            "APP__BOT_WEBHOOK_SECRET_TOKEN is required when the Telegram bot is enabled outside --local."
        )
    if not settings.bot_token.strip():
        raise RuntimeError("BOT_TOKEN is required when the Telegram bot is enabled outside --local.")


def run_polling(application) -> None:
    application.run_polling(allowed_updates=ALLOWED_UPDATES)


def run_webhook(application, settings) -> None:
    secret_token = settings.app_bot_webhook_secret_token.strip() or None
    application.run_webhook(
        listen=settings.app_bot_webhook_listen_host,
        port=settings.app_bot_webhook_port,
        url_path=normalize_webhook_path(settings.app_bot_webhook_path),
        webhook_url=build_webhook_url(settings),
        secret_token=secret_token,
        allowed_updates=ALLOWED_UPDATES,
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging()
    settings = load_settings()
    if args.local:
        settings = apply_local_bot_credentials(settings)
    elif not settings.app_bot_enabled:
        logging.getLogger(__name__).info("Telegram bot is disabled; exiting.")
        return
    else:
        validate_enabled_webhook_settings(settings)
    audio_storage_provider = build_audio_storage_provider(settings)
    application = build_application(
        BotApiClient(settings.app_api_base_url, internal_api_token=settings.app_internal_api_token),
        settings.bot_token,
        settings,
        audio_storage_provider=audio_storage_provider,
    )
    if args.local:
        run_polling(application)
        return
    run_webhook(application, settings)


if __name__ == "__main__":
    main()
