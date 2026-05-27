from __future__ import annotations

import argparse
import gc
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Protocol

from app.composition.provider_helpers import clear_encoder_cache, ensure_runtime_available
from app.composition.root import build_database, build_learning_runtime
from app.config import load_settings
from app.time_utils import TimeService

USER_IMPORT_EMBEDDING_TASK_TYPE = "user_import_embedding_build"
EMBEDDING_STALE_PROCESSING_SECONDS = 3600
LOGGER = logging.getLogger(__name__)


class UserImportEmbeddingRuntime(Protocol):
    def process_due_user_import_embeddings_now(self) -> dict[str, int]: ...


class EmbeddingTaskLogStore(Protocol):
    def mark_stale_processing_fatal(
        self,
        *,
        task_type: str,
        current_time: datetime,
        stale_before: datetime,
        description: str,
        error_text: str,
        result_json: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> int: ...

    def create(
        self,
        *,
        task_type: str,
        status: str,
        current_time: datetime,
        telegram_user_id: int | None = None,
        source_type: str | None = None,
        source_identifier: str | None = None,
        import_job_id: int | None = None,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def update(
        self,
        task_log_id: int,
        *,
        status: str,
        current_time: datetime,
        description: str | None = None,
        error_text: str | None = None,
        result_json: dict[str, Any] | None = None,
        import_job_id: int | None = None,
    ) -> dict[str, Any] | None: ...


class EmbeddingDatabase(Protocol):
    @property
    def task_logs(self) -> EmbeddingTaskLogStore: ...

    def connect(self) -> None: ...

    def run_migrations(self) -> None: ...

    def close(self) -> None: ...


def build_user_import_embedding_runtime(service: Any) -> UserImportEmbeddingRuntime:
    return service.user_import_runtime_service


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


def run_embedding_tick(
    db: EmbeddingDatabase,
    service: UserImportEmbeddingRuntime,
    time_service: TimeService,
) -> dict[str, int]:
    current_time = time_service.now()
    stale_count = db.task_logs.mark_stale_processing_fatal(
        task_type=USER_IMPORT_EMBEDDING_TASK_TYPE,
        current_time=current_time,
        stale_before=current_time - timedelta(seconds=EMBEDDING_STALE_PROCESSING_SECONDS),
        description="User import embedding build likely crashed.",
        error_text="Previous embedding worker task stayed processing past the stale threshold. Check worker logs for OOM, device or host failures.",
        result_json={
            "error_type": "StaleProcessingTask",
            "stale_threshold_seconds": EMBEDDING_STALE_PROCESSING_SECONDS,
        },
    )
    if stale_count:
        LOGGER.error("Marked %s stale embedding task log(s) as fatal", stale_count)
    task_log = db.task_logs.create(
        task_type=USER_IMPORT_EMBEDDING_TASK_TYPE,
        status="processing",
        current_time=current_time,
        description="User import embedding build",
    )
    try:
        summary = service.process_due_user_import_embeddings_now()
    except Exception as error:
        LOGGER.exception("User import embedding build failed")
        db.task_logs.update(
            int(task_log["id"]),
            status="fatal",
            current_time=time_service.now(),
            description="User import embedding build failed",
            error_text=str(error)[:2000],
            result_json={"error_type": type(error).__name__},
        )
        raise
    embedding_failed_count = int(summary.get("embedding_failed_count") or 0)
    if embedding_failed_count:
        db.task_logs.update(
            int(task_log["id"]),
            status="error",
            current_time=time_service.now(),
            description="User import embedding build completed with failed embeddings",
            error_text=(
                f"Embedding build failed for {embedding_failed_count} user dictionary row(s). "
                "Check failed user dictionary rows and worker/provider logs."
            ),
            result_json=summary,
        )
        return summary
    db.task_logs.update(
        int(task_log["id"]),
        status="success",
        current_time=time_service.now(),
        description="User import embedding build completed",
        result_json=summary,
    )
    return summary


def resolve_sleep_until_next_daily_run_seconds(current_time: datetime, run_hour: int) -> float:
    safe_hour = max(0, min(int(run_hour), 23))
    run_at = current_time.replace(hour=safe_hour, minute=0, second=0, microsecond=0)
    if current_time > run_at:
        run_at += timedelta(days=1)
    return max((run_at - current_time).total_seconds(), 0)


def run_embedding_worker_once(settings) -> dict[str, int]:
    db = build_database(settings)
    time_service = TimeService(settings.app_timezone)
    runtime = build_learning_runtime(db, time_service)
    embedding_runtime = build_user_import_embedding_runtime(runtime)
    db.connect()
    db.run_migrations()
    try:
        return run_embedding_tick(db, embedding_runtime, time_service)
    finally:
        db.close()


def run_embedding_worker_loop(settings) -> None:
    db = build_database(settings)
    time_service = TimeService(settings.app_timezone)
    runtime = build_learning_runtime(db, time_service)
    embedding_runtime = build_user_import_embedding_runtime(runtime)
    db.connect()
    db.run_migrations()
    try:
        while True:
            sleep_seconds = resolve_sleep_until_next_daily_run_seconds(
                time_service.now(),
                settings.app_user_import_embedding_build_hour,
            )
            if sleep_seconds > 0:
                LOGGER.info(
                    "Embedding worker sleeping %.0f second(s) until %02d:00",
                    sleep_seconds,
                    settings.app_user_import_embedding_build_hour,
                )
                time.sleep(sleep_seconds)
            try:
                summary = run_embedding_tick(db, embedding_runtime, time_service)
                LOGGER.info("Embedding worker tick completed: %s", json.dumps(summary, ensure_ascii=False))
            except Exception:
                LOGGER.exception("Embedding worker tick failed")
            finally:
                clear_encoder_cache()
                gc.collect()
    finally:
        db.close()


def main() -> None:
    configure_logging()
    ensure_runtime_available()
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one embedding tick and exit.")
    args = parser.parse_args()
    settings = load_settings()
    if args.once:
        summary = run_embedding_worker_once(settings)
        print(json.dumps(summary, ensure_ascii=False))
        return
    run_embedding_worker_loop(settings)


if __name__ == "__main__":
    main()
