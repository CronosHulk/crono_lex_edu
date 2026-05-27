from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MONOBANK_PROVIDER_STATUSES = {
    "created",
    "processing",
    "hold",
    "success",
    "failure",
    "reversed",
    "expired",
}
MONOBANK_INTERNAL_STATUS_MAP = {
    "created": "invoice_created",
    "processing": "processing",
    "hold": "processing",
    "success": "success",
    "failure": "failure",
    "reversed": "reversed",
    "expired": "expired",
}


@dataclass(frozen=True)
class MonobankPaymentStatus:
    provider_status: str
    internal_status: str
    failure_code: str | None = None
    failure_reason: str | None = None


def normalize_monobank_provider_status(value: Any) -> str:
    normalized = str(value or "").strip()
    if normalized not in MONOBANK_PROVIDER_STATUSES:
        raise ValueError("Unsupported Monobank invoice status")
    return normalized


def monobank_payment_status_from_payload(payload: Mapping[str, Any]) -> MonobankPaymentStatus:
    return monobank_payment_status_from_provider_status(
        payload.get("status"),
        payload=payload,
    )


def monobank_payment_status_from_provider_status(
    provider_status: Any,
    *,
    payload: Mapping[str, Any],
) -> MonobankPaymentStatus:
    normalized_status = normalize_monobank_provider_status(provider_status)
    return MonobankPaymentStatus(
        provider_status=normalized_status,
        internal_status=MONOBANK_INTERNAL_STATUS_MAP[normalized_status],
        failure_code=trim_optional(payload.get("errCode"), 128),
        failure_reason=trim_optional(payload.get("failureReason"), 1024),
    )


def trim_optional(value: Any, max_length: int) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    return normalized[:max_length]
