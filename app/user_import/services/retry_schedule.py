from __future__ import annotations

from datetime import datetime, timedelta

from app.user_import.settings import USER_IMPORT_RETRY_DELAYS_SECONDS


def build_user_import_next_retry_at(
    current_time: datetime,
    retry_count: int,
) -> datetime | None:
    if retry_count <= 0 or retry_count > len(USER_IMPORT_RETRY_DELAYS_SECONDS):
        return None
    return current_time + timedelta(seconds=USER_IMPORT_RETRY_DELAYS_SECONDS[retry_count - 1])
