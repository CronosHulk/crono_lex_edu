from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

from app.billing.runtime_settings import read_billing_runtime_settings
from app.composition.root import build_database, build_learning_runtime
from app.config import load_settings
from app.import_scheduler_worker_main import resolve_sleep_until_next_tick_seconds
from app.time_utils import TimeService

LOGGER = logging.getLogger(__name__)


class BillingReconciliationDatabase(Protocol):
    def connect(self) -> None: ...

    def run_migrations(self) -> None: ...

    def close(self) -> None: ...


class BillingReconciliationRuntime(Protocol):
    def process_due_billing_reconciliation(self) -> dict[str, object]: ...


def build_billing_reconciliation_runtime(service: Any) -> BillingReconciliationRuntime:
    return service.billing_reconciliation_runtime_service


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


def run_reconciliation_tick(service: BillingReconciliationRuntime) -> dict[str, object]:
    return service.process_due_billing_reconciliation()


def resolve_tick_seconds(db: BillingReconciliationDatabase) -> int:
    runtime_settings = read_billing_runtime_settings(db)
    return max(int(runtime_settings["reconciliation_interval_seconds"]), 30)


def main() -> None:
    configure_logging()
    settings = load_settings()
    db = build_database(settings)
    time_service = TimeService(settings.app_timezone)
    runtime = build_learning_runtime(db, time_service)
    reconciliation_runtime = build_billing_reconciliation_runtime(runtime)
    db.connect()
    db.run_migrations()
    try:
        while True:
            sleep_seconds = resolve_sleep_until_next_tick_seconds(time.time(), resolve_tick_seconds(db))
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            try:
                result = run_reconciliation_tick(reconciliation_runtime)
                LOGGER.info("Billing reconciliation tick completed: %s", json.dumps(result, ensure_ascii=False))
            except Exception:
                LOGGER.exception("Billing reconciliation tick failed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
