from __future__ import annotations

from datetime import datetime

from app.application.client_reminders.action_service import ClientReminderActionService
from app.contracts import ScreenModel


class FakeReminderTrainingSchedules:
    def __init__(self) -> None:
        self.schedules = {
            501: {
                "id": 501,
                "telegram_user_id": 11,
                "schedule_type": "daily",
                "scheduled_for": datetime(2026, 4, 6, 11, 0, 0),
                "status": "pending",
            }
        }
        self.updated_statuses: list[tuple[int, str]] = []

    def get(self, schedule_id: int):
        return self.schedules.get(schedule_id)

    def update_status(self, schedule_id: int, status: str) -> None:
        self.updated_statuses.append((schedule_id, status))


class CaptureReminderCallbacks:
    def __init__(self) -> None:
        self.current_time = datetime(2026, 4, 6, 10, 7, 0)
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def now(self) -> datetime:
        self.calls.append(("now", (), {}))
        return self.current_time

    def menu(self, telegram_user_id: int, locale: str, **kwargs) -> ScreenModel:
        self.calls.append(("menu", (telegram_user_id, locale), kwargs))
        return ScreenModel(screen_id="menu", text=str(kwargs.get("notice") or ""), metadata={"force_resend": bool(kwargs.get("force_resend"))})

    def start_learning(self, telegram_user_id: int, locale: str, **kwargs) -> ScreenModel:
        self.calls.append(("start", (telegram_user_id, locale), kwargs))
        return ScreenModel(screen_id="start", text="start")


def build_service(
    training_schedules: FakeReminderTrainingSchedules,
    callbacks: CaptureReminderCallbacks,
) -> ClientReminderActionService:
    return ClientReminderActionService(
        training_schedules,
        current_time=callbacks.now,
        build_menu_screen=callbacks.menu,
        start_learning=callbacks.start_learning,
    )


def test_reminder_action_start_uses_owned_schedule() -> None:
    db = FakeReminderTrainingSchedules()
    callbacks = CaptureReminderCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "r:start:501")

    assert screen is not None
    assert screen.screen_id == "start"
    assert callbacks.calls[-1] == ("start", (11, "uk"), {"schedule": db.schedules[501]})


def test_reminder_action_snooze_falls_back_as_unknown_action() -> None:
    db = FakeReminderTrainingSchedules()
    callbacks = CaptureReminderCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "r:snooze:501")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert screen.metadata["force_resend"] is False
    assert db.updated_statuses == []


def test_reminder_action_skip_marks_schedule_skipped() -> None:
    db = FakeReminderTrainingSchedules()
    callbacks = CaptureReminderCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "r:skip:501")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert screen.text == ""
    assert screen.metadata["force_resend"] is True
    assert db.updated_statuses == [(501, "skipped")]


def test_reminder_action_complete_marks_schedule_completed() -> None:
    db = FakeReminderTrainingSchedules()
    callbacks = CaptureReminderCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "r:complete:501")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert "виконаним" in screen.text
    assert screen.metadata["force_resend"] is True
    assert db.updated_statuses == [(501, "completed")]


def test_reminder_action_keep_leaves_schedule_pending() -> None:
    db = FakeReminderTrainingSchedules()
    callbacks = CaptureReminderCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "r:keep:501")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert screen.text == ""
    assert screen.metadata["force_resend"] is True
    assert db.updated_statuses == []


def test_reminder_action_complete_ignores_stale_or_completed_schedule() -> None:
    db = FakeReminderTrainingSchedules()
    db.schedules[501]["scheduled_for"] = datetime(2026, 4, 6, 13, 0, 1)
    callbacks = CaptureReminderCallbacks()

    late_screen = build_service(db, callbacks).handle_action(11, "uk", "r:complete:501")

    assert late_screen is not None
    assert late_screen.screen_id == "menu"
    assert late_screen.text == ""
    assert late_screen.metadata["force_resend"] is False
    assert db.updated_statuses == []

    db.schedules[501]["scheduled_for"] = datetime(2026, 4, 6, 11, 0, 0)
    db.schedules[501]["status"] = "completed"

    completed_screen = build_service(db, callbacks).handle_action(11, "uk", "r:complete:501")

    assert completed_screen is not None
    assert completed_screen.screen_id == "menu"
    assert completed_screen.text == ""
    assert completed_screen.metadata["force_resend"] is False
    assert db.updated_statuses == []


def test_reminder_action_keep_ignores_tomorrow_schedule() -> None:
    db = FakeReminderTrainingSchedules()
    db.schedules[501]["scheduled_for"] = datetime(2026, 4, 7, 9, 0, 0)
    callbacks = CaptureReminderCallbacks()

    screen = build_service(db, callbacks).handle_action(11, "uk", "r:keep:501")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert screen.metadata["force_resend"] is False
    assert db.updated_statuses == []


def test_reminder_action_rejects_foreign_schedule() -> None:
    db = FakeReminderTrainingSchedules()
    callbacks = CaptureReminderCallbacks()

    screen = build_service(db, callbacks).handle_action(99, "uk", "r:start:501")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert [call[0] for call in callbacks.calls] == ["menu"]


def test_reminder_action_ignores_unrelated_action() -> None:
    db = FakeReminderTrainingSchedules()
    callbacks = CaptureReminderCallbacks()

    assert build_service(db, callbacks).handle_action(11, "uk", "m:r") is None
    assert callbacks.calls == []
