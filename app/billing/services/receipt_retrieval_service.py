from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

from app.billing.helpers.receipt_notifications import (
    build_public_checkbox_check_url,
    normalize_receipt_status,
    receipt_delivery_status,
    receipt_file_base64_is_valid,
)
from app.billing.services.provider_port import (
    BillingProviderAuditContext,
    BillingProviderReceiptArtifact,
    BillingProviderReceiptFetchResult,
    BillingReceiptFiscalProviderFactory,
    BillingReceiptFiscalProviderPort,
    billing_provider_api_error_details,
    require_billing_receipt_fiscal_provider_factory,
)
from app.billing.services.provider_runtime import (
    payment_provider_runtime_is_monobank_test,
    resolve_payment_provider_runtime,
)
from app.time_utils import TimeService

MONOBANK_TEST_RECEIPTS_UNAVAILABLE_REASON = "monobank_test_mode_receipts_not_available"


class BillingReceiptRetrievalBillingPort(Protocol):
    def list_payment_receipts(self, payment_id: int) -> list[dict[str, Any]]: ...

    def create_receipt(
        self,
        *,
        payment_id: int,
        receipt_type: str,
        status: str,
        provider_check_id: str | None = None,
        fiscalization_source: str | None = None,
        tax_url: str | None = None,
        file_base64: str | None = None,
        payload_json: dict[str, Any] | None = None,
        bot_delivery_status: str | None = None,
        retry_count: int = 0,
        next_retry_at: datetime | None = None,
        current_time: datetime,
    ) -> dict[str, Any]: ...


class BillingReceiptRetrievalDatabasePort(Protocol):
    billing: BillingReceiptRetrievalBillingPort


class BillingReceiptRetrievalService:
    def __init__(
        self,
        db: BillingReceiptRetrievalDatabasePort,
        time_service: TimeService,
        *,
        billing_provider_factory: BillingReceiptFiscalProviderFactory | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.billing_provider_factory = (
            billing_provider_factory
            or None
        )

    def ensure_success_receipts(
        self,
        payment: dict[str, Any],
        *,
        source_place: str = "billing_bot_receipt",
        retry_delay_seconds: int | None = None,
        max_attempts: int | None = None,
    ) -> list[dict[str, Any]]:
        if payment["status"] != "success":
            return []
        existing = self.db.billing.list_payment_receipts(int(payment["id"]))
        provider_runtime = resolve_payment_provider_runtime(payment)
        if payment_provider_runtime_is_monobank_test(provider_runtime):
            return existing
        fiscal_checks_are_final = any(
            str(row.get("receipt_type")) == "fiscal_check" and receipt_is_available(row)
            for row in existing
        )
        invoice_id = str(payment.get("provider_invoice_id") or "").strip()
        fiscal_check_retry_count = next_receipt_retry_count(existing, "fiscal_check")
        if not invoice_id:
            return existing or [
                self.db.billing.create_receipt(
                    payment_id=int(payment["id"]),
                    receipt_type="fiscal_check",
                    status="unavailable",
                    payload_json={"reason": "missing_provider_invoice_id"},
                    retry_count=fiscal_check_retry_count,
                    current_time=self.time_service.now(),
                )
            ]
        receipt_rows = []
        if not fiscal_checks_are_final and not receipt_retry_exhausted(
            existing, "fiscal_check", max_attempts
        ):
            receipt_rows.extend(
                self._fetch_provider_fiscal_checks(
                    payment,
                    invoice_id,
                    source_place=source_place,
                    retry_count=fiscal_check_retry_count,
                    retry_delay_seconds=retry_delay_seconds,
                    max_attempts=max_attempts,
                )
            )
        if existing or receipt_rows:
            return [*existing, *receipt_rows]
        return [
            self.db.billing.create_receipt(
                payment_id=int(payment["id"]),
                receipt_type="fiscal_check",
                status="unavailable",
                payload_json={"reason": "monobank_fiscal_checks_unavailable"},
                retry_count=fiscal_check_retry_count,
                next_retry_at=self._next_retry_at(
                    fiscal_check_retry_count, retry_delay_seconds, max_attempts
                ),
                current_time=self.time_service.now(),
            )
        ]

    def _fetch_provider_receipt(
        self,
        payment: dict[str, Any],
        invoice_id: str,
        *,
        source_place: str,
        retry_count: int,
        retry_delay_seconds: int | None,
        max_attempts: int | None,
    ) -> list[dict[str, Any]]:
        provider_runtime = resolve_payment_provider_runtime(payment)
        try:
            result = self._billing_provider(
                provider_runtime.provider_key,
                provider_runtime.provider_mode,
            ).fetch_receipt(
                invoice_id,
                audit_context=self._audit_context(payment, invoice_id, source_place),
            )
        except Exception as error:
            api_error_details = billing_provider_api_error_details(error)
            if api_error_details is not None:
                return [
                    self.db.billing.create_receipt(
                        payment_id=int(payment["id"]),
                        receipt_type="receipt",
                        status="unavailable",
                        payload_json={
                            "error_code": api_error_details.error_code,
                            "status_code": api_error_details.status_code,
                            "error_text": str(error),
                        },
                        retry_count=retry_count,
                        next_retry_at=self._next_retry_at(
                            retry_count, retry_delay_seconds, max_attempts
                        ),
                        current_time=self.time_service.now(),
                    )
                ]
            return [
                self.db.billing.create_receipt(
                    payment_id=int(payment["id"]),
                    receipt_type="receipt",
                    status="failed",
                    payload_json={
                        "error_type": type(error).__name__,
                        "error_text": str(error)[:1000],
                    },
                    retry_count=retry_count,
                    next_retry_at=self._next_retry_at(
                        retry_count, retry_delay_seconds, max_attempts
                    ),
                    current_time=self.time_service.now(),
                )
            ]
        if result.unavailable_reason is not None or not result.artifacts:
            return [
                self.db.billing.create_receipt(
                    payment_id=int(payment["id"]),
                    receipt_type=result.receipt_type,
                    status="unavailable",
                    payload_json=_provider_fetch_unavailable_payload(
                        result,
                        fallback_reason="provider_receipt_unavailable",
                    ),
                    retry_count=retry_count,
                    next_retry_at=self._next_retry_at(
                        retry_count, retry_delay_seconds, max_attempts
                    ),
                    current_time=self.time_service.now(),
                )
            ]
        artifact = result.artifacts[0]
        file_base64 = str(artifact.file_base64 or "").strip() or None
        if file_base64 is None:
            return [
                self.db.billing.create_receipt(
                    payment_id=int(payment["id"]),
                    receipt_type=artifact.receipt_type,
                    status="unavailable",
                    payload_json={
                        "reason": "monobank_receipt_file_missing",
                        "provider_payload": result.provider_payload,
                    },
                    retry_count=retry_count,
                    next_retry_at=self._next_retry_at(
                        retry_count, retry_delay_seconds, max_attempts
                    ),
                    current_time=self.time_service.now(),
                )
            ]
        if not receipt_file_base64_is_valid(file_base64):
            return [
                self.db.billing.create_receipt(
                    payment_id=int(payment["id"]),
                    receipt_type=artifact.receipt_type,
                    status="unavailable",
                    payload_json={
                        "reason": "monobank_receipt_file_invalid",
                        "provider_payload": result.provider_payload,
                    },
                    retry_count=retry_count,
                    next_retry_at=self._next_retry_at(
                        retry_count, retry_delay_seconds, max_attempts
                    ),
                    current_time=self.time_service.now(),
                )
            ]
        return [
            self.db.billing.create_receipt(
                payment_id=int(payment["id"]),
                receipt_type=artifact.receipt_type,
                status=normalize_receipt_status(artifact.status),
                file_base64=file_base64,
                payload_json=artifact.payload,
                bot_delivery_status="queued",
                retry_count=retry_count,
                current_time=self.time_service.now(),
            )
        ]

    def _fetch_monobank_receipt(
        self,
        payment: dict[str, Any],
        invoice_id: str,
        *,
        source_place: str,
        retry_count: int,
        retry_delay_seconds: int | None,
        max_attempts: int | None,
    ) -> list[dict[str, Any]]:
        return self._fetch_provider_receipt(
            payment,
            invoice_id,
            source_place=source_place,
            retry_count=retry_count,
            retry_delay_seconds=retry_delay_seconds,
            max_attempts=max_attempts,
        )

    def _fetch_provider_fiscal_checks(
        self,
        payment: dict[str, Any],
        invoice_id: str,
        *,
        source_place: str,
        retry_count: int,
        retry_delay_seconds: int | None,
        max_attempts: int | None,
    ) -> list[dict[str, Any]]:
        provider_runtime = resolve_payment_provider_runtime(payment)
        try:
            result = self._billing_provider(
                provider_runtime.provider_key,
                provider_runtime.provider_mode,
            ).fetch_fiscal_checks(
                invoice_id,
                audit_context=self._audit_context(payment, invoice_id, source_place),
            )
        except Exception as error:
            api_error_details = billing_provider_api_error_details(error)
            return [
                self.db.billing.create_receipt(
                    payment_id=int(payment["id"]),
                    receipt_type="fiscal_check",
                    status="failed" if api_error_details is None else "unavailable",
                    payload_json={
                        "error_type": type(error).__name__,
                        "error_text": str(error)[:1000],
                    },
                    retry_count=retry_count,
                    next_retry_at=self._next_retry_at(
                        retry_count, retry_delay_seconds, max_attempts
                    ),
                    current_time=self.time_service.now(),
                )
            ]
        rows = []
        if result.unavailable_reason is not None or not result.artifacts:
            return [
                self.db.billing.create_receipt(
                    payment_id=int(payment["id"]),
                    receipt_type=result.receipt_type,
                    status="unavailable",
                    payload_json=_provider_fetch_unavailable_payload(
                        result,
                        fallback_reason="provider_fiscal_checks_unavailable",
                    ),
                    retry_count=retry_count,
                    next_retry_at=self._next_retry_at(
                        retry_count, retry_delay_seconds, max_attempts
                    ),
                    current_time=self.time_service.now(),
                )
            ]
        for artifact in result.artifacts:
            tax_url = (
                str(artifact.tax_url or "").strip()
                or _artifact_public_check_url(artifact)
                or ""
            )
            file_base64 = str(artifact.file_base64 or "").strip()
            valid_file_base64 = (
                file_base64 if file_base64 and receipt_file_base64_is_valid(file_base64) else ""
            )
            status = normalize_receipt_status(artifact.status)
            if tax_url:
                status = "done"
            if status == "done" and not tax_url and not valid_file_base64:
                status = "unavailable"
            rows.append(
                self.db.billing.create_receipt(
                    payment_id=int(payment["id"]),
                    receipt_type=artifact.receipt_type,
                    status=status,
                    provider_check_id=artifact.provider_check_id,
                    fiscalization_source=artifact.fiscalization_source,
                    tax_url=tax_url or None,
                    file_base64=valid_file_base64 or None,
                    payload_json=artifact.payload,
                    bot_delivery_status=receipt_delivery_status(
                        queue_delivery=True,
                        tax_url=tax_url,
                        file_base64=valid_file_base64,
                    ),
                    retry_count=retry_count,
                    next_retry_at=self._next_retry_at(
                        retry_count, retry_delay_seconds, max_attempts
                    )
                    if status != "done"
                    else None,
                    current_time=self.time_service.now(),
                )
            )
        if rows:
            return rows
        return [
            self.db.billing.create_receipt(
                payment_id=int(payment["id"]),
                receipt_type=result.receipt_type,
                status="unavailable",
                payload_json=_provider_fetch_unavailable_payload(
                    result,
                    fallback_reason="provider_fiscal_checks_empty",
                ),
                retry_count=retry_count,
                next_retry_at=self._next_retry_at(retry_count, retry_delay_seconds, max_attempts),
                current_time=self.time_service.now(),
            )
        ]

    def _fetch_monobank_fiscal_checks(
        self,
        payment: dict[str, Any],
        invoice_id: str,
        *,
        source_place: str,
        retry_count: int,
        retry_delay_seconds: int | None,
        max_attempts: int | None,
    ) -> list[dict[str, Any]]:
        return self._fetch_provider_fiscal_checks(
            payment,
            invoice_id,
            source_place=source_place,
            retry_count=retry_count,
            retry_delay_seconds=retry_delay_seconds,
            max_attempts=max_attempts,
        )

    def _next_retry_at(
        self,
        retry_count: int,
        retry_delay_seconds: int | None,
        max_attempts: int | None,
    ) -> Any:
        if retry_delay_seconds is None or max_attempts is None or retry_count >= max_attempts:
            return None
        return self.time_service.now() + timedelta(seconds=max(int(retry_delay_seconds), 1))

    def _audit_context(
        self, payment: dict[str, Any], invoice_id: str, source_place: str
    ) -> BillingProviderAuditContext:
        return BillingProviderAuditContext(
            source_place=source_place,
            actor_user_uuid=payment["user_uuid"],
            telegram_user_id=int(payment["telegram_user_id"]),
            payment_id=int(payment["id"]),
            order_reference=payment.get("provider_reference"),
            invoice_id=invoice_id,
        )

    def _billing_provider(
        self, provider_key: str, provider_mode: str
    ) -> BillingReceiptFiscalProviderPort:
        return require_billing_receipt_fiscal_provider_factory(self.billing_provider_factory)(
            provider_key=provider_key,
            provider_mode=provider_mode,
        )


def deliverable_receipt_ids(receipts: list[dict[str, Any]]) -> set[int]:
    return {
        int(row["id"])
        for row in receipts
        if receipt_is_deliverable(row)
        and str(row.get("receipt_type") or "") == "fiscal_check"
        and row.get("bot_delivery_status") != "sent"
    }


def _provider_fetch_unavailable_payload(
    result: BillingProviderReceiptFetchResult,
    *,
    fallback_reason: str,
) -> dict[str, Any]:
    return {
        "reason": result.unavailable_reason or fallback_reason,
        "provider_payload": result.provider_payload,
    }


def _artifact_public_check_url(artifact: BillingProviderReceiptArtifact) -> str | None:
    return build_public_checkbox_check_url(
        {
            "receipt_type": artifact.receipt_type,
            "provider_check_id": artifact.provider_check_id,
            "fiscalization_source": artifact.fiscalization_source,
        }
    )


def receipt_is_deliverable(row: dict[str, Any]) -> bool:
    file_base64 = str(row.get("file_base64") or "").strip()
    return bool(
        row.get("status") == "done"
        and (
            str(row.get("tax_url") or "").strip()
            or (file_base64 and receipt_file_base64_is_valid(file_base64))
        )
    )


def receipt_is_available(row: dict[str, Any]) -> bool:
    return receipt_is_deliverable(row) or build_public_checkbox_check_url(row) is not None


def next_receipt_retry_count(receipts: list[dict[str, Any]], receipt_type: str) -> int:
    return (
        max(
            [
                int(row.get("retry_count") or 0)
                for row in receipts
                if str(row.get("receipt_type") or "") == receipt_type
            ]
            or [0]
        )
        + 1
    )


def receipt_retry_exhausted(
    receipts: list[dict[str, Any]],
    receipt_type: str,
    max_attempts: int | None,
) -> bool:
    if any(
        str(row.get("receipt_type") or "") == receipt_type
        and isinstance(row.get("payload_json"), dict)
        and row["payload_json"].get("reason") == MONOBANK_TEST_RECEIPTS_UNAVAILABLE_REASON
        for row in receipts
    ):
        return True
    if max_attempts is None:
        return False
    max_retry_count = max(
        [
            int(row.get("retry_count") or 0)
            for row in receipts
            if str(row.get("receipt_type") or "") == receipt_type
        ]
        or [0]
    )
    return max_retry_count >= max(int(max_attempts), 1)
