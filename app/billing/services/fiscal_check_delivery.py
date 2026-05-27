from __future__ import annotations

from typing import Any, Protocol

from app.time_utils import TimeService


class _PaymentEventCreator(Protocol):
    def create_payment_event(
        self,
        *,
        payment_id: int,
        event_type: str,
        source: str,
        provider_status: str,
        payload_json: dict[str, Any],
        current_time: Any,
    ) -> Any: ...


class _DatabasePort(Protocol):
    billing: _PaymentEventCreator


class _ReceiptRetrievalPort(Protocol):
    def ensure_success_receipts(
        self, payment: dict[str, Any], *, source_place: str
    ) -> list[dict[str, Any]]: ...


def ensure_success_fiscal_checks_with_event(
    *,
    db: _DatabasePort,
    time_service: TimeService,
    receipt_retrieval: _ReceiptRetrievalPort,
    payment: dict[str, Any],
    source: str,
    source_place: str,
) -> None:
    if payment.get("status") != "success":
        return
    try:
        receipt_retrieval.ensure_success_receipts(payment, source_place=source_place)
    except Exception as error:
        db.billing.create_payment_event(
            payment_id=int(payment["id"]),
            event_type="fiscal_check_retrieval_error",
            source=source,
            provider_status="success",
            payload_json={"error_type": type(error).__name__, "error_text": str(error)[:1000]},
            current_time=time_service.now(),
        )
