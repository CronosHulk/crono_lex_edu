from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from app.contracts import ScreenModel
from app.user_import.services.notification_service import UserImportNotificationService


class FakeAppRuntimeStateRepository:
    def __init__(self) -> None:
        self.state: dict[str, Any] | None = None
        self.updates: list[tuple[str, dict[str, Any], datetime]] = []

    def get(self, key: str) -> dict[str, Any] | None:
        if self.state is None:
            return None
        return {"key": key, "value_json": self.state}

    def set(self, key: str, value_json: dict[str, Any], current_time: datetime) -> None:
        self.state = value_json
        self.updates.append((key, value_json, current_time))


class FakeNotificationDb:
    def __init__(self, profiles: list[dict[str, Any]]) -> None:
        self.profiles = profiles
        self.settings = SimpleNamespace(
            app_user_import_test_mode=False,
            app_admin_magic_link_ttl_minutes=5,
        )
        self.app_runtime_state = FakeAppRuntimeStateRepository()
        self.publish_jobs: list[dict[str, Any]] = []
        self.summary_jobs: list[dict[str, Any]] = []
        self.profiles_by_user_id: dict[int, dict[str, Any] | None] = {}
        self.items_by_job_id: dict[int, list[dict[str, Any]]] = {}
        self.requests = 0
        self.marked_publish_summary_sent: list[tuple[int, datetime]] = []
        self.marked_summary_sent: list[tuple[int, datetime]] = []
        self.import_report_counts = {"total_count": 0, "dictionary_count": 0, "user_dictionary_count": 0}
        self.import_report_requests: list[dict[str, datetime]] = []

    def list_super_admin_profiles(self) -> list[dict[str, Any]]:
        self.requests += 1
        return self.profiles

    @property
    def user_import_jobs(self) -> FakeNotificationDb:
        return self

    def list_completed_pending_publish_summary(self) -> list[dict[str, Any]]:
        return self.publish_jobs

    def list_completed_pending_summary(self) -> list[dict[str, Any]]:
        return self.summary_jobs

    @property
    def user_profiles(self) -> FakeNotificationDb:
        return self

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.profiles_by_user_id.get(telegram_user_id)

    def list_items(self, job_id: int) -> list[dict[str, Any]]:
        return self.items_by_job_id.get(job_id, [])

    def mark_publish_summary_sent(self, job_id: int, current_time: datetime) -> None:
        self.marked_publish_summary_sent.append((job_id, current_time))

    def mark_summary_sent(self, job_id: int, current_time: datetime) -> None:
        self.marked_summary_sent.append((job_id, current_time))

    @property
    def user_import_items(self) -> FakeNotificationDb:
        return self

    def count_import_report_sources(self, *, since: datetime, until: datetime) -> dict[str, int]:
        self.import_report_requests.append({"since": since, "until": until})
        return self.import_report_counts


def test_dispatch_admin_audio_completion_notifications_skips_empty_summary() -> None:
    db = FakeNotificationDb([{"telegram_user_id": 1, "chat_id": 10, "language_code": "uk"}])

    notifications = UserImportNotificationService(db, db.user_profiles).dispatch_admin_audio_completion_notifications({})

    assert notifications == []
    assert db.requests == 0


def test_dispatch_due_user_import_publish_notifications_builds_user_summary_and_marks_jobs() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeNotificationDb([])
    db.publish_jobs = [
        {"id": 10, "telegram_user_id": 1},
        {"id": 20, "telegram_user_id": 2},
    ]
    db.profiles_by_user_id = {
        1: {"chat_id": None, "language_code": "uk"},
        2: {"chat_id": 22, "language_code": "uk"},
    }
    db.items_by_job_id = {
        20: [{"status": "imported"}, {"status": "ready_for_publish"}, {"status": "imported"}],
    }
    summary_calls: list[tuple[int, str, int, int]] = []
    service = UserImportNotificationService(
        db,
        db.user_profiles,
        build_user_import_publish_summary_screen=lambda telegram_user_id, locale, job_id, priority_count: (
            summary_calls.append((telegram_user_id, locale, job_id, priority_count))
            or ScreenModel(screen_id="summary", text=f"{telegram_user_id}:{locale}:{job_id}:{priority_count}")
        ),
    )

    notifications = service.dispatch_due_user_import_publish_notifications(current_time)

    assert summary_calls == [(2, "uk", 20, 2)]
    assert len(notifications) == 1
    assert notifications[0].telegram_user_id == 2
    assert notifications[0].chat_id == 22
    assert notifications[0].screen.text == "2:uk:20:2"
    assert db.marked_publish_summary_sent == [(10, current_time), (20, current_time)]


def test_dispatch_due_user_import_publish_notifications_without_builder_returns_empty() -> None:
    db = FakeNotificationDb([])
    db.publish_jobs = [{"id": 10, "telegram_user_id": 1}]

    notifications = UserImportNotificationService(db, db.user_profiles).dispatch_due_user_import_publish_notifications(
        datetime(2026, 4, 26, 10, 0, 0)
    )

    assert notifications == []
    assert db.marked_publish_summary_sent == []


def test_dispatch_due_user_import_publish_notifications_marks_job_without_telegram_user_id() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeNotificationDb([])
    db.publish_jobs = [{"id": 10}]
    service = UserImportNotificationService(
        db,
        db.user_profiles,
        build_user_import_publish_summary_screen=lambda *args: ScreenModel(screen_id="summary", text="unused"),
    )

    notifications = service.dispatch_due_user_import_publish_notifications(current_time)

    assert notifications == []
    assert db.marked_publish_summary_sent == [(10, current_time)]


def test_dispatch_due_user_import_summary_notifications_builds_screen_and_marks_jobs() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeNotificationDb([])
    db.summary_jobs = [
        {"id": 10, "telegram_user_id": 1, "status": "completed", "last_error": None},
        {"id": 20, "telegram_user_id": 2, "status": "failed", "last_error": "broken"},
    ]
    db.profiles_by_user_id = {
        1: {"chat_id": None, "language_code": "uk"},
        2: {"chat_id": 22, "language_code": "en"},
    }
    db.items_by_job_id = {
        20: [{"lookup_word": "take over", "status": "failed"}],
    }
    summary_calls: list[dict[str, Any]] = []
    service = UserImportNotificationService(
        db,
        db.user_profiles,
        build_user_import_summary_screen=lambda **kwargs: (
            summary_calls.append(kwargs)
            or ScreenModel(screen_id="summary", text=f"{kwargs['locale']}:{kwargs['job_id']}:{kwargs['job_status']}:{kwargs['last_error']}")
        ),
    )

    notifications = service.dispatch_due_user_import_summary_notifications(current_time)

    assert len(notifications) == 1
    assert notifications[0].telegram_user_id == 2
    assert notifications[0].chat_id == 22
    assert notifications[0].screen.text == "uk:20:failed:broken"
    assert summary_calls == [
        {
            "telegram_user_id": 2,
            "locale": "uk",
            "job_id": 20,
            "items": [{"lookup_word": "take over", "status": "failed"}],
            "job_status": "failed",
            "last_error": "broken",
        }
    ]
    assert db.marked_summary_sent == [(10, current_time), (20, current_time)]


def test_dispatch_due_user_import_summary_notifications_marks_job_without_profile() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeNotificationDb([])
    db.summary_jobs = [{"id": 10, "telegram_user_id": 1, "status": "completed", "last_error": None}]
    service = UserImportNotificationService(
        db,
        db.user_profiles,
        build_user_import_summary_screen=lambda **kwargs: ScreenModel(screen_id="summary", text="unused"),
    )

    notifications = service.dispatch_due_user_import_summary_notifications(current_time)

    assert notifications == []
    assert db.marked_summary_sent == [(10, current_time)]


def test_dispatch_due_user_import_summary_notifications_marks_job_without_telegram_user_id() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeNotificationDb([])
    db.summary_jobs = [{"id": 10, "status": "completed", "last_error": None}]
    service = UserImportNotificationService(
        db,
        db.user_profiles,
        build_user_import_summary_screen=lambda **kwargs: ScreenModel(screen_id="summary", text="unused"),
    )

    notifications = service.dispatch_due_user_import_summary_notifications(current_time)

    assert notifications == []
    assert db.marked_summary_sent == [(10, current_time)]


def test_dispatch_due_user_import_summary_notifications_without_builder_returns_empty() -> None:
    db = FakeNotificationDb([])
    db.summary_jobs = [{"id": 10, "telegram_user_id": 1, "status": "completed"}]

    notifications = UserImportNotificationService(db, db.user_profiles).dispatch_due_user_import_summary_notifications(
        datetime(2026, 4, 26, 10, 0, 0)
    )

    assert notifications == []
    assert db.marked_summary_sent == []


def test_dispatch_admin_details_completion_notifications_builds_period_report() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    db = FakeNotificationDb(
        [
            {"telegram_user_id": 1, "chat_id": None, "language_code": "uk"},
            {"telegram_user_id": 2, "chat_id": 20, "language_code": "uk"},
        ]
    )
    db.app_runtime_state.state = {"last_report_at": "2026-04-25T10:00:00"}
    db.import_report_counts = {"total_count": 12, "dictionary_count": 7, "user_dictionary_count": 5}

    notifications = UserImportNotificationService(db, db.user_profiles).dispatch_admin_details_completion_notifications(
        {"phase_ran": True, "queued_for_audio_count": 3, "details_failed_count": 1},
        current_time,
    )

    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.screen.screen_id == "admin:details-summary"
    assert "Усього юзерами за період додано: 12 елементів." in notification.screen.text
    assert "Слів зі словників: 7 елементів." in notification.screen.text
    assert "Нових слів з новими деталями: 3 елементи." in notification.screen.text
    assert [button.action for button in notification.screen.buttons] == ["m:menu"]
    assert db.import_report_requests == [{"since": datetime(2026, 4, 25, 10, 0, 0), "until": current_time}]
    assert db.app_runtime_state.updates[-1] == (
        "user_import:admin_details_report",
        {"last_report_at": current_time.isoformat()},
        current_time,
    )


def test_dispatch_admin_audio_completion_notifications_stays_silent() -> None:
    db = FakeNotificationDb(
        [
            {"telegram_user_id": 1, "chat_id": None, "language_code": "uk"},
            {"telegram_user_id": 2, "chat_id": 20, "language_code": "uk"},
        ]
    )

    notifications = UserImportNotificationService(db, db.user_profiles).dispatch_admin_audio_completion_notifications(
        {
            "ready_for_rotation_count": 1,
            "queued_for_embedding_count": 2,
            "audio_failed_count": 3,
            "unresolved_backlog_count": 6,
            "backlog_words": [" mute ", "", "silent"],
        }
    )

    assert notifications == []
