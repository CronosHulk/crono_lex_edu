from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

import pytest

from app.data_access.error_logs import ErrorLogRepository
from app.data_access.filtering import normalize_filter_values
from app.models import ErrorLog


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, scalars_rows=None, scalar_values=None) -> None:
        self.scalars_rows = list(scalars_rows or [])
        self.scalar_values = list(scalar_values or [])
        self.added = []

    def add(self, row) -> None:
        self.added.append(row)

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        return FakeScalarsResult(self.scalars_rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_normalize_filter_values_splits_deduplicates_and_ignores_blank_values() -> None:
    assert normalize_filter_values(None) == []
    assert normalize_filter_values(" warn, fatal, warn, ") == ["warn", "fatal"]
    assert normalize_filter_values(("debug", "debug", "fatal")) == ["debug", "fatal"]


def test_create_rejects_unknown_level() -> None:
    repository = ErrorLogRepository(FakeSessionManager(FakeSession()))

    with pytest.raises(ValueError, match="Unsupported error level"):
        repository.create("info", "text")


def test_create_persists_context_and_joins_iterable_text() -> None:
    session = FakeSession()
    repository = ErrorLogRepository(FakeSessionManager(session))

    repository.create("WARN", ["route=/x", "boom"], context_json={"task_log_id": 7})

    assert len(session.added) == 1
    assert session.added[0].level == "warn"
    assert session.added[0].text == "route=/x\nboom"
    assert session.added[0].context_json == {"task_log_id": 7}


def test_list_admin_returns_paginated_rows() -> None:
    row = ErrorLog(
        id=5,
        level="warn",
        text="task failed",
        context_json={"task_log_id": 13},
        created=datetime(2026, 5, 6, 10, 2, 0),
    )
    repository = ErrorLogRepository(FakeSessionManager(FakeSession(scalars_rows=[row], scalar_values=[1])))

    payload = repository.list_admin(page=1, page_size=50, level=["warn"], search="task")

    assert payload["total"] == 1
    assert payload["pages"] == 1
    assert payload["items"][0]["id"] == 5
    assert payload["items"][0]["context_json"] == {"task_log_id": 13}


def test_get_filter_metadata_returns_known_levels() -> None:
    repository = ErrorLogRepository(FakeSessionManager(FakeSession(scalars_rows=["debug", "fatal", None])))

    payload = repository.get_filter_metadata()

    assert payload["entity"] == "error_log"
    assert payload["filters"][1]["options"] == [
        {"value": "debug", "label": "debug"},
        {"value": "fatal", "label": "fatal"},
    ]
