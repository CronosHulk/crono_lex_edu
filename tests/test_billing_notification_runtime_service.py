from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from app.application.scheduled_runtime.billing_notification_service import (
    BillingNotificationRuntimeService,
)


class FakeDispatchLock:
    def __init__(self, *, acquired: bool = True) -> None:
        self.acquired = acquired
        self.names: list[str] = []

    @contextmanager
    def __call__(self, name: str):
        self.names.append(name)
        yield self.acquired


class FakeNotificationService:
    def __init__(self) -> None:
        self.calls = 0

    def dispatch_due_billing_notifications(self) -> list[dict[str, Any]]:
        self.calls += 1
        return [{"delivery_kind": "billing_bot_notification", "delivery_id": 5}]


def test_billing_notification_runtime_runs_under_dispatch_lock() -> None:
    dispatch_lock = FakeDispatchLock()
    notification_service = FakeNotificationService()
    runtime_service = BillingNotificationRuntimeService(
        notification_service,
        dispatch_lock=dispatch_lock,
    )

    result = runtime_service.dispatch_due_billing_notifications()

    assert result == [{"delivery_kind": "billing_bot_notification", "delivery_id": 5}]
    assert dispatch_lock.names == ["billing_notifications"]
    assert notification_service.calls == 1


def test_billing_notification_runtime_returns_empty_when_dispatch_lock_is_busy() -> None:
    dispatch_lock = FakeDispatchLock(acquired=False)
    notification_service = FakeNotificationService()
    runtime_service = BillingNotificationRuntimeService(
        notification_service,
        dispatch_lock=dispatch_lock,
    )

    result = runtime_service.dispatch_due_billing_notifications()

    assert result == []
    assert dispatch_lock.names == ["billing_notifications"]
    assert notification_service.calls == 0
