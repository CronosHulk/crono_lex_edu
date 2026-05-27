from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClientWebImportEvent:
    telegram_user_id: int
    job_id: int
    event: str
    status: str | None = None
    item_count: int | None = None

    def payload(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "telegram_user_id": self.telegram_user_id,
            "job_id": self.job_id,
            "event": self.event,
        }
        if self.status is not None:
            data["status"] = self.status
        if self.item_count is not None:
            data["item_count"] = self.item_count
        return data
