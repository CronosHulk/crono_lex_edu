from __future__ import annotations

from datetime import datetime
from typing import Any

SUBSCRIPTION_MAINTENANCE_TASK_TYPE = "subscription_daily_maintenance"
TRIAL_EXPIRATION_TASK_TYPE = "subscription_trial_expiration"


class SubscriptionMaintenanceService:
    def __init__(self, db: Any) -> None:
        self.db = db

    def process_expired_trials(self, *, current_time: datetime) -> dict[str, Any]:
        task_log = self.db.task_logs.create(
            task_type=TRIAL_EXPIRATION_TASK_TYPE,
            status="processing",
            current_time=current_time,
            description="Processing expired subscription trials.",
        )
        try:
            summary = self.db.subscriptions.process_expired_trials(current_time=current_time)
        except Exception as error:
            self.db.task_logs.update(
                int(task_log["id"]),
                status="fatal",
                current_time=current_time,
                description="Failed to process expired subscription trials.",
                error_text=str(error),
                result_json={},
            )
            raise
        self.db.task_logs.update(
            int(task_log["id"]),
            status="success",
            current_time=current_time,
            description=_build_summary_description(summary),
            result_json=summary,
        )
        return {**summary, "task_log_id": task_log["id"]}

    def process_daily_maintenance(self, *, current_time: datetime) -> dict[str, Any]:
        task_log = self.db.task_logs.create(
            task_type=SUBSCRIPTION_MAINTENANCE_TASK_TYPE,
            status="processing",
            current_time=current_time,
            description="Processing daily subscription maintenance.",
        )
        try:
            paid_summary = self.db.subscriptions.process_expired_paid_subscriptions(current_time=current_time)
            trial_summary = self.db.subscriptions.process_expired_trials(current_time=current_time)
            summary = {
                "paid_expiration": paid_summary,
                "trial_expiration": trial_summary,
            }
        except Exception as error:
            self.db.task_logs.update(
                int(task_log["id"]),
                status="fatal",
                current_time=current_time,
                description="Failed to process daily subscription maintenance.",
                error_text=str(error),
                result_json={},
            )
            raise
        self.db.task_logs.update(
            int(task_log["id"]),
            status="success",
            current_time=current_time,
            description=_build_daily_summary_description(summary),
            result_json=summary,
        )
        return {**summary, "task_log_id": task_log["id"]}


def _build_summary_description(summary: dict[str, int]) -> str:
    return (
        "Processed expired subscription trials: "
        f"users={summary.get('processed_users_count', 0)}, "
        f"closed={summary.get('trial_closed_count', 0)}, "
        f"words_clamped={summary.get('words_per_session_clamped_count', 0)}, "
        f"reminders_disabled={summary.get('reminder_rows_disabled_count', 0)}."
    )


def _build_daily_summary_description(summary: dict[str, dict[str, int]]) -> str:
    paid = summary.get("paid_expiration", {})
    trial = summary.get("trial_expiration", {})
    return (
        "Processed daily subscription maintenance: "
        f"paid_users={paid.get('processed_users_count', 0)}, "
        f"paid_downgraded={paid.get('downgraded_to_free_count', 0)}, "
        f"trial_users={trial.get('processed_users_count', 0)}, "
        f"trial_closed={trial.get('trial_closed_count', 0)}."
    )
