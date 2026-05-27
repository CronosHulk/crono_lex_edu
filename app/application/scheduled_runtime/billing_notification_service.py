from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class BillingNotificationRuntimeService:
    def __init__(
        self,
        notification_service: Any,
        *,
        dispatch_lock: Callable[[str], AbstractContextManager[bool]],
    ) -> None:
        self.notification_service = notification_service
        self.dispatch_lock = dispatch_lock

    def dispatch_due_billing_notifications(self) -> list[Any]:
        with self.dispatch_lock("billing_notifications") as acquired:
            if not acquired:
                return []
            return self.notification_service.dispatch_due_billing_notifications()
