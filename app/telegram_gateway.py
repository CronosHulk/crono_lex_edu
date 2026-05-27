from __future__ import annotations

from typing import Any

import httpx


class TelegramGateway:
    def __init__(self, token: str) -> None:
        self.token = token

    def send_message(
        self,
        *,
        chat_id: int | str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        disable_notification: bool = False,
        ignore_errors: bool = False,
    ) -> int | None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_notification": disable_notification,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        result = call_telegram_api(
            self.token,
            "sendMessage",
            payload,
            ignore_errors=ignore_errors,
        )
        message_id = result.get("message_id")
        return int(message_id) if message_id is not None else None

    def delete_message(self, *, chat_id: int | str, message_id: int | str, ignore_errors: bool = False) -> bool:
        result = call_telegram_api(
            self.token,
            "deleteMessage",
            {"chat_id": chat_id, "message_id": message_id},
            ignore_errors=ignore_errors,
        )
        return bool(result) or ignore_errors


def call_telegram_api(token: str, method: str, payload: dict[str, Any], *, ignore_errors: bool = False) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(f"https://api.telegram.org/bot{token}/{method}", json=payload)
            response.raise_for_status()
            data = response.json()
            result = data.get("result")
            return result if isinstance(result, dict) else {}
    except Exception:
        if ignore_errors:
            return {}
        raise
