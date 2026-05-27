from __future__ import annotations

from calendar import monthrange
from datetime import datetime


def add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + int(months)
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
