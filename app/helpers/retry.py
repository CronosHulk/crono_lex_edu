from __future__ import annotations

import time
from collections.abc import Callable

DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 2.0


def normalize_retry_attempts(value: int | None = None) -> int:
    return max(int(value or DEFAULT_RETRY_ATTEMPTS), 1)


def sleep_before_retry(
    *,
    attempt_index: int,
    attempts: int,
    delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    sleep_func: Callable[[float], None] = time.sleep,
) -> None:
    if attempt_index >= attempts - 1:
        return
    sleep_func(max(float(delay_seconds), 0.0))
