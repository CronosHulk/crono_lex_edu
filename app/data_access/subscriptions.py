from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.models import UserLearningSettings, UserReminderSchedule, UserSubscription
from app.orm import SessionManager
from app.subscriptions.periods import add_months as add_months
from app.subscriptions.plans import (
    PLAN_FREE,
    PLAN_PREMIUM,
    PLAN_PREMIUM_PLUS,
    PLAN_TEACHER_FREE,
    PLAN_TEACHER_PREMIUM,
    get_subscription_plan,
)
from app.subscriptions.runtime_settings import read_subscription_runtime_settings

SUBSCRIPTION_STATUS_ACTIVE = "active"
MONTHLY_PLAN_KEYS = {PLAN_PREMIUM, PLAN_PREMIUM_PLUS, PLAN_TEACHER_PREMIUM}
FREE_WORDS_PER_SESSION_MAX = 15


def subscription_to_dict(row: UserSubscription) -> dict[str, Any]:
    return {
        "user_uuid": str(row.user_uuid),
        "plan_key": row.plan_key,
        "start": row.start,
        "end": row.end,
        "trial_start": row.trial_start,
        "trial_end": row.trial_end,
        "payment_required": row.payment_required,
        "payment_due_at": row.payment_due_at,
        "payment_reason": row.payment_reason,
        "status": row.status,
        "created": row.created,
        "updated": row.updated,
    }


class SubscriptionRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get_by_user_uuid(self, user_uuid: str | UUID) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = session.get(UserSubscription, _coerce_uuid(user_uuid))
            return subscription_to_dict(row) if row is not None else None

    def ensure_default_for_user(
        self,
        user_uuid: str | UUID,
        *,
        learning_role: str,
        current_time: datetime,
        trial_duration_days: int,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = self.ensure_default_for_user_in_session(
                session,
                user_uuid,
                learning_role=learning_role,
                current_time=current_time,
                trial_duration_days=trial_duration_days,
            )
            return subscription_to_dict(row)

    def ensure_default_for_user_in_session(
        self,
        session: Any,
        user_uuid: str | UUID,
        *,
        learning_role: str,
        current_time: datetime,
        trial_duration_days: int | None = None,
    ) -> UserSubscription:
        resolved_uuid = _coerce_uuid(user_uuid)
        row = session.get(UserSubscription, resolved_uuid)
        if row is not None:
            return row
        if trial_duration_days is None:
            trial_duration_days = int(read_subscription_runtime_settings(_SessionSettingsReader(session))["trial_duration_days"])
        trial_start = current_time if trial_duration_days > 0 and learning_role == "student" else None
        trial_end = current_time + timedelta(days=trial_duration_days) if trial_start is not None else None
        row = UserSubscription(
            user_uuid=resolved_uuid,
            plan_key=_default_plan_for_role(learning_role),
            start=current_time,
            end=None,
            trial_start=trial_start,
            trial_end=trial_end,
            payment_required=False,
            payment_due_at=None,
            payment_reason=None,
            status=SUBSCRIPTION_STATUS_ACTIVE,
            created=current_time,
            updated=current_time,
        )
        session.add(row)
        return row

    def set_plan_for_user(
        self,
        user_uuid: str | UUID,
        *,
        plan_key: str,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        normalized_plan = str(plan_key or "").strip()
        get_subscription_plan(normalized_plan)
        resolved_uuid = _coerce_uuid(user_uuid)
        with self.session_manager.session() as session:
            row = session.get(UserSubscription, resolved_uuid)
            if row is None:
                row = UserSubscription(user_uuid=resolved_uuid, created=current_time)
                session.add(row)
            row.plan_key = normalized_plan
            row.start = current_time
            row.end = current_time + timedelta(days=30) if normalized_plan in MONTHLY_PLAN_KEYS else None
            row.trial_start = None
            row.trial_end = None
            row.payment_required = False
            row.payment_due_at = None
            row.payment_reason = None
            row.status = SUBSCRIPTION_STATUS_ACTIVE
            row.updated = current_time
            session.flush()
            return subscription_to_dict(row)

    def activate_paid_plan_for_user(
        self,
        user_uuid: str | UUID,
        *,
        plan_key: str,
        period_months: int,
        current_time: datetime,
    ) -> dict[str, Any]:
        normalized_plan = str(plan_key or "").strip()
        if normalized_plan not in MONTHLY_PLAN_KEYS:
            raise ValueError("Paid billing activation requires a monthly paid plan")
        months = int(period_months)
        if months not in {1, 3, 6, 12}:
            raise ValueError("Paid billing activation period must be 1, 3, 6 or 12 months")
        get_subscription_plan(normalized_plan)
        resolved_uuid = _coerce_uuid(user_uuid)
        with self.session_manager.session() as session:
            row = session.get(UserSubscription, resolved_uuid)
            if row is None:
                row = UserSubscription(user_uuid=resolved_uuid, created=current_time)
                session.add(row)
            row.plan_key = normalized_plan
            row.start = current_time
            row.end = add_months(current_time, months)
            row.trial_start = None
            row.trial_end = None
            row.payment_required = False
            row.payment_due_at = None
            row.payment_reason = None
            row.status = SUBSCRIPTION_STATUS_ACTIVE
            row.updated = current_time
            session.flush()
            return subscription_to_dict(row)

    def apply_paid_subscription_projection_for_user(
        self,
        user_uuid: str | UUID,
        *,
        plan_key: str,
        period_start: datetime,
        period_end: datetime,
        current_time: datetime,
    ) -> dict[str, Any]:
        with self.session_manager.session() as session:
            row = self.apply_paid_subscription_projection_for_user_in_session(
                session,
                user_uuid,
                plan_key=plan_key,
                period_start=period_start,
                period_end=period_end,
                current_time=current_time,
            )
            return subscription_to_dict(row)

    def apply_paid_subscription_projection_for_user_in_session(
        self,
        session: Any,
        user_uuid: str | UUID,
        *,
        plan_key: str,
        period_start: datetime,
        period_end: datetime,
        current_time: datetime,
    ) -> UserSubscription:
        normalized_plan = str(plan_key or "").strip()
        if normalized_plan not in MONTHLY_PLAN_KEYS:
            raise ValueError("Paid billing projection requires a monthly paid plan")
        get_subscription_plan(normalized_plan)
        resolved_uuid = _coerce_uuid(user_uuid)
        row = session.get(UserSubscription, resolved_uuid)
        if row is None:
            row = UserSubscription(user_uuid=resolved_uuid, created=current_time)
            session.add(row)
        row.plan_key = normalized_plan
        row.start = period_start
        row.end = period_end
        row.trial_start = None
        row.trial_end = None
        row.payment_required = False
        row.payment_due_at = None
        row.payment_reason = None
        row.status = SUBSCRIPTION_STATUS_ACTIVE
        row.updated = current_time
        session.flush()
        return row

    def downgrade_to_free_for_user(
        self,
        user_uuid: str | UUID,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            row = self.downgrade_to_free_for_user_in_session(session, user_uuid, current_time=current_time)
            return subscription_to_dict(row) if row is not None else None

    def downgrade_to_free_for_user_in_session(
        self,
        session: Any,
        user_uuid: str | UUID,
        *,
        current_time: datetime,
    ) -> UserSubscription | None:
        resolved_uuid = _coerce_uuid(user_uuid)
        row = session.get(UserSubscription, resolved_uuid)
        if row is None:
            return None
        row.plan_key = PLAN_FREE
        row.start = current_time
        row.end = None
        row.trial_start = None
        row.trial_end = None
        row.payment_required = False
        row.payment_due_at = None
        row.payment_reason = None
        row.status = SUBSCRIPTION_STATUS_ACTIVE
        row.updated = current_time
        settings = session.get(UserLearningSettings, row.user_uuid)
        if settings is not None and settings.words_per_session > FREE_WORDS_PER_SESSION_MAX:
            settings.words_per_session = FREE_WORDS_PER_SESSION_MAX
            settings.updated = current_time
        self._disable_extra_daily_reminders_in_session(session, row.user_uuid, current_time=current_time)
        session.flush()
        return row

    def revoke_paid_plan_for_user(
        self,
        user_uuid: str | UUID,
        *,
        plan_key: str,
        activated_at: datetime | None,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        normalized_plan = str(plan_key or "").strip()
        if normalized_plan not in MONTHLY_PLAN_KEYS:
            return None
        resolved_uuid = _coerce_uuid(user_uuid)
        with self.session_manager.session() as session:
            row = session.get(UserSubscription, resolved_uuid)
            if row is None or row.plan_key != normalized_plan:
                return None
            if activated_at is not None and row.start != activated_at:
                return None
            row.plan_key = PLAN_FREE
            row.start = current_time
            row.end = None
            row.trial_start = None
            row.trial_end = None
            row.payment_required = False
            row.payment_due_at = None
            row.payment_reason = None
            row.status = SUBSCRIPTION_STATUS_ACTIVE
            row.updated = current_time
            settings = session.get(UserLearningSettings, row.user_uuid)
            if settings is not None and settings.words_per_session > FREE_WORDS_PER_SESSION_MAX:
                settings.words_per_session = FREE_WORDS_PER_SESSION_MAX
                settings.updated = current_time
            self._disable_extra_daily_reminders_in_session(session, row.user_uuid, current_time=current_time)
            session.flush()
            return subscription_to_dict(row)

    def set_trial_for_user(
        self,
        user_uuid: str | UUID,
        *,
        trial_duration_days: int,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        resolved_uuid = _coerce_uuid(user_uuid)
        with self.session_manager.session() as session:
            row = session.get(UserSubscription, resolved_uuid)
            if row is None:
                row = UserSubscription(
                    user_uuid=resolved_uuid,
                    plan_key=PLAN_FREE,
                    start=current_time,
                    end=None,
                    created=current_time,
                )
                session.add(row)
            if row.plan_key != PLAN_FREE:
                return None
            row.trial_start = current_time
            row.trial_end = current_time + timedelta(days=trial_duration_days)
            row.status = SUBSCRIPTION_STATUS_ACTIVE
            row.updated = current_time
            session.flush()
            return subscription_to_dict(row)

    def clear_trial_for_user(
        self,
        user_uuid: str | UUID,
        *,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        resolved_uuid = _coerce_uuid(user_uuid)
        with self.session_manager.session() as session:
            row = session.get(UserSubscription, resolved_uuid)
            if row is None:
                return None
            row.trial_start = None
            row.trial_end = None
            row.updated = current_time
            session.flush()
            return subscription_to_dict(row)

    def process_expired_trials(self, *, current_time: datetime) -> dict[str, int]:
        with self.session_manager.session() as session:
            subscriptions = session.scalars(
                select(UserSubscription)
                .where(
                    UserSubscription.status == SUBSCRIPTION_STATUS_ACTIVE,
                    UserSubscription.trial_end.is_not(None),
                    UserSubscription.trial_end <= current_time,
                )
                .order_by(UserSubscription.trial_end.asc(), UserSubscription.user_uuid.asc())
            ).all()
            summary = {
                "processed_users_count": 0,
                "trial_closed_count": 0,
                "words_per_session_clamped_count": 0,
                "reminder_rows_disabled_count": 0,
            }
            for subscription in subscriptions:
                summary["processed_users_count"] += 1
                subscription.trial_start = None
                subscription.trial_end = None
                subscription.updated = current_time
                summary["trial_closed_count"] += 1
                settings = session.get(UserLearningSettings, subscription.user_uuid)
                if settings is not None and settings.words_per_session > FREE_WORDS_PER_SESSION_MAX:
                    settings.words_per_session = FREE_WORDS_PER_SESSION_MAX
                    settings.updated = current_time
                    summary["words_per_session_clamped_count"] += 1
                summary["reminder_rows_disabled_count"] += self._disable_extra_daily_reminders_in_session(
                    session,
                    subscription.user_uuid,
                    current_time=current_time,
                )
            return summary

    def process_expired_paid_subscriptions(self, *, current_time: datetime) -> dict[str, int]:
        with self.session_manager.session() as session:
            subscriptions = session.scalars(
                select(UserSubscription)
                .where(
                    UserSubscription.status == SUBSCRIPTION_STATUS_ACTIVE,
                    UserSubscription.plan_key.in_(MONTHLY_PLAN_KEYS),
                    UserSubscription.end.is_not(None),
                    UserSubscription.end <= current_time,
                )
                .order_by(UserSubscription.end.asc(), UserSubscription.user_uuid.asc())
            ).all()
            summary = {
                "processed_users_count": 0,
                "downgraded_to_free_count": 0,
                "words_per_session_clamped_count": 0,
                "reminder_rows_disabled_count": 0,
            }
            for subscription in subscriptions:
                summary["processed_users_count"] += 1
                subscription.plan_key = PLAN_FREE
                subscription.start = current_time
                subscription.end = None
                subscription.trial_start = None
                subscription.trial_end = None
                subscription.payment_required = False
                subscription.payment_due_at = None
                subscription.payment_reason = None
                subscription.status = SUBSCRIPTION_STATUS_ACTIVE
                subscription.updated = current_time
                summary["downgraded_to_free_count"] += 1
                settings = session.get(UserLearningSettings, subscription.user_uuid)
                if settings is not None and settings.words_per_session > FREE_WORDS_PER_SESSION_MAX:
                    settings.words_per_session = FREE_WORDS_PER_SESSION_MAX
                    settings.updated = current_time
                    summary["words_per_session_clamped_count"] += 1
                summary["reminder_rows_disabled_count"] += self._disable_extra_daily_reminders_in_session(
                    session,
                    subscription.user_uuid,
                    current_time=current_time,
                )
            return summary

    def _disable_extra_daily_reminders_in_session(self, session: Any, user_uuid: UUID, *, current_time: datetime) -> int:
        rows = session.scalars(
            select(UserReminderSchedule)
            .where(UserReminderSchedule.user_uuid == user_uuid)
            .order_by(UserReminderSchedule.weekday.asc(), UserReminderSchedule.hour.asc(), UserReminderSchedule.id.asc())
        ).all()
        disabled_count = 0
        enabled_seen_by_weekday: set[int] = set()
        for row in rows:
            if row.status != "enabled":
                continue
            if row.weekday not in enabled_seen_by_weekday:
                enabled_seen_by_weekday.add(row.weekday)
                continue
            row.status = "disabled"
            row.updated = current_time
            disabled_count += 1
        return disabled_count


class _SessionSettingsReader:
    def __init__(self, session: Any) -> None:
        self.app_settings = _SessionAppSettings(session)


class _SessionAppSettings:
    def __init__(self, session: Any) -> None:
        self.session = session

    def get_value(self, key: str) -> dict[str, Any] | None:
        from app.models import AppSetting

        row = self.session.get(AppSetting, key)
        return dict(row.value_json or {}) if row is not None else None


def _default_plan_for_role(learning_role: str) -> str:
    return PLAN_TEACHER_FREE if learning_role == "teacher" else PLAN_FREE


def _coerce_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))
