from __future__ import annotations

from datetime import datetime

from app.application.client_learning.summary_service import ClientLearningSummaryService
from app.contracts import ScreenModel


class FakeSummaryLearningSessions:
    def __init__(self) -> None:
        self.sessions = {
            77: {
                "id": 77,
                "telegram_user_id": 11,
                "language_level_id": 1,
                "level_run_id": 101,
                "session_type": "regular",
                "completed": datetime(2026, 4, 6, 10, 0, 0),
            }
        }
        self.session_words = [
            {"en_uk_attempts": 1, "uk_en_attempts": 2, "gap_attempts": 1},
            {"en_uk_attempts": 3, "uk_en_attempts": 1, "gap_attempts": 2},
            {"en_uk_attempts": 1, "uk_en_attempts": 1, "gap_attempts": 1},
        ]

    def get_session(self, session_id: int):
        return self.sessions.get(session_id)

    def get_session_words(self, session_id: int):
        assert session_id == 77
        return self.session_words


class FakeSummaryUserProfiles:
    def __init__(self) -> None:
        self.profile: dict[str, object] | None = {"daily_reminder_hour": None, "reminder_weekdays": []}

    def get_profile(self, telegram_user_id: int):
        return self.profile


class FakeSummaryLearningProgress:
    def __init__(self) -> None:
        self.progress = {"learned_count": 2, "in_progress_count": 3, "needs_work_count": 1, "total_count": 6}

    def get_user_assignment_summary(self, telegram_user_id: int):
        assert telegram_user_id == 11
        return self.progress


class FakeSummaryTrainingSchedules:
    def __init__(self) -> None:
        self.schedules: dict[object, dict[str, object]] = {}

    def get_existing_for_date(self, telegram_user_id: int, target_date, *, schedule_types=None):
        row = self.schedules.get(target_date)
        if row is None:
            return None
        if schedule_types and row.get("schedule_type") not in schedule_types:
            return None
        return row


class FakeTimeService:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


class FakeReminderDisplay:
    def __init__(self, next_training=None) -> None:
        self.next_training = next_training
        self.calls: list[dict[str, object]] = []

    def get_display_next_training(self, **kwargs):
        self.calls.append(kwargs)
        return self.next_training


def build_menu_screen(telegram_user_id: int, locale: str) -> ScreenModel:
    return ScreenModel(screen_id="menu", text=f"menu:{telegram_user_id}:{locale}")


def build_service(
    learning_sessions: FakeSummaryLearningSessions | None = None,
    user_profiles: FakeSummaryUserProfiles | None = None,
    learning_progress: FakeSummaryLearningProgress | None = None,
    training_schedules: FakeSummaryTrainingSchedules | None = None,
    time_service: FakeTimeService | None = None,
    reminder_display: FakeReminderDisplay | None = None,
) -> tuple[ClientLearningSummaryService, FakeSummaryLearningSessions, FakeSummaryTrainingSchedules, FakeReminderDisplay]:
    learning_sessions = learning_sessions or FakeSummaryLearningSessions()
    user_profiles = user_profiles or FakeSummaryUserProfiles()
    learning_progress = learning_progress or FakeSummaryLearningProgress()
    training_schedules = training_schedules or FakeSummaryTrainingSchedules()
    reminder_display = reminder_display or FakeReminderDisplay()
    return (
        ClientLearningSummaryService(
            learning_sessions,
            user_profiles,
            learning_progress,
            time_service or FakeTimeService(datetime(2026, 4, 6, 12, 0, 0)),
            reminder_display,
            build_menu_screen=build_menu_screen,
        ),
        learning_sessions,
        training_schedules,
        reminder_display,
    )


def test_summary_service_returns_menu_for_missing_session() -> None:
    service, _, _, _ = build_service()

    screen = service.build_summary_screen(999, "uk")

    assert screen.screen_id == "menu"
    assert screen.text == "menu:0:uk"


def test_summary_service_builds_completion_error_metrics_and_finish_button() -> None:
    service, _, _, reminder_display = build_service()

    screen = service.build_summary_screen(77, "uk", notice="Saved")

    assert screen.screen_id == "summary:77"
    assert screen.notice_text == "Saved"
    assert "Супер, тренування завершено." in screen.text
    assert "Було допущено 4 помилки у 2 слова." in screen.text
    assert "Ми обовʼязково повторимо їх пізніше." in screen.text
    assert "Слова в процесі вивчення: 3 слова" in screen.text
    assert "Слова потребують доопрацювання: 1 слово" in screen.text
    assert "Вивчені слова: 2/6" in screen.text
    assert [(button.action, button.text) for button in screen.buttons] == [("m:menu", "Завершити тренування")]
    assert reminder_display.calls == [
        {
            "telegram_user_id": 11,
            "current_time": datetime(2026, 4, 6, 12, 0, 0),
            "reminder_hour": None,
            "reminder_weekdays": [],
        }
    ]


def test_summary_service_uses_no_error_completion_text() -> None:
    learning_sessions = FakeSummaryLearningSessions()
    learning_sessions.session_words = [
        {"en_uk_attempts": 1, "uk_en_attempts": 1, "gap_attempts": 1},
    ]
    service, _, _, _ = build_service(
        learning_sessions=learning_sessions,
    )

    screen = service.build_summary_screen(77, "uk")

    assert "Помилок не було." in screen.text
    assert "Ми обовʼязково повторимо їх пізніше." not in screen.text


def test_summary_service_adds_followup_notice() -> None:
    learning_sessions = FakeSummaryLearningSessions()
    learning_sessions.sessions[77]["session_type"] = "followup"
    service, _, _, _ = build_service(learning_sessions=learning_sessions)

    screen = service.build_summary_screen(77, "uk")

    assert "Вечірнє закріплення не зараховується" in screen.text


def test_summary_service_asks_about_upcoming_reminder_within_two_hours() -> None:
    service, _, _, _ = build_service(
        reminder_display=FakeReminderDisplay(
            {
                "id": 501,
                "telegram_user_id": 11,
                "schedule_type": "daily",
                "scheduled_for": datetime(2026, 4, 6, 13, 30, 0),
            }
        )
    )

    screen = service.build_summary_screen(77, "uk")

    assert "У вас є нагадування о 13:30. Воно ще актуальне?" in screen.text
    assert [(button.action, button.text) for button in screen.buttons] == [
        ("r:complete:501", "Пропустити"),
        ("r:keep:501", "Не пропускати"),
    ]


def test_summary_service_ignores_virtual_or_late_reminders() -> None:
    service, _, _, _ = build_service(
        reminder_display=FakeReminderDisplay(
            {
                "id": None,
                "telegram_user_id": 11,
                "schedule_type": "daily_config",
                "scheduled_for": datetime(2026, 4, 6, 13, 30, 0),
            }
        )
    )
    late_service, _, _, _ = build_service(
        reminder_display=FakeReminderDisplay(
            {
                "id": 502,
                "telegram_user_id": 11,
                "schedule_type": "daily",
                "scheduled_for": datetime(2026, 4, 6, 14, 30, 1),
            }
        )
    )

    assert [(button.action, button.text) for button in service.build_summary_screen(77, "uk").buttons] == [
        ("m:menu", "Завершити тренування")
    ]
    assert [(button.action, button.text) for button in late_service.build_summary_screen(77, "uk").buttons] == [
        ("m:menu", "Завершити тренування")
    ]


def test_summary_service_ignores_tomorrow_reminder_even_inside_two_hour_window() -> None:
    service, _, _, _ = build_service(
        time_service=FakeTimeService(datetime(2026, 4, 6, 23, 30, 0)),
        reminder_display=FakeReminderDisplay(
            {
                "id": 503,
                "telegram_user_id": 11,
                "schedule_type": "planned",
                "scheduled_for": datetime(2026, 4, 7, 0, 30, 0),
                "status": "pending",
            }
        ),
    )

    screen = service.build_summary_screen(77, "uk")

    assert "Воно ще актуальне?" not in screen.text
    assert [(button.action, button.text) for button in screen.buttons] == [
        ("m:menu", "Завершити тренування")
    ]
