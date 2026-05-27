from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from app.application.scheduled_runtime.billing_reconciliation_service import (
    BillingReconciliationRuntimeService,
)


class FakeDispatchLock:
    def __init__(self, *, acquired: bool = True) -> None:
        self.acquired = acquired
        self.names: list[str] = []

    @contextmanager
    def __call__(self, name: str):
        self.names.append(name)
        yield self.acquired


class FakeReconciliationService:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def process_non_terminal_payments(self) -> dict[str, Any]:
        self.events.append("non_terminal_reconciliation")
        return {"checked_count": 2}

    def process_due_internal_recovery(self) -> dict[str, Any]:
        self.events.append("subscription_recovery")
        return {"recovered_count": 1}

    def process_due_success_recheck(self) -> dict[str, Any]:
        self.events.append("success_recheck")
        return {"rechecked_count": 3}


class FakeNotificationService:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def process_due_receipt_retries(self) -> dict[str, Any]:
        self.events.append("receipt_retry")
        return {"retried_count": 4}


def test_billing_reconciliation_runtime_runs_under_dispatch_lock() -> None:
    events: list[str] = []
    dispatch_lock = FakeDispatchLock()
    runtime_service = BillingReconciliationRuntimeService(
        FakeReconciliationService(events),
        FakeNotificationService(events),
        dispatch_lock=dispatch_lock,
    )

    result = runtime_service.process_due_billing_reconciliation()

    assert result == {
        "non_terminal_reconciliation": {"checked_count": 2},
        "subscription_recovery": {"recovered_count": 1},
        "success_recheck": {"rechecked_count": 3},
        "receipt_retry": {"retried_count": 4},
    }
    assert dispatch_lock.names == ["billing_reconciliation"]
    assert events == [
        "non_terminal_reconciliation",
        "subscription_recovery",
        "success_recheck",
        "receipt_retry",
    ]


def test_billing_reconciliation_runtime_returns_empty_when_dispatch_lock_is_busy() -> None:
    events: list[str] = []
    dispatch_lock = FakeDispatchLock(acquired=False)
    runtime_service = BillingReconciliationRuntimeService(
        FakeReconciliationService(events),
        FakeNotificationService(events),
        dispatch_lock=dispatch_lock,
    )

    result = runtime_service.process_due_billing_reconciliation()

    assert result == {}
    assert dispatch_lock.names == ["billing_reconciliation"]
    assert events == []
