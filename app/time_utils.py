from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_project_datetime(value: datetime | None, timezone_name: str = "Europe/Kyiv") -> str:
    if value is None:
        return "-"
    zoneinfo = ZoneInfo(timezone_name)
    if value.tzinfo is None:
        localized = value.replace(tzinfo=zoneinfo)
    else:
        localized = value.astimezone(zoneinfo)
    return localized.strftime(DATETIME_FORMAT)


def round_datetime_up_to_minutes(value: datetime, interval_minutes: int) -> datetime:
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be greater than zero")
    if value.second or value.microsecond:
        value = value.replace(second=0, microsecond=0) + timedelta(minutes=1)
    remainder = value.minute % interval_minutes
    if remainder == 0:
        return value
    return value + timedelta(minutes=interval_minutes - remainder)


def build_schedule_datetime(current_time: datetime, target_date: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(target_date, time(hour=hour, minute=minute), tzinfo=current_time.tzinfo)


@dataclass(frozen=True)
class TimeService:
    timezone_name: str

    @property
    def zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def now(self) -> datetime:
        return datetime.now(self.zoneinfo)

    def format_datetime(self, value: datetime | None) -> str:
        return format_project_datetime(value, self.timezone_name)
