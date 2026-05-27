from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import UUID

import pytest

from app.data_access.admin_auth import (
    AdminAuthRepository,
    admin_bot_restore_to_dict,
    admin_credential_to_dict,
    admin_magic_link_to_dict,
    admin_otp_challenge_to_dict,
    admin_session_to_dict,
)
from app.models import (
    AdminBotRestore,
    AdminCredential,
    AdminMagicLink,
    AdminOtpChallenge,
    AdminSession,
    User,
)

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


class FakeResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_id=None, scalar_values=None, scalars_rows=None) -> None:
        self.row_by_id = row_by_id or {}
        self.scalar_values = list(scalar_values or [])
        self.scalars_rows = list(scalars_rows or [])
        self.added = []
        self.flushed = False

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True

    def get(self, model, primary_key):
        return self.row_by_id.get((model, primary_key), self.row_by_id.get(primary_key))

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        return FakeResult(self.scalars_rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_user(**overrides) -> User:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "uuid": USER_UUID,
        "telegram_user_id": 42,
        "username": "admin",
        "first_name": "Admin",
        "status": "inactive",
        "acl_group_id": 1,
        "interface_locale": "uk",
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return User(**values)


def make_credential(**overrides) -> AdminCredential:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {"user_uuid": USER_UUID, "password_hash": "hash", "created": now, "updated": now}
    values.update(overrides)
    return AdminCredential(**values)


def make_otp(**overrides) -> AdminOtpChallenge:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "id": 501,
        "user_uuid": USER_UUID,
        "otp_hash": "otp",
        "attempts_count": 0,
        "sent_chat_id": 1001,
        "sent_message_id": None,
        "previous_screen_id": "menu",
        "expires": now + timedelta(minutes=5),
        "consumed": None,
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return AdminOtpChallenge(**values)


def make_magic_link(**overrides) -> AdminMagicLink:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "id": 601,
        "user_uuid": USER_UUID,
        "token_hash": "token",
        "target_path": "/admin",
        "expires": now + timedelta(minutes=15),
        "consumed": None,
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return AdminMagicLink(**values)


def make_session(**overrides) -> AdminSession:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "id": 701,
        "user_uuid": USER_UUID,
        "session_token_hash": "session",
        "expires": now + timedelta(hours=12),
        "revoked": None,
        "api_origin": "admin",
        "client_ip": "127.0.0.1",
        "user_agent": "pytest",
        "device_fingerprint_hash": "device",
        "created": now,
        "updated": now,
        "last_seen": now,
    }
    values.update(overrides)
    return AdminSession(**values)


def make_restore(**overrides) -> AdminBotRestore:
    now = datetime(2026, 4, 6, 10, 0, 0)
    values = {
        "id": 801,
        "user_uuid": USER_UUID,
        "chat_id": 1001,
        "previous_screen_id": "menu",
        "status": "queued",
        "scheduled_for": now,
        "sent": None,
        "error_text": None,
        "created": now,
        "updated": now,
    }
    values.update(overrides)
    return AdminBotRestore(**values)


def test_serializers_return_expected_payloads() -> None:
    assert admin_credential_to_dict(make_credential())["password_hash"] == "hash"
    assert admin_otp_challenge_to_dict(make_otp())["previous_screen_id"] == "menu"
    assert admin_magic_link_to_dict(make_magic_link())["target_path"] == "/admin"
    assert admin_session_to_dict(make_session())["device_fingerprint_hash"] == "device"
    assert admin_bot_restore_to_dict(make_restore())["chat_id"] == 1001


def test_ensure_dev_admin_user_creates_or_updates_user_and_credential() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    missing_session = FakeSession(scalar_values=[None])
    repository = AdminAuthRepository(FakeSessionManager(missing_session))

    with pytest.raises(ValueError):
        repository.ensure_dev_admin_user(current_time=current_time)

    create_session = FakeSession(scalar_values=[7, None])
    repository = AdminAuthRepository(FakeSessionManager(create_session))
    payload = repository.ensure_dev_admin_user(current_time=current_time)

    assert payload["telegram_user_id"] == 999_000_001
    assert [type(row).__name__ for row in create_session.added] == ["User", "AdminCredential"]
    assert create_session.flushed is True

    user = make_user(telegram_user_id=99, status="blocked", acl_group_id=2)
    update_session = FakeSession(
        row_by_id={(AdminCredential, USER_UUID): make_credential()},
        scalar_values=[7, user],
    )
    repository = AdminAuthRepository(FakeSessionManager(update_session))
    payload = repository.ensure_dev_admin_user(current_time=current_time)

    assert payload["telegram_user_id"] == 99
    assert user.acl_group_id == 7
    assert user.status == "active"
    assert update_session.added == []


def test_credentials_can_be_read_and_upserted() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    credential = make_credential()
    session = FakeSession(row_by_id={(User, 42): make_user(), (AdminCredential, USER_UUID): credential})
    repository = AdminAuthRepository(FakeSessionManager(session))

    assert repository.get_credential(42)["password_hash"] == "hash"
    assert repository.get_credential(404) is None
    repository.set_password_hash(42, "new", current_time=current_time)
    assert credential.password_hash == "new"
    assert credential.updated == current_time

    create_session = FakeSession(row_by_id={(User, 77): make_user(telegram_user_id=77)})
    repository = AdminAuthRepository(FakeSessionManager(create_session))
    repository.set_password_hash(77, "created", current_time=current_time)
    assert create_session.added[0].user_uuid == USER_UUID
    assert create_session.added[0].password_hash == "created"


def test_otp_challenge_lifecycle() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    row = make_otp()
    session = FakeSession(row_by_id={(User, 42): make_user(), (AdminOtpChallenge, 501): row})
    repository = AdminAuthRepository(FakeSessionManager(session))

    created = repository.create_otp_challenge(
        telegram_user_id=42,
        otp_hash="new",
        expires=current_time + timedelta(minutes=5),
        previous_screen_id="settings",
        sent_chat_id=1001,
        current_time=current_time,
    )
    assert created["otp_hash"] == "new"
    assert session.added[-1].previous_screen_id == "settings"
    assert session.flushed is True

    repository.save_otp_message_id(501, 9001, current_time=current_time)
    assert row.sent_message_id == 9001
    assert repository.get_otp_challenge(501)["id"] == 501
    assert repository.get_otp_challenge(404) is None
    repository.increment_otp_attempts(501, current_time=current_time)
    assert row.attempts_count == 1
    repository.consume_otp_challenge(501, current_time=current_time)
    assert row.consumed == current_time

    repository.save_otp_message_id(404, 1, current_time=current_time)
    repository.increment_otp_attempts(404, current_time=current_time)
    repository.consume_otp_challenge(404, current_time=current_time)


def test_magic_link_lifecycle() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    row = make_magic_link()
    session = FakeSession(row_by_id={(User, 42): make_user(), (AdminMagicLink, 601): row}, scalar_values=[row, None])
    repository = AdminAuthRepository(FakeSessionManager(session))

    created = repository.create_magic_link(
        telegram_user_id=42,
        token_hash="new-token",
        target_path="/admin/users",
        expires=current_time + timedelta(minutes=15),
        current_time=current_time,
    )
    assert created["target_path"] == "/admin/users"
    assert session.flushed is True
    assert repository.get_active_magic_link_by_token_hash("token", current_time=current_time)["id"] == 601
    assert repository.get_active_magic_link_by_token_hash("missing", current_time=current_time) is None

    repository.consume_magic_link(601, current_time=current_time)
    assert row.consumed == current_time
    repository.consume_magic_link(601, current_time=current_time + timedelta(minutes=1))
    assert row.consumed == current_time
    repository.consume_magic_link(404, current_time=current_time)


def test_admin_session_lifecycle_and_token_matching() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    active = make_session()
    revoked = make_session(id=702, session_token_hash="revoked", revoked=current_time)
    session = FakeSession(
        row_by_id={(User, 42): make_user(), (AdminSession, 701): active, (AdminSession, 702): revoked},
        scalars_rows=[active, revoked],
    )
    repository = AdminAuthRepository(FakeSessionManager(session))

    created = repository.create_session(
        telegram_user_id=42,
        session_token_hash="new-session",
        expires=current_time + timedelta(hours=12),
        api_origin="admin",
        client_ip="ip",
        user_agent="agent",
        device_fingerprint_hash="device",
        current_time=current_time,
    )
    assert created["session_token_hash"] == "new-session"
    assert session.flushed is True

    assert repository.get_active_session_by_token_hash(
        token_hash_matcher=lambda value: value == "session",
        current_time=current_time,
    )["id"] == 701
    assert repository.get_active_session_by_token_hash(
        token_hash_matcher=lambda value: value == "missing",
        current_time=current_time,
    ) is None

    repository.touch_session(701, current_time=current_time)
    assert active.last_seen == current_time
    repository.touch_session(702, current_time=current_time + timedelta(minutes=1))
    assert revoked.last_seen != current_time + timedelta(minutes=1)
    repository.touch_session(404, current_time=current_time)

    repository.revoke_session(701, current_time=current_time)
    assert active.revoked == current_time
    repository.revoke_session(702, current_time=current_time + timedelta(minutes=1))
    assert revoked.revoked == current_time
    repository.revoke_session(404, current_time=current_time)

    active.revoked = None
    repository.revoke_session_by_token_match(
        token_hash_matcher=lambda value: value == "session",
        current_time=current_time,
    )
    assert active.revoked == current_time
    repository.revoke_session_by_token_match(
        token_hash_matcher=lambda value: value == "missing",
        current_time=current_time,
    )


def test_admin_bot_restore_lifecycle() -> None:
    current_time = datetime(2026, 4, 6, 11, 0, 0)
    first = make_restore(id=1)
    second = make_restore(id=2)
    session = FakeSession(row_by_id={(User, 42): make_user(), (AdminBotRestore, 1): first}, scalars_rows=[first, second])
    repository = AdminAuthRepository(FakeSessionManager(session))

    created = repository.schedule_bot_restore(
        telegram_user_id=42,
        chat_id=1001,
        previous_screen_id="settings",
        scheduled_for=current_time,
        current_time=current_time,
    )
    assert created["previous_screen_id"] == "settings"
    assert session.flushed is True

    claimed = repository.claim_due_bot_restores(current_time=current_time, limit=10)
    assert [row["id"] for row in claimed] == [1, 2]
    assert first.status == "sent"
    assert first.sent == current_time

    repository.mark_bot_restore_failed(1, error_text="x" * 1200, current_time=current_time)
    assert first.status == "error"
    assert len(first.error_text) == 1000
    repository.mark_bot_restore_failed(404, error_text="missing", current_time=current_time)
