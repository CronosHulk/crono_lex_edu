from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

SECRET_HEADER_NAMES = {"authorization", "x-token", "x-api-key", "api-key"}


@dataclass(frozen=True)
class MonobankAuditContext:
    source_place: str
    actor_user_uuid: str | UUID | None = None
    telegram_user_id: int | None = None
    payment_id: int | None = None
    order_reference: str | None = None
    invoice_id: str | None = None
    request_ip: str | None = None


class MonobankAuditLogger(Protocol):
    def create_monobank_audit_log(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError


def mask_headers(headers: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in headers.items():
        masked[key] = "[redacted]" if key.lower() in SECRET_HEADER_NAMES else value
    return masked


def duration_ms(started: datetime, finished: datetime) -> int:
    return max(int((finished - started).total_seconds() * 1000), 0)
