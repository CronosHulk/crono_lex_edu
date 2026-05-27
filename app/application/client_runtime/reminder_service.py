from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.contracts import ReminderScreenModel


class ClientRuntimeReminderService:
    def __init__(
        self,
        reminder_dispatch_service: Any,
        *,
        dispatch_lock: Callable[[str], AbstractContextManager[bool]],
    ) -> None:
        self.reminder_dispatch_service = reminder_dispatch_service
        self.dispatch_lock = dispatch_lock

    def dispatch_due_reminders(self) -> list[ReminderScreenModel]:
        with self.dispatch_lock("reminders") as acquired:
            if not acquired:
                return []
            return self.reminder_dispatch_service.dispatch_due_reminders()
