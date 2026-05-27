from __future__ import annotations

from typing import Any

from app.billing.services.provider_port import (
    BillingProviderReceiptArtifact,
    BillingProviderReceiptFetchResult,
)


def monobank_receipt_fetch_result(payload: dict[str, Any]) -> BillingProviderReceiptFetchResult:
    file_base64 = str(payload.get("file") or "").strip() or None
    if file_base64 is None:
        return BillingProviderReceiptFetchResult(
            receipt_type="receipt",
            unavailable_reason="monobank_receipt_file_missing",
            provider_payload=payload,
        )
    return BillingProviderReceiptFetchResult(
        receipt_type="receipt",
        artifacts=(
            BillingProviderReceiptArtifact(
                receipt_type="receipt",
                status="done",
                file_base64=file_base64,
                payload=payload,
            ),
        ),
        provider_payload=payload,
    )


def monobank_fiscal_checks_fetch_result(
    payload: dict[str, Any],
) -> BillingProviderReceiptFetchResult:
    checks = payload.get("checks") if isinstance(payload, dict) else None
    if not isinstance(checks, list):
        return BillingProviderReceiptFetchResult(
            receipt_type="fiscal_check",
            unavailable_reason="monobank_fiscal_checks_unavailable",
            provider_payload=payload,
        )
    artifacts = tuple(
        _monobank_fiscal_check_artifact(check) for check in checks if isinstance(check, dict)
    )
    if not artifacts:
        return BillingProviderReceiptFetchResult(
            receipt_type="fiscal_check",
            unavailable_reason="monobank_fiscal_checks_empty",
            provider_payload=payload,
        )
    return BillingProviderReceiptFetchResult(
        receipt_type="fiscal_check",
        artifacts=artifacts,
        provider_payload=payload,
    )


def _monobank_fiscal_check_artifact(check: dict[str, Any]) -> BillingProviderReceiptArtifact:
    return BillingProviderReceiptArtifact(
        receipt_type="fiscal_check",
        status=str(check.get("status") or "").strip(),
        provider_check_id=str(check.get("id") or "").strip() or None,
        fiscalization_source=str(check.get("fiscalizationSource") or "").strip() or None,
        tax_url=str(check.get("taxUrl") or "").strip() or None,
        file_base64=str(check.get("file") or "").strip() or None,
        payload=check,
    )
