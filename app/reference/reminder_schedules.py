from __future__ import annotations

from typing import Any

REMINDER_HOURS = tuple(range(7, 23))
REMINDER_MINUTES = (0, 30)
REMINDER_WEEKDAYS = tuple(range(7))
REMINDER_STATUSES = ("enabled", "disabled")
MAX_REMINDERS_PER_WEEKDAY = 4


def normalize_reminder_schedule(rows: list[dict[str, Any]] | None) -> list[dict[str, int | str]]:
    normalized: list[dict[str, int | str]] = []
    seen: set[tuple[int, int]] = set()
    per_day_counts: dict[int, int] = {}
    for row in rows or []:
        weekday = int(row.get("weekday"))
        hour = int(row.get("hour"))
        minute = int(row.get("minute") or 0)
        status = str(row.get("status") or "enabled")
        title = str(row.get("title") or "").strip()
        if weekday not in REMINDER_WEEKDAYS:
            raise ValueError("weekday must be from 0 to 6")
        if hour not in REMINDER_HOURS:
            raise ValueError("hour must be from 7 to 22")
        if minute not in REMINDER_MINUTES:
            raise ValueError("minute must be 0 or 30")
        if status not in REMINDER_STATUSES:
            raise ValueError("status must be enabled or disabled")
        key = (weekday, hour, minute)
        if key in seen:
            raise ValueError("duplicate reminder schedule row")
        seen.add(key)
        per_day_counts[weekday] = per_day_counts.get(weekday, 0) + 1
        if per_day_counts[weekday] > MAX_REMINDERS_PER_WEEKDAY:
            raise ValueError("maximum 4 reminders per weekday")
        payload: dict[str, int | str] = {"weekday": weekday, "hour": hour, "minute": minute, "status": status}
        if title:
            payload["title"] = title[:80]
        normalized.append(payload)
    return sorted(normalized, key=lambda item: (int(item["weekday"]), int(item["hour"]), int(item["minute"])))


def enabled_reminder_rows(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [row for row in rows or [] if row.get("status") == "enabled"]


def first_enabled_reminder_hour(rows: list[dict[str, Any]] | None) -> int | None:
    enabled = enabled_reminder_rows(rows)
    if not enabled:
        return None
    return int(sorted(enabled, key=lambda item: (int(item["weekday"]), int(item["hour"])))[0]["hour"])


def enabled_reminder_weekdays(rows: list[dict[str, Any]] | None) -> list[int]:
    return sorted({int(row["weekday"]) for row in enabled_reminder_rows(rows)})
