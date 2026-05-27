from __future__ import annotations

from datetime import datetime, timedelta

from app.user_import.services.retry_schedule import build_user_import_next_retry_at
from app.user_import.settings import USER_IMPORT_RETRY_DELAYS_SECONDS


def test_build_user_import_next_retry_at_uses_retry_delay_by_count() -> None:
    current_time = datetime(2026, 5, 19, 12, 0, 0)

    assert build_user_import_next_retry_at(current_time, 1) == current_time + timedelta(
        seconds=USER_IMPORT_RETRY_DELAYS_SECONDS[0]
    )
    assert build_user_import_next_retry_at(current_time, 2) == current_time + timedelta(
        seconds=USER_IMPORT_RETRY_DELAYS_SECONDS[1]
    )


def test_build_user_import_next_retry_at_returns_none_outside_policy() -> None:
    current_time = datetime(2026, 5, 19, 12, 0, 0)

    assert build_user_import_next_retry_at(current_time, 0) is None
    assert build_user_import_next_retry_at(current_time, -1) is None
    assert build_user_import_next_retry_at(
        current_time,
        len(USER_IMPORT_RETRY_DELAYS_SECONDS) + 1,
    ) is None
