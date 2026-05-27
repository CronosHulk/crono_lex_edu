from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.data_access.admin_users import admin_user_to_dict
from app.data_access.user_identity import get_user_by_telegram_id, get_user_uuid_by_telegram_id
from app.models import (
    AclGroup,
    AdminBotRestore,
    AdminCredential,
    AdminMagicLink,
    AdminOtpChallenge,
    AdminSession,
    User,
)
from app.orm import SessionManager


def admin_credential_to_dict(row: AdminCredential) -> dict[str, Any]:
    user_uuid = str(row.user_uuid)
    return {
        "user_id": user_uuid,
        "user_uuid": user_uuid,
        "telegram_user_id": getattr(getattr(row, "user", None), "telegram_user_id", None),
        "password_hash": row.password_hash,
        "created": row.created,
        "updated": row.updated,
    }


def admin_otp_challenge_to_dict(row: AdminOtpChallenge) -> dict[str, Any]:
    user_uuid = str(row.user_uuid)
    return {
        "id": row.id,
        "user_id": user_uuid,
        "user_uuid": user_uuid,
        "telegram_user_id": getattr(getattr(row, "user", None), "telegram_user_id", None),
        "otp_hash": row.otp_hash,
        "attempts_count": row.attempts_count,
        "sent_chat_id": row.sent_chat_id,
        "sent_message_id": row.sent_message_id,
        "previous_screen_id": row.previous_screen_id,
        "expires": row.expires,
        "consumed": row.consumed,
        "created": row.created,
        "updated": row.updated,
    }


def admin_magic_link_to_dict(row: AdminMagicLink) -> dict[str, Any]:
    user_uuid = str(row.user_uuid)
    return {
        "id": row.id,
        "user_id": user_uuid,
        "user_uuid": user_uuid,
        "telegram_user_id": getattr(getattr(row, "user", None), "telegram_user_id", None),
        "token_hash": row.token_hash,
        "target_path": row.target_path,
        "expires": row.expires,
        "consumed": row.consumed,
        "created": row.created,
        "updated": row.updated,
    }


def admin_session_to_dict(row: AdminSession) -> dict[str, Any]:
    user_uuid = str(row.user_uuid)
    return {
        "id": row.id,
        "user_id": user_uuid,
        "user_uuid": user_uuid,
        "telegram_user_id": getattr(getattr(row, "user", None), "telegram_user_id", None),
        "session_token_hash": row.session_token_hash,
        "expires": row.expires,
        "revoked": row.revoked,
        "api_origin": row.api_origin,
        "client_ip": row.client_ip,
        "user_agent": row.user_agent,
        "device_fingerprint_hash": row.device_fingerprint_hash,
        "created": row.created,
        "updated": row.updated,
        "last_seen": row.last_seen,
    }


def admin_bot_restore_to_dict(row: AdminBotRestore) -> dict[str, Any]:
    user_uuid = str(row.user_uuid)
    return {
        "id": row.id,
        "user_id": user_uuid,
        "user_uuid": user_uuid,
        "telegram_user_id": getattr(getattr(row, "user", None), "telegram_user_id", None),
        "chat_id": row.chat_id,
        "previous_screen_id": row.previous_screen_id,
        "status": row.status,
        "scheduled_for": row.scheduled_for,
        "sent": row.sent,
        "error_text": row.error_text,
        "created": row.created,
        "updated": row.updated,
    }


class AdminAuthRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def ensure_dev_admin_user(self, *, current_time: datetime) -> dict[str, Any]:
        with self.session_manager.session() as session:
            group_id = session.scalar(select(AclGroup.id).where(AclGroup.title == "super_admin").limit(1))
            if group_id is None:
                raise ValueError("ACL group 'super_admin' is not configured")
            user = session.scalar(select(User).where(func.lower(User.username) == "admin").limit(1))
            if user is None:
                user = User(
                    telegram_user_id=999_000_001,
                    username="admin",
                    first_name="Local Admin",
                    status="active",
                    acl_group_id=group_id,
                    interface_locale="uk",
                    created=current_time,
                    updated=current_time,
                )
                session.add(user)
            else:
                user.acl_group_id = group_id
                user.status = "active"
                user.updated = current_time
            credential = session.get(AdminCredential, user.uuid)
            if credential is None:
                session.add(AdminCredential(user_uuid=user.uuid, created=current_time))
            session.flush()
            return admin_user_to_dict(user, "super_admin")

    def get_credential(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            row = session.get(AdminCredential, user_uuid) if user_uuid is not None else None
            return admin_credential_to_dict(row) if row is not None else None

    def set_password_hash(self, telegram_user_id: int, password_hash: str, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return
            row = session.get(AdminCredential, user_uuid)
            if row is None:
                row = AdminCredential(user_uuid=user_uuid, created=current_time)
                session.add(row)
            row.password_hash = password_hash
            row.updated = current_time

    def mark_password_prompted(self, telegram_user_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            user = get_user_by_telegram_id(session, telegram_user_id)
            if user is not None:
                user.admin_web_password_prompted = True
                user.updated = current_time

    def create_otp_challenge(
        self,
        *,
        telegram_user_id: int,
        otp_hash: str,
        expires: datetime,
        previous_screen_id: str | None,
        sent_chat_id: int | None,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            row = AdminOtpChallenge(
                user_uuid=user_uuid,
                otp_hash=otp_hash,
                expires=expires,
                previous_screen_id=previous_screen_id,
                sent_chat_id=sent_chat_id,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return admin_otp_challenge_to_dict(row)

    def save_otp_message_id(self, challenge_id: int, message_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(AdminOtpChallenge, challenge_id)
            if row is not None:
                row.sent_message_id = message_id
                row.updated = current_time

    def get_otp_challenge(self, challenge_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(AdminOtpChallenge, challenge_id)
            return admin_otp_challenge_to_dict(row) if row is not None else None

    def increment_otp_attempts(self, challenge_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(AdminOtpChallenge, challenge_id)
            if row is not None:
                row.attempts_count += 1
                row.updated = current_time

    def consume_otp_challenge(self, challenge_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(AdminOtpChallenge, challenge_id)
            if row is not None:
                row.consumed = current_time
                row.updated = current_time

    def create_magic_link(
        self,
        *,
        telegram_user_id: int,
        token_hash: str,
        target_path: str,
        expires: datetime,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            row = AdminMagicLink(
                user_uuid=user_uuid,
                token_hash=token_hash,
                target_path=target_path,
                expires=expires,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return admin_magic_link_to_dict(row)

    def get_active_magic_link_by_token_hash(
        self,
        token_hash: str,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(AdminMagicLink)
                .where(
                    AdminMagicLink.token_hash == token_hash,
                    AdminMagicLink.consumed.is_(None),
                    AdminMagicLink.expires > current_time,
                )
                .limit(1)
            )
            return admin_magic_link_to_dict(row) if row is not None else None

    def consume_magic_link(self, magic_link_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(AdminMagicLink, magic_link_id)
            if row is not None and row.consumed is None:
                row.consumed = current_time
                row.updated = current_time

    def create_session(
        self,
        *,
        telegram_user_id: int,
        session_token_hash: str,
        expires: datetime,
        api_origin: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_fingerprint_hash: str | None = None,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            row = AdminSession(
                user_uuid=user_uuid,
                session_token_hash=session_token_hash,
                expires=expires,
                api_origin=api_origin,
                client_ip=client_ip,
                user_agent=user_agent,
                device_fingerprint_hash=device_fingerprint_hash,
                created=current_time,
                updated=current_time,
                last_seen=current_time,
            )
            session.add(row)
            session.flush()
            return admin_session_to_dict(row)

    def get_active_session_by_token_hash(self, *, token_hash_matcher, current_time: datetime) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(AdminSession)
                .where(AdminSession.revoked.is_(None), AdminSession.expires > current_time)
                .order_by(AdminSession.last_seen.desc().nullslast(), AdminSession.created.desc())
            ).all()
            for row in rows:
                if token_hash_matcher(row.session_token_hash):
                    return admin_session_to_dict(row)
            return None

    def touch_session(self, session_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(AdminSession, session_id)
            if row is None:
                return
            if row is not None and row.revoked is None:
                row.last_seen = current_time
            row.updated = current_time

    def revoke_session(self, session_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(AdminSession, session_id)
            if row is not None and row.revoked is None:
                row.revoked = current_time
                row.updated = current_time

    def revoke_session_by_token_match(self, *, token_hash_matcher, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            rows = session.scalars(select(AdminSession).where(AdminSession.revoked.is_(None))).all()
            for row in rows:
                if token_hash_matcher(row.session_token_hash):
                    row.revoked = current_time
                    row.updated = current_time
                    return

    def schedule_bot_restore(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        previous_screen_id: str | None,
        scheduled_for: datetime,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            row = AdminBotRestore(
                user_uuid=user_uuid,
                chat_id=chat_id,
                previous_screen_id=previous_screen_id,
                scheduled_for=scheduled_for,
                status="queued",
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return admin_bot_restore_to_dict(row)

    def claim_due_bot_restores(self, *, current_time: datetime, limit: int = 50) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(AdminBotRestore)
                .where(
                    AdminBotRestore.status == "queued",
                    AdminBotRestore.scheduled_for <= current_time,
                )
                .order_by(AdminBotRestore.scheduled_for.asc(), AdminBotRestore.id.asc())
                .limit(limit)
            ).all()
            claimed: list[dict[str, Any]] = []
            for row in rows:
                row.status = "sent"
                row.sent = current_time
                row.updated = current_time
                claimed.append(admin_bot_restore_to_dict(row))
            return claimed

    def mark_bot_restore_failed(self, restore_id: int, *, error_text: str, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(AdminBotRestore, restore_id)
            if row is None:
                return
            row.status = "error"
            row.error_text = error_text[:1000]
            row.updated = current_time
