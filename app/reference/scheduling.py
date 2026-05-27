from __future__ import annotations

from app.i18n import translate
from app.time_utils import build_schedule_datetime

MORNING_HOURS = (8, 9, 10, 11)
DAY_HOURS = (12, 13, 14, 15, 16, 17)
EVENING_HOURS = (19, 20, 21, 22)
HOURS_BY_PERIOD = {
    "morning": MORNING_HOURS,
    "day": DAY_HOURS,
    "evening": EVENING_HOURS,
}
WEEKDAY_CODES = (0, 1, 2, 3, 4, 5, 6)
WEEKDAY_NAMES = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}

__all__ = [
    "DAY_HOURS",
    "EVENING_HOURS",
    "HOURS_BY_PERIOD",
    "MORNING_HOURS",
    "WEEKDAY_CODES",
    "WEEKDAY_NAMES",
    "build_schedule_datetime",
    "format_hour_label",
    "format_weekday_labels",
    "weekday_name",
]


def format_hour_label(hour: int) -> str:
    return f"{hour:02d}:00"


def weekday_name(weekday: int) -> str:
    return WEEKDAY_NAMES[weekday]


def format_weekday_labels(locale: str, weekdays: list[int]) -> str:
    if not weekdays:
        return translate(locale, "reminder_not_set")
    labels = [translate(locale, f"reminder_day_short_{weekday_name(code)}") for code in sorted(set(weekdays))]
    return ", ".join(labels)
