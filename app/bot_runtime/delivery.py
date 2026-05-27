from __future__ import annotations

import asyncio
import logging

from telegram import InlineKeyboardMarkup, InputMediaAudio, ReplyKeyboardRemove
from telegram.ext import Application

from app.bot_runtime.rendering import build_audio_display_filename, open_audio_binary
from app.bot_runtime.state import ActiveScreenMessage
from app.contracts import ScreenModel
from app.storage.audio import AudioStorageProvider

LOGGER = logging.getLogger(__name__)


async def try_edit_active_screen(
    application: Application,
    chat_id: int,
    active_message: ActiveScreenMessage,
    screen: ScreenModel,
    keyboard: InlineKeyboardMarkup | None,
    screen_text: str,
) -> bool:
    try:
        if active_message.has_audio and screen.audio_path:
            storage_provider = _audio_storage_provider_from_application(application)
            with open_audio_binary(screen.audio_path, storage_provider) as audio_file:
                await application.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=active_message.message_id,
                    media=InputMediaAudio(
                        media=audio_file,
                        caption=screen_text,
                        parse_mode=screen.parse_mode,
                        filename=build_audio_display_filename(screen.audio_path),
                    ),
                    reply_markup=keyboard,
                )
        elif active_message.has_audio:
            return False
        elif screen.audio_path:
            return False
        else:
            await application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=active_message.message_id,
                text=screen_text,
                parse_mode=screen.parse_mode,
                reply_markup=keyboard,
            )
    except asyncio.CancelledError:
        raise
    except Exception as error:
        if is_message_not_modified_error(error):
            return True
        if is_message_not_editable_error(error):
            return False
        raise

    active_message.has_audio = bool(screen.audio_path)
    active_message.screen_id = screen.screen_id
    return True


async def send_new_screen_message(
    application: Application,
    chat_id: int,
    screen: ScreenModel,
    keyboard: InlineKeyboardMarkup | None,
    screen_text: str,
    disable_notification: bool,
):
    if screen.audio_path:
        storage_provider = _audio_storage_provider_from_application(application)
        with open_audio_binary(screen.audio_path, storage_provider) as audio_file:
            return await application.bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                caption=screen_text,
                reply_markup=keyboard,
                parse_mode=screen.parse_mode,
                filename=build_audio_display_filename(screen.audio_path),
                disable_notification=disable_notification,
            )
    return await application.bot.send_message(
        chat_id=chat_id,
        text=screen_text,
        reply_markup=keyboard,
        parse_mode=screen.parse_mode,
        disable_notification=disable_notification,
    )


async def ensure_reply_keyboard_removed(
    application: Application,
    chat_id: int,
    user_data: dict | None,
) -> None:
    if user_data is None:
        return
    if user_data.get("reply_keyboard_removed", False):
        return

    cleanup_message = await application.bot.send_message(
        chat_id=chat_id,
        text="Оновлюю інтерфейс…",
        reply_markup=ReplyKeyboardRemove(),
        disable_notification=True,
    )
    user_data["reply_keyboard_removed"] = True
    try:
        await application.bot.delete_message(chat_id=chat_id, message_id=cleanup_message.message_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        LOGGER.debug(
            "Failed to delete temporary reply keyboard removal message_id=%s in chat_id=%s",
            cleanup_message.message_id,
            chat_id,
        )


def is_message_not_modified_error(error: Exception) -> bool:
    error_text = str(error).lower()
    patterns = (
        "message is not modified",
        "specified new message content and reply markup are exactly the same",
    )
    return any(pattern in error_text for pattern in patterns)


def _audio_storage_provider_from_application(application: Application) -> AudioStorageProvider:
    bot_data = getattr(application, "bot_data", {})
    provider = bot_data.get("audio_storage_provider")
    if provider is None:
        raise RuntimeError("Telegram audio storage provider is not configured")
    return provider


def is_message_not_editable_error(error: Exception) -> bool:
    error_text = str(error).lower()
    patterns = (
        "message to edit not found",
        "message to delete not found",
        "there is no text in the message to edit",
        "message can't be edited",
    )
    return any(pattern in error_text for pattern in patterns)
