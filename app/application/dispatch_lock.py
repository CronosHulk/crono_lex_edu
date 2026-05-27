from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager


class DispatchLock:
    @contextmanager
    def __call__(self, name: str) -> Iterator[bool]:
        yield True
