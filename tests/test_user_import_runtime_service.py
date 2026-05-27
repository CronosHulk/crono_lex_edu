from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.user_import.services.runtime_service import UserImportRuntimeService


class FakeAppRuntimeStateRepository:
    def __init__(self) -> None:
        self.state: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        value = self.state.get(key)
        return {"key": key, "value_json": dict(value)} if value is not None else None

    def set(self, key: str, value_json: dict[str, Any], current_time: datetime) -> None:
        self.state[key] = dict(value_json)


class FakeRuntimeDb:
    def __init__(self) -> None:
        self.jobs = [{"id": 1, "telegram_user_id": 42}]
        self.claims: list[dict[str, Any]] = []
        self.user_dictionary = object()
        self.app_runtime_state = FakeAppRuntimeStateRepository()

    @property
    def user_import_jobs(self) -> FakeRuntimeDb:
        return self

    def claim_queued(
        self,
        *,
        current_time: datetime,
        claimed_until: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        self.claims.append(
            {"current_time": current_time, "claimed_until": claimed_until, "limit": limit}
        )
        return self.jobs


class FakeTimeService:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeJobProcessingService:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def process_claimed_job(self, job: dict[str, Any], **kwargs: Any) -> tuple[dict[str, Any], int]:
        self.calls.append(f"job:{job['id']}")
        return {"requests_used": 1}, 7


class FakeUserDictionaryBuildService:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.details_calls: list[dict[str, Any]] = []
        self.embedding_calls: list[dict[str, Any]] = []

    def should_run_details_phase(self, current_time: datetime) -> bool:
        return True

    def should_run_audio_phase(self, current_time: datetime) -> bool:
        return True

    def process_due_details_builds(self, **kwargs: Any) -> dict[str, int]:
        self.calls.append("user_details")
        self.details_calls.append(kwargs)
        return {"queued_for_audio_count": 1, "details_failed_count": 0}

    def process_due_embedding_builds(self, **kwargs: Any) -> dict[str, int]:
        self.calls.append("user_embedding")
        self.embedding_calls.append(kwargs)
        return {"ready_for_rotation_count": 1, "retry_scheduled_count": 0}

    def process_due_audio_builds(self, **kwargs: Any) -> dict[str, int]:
        self.calls.append("user_audio")
        return {
            "ready_for_rotation_count": 1,
            "queued_for_embedding_count": 0,
            "audio_failed_count": 0,
        }


class FakeNotificationService:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def dispatch_due_user_import_publish_notifications(self, current_time: datetime) -> list[str]:
        self.calls.append("notify:user_publish")
        return ["user_publish"]

    def dispatch_admin_audio_completion_notifications(self, summary: dict[str, Any]) -> list[str]:
        self.calls.append("notify:admin_audio")
        assert summary == {
            "ready_for_rotation_count": 1,
            "queued_for_embedding_count": 0,
            "audio_failed_count": 0,
        }
        return ["admin_audio"]

    def dispatch_admin_details_completion_notifications(
        self, summary: dict[str, Any], current_time: datetime
    ) -> list[str]:
        if not summary.get("phase_ran"):
            return []
        self.calls.append("notify:admin_details")
        assert summary == {
            "queued_for_audio_count": 1,
            "details_failed_count": 0,
            "phase_ran": True,
        }
        return ["admin_details"]

    def dispatch_due_user_import_summary_notifications(self, current_time: datetime) -> list[str]:
        self.calls.append("notify:user_summary")
        return ["user_summary"]


class FakeBoundGoogleDocSyncService:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def enqueue_due_bound_google_doc_imports(
        self, current_time: datetime, claimed_until: datetime
    ) -> None:
        self.calls.append("bound_sync")

    def enqueue_post_upgrade_rescans(self, current_time: datetime, claimed_until: datetime) -> None:
        self.calls.append("post_upgrade_rescan")


def build_service(
    *,
    db: FakeRuntimeDb | None = None,
    current_time: datetime | None = None,
    sync_provider_pricing_snapshots: (
        Callable[[FakeRuntimeDb, datetime], dict[str, Any]] | None
    ) = None,
) -> tuple[UserImportRuntimeService, FakeRuntimeDb, list[str], FakeUserDictionaryBuildService]:
    calls: list[str] = []
    db = db or FakeRuntimeDb()
    user_dictionary_build_service = FakeUserDictionaryBuildService(calls)
    service = UserImportRuntimeService(
        db,
        FakeTimeService(current_time or datetime(2026, 4, 26, 9, 0, 0)),
        job_processing_service=FakeJobProcessingService(calls),
        user_dictionary_build_service=user_dictionary_build_service,
        notification_service=FakeNotificationService(calls),
        bound_google_doc_sync_service=FakeBoundGoogleDocSyncService(calls),
        sync_provider_pricing_snapshots=sync_provider_pricing_snapshots
        or (lambda _db, _current_time: {}),
    )
    return service, db, calls, user_dictionary_build_service


def test_process_due_user_vocabulary_imports_runs_phases_and_notifications_in_order() -> None:
    service, db, calls, _ = build_service()

    notifications = service.process_due_user_vocabulary_imports()

    assert calls == [
        "user_details",
        "job:1",
        "user_audio",
        "notify:admin_details",
        "notify:user_publish",
        "notify:admin_audio",
        "notify:user_summary",
    ]
    assert notifications == ["admin_details", "user_publish", "admin_audio", "user_summary"]
    assert db.claims[0]["limit"] == 10


def test_process_due_user_vocabulary_imports_syncs_provider_pricing_snapshots() -> None:
    sync_calls: list[tuple[FakeRuntimeDb, datetime]] = []
    current_time = datetime(2026, 4, 26, 9, 0, 0)

    def sync_provider_pricing_snapshots(
        db: FakeRuntimeDb,
        current_time: datetime,
    ) -> dict[str, Any]:
        sync_calls.append((db, current_time))
        return {"synced": 1}

    service, db, _, _ = build_service(
        current_time=current_time,
        sync_provider_pricing_snapshots=sync_provider_pricing_snapshots,
    )

    service.process_due_user_vocabulary_imports()

    assert sync_calls == [(db, current_time)]


def test_process_due_user_vocabulary_imports_at_can_include_bound_sync_for_worker_path() -> None:
    service, _, calls, _ = build_service()

    service.process_due_user_vocabulary_imports_at(
        current_time=datetime(2026, 4, 26, 9, 0, 0),
        emit_notifications=False,
        include_bound_sync=True,
    )

    assert "bound_sync" in calls
    assert "post_upgrade_rescan" not in calls


def test_process_due_user_vocabulary_imports_at_can_skip_sync_and_notifications() -> None:
    service, _, calls, _ = build_service()

    notifications = service.process_due_user_vocabulary_imports_at(
        current_time=datetime(2026, 4, 26, 9, 0, 0),
        emit_notifications=False,
        include_bound_sync=False,
    )

    assert calls == ["user_details", "job:1", "user_audio"]
    assert notifications == []


def test_process_due_post_upgrade_rescans_runs_only_rescan_phase() -> None:
    service, _, calls, _ = build_service()

    notifications = service.process_due_post_upgrade_rescans()

    assert calls == ["post_upgrade_rescan"]
    assert notifications == []


def test_process_due_bound_google_doc_syncs_runs_only_bound_sync_phase() -> None:
    service, _, calls, _ = build_service()

    notifications = service.process_due_bound_google_doc_syncs()

    assert calls == ["bound_sync"]
    assert notifications == []


def test_process_due_import_scheduler_tick_runs_scheduler_phases_and_dedupes_details() -> None:
    service, db, calls, _ = build_service(current_time=datetime(2026, 4, 26, 9, 0, 0))

    notifications = service.process_due_import_scheduler_tick()
    second_notifications = service.process_due_import_scheduler_tick()

    assert calls == [
        "post_upgrade_rescan",
        "bound_sync",
        "user_details",
        "job:1",
        "user_audio",
        "notify:admin_details",
        "notify:user_publish",
        "notify:admin_audio",
        "notify:user_summary",
        "post_upgrade_rescan",
        "bound_sync",
        "job:1",
        "notify:user_publish",
        "notify:user_summary",
    ]
    assert notifications == ["admin_details", "user_publish", "admin_audio", "user_summary"]
    assert second_notifications == ["user_publish", "user_summary"]
    assert (
        db.app_runtime_state.state["user_import_details_schedule"]["last_schedule_key"]
        == "2026-04-26:2:all"
    )
    assert (
        db.app_runtime_state.state["user_import_audio_schedule"]["last_schedule_key"]
        == "2026-04-26:2:all"
    )


def test_process_due_user_import_embeddings_now_uses_runtime_embedding_gate() -> None:
    service, _, calls, user_dictionary_build_service = build_service()

    summary = service.process_due_user_import_embeddings_now()

    assert summary == {"ready_for_rotation_count": 1, "retry_scheduled_count": 0}
    assert calls == ["user_embedding"]
    assert user_dictionary_build_service.embedding_calls == [
        {"current_time": datetime(2026, 4, 26, 9, 0, 0), "force": False}
    ]


def test_process_user_import_attribute_queue_now_forces_details_build() -> None:
    service, _, calls, user_dictionary_build_service = build_service()
    current_time = datetime(2026, 5, 1, 9, 0, 0)

    service.process_user_import_attribute_queue_now(current_time)

    assert calls == ["user_details"]
    assert user_dictionary_build_service.details_calls == [
        {
            "current_time": current_time,
            "force": True,
        }
    ]
