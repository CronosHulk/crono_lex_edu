from __future__ import annotations

from datetime import datetime


def priority_rank_from_datetime(current_time: datetime) -> int:
    return int(current_time.timestamp())
