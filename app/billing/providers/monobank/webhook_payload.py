from __future__ import annotations

import json
from typing import Any

from app.billing.services.provider_port import BillingProviderWebhookPayload
from app.domain.billing.monobank_statuses import normalize_monobank_provider_status


class BillingWebhookPayloadError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


def parse_monobank_webhook_payload(raw_body: bytes) -> BillingProviderWebhookPayload:
    payload = parse_monobank_webhook_body(raw_body)
    return BillingProviderWebhookPayload(
        invoice_id=normalize_invoice_id(payload.get("invoiceId")),
        provider_status=normalize_provider_status(payload.get("status")),
        payload=payload,
    )


def parse_monobank_webhook_body(raw_body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BillingWebhookPayloadError(
            400, "invalid_json", "Webhook body must be a JSON object"
        ) from error
    if not isinstance(payload, dict):
        raise BillingWebhookPayloadError(
            400, "invalid_json", "Webhook body must be a JSON object"
        )
    return payload


def normalize_invoice_id(value: Any) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise BillingWebhookPayloadError(400, "missing_invoice_id", "invoiceId is required")
    if len(normalized) > 128:
        raise BillingWebhookPayloadError(
            400, "invalid_invoice_id", "invoiceId must be at most 128 chars"
        )
    return normalized


def normalize_provider_status(value: Any) -> str:
    try:
        return normalize_monobank_provider_status(value)
    except ValueError as error:
        raise BillingWebhookPayloadError(
            400, "invalid_status", "Unsupported Monobank invoice status"
        ) from error


__all__ = [
    "BillingWebhookPayloadError",
    "parse_monobank_webhook_body",
    "parse_monobank_webhook_payload",
    "normalize_invoice_id",
    "normalize_provider_status",
]
