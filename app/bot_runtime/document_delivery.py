from __future__ import annotations

import logging

from telegram.ext import Application

from app.bot_api_client import BotApiClient
from app.bot_runtime.documents import (
    read_screen_documents,
    resolve_document_path,
)
from app.bot_runtime.message_tracking import track_sent_bot_message
from app.contracts import ScreenModel
from app.screen_delivery_policy import read_screen_delivery_policy

LOGGER = logging.getLogger(__name__)


async def send_screen_documents(
    *,
    application: Application,
    chat_id: int,
    screen: ScreenModel,
    user_data: dict | None,
    telegram_user_id: int | None,
    disable_notification: bool,
) -> None:
    api_client: BotApiClient | None = application.bot_data.get("api_client")
    policy = read_screen_delivery_policy(screen)
    documents = read_screen_documents(screen)
    if not documents:
        return
    for index, document in enumerate(documents, start=1):
        document_path = resolve_document_path(document["path"] or "")
        if not document_path.exists():
            LOGGER.debug("Document artifact is missing path=%s screen_id=%s", document_path, screen.screen_id)
            continue
        with document_path.open("rb") as document_file:
            sent_message = await application.bot.send_document(
                chat_id=chat_id,
                document=document_file,
                caption=document["caption"],
                parse_mode=screen.parse_mode,
                filename=document["filename"],
                disable_notification=disable_notification,
            )
        tracked_row = await track_sent_bot_message(
            api_client=api_client,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            screen_id=f"attachment:{screen.screen_id}:{index}",
            message_id=sent_message.message_id,
            delete_after_hours=policy.delete_after_hours,
        )
        if user_data is None:
            continue
        user_data.setdefault("bot_message_ids", [])
        user_data.setdefault("bot_message_log_refs", [])
        user_data["bot_message_ids"].append(sent_message.message_id)
        if tracked_row is not None:
            user_data["bot_message_log_refs"].append(
                {"message_id": sent_message.message_id, "message_log_id": getattr(tracked_row, "id", None)}
            )
