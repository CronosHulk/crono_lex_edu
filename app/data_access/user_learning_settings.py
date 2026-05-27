from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.data_access.reminder_schedule_serialization import reminder_schedule_to_dict
from app.data_access.user_identity import get_user_uuid_by_telegram_id
from app.models import AppVersion, UserLearningSettings, UserReminderSchedule, UserReminderWeekday
from app.orm import SessionManager
from app.reference.reminder_schedules import (
    enabled_reminder_weekdays,
    first_enabled_reminder_hour,
    normalize_reminder_schedule,
)


class UserLearningSettingsRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def _get_or_create_settings(self, session, telegram_user_id: int) -> UserLearningSettings:
        user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
        if user_uuid is None:
            raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
        settings = session.get(UserLearningSettings, user_uuid)
        if settings is None:
            settings = UserLearningSettings(user_uuid=user_uuid)
            session.add(settings)
        return settings

    def get_current_app_version(self) -> str | None:
        with self.session_manager.session() as session:
            row = session.get(AppVersion, "current")
            return row.version if row is not None and row.is_active else None

    def set_current_app_version(self, version: str, *, current_time: datetime) -> str:
        with self.session_manager.session() as session:
            row = session.get(AppVersion, "current")
            if row is None:
                row = AppVersion(key="current", version=version, is_active=True, created=current_time, updated=current_time)
                session.add(row)
            else:
                row.version = version
                row.is_active = True
                row.updated = current_time
            session.flush()
            return row.version

    def set_words_per_session(self, telegram_user_id: int, words_per_session: int) -> None:
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            settings.words_per_session = words_per_session

    def set_daily_reminder_hour(self, telegram_user_id: int, daily_reminder_hour: int | None) -> None:
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            settings.daily_reminder_hour = daily_reminder_hour
            weekdays = self._get_legacy_weekdays_in_session(session, settings.user_uuid)
            self._replace_schedule_in_session(
                session,
                settings.user_uuid,
                [
                    {"weekday": weekday, "hour": daily_reminder_hour, "minute": 0, "status": "enabled"}
                    for weekday in weekdays
                    if daily_reminder_hour is not None
                ],
            )

    def get_reminder_weekdays(self, telegram_user_id: int) -> list[int]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return []
            schedule = self._list_schedule_in_session(session, user_uuid)
            if schedule:
                return enabled_reminder_weekdays(schedule)
            return self._get_legacy_weekdays_in_session(session, user_uuid)

    def list_reminder_schedule(self, telegram_user_id: int) -> list[dict[str, object]]:
        with self.session_manager.session() as session:
            user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
            if user_uuid is None:
                return []
            return self._list_schedule_in_session(session, user_uuid)

    def replace_reminder_schedule(self, telegram_user_id: int, schedule_rows: list[dict[str, object]]) -> list[dict[str, object]]:
        normalized = normalize_reminder_schedule(schedule_rows)
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            self._replace_schedule_in_session(session, settings.user_uuid, normalized)
            self._sync_legacy_fields_in_session(session, settings, normalized)
            session.flush()
            return self._list_schedule_in_session(session, settings.user_uuid)

    def _get_legacy_weekdays_in_session(self, session, user_uuid) -> list[int]:
        return list(
            session.scalars(
                select(UserReminderWeekday.weekday)
                .where(UserReminderWeekday.user_uuid == user_uuid)
                .order_by(UserReminderWeekday.weekday.asc())
            ).all()
        )

    def _list_schedule_in_session(self, session, user_uuid) -> list[dict[str, object]]:
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

    def _replace_schedule_in_session(self, session, user_uuid, schedule_rows: list[dict[str, object]]) -> None:
        rows = session.scalars(
            select(UserReminderSchedule).where(UserReminderSchedule.user_uuid == user_uuid)
        ).all()
        for row in rows:
            session.delete(row)
        for row in normalize_reminder_schedule(schedule_rows):
            session.add(
                UserReminderSchedule(
                    user_uuid=user_uuid,
                    weekday=int(row["weekday"]),
                    hour=int(row["hour"]),
                    minute=int(row["minute"]),
                    title=str(row.get("title") or "") or None,
                    status=str(row["status"]),
                )
            )

    def _sync_legacy_fields_in_session(
        self,
        session,
        settings: UserLearningSettings,
        schedule_rows: list[dict[str, object]],
    ) -> None:
        settings.daily_reminder_hour = first_enabled_reminder_hour(schedule_rows)
        rows = session.scalars(
            select(UserReminderWeekday).where(UserReminderWeekday.user_uuid == settings.user_uuid)
        ).all()
        for row in rows:
            session.delete(row)
        for weekday in enabled_reminder_weekdays(schedule_rows):
            session.add(UserReminderWeekday(user_uuid=settings.user_uuid, weekday=weekday))

    def _set_legacy_weekdays_in_session(self, session, user_uuid, weekdays: list[int]) -> None:
        rows = session.scalars(
            select(UserReminderWeekday).where(UserReminderWeekday.user_uuid == user_uuid)
        ).all()
        for row in rows:
            session.delete(row)
        for weekday in sorted({weekday for weekday in weekdays if 0 <= weekday <= 6}):
            session.add(UserReminderWeekday(user_uuid=user_uuid, weekday=weekday))

    def set_reminder_weekdays(self, telegram_user_id: int, weekdays: list[int]) -> None:
        normalized = sorted({weekday for weekday in weekdays if 0 <= weekday <= 6})
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            existing_schedule = self._list_schedule_in_session(session, settings.user_uuid)
            enabled_times = sorted(
                {
                    (int(row["hour"]), int(row.get("minute") or 0))
                    for row in existing_schedule
                    if row.get("status") == "enabled"
                }
            )
            if not enabled_times and settings.daily_reminder_hour is not None:
                enabled_times = [(int(settings.daily_reminder_hour), 0)]
            self._set_legacy_weekdays_in_session(session, settings.user_uuid, normalized)
            self._replace_schedule_in_session(
                session,
                settings.user_uuid,
                [
                    {"weekday": weekday, "hour": hour, "minute": minute, "status": "enabled"}
                    for weekday in normalized
                    for hour, minute in enabled_times
                ],
            )

    def clear_daily_reminder_settings(self, telegram_user_id: int) -> None:
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            settings.daily_reminder_hour = None
            rows = session.scalars(
                select(UserReminderWeekday).where(UserReminderWeekday.user_uuid == settings.user_uuid)
            ).all()
            for row in rows:
                session.delete(row)
            schedule_rows = session.scalars(
                select(UserReminderSchedule).where(UserReminderSchedule.user_uuid == settings.user_uuid)
            ).all()
            for row in schedule_rows:
                session.delete(row)
