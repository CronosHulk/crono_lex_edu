from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.data_access.acl_permissions import AclPermissionRepository
from app.data_access.reminder_schedule_serialization import reminder_schedule_to_dict
from app.data_access.subscriptions import SubscriptionRepository
from app.data_access.user_identity import get_user_by_telegram_id
from app.helpers.locale import normalize_interface_locale
from app.models import (
    AclGroup,
    LanguageLevel,
    User,
    UserEvent,
    UserLearningSettings,
    UserReminderSchedule,
    UserReminderWeekday,
)
from app.orm import SessionManager
from app.reference.reminder_schedules import enabled_reminder_weekdays, first_enabled_reminder_hour
from app.reference.service import DEFAULT_LANGUAGE_LEVEL_TITLE


def user_profile_to_dict(
    user: User,
    level: LanguageLevel | None,
    settings: UserLearningSettings | None,
    acl_group_title: str | None,
    *,
    reminder_weekdays: list[int] | None = None,
    reminder_schedule: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    user_id = str(user.uuid) if user.uuid is not None else None
    effective_reminder_hour = first_enabled_reminder_hour(reminder_schedule)
    if effective_reminder_hour is None and settings is not None:
        effective_reminder_hour = settings.daily_reminder_hour
    payload = {
        "id": user_id,
        "user_id": user_id,
        "telegram_user_id": user.telegram_user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language_code": user.language_code,
        "interface_locale": user.interface_locale,
        "client_web_password_prompted": user.client_web_password_prompted,
        "is_premium": user.is_premium,
        "status": user.status,
        "learning_role": getattr(user, "learning_role", "student") or "student",
        "chat_id": user.chat_id,
        "chat_type": user.chat_type,
        "created": user.created,
        "updated": user.updated,
        "acl_group_title": acl_group_title,
        "language_level_id": level.id if level is not None else None,
        "language_level_title": level.title if level is not None else None,
        "words_per_session": settings.words_per_session if settings is not None else 10,
        "daily_reminder_hour": effective_reminder_hour,
        "preferred_gender": settings.preferred_gender if settings is not None else None,
        "import_google_doc_id": settings.import_google_doc_id if settings is not None else None,
        "is_import_google_doc_auto_sync_enabled": (
            settings.is_import_google_doc_auto_sync_enabled if settings is not None else False
        ),
        "import_google_doc_last_synced": settings.import_google_doc_last_synced if settings is not None else None,
        "import_google_doc_last_error": settings.import_google_doc_last_error if settings is not None else None,
        "import_google_doc_retry_count": settings.import_google_doc_retry_count if settings is not None else 0,
        "import_google_doc_next_retry_at": settings.import_google_doc_next_retry_at if settings is not None else None,
        "import_google_doc_claimed_until": settings.import_google_doc_claimed_until if settings is not None else None,
    }
    if reminder_schedule is not None:
        payload["reminder_schedule"] = reminder_schedule
    if reminder_schedule:
        reminder_weekdays = enabled_reminder_weekdays(reminder_schedule)
    if reminder_weekdays is not None:
        payload["reminder_weekdays"] = sorted(reminder_weekdays)
    return payload


class UserProfileRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def _get_or_create_settings(self, session, telegram_user_id: int) -> UserLearningSettings:
        user = get_user_by_telegram_id(session, telegram_user_id)
        if user is None or user.uuid is None:
            raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
        settings = session.get(UserLearningSettings, user.uuid)
        if settings is None:
            settings = UserLearningSettings(user_uuid=user.uuid)
            session.add(settings)
        return settings

    def _student_acl_group_id(self, session) -> int:
        group_id = session.scalar(select(AclGroup.id).where(AclGroup.title == "student").limit(1))
        if group_id is None:
            raise ValueError("ACL group 'student' is not configured")
        return int(group_id)

    def _default_language_level_id(self, session) -> int:
        level_id = session.scalar(
            select(LanguageLevel.id).where(LanguageLevel.title == DEFAULT_LANGUAGE_LEVEL_TITLE).limit(1)
        )
        if level_id is None:
            raise ValueError(f"Language level '{DEFAULT_LANGUAGE_LEVEL_TITLE}' is not configured")
        return int(level_id)

    def _resolve_acl_group_id(self, session, payload: dict[str, Any]) -> int:
        explicit_group_id = payload.get("acl_group_id")
        if explicit_group_id:
            return int(explicit_group_id)
        return self._student_acl_group_id(session)

    def upsert_user(self, payload: dict[str, Any]) -> None:
        with self.session_manager.session() as session:
            user = get_user_by_telegram_id(session, payload["telegram_user_id"])
            is_new_user = user is None
            if user is None:
                resolved_acl_group_id = self._resolve_acl_group_id(session, payload)
                language_level_id = self._default_language_level_id(session)
                interface_locale = normalize_interface_locale(payload.get("language_code"))
                user = User(
                    uuid=uuid4(),
                    telegram_user_id=payload["telegram_user_id"],
                    status="active",
                    learning_role=str(payload.get("learning_role") or "student"),
                    acl_group_id=resolved_acl_group_id,
                    language_level_id=language_level_id,
                    language_code=interface_locale,
                    interface_locale=interface_locale,
                )
                session.add(user)
                session.add(UserLearningSettings(user_uuid=user.uuid))
            elif payload.get("acl_group_id") and user.acl_group_id != int(payload["acl_group_id"]):
                user.acl_group_id = int(payload["acl_group_id"])
            for field in (
                "is_bot",
                "first_name",
                "last_name",
                "username",
                "is_premium",
                "chat_id",
                "chat_type",
                "chat_username",
                "chat_title",
            ):
                setattr(user, field, payload.get(field))
            user.raw_telegram_json = json.loads(payload["raw_telegram_json"]) if payload.get("raw_telegram_json") else None
            user.updated = func.now()
            if not is_new_user:
                self._get_or_create_settings(session, user.telegram_user_id)
            SubscriptionRepository(self.session_manager).ensure_default_for_user_in_session(
                session,
                user.uuid,
                learning_role=user.learning_role,
                current_time=datetime.now(UTC),
            )

    def save_user_event(
        self,
        telegram_user_id: int,
        event_type: str,
        raw_update_json: dict[str, Any],
        message_text: str | None = None,
        callback_data: str | None = None,
    ) -> None:
        with self.session_manager.session() as session:
            session.add(
                UserEvent(
                    telegram_user_id=telegram_user_id,
                    event_type=event_type,
                    message_text=message_text,
                    callback_data=callback_data,
                    raw_update_json=raw_update_json,
                )
            )

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.execute(
                select(User, LanguageLevel, UserLearningSettings, AclGroup.title)
                .outerjoin(LanguageLevel, LanguageLevel.id == User.language_level_id)
                .outerjoin(UserLearningSettings, UserLearningSettings.user_uuid == User.uuid)
                .outerjoin(AclGroup, AclGroup.id == User.acl_group_id)
                .where(User.telegram_user_id == telegram_user_id)
            ).first()
            if row is None:
                return None
            user, level, settings, acl_group_title = row
            reminder_schedule = self._list_reminder_schedule_in_session(session, user.uuid)
            reminder_weekdays = list(
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
                reminder_weekdays=reminder_weekdays,
                reminder_schedule=reminder_schedule,
            )

    def get_profile_by_user_uuid(self, user_uuid: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.execute(
                select(User, LanguageLevel, UserLearningSettings, AclGroup.title)
                .outerjoin(LanguageLevel, LanguageLevel.id == User.language_level_id)
                .outerjoin(UserLearningSettings, UserLearningSettings.user_uuid == User.uuid)
                .outerjoin(AclGroup, AclGroup.id == User.acl_group_id)
                .where(User.uuid == UUID(str(user_uuid)))
                .limit(1)
            ).first()
            if row is None:
                return None
            user, level, settings, acl_group_title = row
            return user_profile_to_dict(
                user,
                level,
                settings,
                acl_group_title,
                reminder_schedule=self._list_reminder_schedule_in_session(session, user.uuid),
            )

    def _list_reminder_schedule_in_session(self, session, user_uuid) -> list[dict[str, Any]]:
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

    def set_interface_locale(self, telegram_user_id: int, interface_locale: str) -> None:
        with self.session_manager.session() as session:
            user = get_user_by_telegram_id(session, telegram_user_id)
            if user is not None:
                user.interface_locale = interface_locale
                user.language_code = interface_locale
                user.updated = func.now()

    def is_super_admin(self, telegram_user_id: int) -> bool:
        with self.session_manager.session() as session:
            acl_group_title = session.scalar(
                select(AclGroup.title)
                .join(User, User.acl_group_id == AclGroup.id)
                .where(User.telegram_user_id == telegram_user_id)
                .limit(1)
            )
            return str(acl_group_title or "") == "super_admin"

    def can_access(self, telegram_user_id: int, *, action: str, environment: str) -> bool:
        profile = self.get_profile(telegram_user_id)
        if profile is None:
            return False
        rule = AclPermissionRepository(self.session_manager).get_effective_rule(
            group_title=str(profile.get("acl_group_title") or ""),
            action=action,
            environment=environment,
        )
        return rule == "enabled"

    def list_profiles_with_access(self, *, action: str, environment: str) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.execute(
                select(User, LanguageLevel, UserLearningSettings, AclGroup.title)
                .join(AclGroup, AclGroup.id == User.acl_group_id)
                .outerjoin(LanguageLevel, LanguageLevel.id == User.language_level_id)
                .outerjoin(UserLearningSettings, UserLearningSettings.user_uuid == User.uuid)
                .where(
                    User.status == "active",
                    User.chat_id.is_not(None),
                )
                .order_by(User.telegram_user_id.asc())
            ).all()
        acl_permissions = AclPermissionRepository(self.session_manager)
        profiles = []
        for user, level, settings, acl_group_title in rows:
            if acl_permissions.get_effective_rule(
                group_title=str(acl_group_title or ""),
                action=action,
                environment=environment,
            ) == "enabled":
                profiles.append(user_profile_to_dict(user, level, settings, acl_group_title))
        return profiles

    def list_super_admin_profiles(self) -> list[dict[str, Any]]:
        return self._list_super_admin_profiles_by_role()

    def _list_super_admin_profiles_by_role(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.execute(
                select(User, LanguageLevel, UserLearningSettings, AclGroup.title)
                .join(AclGroup, AclGroup.id == User.acl_group_id)
                .outerjoin(LanguageLevel, LanguageLevel.id == User.language_level_id)
                .outerjoin(UserLearningSettings, UserLearningSettings.user_uuid == User.uuid)
                .where(
                    User.status == "active",
                    AclGroup.title == "super_admin",
                    User.chat_id.is_not(None),
                )
                .order_by(User.telegram_user_id.asc())
            ).all()
            return [
                user_profile_to_dict(user, level, settings, acl_group_title)
                for user, level, settings, acl_group_title in rows
            ]
