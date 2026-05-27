from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.time_utils import TimeService


class SubscriptionMaintenanceRuntimeService:
    def __init__(
        self,
        maintenance_service: Any,
        time_service: TimeService,
        *,
        dispatch_lock: Callable[[str], AbstractContextManager[bool]],
    ) -> None:
        self.maintenance_service = maintenance_service
        self.time_service = time_service
        self.dispatch_lock = dispatch_lock

    def process_due_subscription_maintenance(self) -> dict[str, Any]:
        with self.dispatch_lock("subscription_maintenance") as acquired:
            if not acquired:
                return {}
            return self.maintenance_service.process_daily_maintenance(
                current_time=self.time_service.now()
            )
