from __future__ import annotations

from app.application.dispatch_lock import DispatchLock


def test_dispatch_lock_always_allows_named_work() -> None:
    dispatch_lock = DispatchLock()

    with dispatch_lock("reminders") as acquired:
        assert acquired is True

    with dispatch_lock("user_import_attribute_build:42") as acquired:
        assert acquired is True
