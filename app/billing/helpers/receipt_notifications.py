from __future__ import annotations

import base64
import binascii
from typing import Any
from urllib.parse import urlparse

from app.billing.services.receipt_storage_port import (
    BillingReceiptArtifactRef,
    BillingReceiptStorageProvider,
)
from app.contracts import ButtonModel, DocumentAttachmentModel, ScreenModel
from app.domain.billing.constants import BILLING_PROVIDER_MONOBANK
from app.screen_delivery_policy import with_delete_after_hours

BILLING_CLOSE_ACTION = "billing:close"
CHECKBOX_PUBLIC_CHECK_BASE_URL = "https://check.checkbox.ua"


def build_payment_notification_screen(payment: dict[str, Any], receipts: list[dict[str, Any]]) -> ScreenModel:
    status = str(payment["status"])
    lines = [
        build_status_title(status),
        "",
        f"Замовлення: {payment['provider_reference']}",
        f"Тариф: {payment['plan_key']}",
        build_payment_period_text(payment),
        f"Сума: {format_amount_uah(int(payment['amount_minor']))}",
    ]
    promotion_text = build_payment_promotion_text(payment)
    if promotion_text:
        lines.append(promotion_text)
    if is_test_payment(payment):
        lines.extend(["", "Тестовий платіж"])
    failure_reason = str(payment.get("failure_reason") or "").strip()
    if status in {"failure", "expired", "reversed"} and failure_reason:
        lines.extend(["", f"Причина: {failure_reason}"])
    if status == "success":
        lines.extend(["", build_receipt_status_text(receipts, payment=payment)])
    screen = ScreenModel(
        screen_id=f"billing:payment:{payment['id']}",
        text="\n".join(lines),
        buttons=build_close_buttons(),
        documents=[],
        keyboard_type="inline",
        metadata={"buttons_per_row": 1},
    )
    return with_delete_after_hours(screen, 168)


def build_receipt_delivery_screen(
    payment: dict[str, Any],
    receipt: dict[str, Any],
    *,
    billing_receipt_storage_provider: BillingReceiptStorageProvider,
) -> ScreenModel:
    lines = [
        "Чек за оплату готовий",
        "",
        f"Замовлення: {payment['provider_reference']}",
        f"Тариф: {payment['plan_key']}",
        build_payment_period_text(payment),
        f"Сума: {format_amount_uah(int(payment['amount_minor']))}",
    ]
    promotion_text = build_payment_promotion_text(payment)
    if promotion_text:
        lines.append(promotion_text)
    if is_test_payment(payment):
        lines.extend(["", "Тестовий платіж"])
    screen = ScreenModel(
        screen_id=f"billing:receipt:{receipt['id']}",
        text="\n".join(lines),
        buttons=build_receipt_buttons([receipt]),
        documents=build_receipt_documents(
            [receipt], billing_receipt_storage_provider=billing_receipt_storage_provider
        ),
        keyboard_type="inline",
        metadata={"buttons_per_row": 1},
    )
    return with_delete_after_hours(screen, 168)


def build_receipt_admin_alert_screen(payment: dict[str, Any], receipt: dict[str, Any]) -> ScreenModel:
    screen = ScreenModel(
        screen_id=f"billing:receipt-alert:{receipt['id']}",
        text="\n".join(
            [
                "Проблема видачі чека оплати",
                "",
                f"Payment ID: {payment['id']}",
                f"Order: {payment['provider_reference']}",
                f"User: {payment['telegram_user_id']}",
                f"Plan: {payment['plan_key']} / {payment['period_months']} міс.",
                f"Receipt ID: {receipt['id']}",
                f"Receipt type: {receipt['receipt_type']}",
                f"Receipt status: {receipt['status']}",
                f"Attempts: {receipt.get('retry_count') or 0}",
            ]
        ),
        buttons=[],
        keyboard_type="inline",
    )
    return with_delete_after_hours(screen, 168)


def build_status_title(status: str) -> str:
    if status == "success":
        return "Оплата успішна"
    if status == "expired":
        return "Оплата не пройшла: рахунок прострочений"
    if status == "reversed":
        return "Оплата повернена"
    return "Оплата не пройшла"


def build_payment_period_text(payment: dict[str, Any]) -> str:
    period_months = int(payment["period_months"])
    granted_period_months = read_granted_period_months(payment)
    if granted_period_months > period_months:
        return f"Період: {period_months} міс. (нараховано {granted_period_months} міс.)"
    return f"Період: {period_months} міс."


def build_payment_promotion_text(payment: dict[str, Any]) -> str | None:
    promotion = read_payment_promotion(payment)
    if not promotion:
        return None
    label = str(promotion.get("label") or "").strip()
    if not label:
        return None
    return f"Акція: {label}"


def read_granted_period_months(payment: dict[str, Any]) -> int:
    try:
        direct_value = int(payment.get("granted_period_months") or 0)
    except (TypeError, ValueError):
        direct_value = 0
    if direct_value > 0:
        return direct_value
    quote = read_checkout_quote(payment)
    try:
        quote_value = int(quote.get("granted_period_months") or 0)
    except (TypeError, ValueError):
        quote_value = 0
    return quote_value if quote_value > 0 else int(payment["period_months"])


def read_payment_promotion(payment: dict[str, Any]) -> dict[str, Any]:
    quote = read_checkout_quote(payment)
    promotion = quote.get("promotion")
    return promotion if isinstance(promotion, dict) else {}


def read_checkout_quote(payment: dict[str, Any]) -> dict[str, Any]:
    provider_payload = payment.get("provider_status_json")
    if not isinstance(provider_payload, dict):
        return {}
    quote = provider_payload.get("checkout_quote")
    return quote if isinstance(quote, dict) else {}


def build_receipt_status_text(receipts: list[dict[str, Any]], *, payment: dict[str, Any] | None = None) -> str:
    if payment is not None and is_monobank_test_payment(payment):
        return "Фіскальний чек не запитується: Monobank sandbox не створює фіскальні чеки."
    if receipts:
        return "Чек можна отримати в особистому кабінеті в історії платежів."
    return "Чек буде доступний в особистому кабінеті в історії платежів."


def build_close_buttons() -> list[ButtonModel]:
    return [ButtonModel(action=BILLING_CLOSE_ACTION, text="Закрити")]


def build_receipt_buttons(receipts: list[dict[str, Any]]) -> list[ButtonModel]:
    buttons: list[ButtonModel] = []
    for row in receipts:
        if str(row.get("receipt_type") or "") != "fiscal_check":
            continue
        tax_url = build_public_receipt_url(row) or ""
        if tax_url:
            buttons.append(ButtonModel(action="billing:receipt", text="Відкрити чек", url=tax_url))
            break
    buttons.append(ButtonModel(action=BILLING_CLOSE_ACTION, text="Закрити"))
    return buttons


def build_receipt_documents(
    receipts: list[dict[str, Any]],
    *,
    billing_receipt_storage_provider: BillingReceiptStorageProvider,
) -> list[DocumentAttachmentModel]:
    documents: list[DocumentAttachmentModel] = []
    for row in receipts:
        if str(row.get("receipt_type") or "") != "fiscal_check":
            continue
        file_base64 = str(row.get("file_base64") or "").strip()
        if not file_base64:
            continue
        artifact = write_receipt_file(
            receipt_id=int(row["id"]),
            file_base64=file_base64,
            billing_receipt_storage_provider=billing_receipt_storage_provider,
        )
        if artifact is None:
            continue
        documents.append(
            DocumentAttachmentModel(
                path=artifact.path,
                filename=artifact.filename,
                caption="Чек оплати",
            )
        )
    return documents


def build_public_checkbox_check_url(row: dict[str, Any]) -> str | None:
    if str(row.get("receipt_type") or "fiscal_check") != "fiscal_check":
        return None
    if str(row.get("fiscalizationSource") or row.get("fiscalization_source") or "").strip().lower() != "checkbox":
        return None
    provider_check_id = str(row.get("provider_check_id") or "").strip()
    if not provider_check_id and "fiscalizationSource" in row:
        provider_check_id = str(row.get("id") or "").strip()
    if not provider_check_id:
        return None
    return f"{CHECKBOX_PUBLIC_CHECK_BASE_URL}/{provider_check_id}"


def build_public_receipt_url(row: dict[str, Any]) -> str | None:
    checkbox_url = build_public_checkbox_check_url(row)
    if checkbox_url:
        return checkbox_url
    if str(row.get("status") or "") != "done":
        return None
    tax_url = str(row.get("tax_url") or "").strip()
    if not tax_url or is_tax_cabinet_url(tax_url):
        return None
    return tax_url


def is_tax_cabinet_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.hostname == "cabinet.tax.gov.ua"


def write_receipt_file(
    *,
    receipt_id: int,
    file_base64: str,
    billing_receipt_storage_provider: BillingReceiptStorageProvider,
) -> BillingReceiptArtifactRef | None:
    payload = decode_receipt_file_base64(file_base64)
    if payload is None:
        return None
    return billing_receipt_storage_provider.write_receipt_file(
        receipt_id=receipt_id,
        payload=payload,
    )


def receipt_file_base64_is_valid(file_base64: str) -> bool:
    return decode_receipt_file_base64(file_base64) is not None


def decode_receipt_file_base64(file_base64: str) -> bytes | None:
    try:
        payload = base64.b64decode(file_base64, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not payload:
        return None
    return payload


def normalize_receipt_status(value: Any) -> str:
    status = str(value or "").strip()
    return status if status in {"new", "process", "done", "failed"} else "unavailable"


def receipt_delivery_status(*, queue_delivery: bool, tax_url: str, file_base64: str = "") -> str | None:
    if not tax_url and not file_base64:
        return None
    if tax_url:
        return "sent"
    return "queued" if queue_delivery else "sent"


def build_receipt_retry_description(summary: dict[str, Any]) -> str:
    return (
        "Retried billing receipt retrieval: "
        f"checked={summary.get('checked_count', 0)}, "
        f"done={summary.get('done_count', 0)}, "
        f"pending={summary.get('pending_count', 0)}, "
        f"exhausted={summary.get('exhausted_count', 0)}, "
        f"errors={summary.get('error_count', 0)}."
    )


def format_amount_uah(amount_minor: int) -> str:
    hryvnias = amount_minor // 100
    kopiykas = amount_minor % 100
    if kopiykas:
        return f"{hryvnias},{kopiykas:02d} грн"
    return f"{hryvnias} грн"


def is_test_payment(payment: dict[str, Any]) -> bool:
    return str(payment.get("provider_mode") or "") == "test"


def is_monobank_test_payment(payment: dict[str, Any]) -> bool:
    provider = str(payment.get("provider") or "").strip() or BILLING_PROVIDER_MONOBANK
    return is_test_payment(payment) and provider == BILLING_PROVIDER_MONOBANK
