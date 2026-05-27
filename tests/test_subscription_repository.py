from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.data_access.subscriptions import SubscriptionRepository
from app.models import AppSetting, UserLearningSettings, UserReminderSchedule, UserSubscription
from app.subscriptions.periods import add_months


class FakeSession:
    def __init__(self, rows=None) -> None:
        self.rows = rows or {}
        self.added = []
        self.scalars_calls = 0

    def get(self, model, primary_key):
        return self.rows.get((model, primary_key))

    def add(self, row) -> None:
        self.added.append(row)
        if isinstance(row, UserSubscription):
            self.rows[(UserSubscription, row.user_uuid)] = row

    def scalars(self, statement):
        self.scalars_calls += 1
        model_filter = UserSubscription if self.scalars_calls == 1 else UserReminderSchedule
        return FakeScalarsResult([row for (model, _key), row in self.rows.items() if model is model_filter])

    def flush(self) -> None:
        pass


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_ensure_default_for_student_creates_free_subscription_with_trial() -> None:
    user_uuid = uuid4()
    current_time = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    repository = SubscriptionRepository(FakeSessionManager(FakeSession()))

    payload = repository.ensure_default_for_user(
        user_uuid,
        learning_role="student",
        current_time=current_time,
        trial_duration_days=7,
    )

    assert payload["user_uuid"] == str(user_uuid)
    assert payload["plan_key"] == "free"
    assert payload["start"] == current_time
    assert payload["end"] is None
    assert payload["trial_start"] == current_time
    assert payload["trial_end"] == current_time + timedelta(days=7)


def test_ensure_default_for_teacher_uses_teacher_free_without_trial() -> None:
    user_uuid = uuid4()
    current_time = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    repository = SubscriptionRepository(FakeSessionManager(FakeSession()))

    payload = repository.ensure_default_for_user(
        str(user_uuid),
        learning_role="teacher",
        current_time=current_time,
        trial_duration_days=7,
    )

    assert payload["plan_key"] == "teacher_free"
    assert payload["trial_start"] is None
    assert payload["trial_end"] is None


def test_ensure_default_reads_trial_duration_from_subscription_settings_inside_session() -> None:
    user_uuid = uuid4()
    current_time = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    setting = AppSetting(
        key="subscriptions.runtime_settings",
        value_json={"trial_duration_days": 14},
        created=current_time,
        updated=current_time,
    )
    session = FakeSession(rows={(AppSetting, "subscriptions.runtime_settings"): setting})
    repository = SubscriptionRepository(FakeSessionManager(session))

    row = repository.ensure_default_for_user_in_session(
        session,
        user_uuid,
        learning_role="student",
        current_time=current_time,
    )

    assert row.trial_end == current_time + timedelta(days=14)


def test_ensure_default_keeps_existing_subscription() -> None:
    user_uuid = uuid4()
    current_time = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    existing = UserSubscription(
        user_uuid=user_uuid,
        plan_key="premium",
        start=current_time,
        status="active",
        created=current_time,
        updated=current_time,
    )
    session = FakeSession(rows={(UserSubscription, user_uuid): existing})
    repository = SubscriptionRepository(FakeSessionManager(session))

    payload = repository.ensure_default_for_user(
        UUID(str(user_uuid)),
        learning_role="student",
        current_time=current_time,
        trial_duration_days=7,
    )

    assert payload["plan_key"] == "premium"
    assert session.added == []


def test_set_plan_for_user_sets_monthly_period_and_clears_trial() -> None:
    user_uuid = uuid4()
    old_time = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    current_time = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    existing = UserSubscription(
        user_uuid=user_uuid,
        plan_key="free",
        start=old_time,
        trial_start=old_time,
        trial_end=old_time + timedelta(days=7),
        status="active",
        created=old_time,
        updated=old_time,
    )
    session = FakeSession(rows={(UserSubscription, user_uuid): existing})
    repository = SubscriptionRepository(FakeSessionManager(session))

    payload = repository.set_plan_for_user(user_uuid, plan_key="premium", current_time=current_time)

    assert payload["plan_key"] == "premium"
    assert payload["start"] == current_time
    assert payload["end"] == current_time + timedelta(days=30)
    assert payload["trial_start"] is None
    assert payload["trial_end"] is None
    assert payload["payment_required"] is False
    assert payload["payment_due_at"] is None
    assert payload["payment_reason"] is None


def test_set_plan_for_user_keeps_permanent_plan_without_end() -> None:
    user_uuid = uuid4()
    current_time = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    repository = SubscriptionRepository(FakeSessionManager(FakeSession()))

    payload = repository.set_plan_for_user(user_uuid, plan_key="permanent_premium", current_time=current_time)

    assert payload["plan_key"] == "permanent_premium"
    assert payload["end"] is None


def test_activate_paid_plan_for_user_uses_purchased_month_period_and_clears_trial() -> None:
    user_uuid = uuid4()
    old_time = datetime(2026, 1, 31, 10, 0, tzinfo=UTC)
    current_time = datetime(2026, 5, 31, 10, 0, tzinfo=UTC)
    existing = UserSubscription(
        user_uuid=user_uuid,
        plan_key="free",
        start=old_time,
        trial_start=old_time,
        trial_end=old_time + timedelta(days=7),
        status="active",
        created=old_time,
        updated=old_time,
    )
    session = FakeSession(rows={(UserSubscription, user_uuid): existing})
    repository = SubscriptionRepository(FakeSessionManager(session))

    payload = repository.activate_paid_plan_for_user(
        user_uuid,
        plan_key="premium_plus",
        period_months=3,
        current_time=current_time,
    )

    assert payload["plan_key"] == "premium_plus"
    assert payload["start"] == current_time
    assert payload["end"] == datetime(2026, 8, 31, 10, 0, tzinfo=UTC)
    assert payload["trial_start"] is None
    assert payload["trial_end"] is None
    assert payload["payment_required"] is False


def test_revoke_paid_plan_for_user_downgrades_only_matching_activation() -> None:
    user_uuid = uuid4()
    activated_at = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)
    current_time = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    existing = UserSubscription(
        user_uuid=user_uuid,
        plan_key="premium",
        start=activated_at,
        end=datetime(2026, 6, 6, 10, 0, tzinfo=UTC),
        status="active",
        created=activated_at,
        updated=activated_at,
    )
    settings = UserLearningSettings(user_uuid=user_uuid, words_per_session=40)
    first_monday = UserReminderSchedule(id=1, user_uuid=user_uuid, weekday=0, hour=9, status="enabled")
    second_monday = UserReminderSchedule(id=2, user_uuid=user_uuid, weekday=0, hour=20, status="enabled")
    session = FakeSession(
        rows={
            (UserSubscription, user_uuid): existing,
            (UserLearningSettings, user_uuid): settings,
            (UserReminderSchedule, 1): first_monday,
            (UserReminderSchedule, 2): second_monday,
        }
    )
    session.scalars_calls = 1
    repository = SubscriptionRepository(FakeSessionManager(session))

    payload = repository.revoke_paid_plan_for_user(
        user_uuid,
        plan_key="premium",
        activated_at=activated_at,
        current_time=current_time,
    )

    assert payload["plan_key"] == "free"
    assert payload["start"] == current_time
    assert payload["end"] is None
    assert settings.words_per_session == 15
    assert first_monday.status == "enabled"
    assert second_monday.status == "disabled"


def test_revoke_paid_plan_for_user_preserves_newer_same_plan_activation() -> None:
    user_uuid = uuid4()
    old_activation = datetime(2026, 5, 6, 10, 0, tzinfo=UTC)
    newer_activation = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    existing = UserSubscription(
        user_uuid=user_uuid,
        plan_key="premium",
        start=newer_activation,
        end=datetime(2026, 6, 7, 10, 0, tzinfo=UTC),
        status="active",
        created=old_activation,
        updated=newer_activation,
    )
    repository = SubscriptionRepository(FakeSessionManager(FakeSession(rows={(UserSubscription, user_uuid): existing})))

    payload = repository.revoke_paid_plan_for_user(
        user_uuid,
        plan_key="premium",
        activated_at=old_activation,
        current_time=datetime(2026, 5, 8, 10, 0, tzinfo=UTC),
    )

    assert payload is None
    assert existing.plan_key == "premium"
    assert existing.start == newer_activation


def test_add_months_clamps_to_last_day_of_target_month() -> None:
    assert add_months(datetime(2026, 1, 31, 10, 0, tzinfo=UTC), 1) == datetime(
        2026, 2, 28, 10, 0, tzinfo=UTC
    )


def test_set_and_clear_trial_for_user_preserves_plan() -> None:
    user_uuid = uuid4()
    old_time = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    current_time = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    existing = UserSubscription(
        user_uuid=user_uuid,
        plan_key="free",
        start=old_time,
        status="active",
        created=old_time,
        updated=old_time,
    )
    repository = SubscriptionRepository(FakeSessionManager(FakeSession(rows={(UserSubscription, user_uuid): existing})))

    enabled = repository.set_trial_for_user(user_uuid, trial_duration_days=7, current_time=current_time)
    cleared = repository.clear_trial_for_user(user_uuid, current_time=current_time)

    assert enabled["plan_key"] == "free"
    assert enabled["trial_start"] == current_time
    assert enabled["trial_end"] == current_time + timedelta(days=7)
    assert cleared["plan_key"] == "free"
    assert cleared["trial_start"] is None
    assert cleared["trial_end"] is None


def test_set_trial_for_user_rejects_paid_plan() -> None:
    user_uuid = uuid4()
    old_time = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    current_time = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    existing = UserSubscription(
        user_uuid=user_uuid,
        plan_key="premium",
        start=old_time,
        status="active",
        created=old_time,
        updated=old_time,
    )
    repository = SubscriptionRepository(FakeSessionManager(FakeSession(rows={(UserSubscription, user_uuid): existing})))

    assert repository.set_trial_for_user(user_uuid, trial_duration_days=7, current_time=current_time) is None
    assert existing.trial_start is None
    assert existing.trial_end is None


def test_process_expired_trials_clamps_words_and_disables_extra_daily_reminders() -> None:
    user_uuid = uuid4()
    old_time = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    current_time = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)
    subscription = UserSubscription(
        user_uuid=user_uuid,
        plan_key="free",
        start=old_time,
        trial_start=old_time,
        trial_end=old_time + timedelta(days=7),
        status="active",
        created=old_time,
        updated=old_time,
    )
    settings = UserLearningSettings(user_uuid=user_uuid, words_per_session=30)
    first_monday = UserReminderSchedule(id=1, user_uuid=user_uuid, weekday=0, hour=9, status="enabled")
    second_monday = UserReminderSchedule(id=2, user_uuid=user_uuid, weekday=0, hour=20, status="enabled")
    first_tuesday = UserReminderSchedule(id=3, user_uuid=user_uuid, weekday=1, hour=10, status="enabled")
    disabled_tuesday = UserReminderSchedule(id=4, user_uuid=user_uuid, weekday=1, hour=21, status="disabled")
    session = FakeSession(
        rows={
            (UserSubscription, user_uuid): subscription,
            (UserLearningSettings, user_uuid): settings,
            (UserReminderSchedule, 1): first_monday,
            (UserReminderSchedule, 2): second_monday,
            (UserReminderSchedule, 3): first_tuesday,
            (UserReminderSchedule, 4): disabled_tuesday,
        }
    )
    repository = SubscriptionRepository(FakeSessionManager(session))

    summary = repository.process_expired_trials(current_time=current_time)

    assert summary == {
        "processed_users_count": 1,
        "trial_closed_count": 1,
        "words_per_session_clamped_count": 1,
        "reminder_rows_disabled_count": 1,
    }
    assert subscription.trial_start is None
    assert subscription.trial_end is None
    assert settings.words_per_session == 15
    assert first_monday.status == "enabled"
    assert second_monday.status == "disabled"
    assert first_tuesday.status == "enabled"
    assert disabled_tuesday.status == "disabled"


def test_process_expired_paid_subscriptions_downgrades_to_free_and_applies_free_caps() -> None:
    user_uuid = uuid4()
    old_time = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    current_time = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    subscription = UserSubscription(
        user_uuid=user_uuid,
        plan_key="premium",
        start=old_time,
        end=current_time,
        status="active",
        created=old_time,
        updated=old_time,
    )
    settings = UserLearningSettings(user_uuid=user_uuid, words_per_session=30)
    first_monday = UserReminderSchedule(id=1, user_uuid=user_uuid, weekday=0, hour=9, status="enabled")
    second_monday = UserReminderSchedule(id=2, user_uuid=user_uuid, weekday=0, hour=20, status="enabled")
    session = FakeSession(
        rows={
            (UserSubscription, user_uuid): subscription,
            (UserLearningSettings, user_uuid): settings,
            (UserReminderSchedule, 1): first_monday,
            (UserReminderSchedule, 2): second_monday,
        }
    )
    repository = SubscriptionRepository(FakeSessionManager(session))

    summary = repository.process_expired_paid_subscriptions(current_time=current_time)

    assert summary == {
        "processed_users_count": 1,
        "downgraded_to_free_count": 1,
        "words_per_session_clamped_count": 1,
        "reminder_rows_disabled_count": 1,
    }
    assert subscription.plan_key == "free"
    assert subscription.end is None
    assert settings.words_per_session == 15
    assert first_monday.status == "enabled"
    assert second_monday.status == "disabled"
