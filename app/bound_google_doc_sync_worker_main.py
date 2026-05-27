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


class BoundGoogleDocSyncRuntime(Protocol):
    def process_due_bound_google_doc_syncs(self) -> list[object]: ...


def build_bound_google_doc_sync_runtime(service: Any) -> BoundGoogleDocSyncRuntime:
    return service.user_import_scheduled_runtime_service


def run_bound_google_doc_sync(service: BoundGoogleDocSyncRuntime) -> dict[str, str]:
    service.process_due_bound_google_doc_syncs()
    return {"status": "ok"}


def main() -> None:
    configure_logging()
    settings = load_settings()
    db = build_database(settings)
    time_service = TimeService(settings.app_timezone)
    runtime = build_learning_runtime(db, time_service)
    sync_runtime = build_bound_google_doc_sync_runtime(runtime)
    db.connect()
    db.run_migrations()
    try:
        result = run_bound_google_doc_sync(sync_runtime)
    finally:
        db.close()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
