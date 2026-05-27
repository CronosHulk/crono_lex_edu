from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Protocol

from app.billing.runtime_settings import read_billing_runtime_settings
from app.composition.root import build_database, build_learning_runtime
from app.config import load_settings
from app.time_utils import TimeService

LOGGER = logging.getLogger(__name__)


class SubscriptionMaintenanceDatabase(Protocol):
    app_settings: Any

    def connect(self) -> None: ...

    def run_migrations(self) -> None: ...

    def close(self) -> None: ...


class SubscriptionMaintenanceRuntime(Protocol):
    def process_due_subscription_maintenance(self) -> dict[str, object]: ...


def build_subscription_maintenance_runtime(service: Any) -> SubscriptionMaintenanceRuntime:
    return service.subscription_maintenance_runtime_service


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


def run_subscription_maintenance_tick(service: SubscriptionMaintenanceRuntime) -> dict[str, object]:
    return service.process_due_subscription_maintenance()


def resolve_run_hour(db: SubscriptionMaintenanceDatabase) -> int:
    runtime_settings = read_billing_runtime_settings(db)
    return int(runtime_settings["subscription_expiration_hour"])


def resolve_sleep_until_next_daily_run_seconds(current_time: datetime, run_hour: int) -> float:
    safe_hour = max(0, min(int(run_hour), 23))
    run_at = current_time.replace(hour=safe_hour, minute=0, second=0, microsecond=0)
    if current_time > run_at:
        run_at += timedelta(days=1)
    return max((run_at - current_time).total_seconds(), 0)


def main() -> None:
    configure_logging()
    settings = load_settings()
    db = build_database(settings)
    time_service = TimeService(settings.app_timezone)
    runtime = build_learning_runtime(db, time_service)
    maintenance_runtime = build_subscription_maintenance_runtime(runtime)
    db.connect()
    db.run_migrations()
    try:
        while True:
            sleep_seconds = resolve_sleep_until_next_daily_run_seconds(
                time_service.now(),
                resolve_run_hour(db),
            )
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            try:
                result = run_subscription_maintenance_tick(maintenance_runtime)
                LOGGER.info("Subscription maintenance completed: %s", json.dumps(result, ensure_ascii=False))
            except Exception:
                LOGGER.exception("Subscription maintenance failed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
