"""Deprecated compatibility shim for webhook payload parsing."""

from __future__ import annotations


class BillingWebhookPayloadError(RuntimeError):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


def _compat_error() -> BillingWebhookPayloadError:
    return BillingWebhookPayloadError(
        500,
        "removed",
        "app.billing.services.monobank_webhook_payload is deprecated and removed",
    )


def parse_monobank_webhook_body(raw_body: bytes):
    raise _compat_error()


def parse_monobank_webhook_payload(raw_body: bytes):
    raise _compat_error()


def normalize_invoice_id(value):
    raise _compat_error()


def normalize_provider_status(value):
    raise _compat_error()


__all__ = [
    "BillingWebhookPayloadError",
    "parse_monobank_webhook_body",
    "parse_monobank_webhook_payload",
    "normalize_invoice_id",
    "normalize_provider_status",
]
