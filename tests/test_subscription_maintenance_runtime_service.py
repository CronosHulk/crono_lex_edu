from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

from app.application.scheduled_runtime.subscription_maintenance_service import (
    SubscriptionMaintenanceRuntimeService,
)


class FakeDispatchLock:
    def __init__(self, *, acquired: bool = True) -> None:
        self.acquired = acquired
        self.names: list[str] = []

    @contextmanager
    def __call__(self, name: str):
        self.names.append(name)
        yield self.acquired


class FakeMaintenanceService:
    def __init__(self) -> None:
        self.calls: list[datetime] = []

    def process_daily_maintenance(self, *, current_time: datetime) -> dict[str, object]:
        self.calls.append(current_time)
        return {"task_log_id": 77, "status": "ok"}


class FakeTimeService:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


def test_subscription_maintenance_runtime_runs_under_dispatch_lock() -> None:
    current_time = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    dispatch_lock = FakeDispatchLock()
    maintenance_service = FakeMaintenanceService()
    runtime_service = SubscriptionMaintenanceRuntimeService(
        maintenance_service,
        FakeTimeService(current_time),
        dispatch_lock=dispatch_lock,
    )

    result = runtime_service.process_due_subscription_maintenance()

    assert result == {"task_log_id": 77, "status": "ok"}
    assert dispatch_lock.names == ["subscription_maintenance"]
    assert maintenance_service.calls == [current_time]


def test_subscription_maintenance_runtime_returns_empty_when_dispatch_lock_is_busy() -> None:
    current_time = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    dispatch_lock = FakeDispatchLock(acquired=False)
    maintenance_service = FakeMaintenanceService()
    runtime_service = SubscriptionMaintenanceRuntimeService(
        maintenance_service,
        FakeTimeService(current_time),
        dispatch_lock=dispatch_lock,
    )

    result = runtime_service.process_due_subscription_maintenance()

    assert result == {}
    assert dispatch_lock.names == ["subscription_maintenance"]
    assert maintenance_service.calls == []
