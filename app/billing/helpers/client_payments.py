from __future__ import annotations


def build_public_payment_failure_message(status: str, failure_reason: object | None = None) -> str | None:
    normalized_status = str(status or "").strip()
    normalized_reason = str(failure_reason or "").strip()
    if normalized_status == "success":
        return None
    if normalized_status == "expired":
        return "Payment expired"
    if normalized_status == "reversed":
        return "Payment was reversed"
    if normalized_status == "failure":
        return normalized_reason[:300] if normalized_reason else "Payment failed"
    return None
