from __future__ import annotations

from datetime import UTC, datetime

from app.subscriptions.maintenance import (
    SUBSCRIPTION_MAINTENANCE_TASK_TYPE,
    TRIAL_EXPIRATION_TASK_TYPE,
    SubscriptionMaintenanceService,
)


class FakeSubscriptions:
    def __init__(self) -> None:
        self.summary = {
            "processed_users_count": 2,
            "trial_closed_count": 2,
            "words_per_session_clamped_count": 1,
            "reminder_rows_disabled_count": 3,
        }
        self.paid_summary = {
            "processed_users_count": 1,
            "downgraded_to_free_count": 1,
            "words_per_session_clamped_count": 1,
            "reminder_rows_disabled_count": 1,
        }
        self.calls: list[datetime] = []
        self.paid_calls: list[datetime] = []

    def process_expired_trials(self, *, current_time: datetime):
        self.calls.append(current_time)
        return self.summary

    def process_expired_paid_subscriptions(self, *, current_time: datetime):
        self.paid_calls.append(current_time)
        return self.paid_summary


class FakeTaskLogs:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.updated: list[tuple[int, dict[str, object]]] = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return {"id": 77, **kwargs}

    def update(self, task_log_id: int, **kwargs):
        self.updated.append((task_log_id, kwargs))
        return {"id": task_log_id, **kwargs}


class FakeDatabase:
    def __init__(self) -> None:
        self.subscriptions = FakeSubscriptions()
        self.task_logs = FakeTaskLogs()


def test_subscription_maintenance_processes_expired_trials_and_logs_summary() -> None:
    db = FakeDatabase()
    current_time = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)

    summary = SubscriptionMaintenanceService(db).process_expired_trials(current_time=current_time)

    assert db.subscriptions.calls == [current_time]
    assert summary == {**db.subscriptions.summary, "task_log_id": 77}
    assert db.task_logs.created[0]["task_type"] == TRIAL_EXPIRATION_TASK_TYPE
    assert db.task_logs.created[0]["status"] == "processing"
    assert db.task_logs.updated == [
        (
            77,
            {
                "status": "success",
                "current_time": current_time,
                "description": "Processed expired subscription trials: users=2, closed=2, words_clamped=1, reminders_disabled=3.",
                "result_json": db.subscriptions.summary,
            },
        )
    ]


def test_subscription_daily_maintenance_processes_paid_and_trial_expiration() -> None:
    db = FakeDatabase()
    current_time = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)

    summary = SubscriptionMaintenanceService(db).process_daily_maintenance(current_time=current_time)

    assert db.subscriptions.paid_calls == [current_time]
    assert db.subscriptions.calls == [current_time]
    assert summary == {
        "paid_expiration": db.subscriptions.paid_summary,
        "trial_expiration": db.subscriptions.summary,
        "task_log_id": 77,
    }
    assert db.task_logs.created[0]["task_type"] == SUBSCRIPTION_MAINTENANCE_TASK_TYPE
    assert db.task_logs.updated[0][1] == {
        "status": "success",
        "current_time": current_time,
        "description": "Processed daily subscription maintenance: paid_users=1, paid_downgraded=1, trial_users=2, trial_closed=2.",
        "result_json": {
            "paid_expiration": db.subscriptions.paid_summary,
            "trial_expiration": db.subscriptions.summary,
        },
    }
