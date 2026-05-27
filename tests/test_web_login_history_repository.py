from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from app.data_access.web_login_history import WebLoginHistoryRepository
from app.models import WebLoginHistory

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


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
        self.flushed = False

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True

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


def make_history(**overrides) -> WebLoginHistory:
    values = {
        "id": 11,
        "user_uuid": USER_UUID,
        "username_attempted": "admin",
        "interface_context": "admin_web",
        "event_type": "magic_login",
        "result": "success",
        "api_origin": "https://cronolex.local",
        "api_path": "/api/v1/admin/auth",
        "client_ip": "127.0.0.1",
        "user_agent": "pytest",
        "device_fingerprint_hash": "hash",
        "details_json": {"ok": True},
        "created": datetime(2026, 5, 6, 10, 0, 0),
    }
    values.update(overrides)
    return WebLoginHistory(**values)


def test_create_persists_defaults_and_payload() -> None:
    current_time = datetime(2026, 5, 6, 10, 0, 0)
    session = FakeSession()
    repository = WebLoginHistoryRepository(FakeSessionManager(session))

    payload = repository.create(
        telegram_user_id=42,
        username_attempted="admin",
        interface_context="admin_web",
        event_type="magic_login",
        result="success",
        api_origin="https://cronolex.local",
        api_path="/login",
        client_ip="127.0.0.1",
        user_agent="pytest",
        device_fingerprint_hash="hash",
        current_time=current_time,
    )

    assert session.flushed is True
    assert session.added[0].details_json == {}
    assert session.added[0].created == current_time
    assert payload["details_json"] == {}


def test_list_admin_returns_paginated_rows_with_filters() -> None:
    repository = WebLoginHistoryRepository(
        FakeSessionManager(FakeSession(scalars_rows=[make_history(details_json=None)], scalar_values=[1]))
    )

    payload = repository.list_admin(
        page=1,
        page_size=50,
        user_id=str(USER_UUID),
        interface_context="admin_web,admin_bot",
        result=["success"],
        api_origin=" CRONOLEX ",
    )

    assert payload["total"] == 1
    assert payload["pages"] == 1
    assert payload["items"][0]["id"] == 11
    assert payload["items"][0]["details_json"] == {}


def test_list_latest_for_user_clamps_limit_and_returns_rows() -> None:
    repository = WebLoginHistoryRepository(FakeSessionManager(FakeSession(scalars_rows=[make_history()])))

    assert repository.list_latest_for_user(str(USER_UUID), limit=500)[0]["id"] == 11
    assert repository.list_latest_for_user(str(USER_UUID), limit=0)[0]["id"] == 11
