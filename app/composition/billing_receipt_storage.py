from __future__ import annotations

from typing import Any

from app.billing.services.receipt_storage_port import BillingReceiptStorageProvider
from app.storage.billing_receipts import (
    FileSystemBillingReceiptStorageProvider,
)


def build_billing_receipt_storage_provider(
    settings: Any,
) -> BillingReceiptStorageProvider:
    return FileSystemBillingReceiptStorageProvider(
        settings.app_billing_receipt_storage_dir,
    )
