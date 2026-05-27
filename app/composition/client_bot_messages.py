from __future__ import annotations

from typing import Any

from app.application.client.bot_message_service import ClientBotMessageService
from app.application.client_runtime.bot_message_service import ClientRuntimeBotMessageService
from app.data_access.bot_message_logs import BotMessageLogRepository


def configure_client_bot_message_runtime(service: Any, db: Any) -> None:
    bot_message_logs_repo = getattr(db, "bot_message_logs", None) or BotMessageLogRepository(db)
    service.client_bot_message_service = ClientBotMessageService(
        bot_message_logs_repo,
        service.time_service,
        retention_days=getattr(db.settings, "app_bot_message_retention_days", 30),
    )
    service.client_runtime_bot_message_service = ClientRuntimeBotMessageService(
        service.client_bot_message_service,
        dispatch_lock=service.dispatch_lock,
    )

