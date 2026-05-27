from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

UPCOMING_REMINDER_WINDOW = timedelta(hours=2)
UPCOMING_REMINDER_STATUSES = {"pending", "sent"}


def is_actionable_upcoming_reminder(
    schedule: dict[str, Any],
    current_time: datetime,
    *,
    window: timedelta = UPCOMING_REMINDER_WINDOW,
) -> bool:
    scheduled_for = schedule.get("scheduled_for")
    if not isinstance(scheduled_for, datetime):
        return False
    if scheduled_for.date() != current_time.date():
        return False
    if str(schedule.get("status") or "pending") not in UPCOMING_REMINDER_STATUSES:
        return False
    return current_time <= scheduled_for <= current_time + window
