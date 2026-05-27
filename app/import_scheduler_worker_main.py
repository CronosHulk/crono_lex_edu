from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

from app.composition.root import build_database, build_learning_runtime
from app.config import load_settings
from app.time_utils import TimeService
from app.user_import.runtime_settings import read_user_import_runtime_settings

LOGGER = logging.getLogger(__name__)


class ImportSchedulerRuntime(Protocol):
    def process_due_import_scheduler_tick(self) -> list[object]: ...


class ImportSchedulerDatabase(Protocol):
    def connect(self) -> None: ...
    def run_migrations(self) -> None: ...
    def close(self) -> None: ...


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


def run_scheduler_tick(service: ImportSchedulerRuntime) -> dict[str, int]:
    notifications = service.process_due_import_scheduler_tick()
    return {"notification_count": len(notifications)}


def build_import_scheduler_runtime(service: Any) -> ImportSchedulerRuntime:
    return service.user_import_scheduled_runtime_service


def resolve_tick_seconds(db: ImportSchedulerDatabase) -> int:
    runtime_settings = read_user_import_runtime_settings(db)
    return max(int(runtime_settings["scheduler_tick_minutes"]), 1) * 60


def resolve_sleep_until_next_tick_seconds(
    current_timestamp: float,
    tick_seconds: int,
) -> float:
    safe_tick_seconds = max(int(tick_seconds), 1)
    remainder = current_timestamp % safe_tick_seconds
    if remainder == 0:
        return 0
    return safe_tick_seconds - remainder


def main() -> None:
    configure_logging()
    settings = load_settings()
    db = build_database(settings)
    time_service = TimeService(settings.app_timezone)
    runtime = build_learning_runtime(db, time_service)
    scheduler_runtime = build_import_scheduler_runtime(runtime)
    db.connect()
    db.run_migrations()
    try:
        while True:
            sleep_seconds = resolve_sleep_until_next_tick_seconds(
                time.time(),
                resolve_tick_seconds(db),
            )
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            try:
                result = run_scheduler_tick(scheduler_runtime)
                LOGGER.info(
                    "Import scheduler tick completed: %s", json.dumps(result, ensure_ascii=False)
                )
            except Exception:
                LOGGER.exception("Import scheduler tick failed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
