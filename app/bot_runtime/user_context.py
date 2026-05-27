from __future__ import annotations

from telegram import Update

from app.bot_runtime.telegram_payload import serialize_telegram_payload
from app.contracts import TelegramUserContext


def build_user_context(update: Update) -> TelegramUserContext:
    user = update.effective_user
    if user is None:
        raise RuntimeError("Telegram user is required")

    chat = update.effective_chat
    return TelegramUserContext(
        telegram_user_id=user.id,
        is_bot=user.is_bot,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        language_code=user.language_code,
        is_premium=getattr(user, "is_premium", None),
        chat_id=getattr(chat, "id", None),
        chat_type=getattr(chat, "type", None),
        chat_username=getattr(chat, "username", None),
        chat_title=getattr(chat, "title", None),
        raw_telegram_json=serialize_telegram_payload(user, chat),
    )
