from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from app.user_import.services.bound_google_doc_sync_service import (
    UserImportBoundGoogleDocSyncService,
)


class FakeTaskLogRepository(list[dict[str, Any]]):
    def create(self, **kwargs: Any) -> dict[str, Any]:
        task_log = {"id": len(self) + 1, **kwargs}
        self.append(task_log)
        return task_log

    def create_for_user_uuid(self, **kwargs: Any) -> dict[str, Any]:
        return self.create(**kwargs)

    def update(self, task_log_id: int, **kwargs: Any) -> None:
        self[task_log_id - 1].update(kwargs)

    def claim_queued(self, *, task_type: str, current_time: datetime, limit: int) -> list[dict[str, Any]]:
        payload = []
        for row in self:
            if row.get("task_type") == task_type and row.get("status") == "queued":
                row["status"] = "processing"
                row["updated"] = current_time
                payload.append(dict(row))
                if len(payload) >= limit:
                    break
        return payload

    def has_active_for_user(self, *, task_type: str, user_uuid: str, statuses: set[str] | None = None) -> bool:
        active_statuses = statuses or {"queued", "processing"}
        return any(
            row.get("task_type") == task_type
            and row.get("user_uuid") == user_uuid
            and row.get("status") in active_statuses
            for row in self
        )

    def has_for_user_source(
        self,
        *,
        task_type: str,
        user_uuid: str,
        source_identifier: str,
        statuses: set[str],
        source_type: str | None = None,
    ) -> bool:
        return any(
            row.get("task_type") == task_type
            and row.get("user_uuid") == user_uuid
            and row.get("source_identifier") == source_identifier
            and row.get("status") in statuses
            and (source_type is None or row.get("source_type") == source_type)
            for row in self
        )


class FakeBoundSyncDb:
    def __init__(self) -> None:
        self.settings = SimpleNamespace()
        self.rows: list[dict[str, Any]] = []
        self.claim_calls: list[dict[str, Any]] = []
        self.task_logs = FakeTaskLogRepository()
        self.jobs: dict[int, dict[str, Any]] = {}
        self.unfinished_items: dict[int, list[dict[str, Any]]] = {}
        self.completed_jobs: list[dict[str, Any]] = []
        self.bound_doc: dict[str, Any] | None = None
        self.post_upgrade_candidates: list[dict[str, Any]] = []
        self.post_upgrade_candidate_calls: list[dict[str, Any]] = []

    @property
    def user_import_google_docs(self) -> FakeBoundSyncDb:
        return self

    def claim_due_syncs(
        self,
        current_time: datetime,
        sync_hour: int,
        sync_interval_days: int,
        claimed_until: datetime,
        *,
        sync_weekdays: list[int] | None = None,
        limit: int,
    ) -> list[dict[str, Any]]:
        self.claim_calls.append(
            {
                "current_time": current_time,
                "sync_hour": sync_hour,
                "sync_interval_days": sync_interval_days,
                "sync_weekdays": sync_weekdays,
                "claimed_until": claimed_until,
                "limit": limit,
            }
        )
        return self.rows[:limit]

    def get_bound_doc_for_telegram_user(self, telegram_user_id: int) -> dict[str, Any] | None:
        if self.bound_doc is None:
            return None
        if int(self.bound_doc["telegram_user_id"]) != telegram_user_id:
            return None
        return dict(self.bound_doc)

    def list_post_upgrade_rescan_candidates(
        self,
        *,
        current_time: datetime,
        paid_plan_keys: set[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        self.post_upgrade_candidate_calls.append(
            {
                "current_time": current_time,
                "paid_plan_keys": paid_plan_keys,
                "limit": limit,
            }
        )
        return [dict(row) for row in self.post_upgrade_candidates[:limit]]

    @property
    def user_import_jobs(self) -> FakeBoundSyncDb:
        return self

    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if job is None or job["telegram_user_id"] != telegram_user_id:
            return None
        return dict(job)

    def list_unfinished_items(self, job_id: int) -> list[dict[str, Any]]:
        return list(self.unfinished_items.get(job_id, []))

    def complete(self, job_id: int, *, status: str, current_time: datetime) -> None:
        self.completed_jobs.append({"job_id": job_id, "status": status, "current_time": current_time})


class FakeSyncProcessor:
    def __init__(self) -> None:
        self.process_results: dict[int, dict[str, Any] | Exception] = {}
        self.process_calls: list[dict[str, Any]] = []
        self.failure_calls: list[dict[str, Any]] = []

    def process_bound_google_doc_sync_row(
        self,
        row: dict[str, Any],
        current_time: datetime,
        *,
        task_log_id: int,
        max_import_entries: int | None = None,
        task_scope: str = "bound_google_doc_sync",
        restart_from_beginning: bool = False,
    ) -> dict[str, Any]:
        self.process_calls.append(
            {
                "row": row,
                "current_time": current_time,
                "task_log_id": task_log_id,
                "max_import_entries": max_import_entries,
                "task_scope": task_scope,
                "restart_from_beginning": restart_from_beginning,
            }
        )
        result = self.process_results.get(int(row["telegram_user_id"]), {"created_import_job_id": 900})
        if isinstance(result, Exception):
            raise result
        return result

    def mark_bound_google_doc_sync_failed(
        self,
        row: dict[str, Any],
        current_time: datetime,
        error: Exception,
        *,
        task_log_id: int,
        build_task_error_context: Any,
        build_next_retry_at: Any,
    ) -> None:
        self.failure_calls.append(
            {
                "row": row,
                "current_time": current_time,
                "error": error,
                "task_log_id": task_log_id,
                "error_context": build_task_error_context(task_log_id=task_log_id),
                "next_retry_at": build_next_retry_at(current_time, 2),
            }
        )


def build_service(
    db: FakeBoundSyncDb,
    sync_processor: FakeSyncProcessor,
    *,
    prepare_import_job_items: Any = None,
) -> UserImportBoundGoogleDocSyncService:
    return UserImportBoundGoogleDocSyncService(
        db,
        db.user_import_google_docs,
        sync_processor,  # type: ignore[arg-type]
        build_task_error_context=lambda **kwargs: {"context": kwargs},
        build_next_retry_at=lambda current_time, retry_count: current_time + timedelta(minutes=retry_count),
        max_doc_syncs_per_run=2,
        prepare_import_job_items=prepare_import_job_items,
    )


def test_enqueue_due_bound_google_doc_imports_updates_success_task_log() -> None:
    current_time = datetime(2026, 4, 26, 2, 0, 0)
    claimed_until = current_time + timedelta(minutes=15)
    db = FakeBoundSyncDb()
    db.rows = [{"telegram_user_id": 42, "source_identifier": "doc"}]
    sync_processor = FakeSyncProcessor()
    sync_processor.process_results[42] = {"created_import_job_id": 77, "queued_new_words_count": 2}

    build_service(db, sync_processor).enqueue_due_bound_google_doc_imports(current_time, claimed_until)

    assert db.claim_calls == [
        {
            "current_time": current_time,
            "sync_hour": 0,
            "sync_interval_days": 3,
            "sync_weekdays": None,
            "claimed_until": claimed_until,
            "limit": 2,
        }
    ]
    assert sync_processor.process_calls[0]["task_log_id"] == 1
    assert db.task_logs[0]["status"] == "success"
    assert db.task_logs[0]["result_json"] == {"created_import_job_id": 77, "queued_new_words_count": 2}
    assert db.task_logs[0]["import_job_id"] == 77


def test_enqueue_due_bound_google_doc_imports_marks_failed_sync_and_continues() -> None:
    current_time = datetime(2026, 4, 26, 2, 0, 0)
    claimed_until = current_time + timedelta(minutes=15)
    db = FakeBoundSyncDb()
    db.rows = [
        {"telegram_user_id": 42, "source_identifier": "bad-doc"},
        {"telegram_user_id": 43, "source_identifier": "good-doc"},
    ]
    sync_processor = FakeSyncProcessor()
    failure = RuntimeError("provider down")
    sync_processor.process_results[42] = failure
    sync_processor.process_results[43] = {"created_import_job_id": 78}

    build_service(db, sync_processor).enqueue_due_bound_google_doc_imports(current_time, claimed_until)

    assert sync_processor.failure_calls[0]["row"] == {"telegram_user_id": 42, "source_identifier": "bad-doc"}
    assert sync_processor.failure_calls[0]["error"] is failure
    assert sync_processor.failure_calls[0]["task_log_id"] == 1
    assert sync_processor.failure_calls[0]["error_context"] == {"context": {"task_log_id": 1}}
    assert sync_processor.failure_calls[0]["next_retry_at"] == current_time + timedelta(minutes=2)
    assert db.task_logs[1]["status"] == "success"


def test_enqueue_due_bound_google_doc_imports_uses_default_sync_interval_days() -> None:
    current_time = datetime(2026, 4, 26, 2, 0, 0)
    db = FakeBoundSyncDb()
    sync_processor = FakeSyncProcessor()

    build_service(db, sync_processor).enqueue_due_bound_google_doc_imports(
        current_time,
        current_time + timedelta(minutes=15),
    )

    assert db.claim_calls[0]["sync_interval_days"] == 3
    assert db.claim_calls[0]["sync_weekdays"] is None


def test_enqueue_due_bound_google_doc_imports_passes_weekday_preset() -> None:
    current_time = datetime(2026, 4, 26, 2, 0, 0)
    db = FakeBoundSyncDb()
    db.settings = SimpleNamespace()
    db.app_settings = SimpleNamespace(
        get_value=lambda _key: {
            "google_doc_sync_weekdays": [0, 2, 4],
        }
    )
    sync_processor = FakeSyncProcessor()

    build_service(db, sync_processor).enqueue_due_bound_google_doc_imports(
        current_time,
        current_time + timedelta(minutes=15),
    )

    assert db.claim_calls[0]["sync_weekdays"] == [0, 2, 4]


def test_process_and_failure_methods_delegate_to_processor_protocol() -> None:
    current_time = datetime(2026, 4, 26, 2, 0, 0)
    db = FakeBoundSyncDb()
    sync_processor = FakeSyncProcessor()
    service = build_service(db, sync_processor)
    row = {"telegram_user_id": 42, "source_identifier": "doc"}

    assert service.sync_processor is sync_processor
    assert service.process_bound_google_doc_sync_row(row, current_time, task_log_id=5) == {"created_import_job_id": 900}
    service.mark_bound_google_doc_sync_failed(row, current_time, RuntimeError("boom"), task_log_id=6)

    assert sync_processor.process_calls[0] == {
        "row": row,
        "current_time": current_time,
        "task_log_id": 5,
        "max_import_entries": None,
        "task_scope": "bound_google_doc_sync",
        "restart_from_beginning": False,
    }
    assert sync_processor.failure_calls[0]["task_log_id"] == 6


def test_process_bound_google_doc_sync_prepares_created_job_immediately() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.jobs[77] = {"id": 77, "telegram_user_id": 42}
    sync_processor = FakeSyncProcessor()
    sync_processor.process_results[42] = {"created_import_job_id": 77}
    prepare_calls: list[dict[str, Any]] = []

    def prepare_import_job_items(job: dict[str, Any], current_time: datetime, *, task_log_id: int | None) -> None:
        prepare_calls.append({"job": job, "current_time": current_time, "task_log_id": task_log_id})

    service = build_service(db, sync_processor, prepare_import_job_items=prepare_import_job_items)

    result = service.process_bound_google_doc_sync_row(
        {"telegram_user_id": 42, "source_identifier": "doc"},
        current_time,
        task_log_id=5,
    )

    assert result == {"created_import_job_id": 77}
    assert prepare_calls == [{"job": {"id": 77, "telegram_user_id": 42}, "current_time": current_time, "task_log_id": 5}]
    assert db.completed_jobs == [{"job_id": 77, "status": "completed", "current_time": current_time}]


def test_process_bound_google_doc_sync_keeps_job_open_when_items_remain_unfinished() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.jobs[77] = {"id": 77, "telegram_user_id": 42}
    db.unfinished_items[77] = [{"id": 1, "status": "pending"}]
    sync_processor = FakeSyncProcessor()
    sync_processor.process_results[42] = {"created_import_job_id": 77}

    service = build_service(
        db,
        sync_processor,
        prepare_import_job_items=lambda job, current_time, task_log_id=None: None,
    )

    service.process_bound_google_doc_sync_row(
        {"telegram_user_id": 42, "source_identifier": "doc"},
        current_time,
        task_log_id=5,
    )

    assert db.completed_jobs == []


def test_post_upgrade_rescan_uses_bound_doc_and_300_word_restart_scope() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.bound_doc = {"telegram_user_id": 42, "source_identifier": "doc"}
    db.jobs[77] = {"id": 77, "telegram_user_id": 42}
    sync_processor = FakeSyncProcessor()
    sync_processor.process_results[42] = {"created_import_job_id": 77, "queued_new_words_count": 3}

    result = build_service(db, sync_processor).rescan_after_plan_upgrade(
        telegram_user_id=42,
        user_uuid="11111111-1111-4111-8111-111111111111",
        current_time=current_time,
    )

    assert result == {"created_import_job_id": 77, "queued_new_words_count": 3}
    assert sync_processor.process_calls[0]["max_import_entries"] == 300
    assert sync_processor.process_calls[0]["task_scope"] == "post_upgrade_google_doc_rescan"
    assert sync_processor.process_calls[0]["restart_from_beginning"] is True
    assert sync_processor.process_calls[0]["row"]["user_uuid"] == "11111111-1111-4111-8111-111111111111"
    assert db.task_logs[0]["task_type"] == "post_upgrade_google_doc_rescan"
    assert db.task_logs[0]["status"] == "success"
    assert db.task_logs[0]["result_json"]["rescan_limit"] == 300


def test_queue_post_upgrade_rescan_creates_queued_task_without_processing_doc() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.bound_doc = {"telegram_user_id": 42, "source_identifier": "doc"}
    sync_processor = FakeSyncProcessor()

    result = build_service(db, sync_processor).queue_post_upgrade_rescan(
        telegram_user_id=42,
        user_uuid="11111111-1111-4111-8111-111111111111",
        current_time=current_time,
    )

    assert result == {"status": "queued", "task_log_id": 1, "rescan_limit": 300}
    assert db.task_logs[0]["status"] == "queued"
    assert db.task_logs[0]["task_type"] == "post_upgrade_google_doc_rescan"
    assert db.task_logs[0]["user_uuid"] == "11111111-1111-4111-8111-111111111111"
    assert sync_processor.process_calls == []


def test_queue_post_upgrade_rescan_reuses_active_task_for_user() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.bound_doc = {"telegram_user_id": 42, "source_identifier": "doc"}
    db.task_logs.create(
        task_type="post_upgrade_google_doc_rescan",
        status="processing",
        current_time=current_time,
        user_uuid="11111111-1111-4111-8111-111111111111",
        source_type="google_doc",
        source_identifier="doc",
        result_json={"telegram_user_id": 42, "rescan_limit": 300},
    )
    sync_processor = FakeSyncProcessor()

    result = build_service(db, sync_processor).queue_post_upgrade_rescan(
        telegram_user_id=42,
        user_uuid="11111111-1111-4111-8111-111111111111",
        current_time=current_time,
    )

    assert result == {"status": "queued", "task_log_id": None, "rescan_limit": 300}
    assert len(db.task_logs) == 1
    assert sync_processor.process_calls == []


def test_queue_post_upgrade_rescan_reuses_success_task_for_same_doc() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.bound_doc = {"telegram_user_id": 42, "source_identifier": "doc"}
    db.task_logs.create(
        task_type="post_upgrade_google_doc_rescan",
        status="success",
        current_time=current_time,
        user_uuid="11111111-1111-4111-8111-111111111111",
        source_type="google_doc",
        source_identifier="doc",
        result_json={"telegram_user_id": 42, "rescan_limit": 300},
    )
    sync_processor = FakeSyncProcessor()

    result = build_service(db, sync_processor).queue_post_upgrade_rescan(
        telegram_user_id=42,
        user_uuid="11111111-1111-4111-8111-111111111111",
        current_time=current_time + timedelta(hours=1),
    )

    assert result == {"status": "queued", "task_log_id": None, "rescan_limit": 300}
    assert len(db.task_logs) == 1
    assert sync_processor.process_calls == []


def test_enqueue_post_upgrade_rescans_processes_queued_task() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.task_logs.create(
        task_type="post_upgrade_google_doc_rescan",
        status="queued",
        current_time=current_time,
        user_uuid="11111111-1111-4111-8111-111111111111",
        source_type="google_doc",
        source_identifier="doc",
        result_json={"telegram_user_id": 42, "rescan_limit": 300},
    )
    db.jobs[77] = {"id": 77, "telegram_user_id": 42}
    sync_processor = FakeSyncProcessor()
    sync_processor.process_results[42] = {"created_import_job_id": 77, "queued_new_words_count": 3}

    build_service(db, sync_processor).enqueue_post_upgrade_rescans(
        current_time,
        current_time + timedelta(minutes=15),
    )

    assert sync_processor.process_calls[0]["max_import_entries"] == 300
    assert sync_processor.process_calls[0]["task_scope"] == "post_upgrade_google_doc_rescan"
    assert sync_processor.process_calls[0]["restart_from_beginning"] is True
    assert db.task_logs[0]["status"] == "success"
    assert db.task_logs[0]["import_job_id"] == 77


def test_enqueue_post_upgrade_rescans_queues_missing_paid_doc_rescan_before_processing() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.post_upgrade_candidates = [
        {
            "telegram_user_id": 42,
            "user_uuid": "11111111-1111-4111-8111-111111111111",
            "source_identifier": "doc",
        }
    ]
    db.jobs[77] = {"id": 77, "telegram_user_id": 42}
    sync_processor = FakeSyncProcessor()
    sync_processor.process_results[42] = {"created_import_job_id": 77, "queued_new_words_count": 3}

    build_service(db, sync_processor).enqueue_post_upgrade_rescans(
        current_time,
        current_time + timedelta(minutes=15),
    )

    assert db.post_upgrade_candidate_calls[0]["paid_plan_keys"] == {"premium", "premium_plus"}
    assert db.task_logs[0]["task_type"] == "post_upgrade_google_doc_rescan"
    assert db.task_logs[0]["status"] == "success"
    assert sync_processor.process_calls[0]["restart_from_beginning"] is True


def test_enqueue_post_upgrade_rescans_does_not_repeat_success_for_same_paid_doc() -> None:
    first_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.post_upgrade_candidates = [
        {
            "telegram_user_id": 42,
            "user_uuid": "11111111-1111-4111-8111-111111111111",
            "source_identifier": "doc",
        }
    ]
    db.jobs[77] = {"id": 77, "telegram_user_id": 42}
    sync_processor = FakeSyncProcessor()
    sync_processor.process_results[42] = {"created_import_job_id": 77, "queued_new_words_count": 3}
    service = build_service(db, sync_processor)

    service.enqueue_post_upgrade_rescans(first_time, first_time + timedelta(minutes=15))
    service.enqueue_post_upgrade_rescans(first_time + timedelta(hours=1), first_time + timedelta(hours=1, minutes=15))

    assert db.post_upgrade_candidate_calls[0]["paid_plan_keys"] == {"premium", "premium_plus"}
    assert len(db.post_upgrade_candidate_calls) == 2
    assert len(db.task_logs) == 1
    assert db.task_logs[0]["status"] == "success"
    assert len(sync_processor.process_calls) == 1


def test_enqueue_post_upgrade_rescans_skips_preexisting_duplicate_queued_task() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.task_logs.create(
        task_type="post_upgrade_google_doc_rescan",
        status="success",
        current_time=current_time,
        user_uuid="11111111-1111-4111-8111-111111111111",
        source_type="google_doc",
        source_identifier="doc",
        result_json={"telegram_user_id": 42, "rescan_limit": 300},
    )
    db.task_logs.create(
        task_type="post_upgrade_google_doc_rescan",
        status="queued",
        current_time=current_time,
        user_uuid="11111111-1111-4111-8111-111111111111",
        source_type="google_doc",
        source_identifier="doc",
        result_json={"telegram_user_id": 42, "rescan_limit": 300},
    )
    sync_processor = FakeSyncProcessor()

    build_service(db, sync_processor).enqueue_post_upgrade_rescans(
        current_time + timedelta(hours=1),
        current_time + timedelta(hours=1, minutes=15),
    )

    assert len(db.task_logs) == 2
    assert db.task_logs[1]["status"] == "success"
    assert db.task_logs[1]["result_json"]["skipped_reason"] == "post_upgrade_rescan_already_completed"
    assert sync_processor.process_calls == []


def test_enqueue_post_upgrade_rescans_streams_all_queued_tasks() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    sync_processor = FakeSyncProcessor()
    for index in range(12):
        telegram_user_id = 100 + index
        db.task_logs.create(
            task_type="post_upgrade_google_doc_rescan",
            status="queued",
            current_time=current_time,
            user_uuid=f"11111111-1111-4111-8111-1111111111{index:02d}",
            source_type="google_doc",
            source_identifier=f"doc-{index}",
            result_json={"telegram_user_id": telegram_user_id, "rescan_limit": 300},
        )
        sync_processor.process_results[telegram_user_id] = {
            "created_import_job_id": None,
            "queued_new_words_count": 0,
        }

    build_service(db, sync_processor).enqueue_post_upgrade_rescans(
        current_time,
        current_time + timedelta(minutes=15),
    )

    assert len(sync_processor.process_calls) == 12
    assert {row["status"] for row in db.task_logs} == {"success"}


def test_post_upgrade_rescan_returns_safe_failure_payload() -> None:
    current_time = datetime(2026, 5, 3, 12, 0, 0)
    db = FakeBoundSyncDb()
    db.bound_doc = {"telegram_user_id": 42, "source_identifier": "doc"}
    sync_processor = FakeSyncProcessor()
    sync_processor.process_results[42] = RuntimeError("secret provider token leaked")

    result = build_service(db, sync_processor).rescan_after_plan_upgrade(
        telegram_user_id=42,
        user_uuid="11111111-1111-4111-8111-111111111111",
        current_time=current_time,
    )

    assert result == {
        "status": "failed",
        "error": "Post-upgrade Google Doc rescan failed",
        "task_log_id": 1,
    }
    assert "secret" not in result["error"]
    assert sync_processor.failure_calls[0]["task_log_id"] == 1
