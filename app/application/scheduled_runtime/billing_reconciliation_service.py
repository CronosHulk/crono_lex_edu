from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class BillingReconciliationRuntimeService:
    def __init__(
        self,
        reconciliation_service: Any,
        notification_service: Any,
        *,
        dispatch_lock: Callable[[str], AbstractContextManager[bool]],
    ) -> None:
        self.reconciliation_service = reconciliation_service
        self.notification_service = notification_service
        self.dispatch_lock = dispatch_lock

    def process_due_billing_reconciliation(self) -> dict[str, Any]:
        with self.dispatch_lock("billing_reconciliation") as acquired:
            if not acquired:
                return {}
            return {
                "non_terminal_reconciliation": self.reconciliation_service.process_non_terminal_payments(),
                "subscription_recovery": self.reconciliation_service.process_due_internal_recovery(),
                "success_recheck": self.reconciliation_service.process_due_success_recheck(),
                "receipt_retry": self.notification_service.process_due_receipt_retries(),
            }
