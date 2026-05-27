from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

import pytest

from app.application.scheduled_runtime.user_import_service import (
    UserImportScheduledRuntimeService,
)


class FakeDispatchLock:
    def __init__(self, *, acquired: bool = True) -> None:
        self.acquired = acquired
        self.names: list[str] = []

    @contextmanager
    def __call__(self, name: str):
        self.names.append(name)
        yield self.acquired


class FakeUserImportRuntimeService:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.attribute_queue_calls: list[datetime] = []

    def process_due_user_vocabulary_imports(self) -> list[dict[str, str]]:
        self.calls.append("process_due_user_vocabulary_imports")
        return [{"kind": "user_imports"}]

    def process_due_post_upgrade_rescans(self) -> list[dict[str, str]]:
        self.calls.append("process_due_post_upgrade_rescans")
        return [{"kind": "post_upgrade_rescans"}]

    def process_due_bound_google_doc_syncs(self) -> list[dict[str, str]]:
        self.calls.append("process_due_bound_google_doc_syncs")
        return [{"kind": "bound_google_doc_syncs"}]

    def process_due_import_scheduler_tick(self) -> list[dict[str, str]]:
        self.calls.append("process_due_import_scheduler_tick")
        return [{"kind": "import_scheduler"}]

    def process_user_import_attribute_queue_now(self, current_time: datetime) -> None:
        self.attribute_queue_calls.append(current_time)


SCHEDULED_RUNTIME_CASES = [
    (
        "process_due_user_vocabulary_imports",
        "user_imports",
        [{"kind": "user_imports"}],
    ),
    (
        "process_due_post_upgrade_rescans",
        "post_upgrade_rescans",
        [{"kind": "post_upgrade_rescans"}],
    ),
    (
        "process_due_bound_google_doc_syncs",
        "bound_google_doc_syncs",
        [{"kind": "bound_google_doc_syncs"}],
    ),
    (
        "process_due_import_scheduler_tick",
        "import_scheduler",
        [{"kind": "import_scheduler"}],
    ),
]


@pytest.mark.parametrize(("method_name", "lock_name", "expected"), SCHEDULED_RUNTIME_CASES)
def test_user_import_scheduled_runtime_runs_under_dispatch_lock(
    method_name: str,
    lock_name: str,
    expected: list[dict[str, str]],
) -> None:
    dispatch_lock = FakeDispatchLock()
    user_import_runtime_service = FakeUserImportRuntimeService()
    runtime_service = UserImportScheduledRuntimeService(
        user_import_runtime_service,
        dispatch_lock=dispatch_lock,
    )

    result = getattr(runtime_service, method_name)()

    assert result == expected
    assert dispatch_lock.names == [lock_name]
    assert user_import_runtime_service.calls == [method_name]


@pytest.mark.parametrize(("method_name", "lock_name", "_expected"), SCHEDULED_RUNTIME_CASES)
def test_user_import_scheduled_runtime_returns_empty_when_dispatch_lock_is_busy(
    method_name: str,
    lock_name: str,
    _expected: list[dict[str, str]],
) -> None:
    dispatch_lock = FakeDispatchLock(acquired=False)
    user_import_runtime_service = FakeUserImportRuntimeService()
    runtime_service = UserImportScheduledRuntimeService(
        user_import_runtime_service,
        dispatch_lock=dispatch_lock,
    )

    result = getattr(runtime_service, method_name)()

    assert result == []
    assert dispatch_lock.names == [lock_name]
    assert user_import_runtime_service.calls == []


def test_user_import_scheduled_runtime_processes_attribute_queue_under_user_scoped_lock() -> None:
    dispatch_lock = FakeDispatchLock()
    user_import_runtime_service = FakeUserImportRuntimeService()
    runtime_service = UserImportScheduledRuntimeService(
        user_import_runtime_service,
        dispatch_lock=dispatch_lock,
    )
    current_time = datetime(2026, 5, 1, 9, 0, 0)

    result = runtime_service.process_user_import_attribute_queue_now(42, current_time)

    assert result is None
    assert dispatch_lock.names == ["user_import_attribute_build:42"]
    assert user_import_runtime_service.attribute_queue_calls == [current_time]


def test_user_import_scheduled_runtime_skips_attribute_queue_when_user_lock_is_busy() -> None:
    dispatch_lock = FakeDispatchLock(acquired=False)
    user_import_runtime_service = FakeUserImportRuntimeService()
    runtime_service = UserImportScheduledRuntimeService(
        user_import_runtime_service,
        dispatch_lock=dispatch_lock,
    )

    result = runtime_service.process_user_import_attribute_queue_now(
        42,
        datetime(2026, 5, 1, 9, 0, 0),
    )

    assert result is None
    assert dispatch_lock.names == ["user_import_attribute_build:42"]
    assert user_import_runtime_service.attribute_queue_calls == []
