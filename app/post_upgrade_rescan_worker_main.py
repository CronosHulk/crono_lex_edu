from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.composition.root import build_database, build_learning_runtime
from app.config import load_settings
from app.time_utils import TimeService


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


class PostUpgradeRescanRuntime(Protocol):
    def process_due_post_upgrade_rescans(self) -> list[object]: ...


def run_post_upgrade_rescan(service: PostUpgradeRescanRuntime) -> dict[str, str]:
    service.process_due_post_upgrade_rescans()
    return {"status": "ok"}


def build_post_upgrade_rescan_runtime(service: Any) -> PostUpgradeRescanRuntime:
    return service.user_import_scheduled_runtime_service


def main() -> None:
    configure_logging()
    settings = load_settings()
    db = build_database(settings)
    time_service = TimeService(settings.app_timezone)
    runtime = build_learning_runtime(db, time_service)
    rescan_runtime = build_post_upgrade_rescan_runtime(runtime)
    db.connect()
    db.run_migrations()
    try:
        result = run_post_upgrade_rescan(rescan_runtime)
    finally:
        db.close()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
