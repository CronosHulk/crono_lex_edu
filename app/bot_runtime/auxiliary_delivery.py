from __future__ import annotations

import asyncio

from telegram.ext import Application

from app.bot_api_client import BotApiClient
from app.bot_runtime.delivery import is_message_not_editable_error, is_message_not_modified_error
from app.bot_runtime.message_tracking import clear_messages, track_sent_bot_message
from app.bot_runtime.rendering import build_keyboard
from app.bot_runtime.state import (
    ActiveScreenMessage,
    build_message_log_refs,
    clear_auxiliary_screen_message_state,
    get_auxiliary_screen_message,
    save_auxiliary_screen_message,
)
from app.contracts import ButtonModel, ScreenModel


async def sync_auxiliary_screen_message(
    *,
    application: Application,
    api_client: BotApiClient | None,
    chat_id: int,
    user_data: dict | None,
    telegram_user_id: int | None,
    auxiliary_text: str | None,
    disable_notification: bool,
    auxiliary_buttons: list[ButtonModel] | None = None,
) -> None:
    auxiliary_message = get_auxiliary_screen_message(user_data)
    if auxiliary_text is None:
        if auxiliary_message is None:
            return
        await clear_messages(
            chat_id,
            application,
            [auxiliary_message.message_id],
            build_message_log_refs([auxiliary_message]),
        )
        clear_auxiliary_screen_message_state(user_data)
        return
    if auxiliary_message is not None:
        try:
            await application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=auxiliary_message.message_id,
                text=auxiliary_text,
                reply_markup=build_auxiliary_keyboard(auxiliary_buttons or []),
            )
            return
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if not is_message_not_modified_error(error) and not is_message_not_editable_error(error):
                raise
            if is_message_not_modified_error(error):
                return
            await clear_messages(
                chat_id,
                application,
                [auxiliary_message.message_id],
                build_message_log_refs([auxiliary_message]),
            )
            clear_auxiliary_screen_message_state(user_data)
            auxiliary_message = None
    sent_message = await application.bot.send_message(
        chat_id=chat_id,
        text=auxiliary_text,
        reply_markup=build_auxiliary_keyboard(auxiliary_buttons or []),
        disable_notification=disable_notification,
    )
    tracked_row = await track_sent_bot_message(
        api_client=api_client,
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        screen_id="auxiliary:card_hint",
        message_id=sent_message.message_id,
    )
    if user_data is not None:
        save_auxiliary_screen_message(
            user_data,
            ActiveScreenMessage(
                message_id=sent_message.message_id,
                message_log_id=getattr(tracked_row, "id", None),
                screen_id="auxiliary:card_hint",
            ),
        )


def build_auxiliary_keyboard(buttons: list[ButtonModel]):
    if not buttons:
        return None
    return build_keyboard(
        ScreenModel(
            screen_id="auxiliary",
            text="auxiliary",
            buttons=buttons,
            metadata={"buttons_per_row": 1},
        )
    )
