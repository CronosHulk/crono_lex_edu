from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.data_access.reminder_schedule_serialization import reminder_schedule_to_dict
from app.data_access.user_identity import get_user_by_telegram_id, get_user_uuid_by_telegram_id
from app.data_access.user_profiles import user_profile_to_dict
from app.models import (
    AclGroup,
    ClientWebCredential,
    ClientWebMagicLink,
    ClientWebOtpChallenge,
    ClientWebSession,
    LanguageLevel,
    User,
    UserLearningSettings,
    UserReminderSchedule,
    UserReminderWeekday,
)
from app.orm import SessionManager


def credential_to_dict(row: ClientWebCredential) -> dict[str, Any]:
    user_uuid = str(row.user_uuid)
    return {
        "user_id": user_uuid,
        "user_uuid": user_uuid,
        "telegram_user_id": getattr(getattr(row, "user", None), "telegram_user_id", None),
        "password_hash": row.password_hash,
        "created": row.created,
        "updated": row.updated,
    }


def otp_challenge_to_dict(row: ClientWebOtpChallenge) -> dict[str, Any]:
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
        "expires": row.expires,
        "consumed": row.consumed,
        "created": row.created,
        "updated": row.updated,
    }


def session_to_dict(row: ClientWebSession) -> dict[str, Any]:
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


def magic_link_to_dict(row: ClientWebMagicLink) -> dict[str, Any]:
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


def list_reminder_schedule_in_session(session, user_uuid) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(UserReminderSchedule)
        .where(UserReminderSchedule.user_uuid == user_uuid)
        .order_by(
            UserReminderSchedule.weekday.asc(),
            UserReminderSchedule.hour.asc(),
            UserReminderSchedule.minute.asc(),
        )
    ).all()
    return [reminder_schedule_to_dict(row) for row in rows]


class ClientWebAuthRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.execute(
                select(User, LanguageLevel, UserLearningSettings, AclGroup.title)
                .outerjoin(LanguageLevel, LanguageLevel.id == User.language_level_id)
                .outerjoin(UserLearningSettings, UserLearningSettings.user_uuid == User.uuid)
                .outerjoin(AclGroup, AclGroup.id == User.acl_group_id)
                .where(func.lower(User.username) == username.lower(), User.status == "active")
                .limit(1)
            ).first()
            if row is None:
                return None
            user, level, settings, acl_group_title = row
            weekdays = list(
                session.scalars(
                    select(UserReminderWeekday.weekday)
                    .where(UserReminderWeekday.user_uuid == user.uuid)
                    .order_by(UserReminderWeekday.weekday.asc())
                ).all()
            )
            return user_profile_to_dict(
                user,
                level,
                settings,
                acl_group_title,
                reminder_weekdays=weekdays,
                reminder_schedule=list_reminder_schedule_in_session(session, user.uuid),
            )

    def get_user_by_id(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.execute(
                select(User, LanguageLevel, UserLearningSettings, AclGroup.title)
                .outerjoin(LanguageLevel, LanguageLevel.id == User.language_level_id)
                .outerjoin(UserLearningSettings, UserLearningSettings.user_uuid == User.uuid)
                .outerjoin(AclGroup, AclGroup.id == User.acl_group_id)
                .where(User.telegram_user_id == telegram_user_id, User.status == "active")
                .limit(1)
            ).first()
            if row is None:
                return None
            user, level, settings, acl_group_title = row
            weekdays = list(
                session.scalars(
                    select(UserReminderWeekday.weekday)
                    .where(UserReminderWeekday.user_uuid == user.uuid)
                    .order_by(UserReminderWeekday.weekday.asc())
                ).all()
            )
            return user_profile_to_dict(
                user,
                level,
                settings,
                acl_group_title,
                reminder_weekdays=weekdays,
                reminder_schedule=list_reminder_schedule_in_session(session, user.uuid),
            )

    def get_credential(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            row = session.get(ClientWebCredential, user_uuid) if user_uuid is not None else None
            return credential_to_dict(row) if row is not None else None

    def set_password_hash(self, telegram_user_id: int, password_hash: str, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return
            row = session.get(ClientWebCredential, user_uuid)
            if row is None:
                row = ClientWebCredential(user_uuid=user_uuid, created=current_time)
                session.add(row)
            row.password_hash = password_hash
            row.updated = current_time

    def clear_password_hash(self, telegram_user_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            row = session.get(ClientWebCredential, user_uuid) if user_uuid is not None else None
            if row is not None:
                row.password_hash = None
                row.updated = current_time
            user = get_user_by_telegram_id(session, telegram_user_id)
            if user is not None:
                user.client_web_password_prompted = False
                user.updated = current_time

    def mark_password_prompted(self, telegram_user_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            user = get_user_by_telegram_id(session, telegram_user_id)
            if user is not None:
                user.client_web_password_prompted = True
                user.updated = current_time

    def create_otp_challenge(
        self,
        *,
        telegram_user_id: int,
        otp_hash: str,
        expires: datetime,
        sent_chat_id: int | None,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            row = ClientWebOtpChallenge(
                user_uuid=user_uuid,
                otp_hash=otp_hash,
                expires=expires,
                sent_chat_id=sent_chat_id,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return otp_challenge_to_dict(row)

    def save_otp_message_id(self, challenge_id: int, message_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(ClientWebOtpChallenge, challenge_id)
            if row is not None:
                row.sent_message_id = message_id
                row.updated = current_time

    def get_otp_challenge(self, challenge_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(ClientWebOtpChallenge, challenge_id)
            return otp_challenge_to_dict(row) if row is not None else None

    def increment_otp_attempts(self, challenge_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(ClientWebOtpChallenge, challenge_id)
            if row is not None:
                row.attempts_count += 1
                row.updated = current_time

    def consume_otp_challenge(self, challenge_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(ClientWebOtpChallenge, challenge_id)
            if row is not None:
                row.consumed = current_time
                row.updated = current_time

    def create_session(
        self,
        *,
        telegram_user_id: int,
        session_token_hash: str,
        expires: datetime,
        api_origin: str | None,
        client_ip: str | None,
        user_agent: str | None,
        device_fingerprint_hash: str | None,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
            row = ClientWebSession(
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
            return session_to_dict(row)

    def get_active_session_by_token_hash(self, *, token_hash_matcher, current_time: datetime) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            rows = session.scalars(
                select(ClientWebSession).where(ClientWebSession.revoked.is_(None), ClientWebSession.expires > current_time)
            ).all()
            for row in rows:
                if token_hash_matcher(row.session_token_hash):
                    return session_to_dict(row)
        return None

    def touch_session(self, session_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(ClientWebSession, session_id)
            if row is not None and row.revoked is None:
                row.last_seen = current_time
                row.updated = current_time

    def revoke_session(self, session_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(ClientWebSession, session_id)
            if row is not None and row.revoked is None:
                row.revoked = current_time
                row.updated = current_time

    def revoke_session_by_token_match(self, *, token_hash_matcher, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            rows = session.scalars(select(ClientWebSession).where(ClientWebSession.revoked.is_(None))).all()
            for row in rows:
                if token_hash_matcher(row.session_token_hash):
                    row.revoked = current_time
                    row.updated = current_time

    def revoke_sessions_for_user(self, telegram_user_id: int, *, current_time: datetime) -> int:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return 0
            rows = session.scalars(
                select(ClientWebSession).where(
                    ClientWebSession.user_uuid == user_uuid,
                    ClientWebSession.revoked.is_(None),
                )
            ).all()
            for row in rows:
                row.revoked = current_time
                row.updated = current_time
            return len(rows)

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
            row = ClientWebMagicLink(
                user_uuid=user_uuid,
                token_hash=token_hash,
                target_path=target_path,
                expires=expires,
                created=current_time,
                updated=current_time,
            )
            session.add(row)
            session.flush()
            return magic_link_to_dict(row)

    def get_active_magic_link_by_token_hash(self, token_hash: str, *, current_time: datetime) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(ClientWebMagicLink)
                .where(
                    ClientWebMagicLink.token_hash == token_hash,
                    ClientWebMagicLink.consumed.is_(None),
                    ClientWebMagicLink.expires > current_time,
                )
                .limit(1)
            )
            return magic_link_to_dict(row) if row is not None else None

    def get_magic_link_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.scalar(
                select(ClientWebMagicLink)
                .where(ClientWebMagicLink.token_hash == token_hash)
                .order_by(ClientWebMagicLink.created.desc(), ClientWebMagicLink.id.desc())
                .limit(1)
            )
            return magic_link_to_dict(row) if row is not None else None

    def consume_magic_link(self, magic_link_id: int, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            row = session.get(ClientWebMagicLink, magic_link_id)
            if row is not None and row.consumed is None:
                row.consumed = current_time
                row.updated = current_time
