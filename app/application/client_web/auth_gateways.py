from __future__ import annotations

from typing import Any, Protocol


class ClientWebAuthTelegramGateway(Protocol):
    def send_message(
        self,
        *,
        chat_id: int | str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        disable_notification: bool = False,
        ignore_errors: bool = False,
    ) -> int | None: ...

    def delete_message(self, *, chat_id: int | str, message_id: int | str, ignore_errors: bool = False) -> bool: ...
