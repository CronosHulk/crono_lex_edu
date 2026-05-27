from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from app.data_access.app_runtime_state import AppRuntimeStateRepository
from app.models import AppRuntimeState


class FakeSession:
    def __init__(self, *, row_by_key=None) -> None:
        self.row_by_key = row_by_key or {}
        self.added = []

    def get(self, model, primary_key):
        return self.row_by_key.get(primary_key)

    def add(self, row) -> None:
        self.added.append(row)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_get_returns_payload_with_empty_value_default_or_none() -> None:
    updated = datetime(2026, 5, 6, 10, 0, 0)
    row = AppRuntimeState(key="dispatch", value_json=None, updated=updated)
    repository = AppRuntimeStateRepository(FakeSessionManager(FakeSession(row_by_key={"dispatch": row})))

    assert repository.get("dispatch") == {"key": "dispatch", "value_json": {}, "updated": updated}
    assert repository.get("missing") is None


def test_set_creates_missing_state() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    session = FakeSession()
    repository = AppRuntimeStateRepository(FakeSessionManager(session))

    repository.set("dispatch", {"last_id": 7}, current_time)

    assert len(session.added) == 1
    assert session.added[0].key == "dispatch"
    assert session.added[0].value_json == {"last_id": 7}
    assert session.added[0].updated == current_time


def test_set_updates_existing_state() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    row = AppRuntimeState(key="dispatch", value_json={"last_id": 1}, updated=current_time)
    repository = AppRuntimeStateRepository(FakeSessionManager(FakeSession(row_by_key={"dispatch": row})))

    repository.set("dispatch", {"last_id": 8}, current_time)

    assert row.value_json == {"last_id": 8}
    assert row.updated == current_time
