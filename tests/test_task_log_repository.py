from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

import pytest

from app.data_access.task_logs import TaskLogRepository
from app.models import TaskLog, User

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(
        self,
        *,
        row_by_id=None,
        scalars_rows=None,
        scalars_queue=None,
        scalar_values=None,
    ) -> None:
        self.row_by_id = row_by_id or {}
        self.scalars_rows = list(scalars_rows or [])
        self.scalars_queue = list(scalars_queue or [])
        self.scalar_values = list(scalar_values or [])
        self.added = []
        self.flushed = False
        self.scalar_statements = []
        self.scalars_statements = []

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True

    def get(self, model, primary_key):
        return self.row_by_id.get(primary_key)

    def scalar(self, statement):
        self.scalar_statements.append(statement)
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        self.scalars_statements.append(statement)
        if self.scalars_queue:
            return FakeScalarsResult(self.scalars_queue.pop(0))
        return FakeScalarsResult(self.scalars_rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_task_log(**overrides) -> TaskLog:
    values = {
        "id": 13,
        "task_type": "user_import_audio_build",
        "status": "processing",
        "user_uuid": USER_UUID,
        "source_type": "google_doc",
        "source_identifier": "doc-1",
        "import_job_id": 7,
        "description": "started",
        "error_text": None,
        "result_json": {"ready": 1},
        "started": datetime(2026, 5, 6, 10, 1, 0),
        "finished": None,
        "created": datetime(2026, 5, 6, 10, 1, 0),
        "updated": datetime(2026, 5, 6, 10, 1, 0),
    }
    values.update(overrides)
    return TaskLog(**values)


def test_create_validates_status_and_sets_finished_for_terminal_status() -> None:
    session = FakeSession(row_by_id={42: User(uuid=USER_UUID, telegram_user_id=42)})
    repository = TaskLogRepository(FakeSessionManager(session))
    current_time = datetime(2026, 5, 6, 10, 0, 0)

    with pytest.raises(ValueError, match="Unsupported task status"):
        repository.create(task_type="x", status="unknown", current_time=current_time)

    payload = repository.create(
        task_type="bound_google_doc_sync",
        status="success",
        current_time=current_time,
        telegram_user_id=42,
        result_json=None,
    )

    assert session.flushed is True
    assert session.added[0].finished == current_time
    assert session.added[0].result_json == {}
    assert payload["task_type"] == "bound_google_doc_sync"


def test_create_accepts_queued_status_without_finished_time() -> None:
    repository = TaskLogRepository(FakeSessionManager(FakeSession()))
    current_time = datetime(2026, 5, 6, 10, 0, 0)

    payload = repository.create_for_user_uuid(
        task_type="post_upgrade_google_doc_rescan",
        status="queued",
        current_time=current_time,
        user_uuid=USER_UUID,
    )

    assert payload["status"] == "queued"
    assert payload["finished"] is None


def test_update_changes_row_and_returns_none_for_missing_row() -> None:
    current_time = datetime(2026, 5, 6, 10, 2, 0)
    row = make_task_log()
    repository = TaskLogRepository(FakeSessionManager(FakeSession(row_by_id={13: row})))

    payload = repository.update(
        13,
        status="error",
        current_time=current_time,
        description="failed",
        error_text="boom",
        result_json={"error": "boom"},
        import_job_id=8,
    )

    assert payload is not None
    assert payload["status"] == "error"
    assert payload["result_json"] == {"error": "boom"}
    assert row.finished == current_time
    assert row.import_job_id == 8
    assert repository.update(404, status="success", current_time=current_time) is None


def test_get_returns_payload_or_none() -> None:
    repository = TaskLogRepository(FakeSessionManager(FakeSession(row_by_id={13: make_task_log()})))

    assert repository.get(13)["id"] == 13
    assert repository.get(404) is None


def test_list_admin_returns_paginated_rows() -> None:
    session = FakeSession(scalars_rows=[make_task_log()], scalar_values=[1])
    repository = TaskLogRepository(FakeSessionManager(session))

    payload = repository.list_admin(
        page=1,
        page_size=50,
        task_type=["user_import_audio_build"],
        status=["processing"],
        user_id=str(USER_UUID),
        import_job_id=7,
        search="audio",
    )

    assert payload["total"] == 1
    assert payload["pages"] == 1
    assert payload["items"][0]["id"] == 13
    statement = session.scalar_statements[0]
    compiled = str(statement)
    assert "billing_%" in statement.compile().params.values()
    assert "subscription_%" in statement.compile().params.values()
    assert "NOT" in compiled


def test_list_admin_can_scope_to_billing_or_all_task_logs() -> None:
    billing_session = FakeSession(scalars_rows=[make_task_log(task_type="billing_monobank_reconciliation")], scalar_values=[1])
    billing_repository = TaskLogRepository(FakeSessionManager(billing_session))

    billing_payload = billing_repository.list_admin(page=1, page_size=50, scope="billing")

    assert billing_payload["items"][0]["task_type"] == "billing_monobank_reconciliation"
    billing_statement = billing_session.scalar_statements[0]
    billing_compiled = str(billing_statement)
    assert "billing_%" in billing_statement.compile().params.values()
    assert "subscription_%" in billing_statement.compile().params.values()
    assert "NOT" not in billing_compiled

    all_session = FakeSession(scalars_rows=[make_task_log()], scalar_values=[1])
    all_repository = TaskLogRepository(FakeSessionManager(all_session))

    all_repository.list_admin(page=1, page_size=50, scope="all")

    all_statement = all_session.scalar_statements[0]
    all_compiled = str(all_statement)
    assert "billing_%" not in all_compiled
    assert "subscription_%" not in all_compiled

    with pytest.raises(ValueError, match="Unsupported task log scope"):
        all_repository.list_admin(page=1, page_size=50, scope="unknown")


def test_get_filter_metadata_returns_task_types_and_statuses() -> None:
    repository = TaskLogRepository(FakeSessionManager(FakeSession()))

    payload = repository.get_filter_metadata(scope="billing")

    assert payload["entity"] == "task_logs"
    assert payload["scope"] == "billing"
    assert payload["filters"][1]["options"] == [
        {"value": "billing_payment_reconciliation", "label": "billing_payment_reconciliation"},
        {"value": "billing_payment_success_recheck", "label": "billing_payment_success_recheck"},
        {"value": "billing_receipt_retry", "label": "billing_receipt_retry"},
        {"value": "billing_subscription_purchase_recovery", "label": "billing_subscription_purchase_recovery"},
        {"value": "subscription_daily_maintenance", "label": "subscription_daily_maintenance"},
        {"value": "subscription_trial_expiration", "label": "subscription_trial_expiration"},
    ]
    task_type_options = [item["value"] for item in payload["filters"][1]["options"]]
    assert "billing_monobank_receipt_retry" not in task_type_options
    assert "billing_monobank_reconciliation" not in task_type_options
    assert "billing_monobank_success_recheck" not in task_type_options
    assert payload["filters"][2]["options"] == [
        {"value": "queued", "label": "queued"},
        {"value": "processing", "label": "processing"},
        {"value": "success", "label": "success"},
        {"value": "error", "label": "error"},
        {"value": "fatal", "label": "fatal"},
    ]


def test_get_filter_metadata_returns_all_operation_task_types_without_billing() -> None:
    repository = TaskLogRepository(FakeSessionManager(FakeSession()))

    payload = repository.get_filter_metadata(scope="operations")

    options = [item["value"] for item in payload["filters"][1]["options"]]
    assert "bound_google_doc_sync" in options
    assert "post_upgrade_google_doc_rescan" in options
    assert "user_import_embedding_build" in options
    assert "user_vocabulary_import_job_process" in options
    assert "billing_payment_reconciliation" not in options
    assert "billing_payment_success_recheck" not in options
    assert "billing_receipt_retry" not in options
    assert "billing_monobank_reconciliation" not in options
    assert "subscription_daily_maintenance" not in options


def test_get_latest_for_import_job_returns_latest_payload_or_none() -> None:
    repository = TaskLogRepository(FakeSessionManager(FakeSession(scalar_values=[make_task_log(), None])))

    assert repository.get_latest_for_import_job(7, task_type="user_import_audio_build")["id"] == 13
    assert repository.get_latest_for_import_job(404) is None


def test_claim_queued_marks_tasks_processing() -> None:
    current_time = datetime(2026, 5, 6, 10, 2, 0)
    row = make_task_log(task_type="post_upgrade_google_doc_rescan", status="queued")
    repository = TaskLogRepository(FakeSessionManager(FakeSession(scalars_rows=[row])))

    payload = repository.claim_queued(
        task_type="post_upgrade_google_doc_rescan",
        current_time=current_time,
        limit=1,
    )

    assert payload[0]["status"] == "processing"
    assert row.status == "processing"
    assert row.updated == current_time


def test_iter_claim_queued_streams_until_queue_is_empty() -> None:
    current_time = datetime(2026, 5, 6, 10, 2, 0)
    first = make_task_log(id=13, task_type="post_upgrade_google_doc_rescan", status="queued")
    second = make_task_log(id=14, task_type="post_upgrade_google_doc_rescan", status="queued")
    repository = TaskLogRepository(FakeSessionManager(FakeSession(scalars_queue=[[first], [second], []])))

    payload = list(
        repository.iter_claim_queued(
            task_type="post_upgrade_google_doc_rescan",
            current_time=current_time,
        )
    )

    assert [row["id"] for row in payload] == [13, 14]
    assert first.status == "processing"
    assert second.status == "processing"


def test_requeue_stale_processing_marks_tasks_queued() -> None:
    current_time = datetime(2026, 5, 6, 10, 2, 0)
    row = make_task_log(
        task_type="post_upgrade_google_doc_rescan",
        status="processing",
        result_json={"telegram_user_id": 42},
    )
    repository = TaskLogRepository(FakeSessionManager(FakeSession(scalars_rows=[row])))

    count = repository.requeue_stale_processing(
        task_type="post_upgrade_google_doc_rescan",
        current_time=current_time,
        stale_before=datetime(2026, 5, 6, 8, 0, 0),
    )

    assert count == 1
    assert row.status == "queued"
    assert row.finished is None
    assert row.updated == current_time
    assert row.result_json["telegram_user_id"] == 42
    assert row.result_json["requeue_reason"] == "stale_processing"


def test_has_active_for_user_checks_queued_or_processing_tasks() -> None:
    repository = TaskLogRepository(FakeSessionManager(FakeSession(scalar_values=[1])))

    assert repository.has_active_for_user(
        task_type="post_upgrade_google_doc_rescan",
        user_uuid=USER_UUID,
    ) is True


def test_has_for_user_source_checks_requested_statuses() -> None:
    repository = TaskLogRepository(FakeSessionManager(FakeSession(scalar_values=[1, 0])))

    assert repository.has_for_user_source(
        task_type="post_upgrade_google_doc_rescan",
        user_uuid=USER_UUID,
        source_type="google_doc",
        source_identifier="doc-1",
        statuses={"queued", "processing", "success"},
    ) is True
    assert repository.has_for_user_source(
        task_type="post_upgrade_google_doc_rescan",
        user_uuid=USER_UUID,
        source_type="google_doc",
        source_identifier="",
        statuses={"success"},
    ) is False
