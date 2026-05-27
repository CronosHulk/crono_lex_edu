from __future__ import annotations

from app.application.client_reminders.settings_service import ClientReminderSettingsService


class FakeReminderSettingsStore:
    def __init__(self) -> None:
        self.profile = {
            "daily_reminder_hour": None,
            "reminder_weekdays": [],
            "reminder_schedule": [],
        }

    def get_profile(self, telegram_user_id: int):
        return self.profile

    def set_daily_reminder_hour(self, telegram_user_id: int, daily_reminder_hour: int | None) -> None:
        self.profile["daily_reminder_hour"] = daily_reminder_hour

    def list_reminder_schedule(self, telegram_user_id: int) -> list[dict[str, object]]:
        return list(self.profile["reminder_schedule"])

    def replace_reminder_schedule(self, telegram_user_id: int, schedule_rows: list[dict[str, object]]) -> list[dict[str, object]]:
        self.profile["reminder_schedule"] = sorted(
            [dict(row) for row in schedule_rows],
            key=lambda row: (int(row["weekday"]), int(row["hour"])),
        )
        enabled_rows = [row for row in self.profile["reminder_schedule"] if row["status"] == "enabled"]
        self.profile["daily_reminder_hour"] = int(enabled_rows[0]["hour"]) if enabled_rows else None
        self.profile["reminder_weekdays"] = sorted({int(row["weekday"]) for row in enabled_rows})
        return list(self.profile["reminder_schedule"])

    def get_reminder_weekdays(self, telegram_user_id: int) -> list[int]:
        return list(self.profile["reminder_weekdays"])

    def set_reminder_weekdays(self, telegram_user_id: int, weekdays: list[int]) -> None:
        self.profile["reminder_weekdays"] = sorted(set(weekdays))
        hours = sorted({int(row["hour"]) for row in self.profile["reminder_schedule"] if row["status"] == "enabled"})
        if not hours and self.profile["daily_reminder_hour"] is not None:
            hours = [int(self.profile["daily_reminder_hour"])]
        self.profile["reminder_schedule"] = [
            {"weekday": weekday, "hour": hour, "status": "enabled"}
            for weekday in self.profile["reminder_weekdays"]
            for hour in hours
        ]

    def clear_daily_reminder_settings(self, telegram_user_id: int) -> None:
        self.profile["daily_reminder_hour"] = None
        self.profile["reminder_weekdays"] = []
        self.profile["reminder_schedule"] = []


def build_service(store: FakeReminderSettingsStore | None = None, reminders_per_day: int = 1) -> ClientReminderSettingsService:
    store = store or FakeReminderSettingsStore()
    return ClientReminderSettingsService(store, store, resolve_reminders_per_day=lambda _telegram_user_id: reminders_per_day)


def test_reminder_settings_service_builds_hour_picker_layout() -> None:
    screen = build_service().handle_action(1, "uk", "m:n:period:day")

    assert screen.screen_id == "menu:notifications:hours:day"
    assert screen.metadata["button_row_widths"] == [2, 2, 2, 1, 1]
    assert screen.buttons[-2].action == "m:n:pick"
    assert screen.buttons[-1].action == "m:menu"


def test_reminder_settings_service_marks_current_period_and_hour() -> None:
    db = FakeReminderSettingsStore()
    db.profile["reminder_schedule"] = [{"weekday": 0, "hour": 10, "status": "enabled"}]
    service = build_service(db)

    period_screen = service.handle_action(1, "uk", "m:n:pick")
    hour_screen = service.handle_action(1, "uk", "m:n:period:morning")

    assert period_screen.buttons[0].text == "✓ Ранок"
    assert "✓ День" not in [button.text for button in period_screen.buttons]
    assert "✓ 10:00" in [button.text for button in hour_screen.buttons]


def test_reminder_settings_service_saves_hour_and_opens_weekdays() -> None:
    db = FakeReminderSettingsStore()

    screen = build_service(db).handle_action(1, "uk", "m:n:hour:10")

    assert db.profile["daily_reminder_hour"] == 10
    assert screen.screen_id == "menu:notifications:days"
    assert "10:00" in screen.text


def test_reminder_settings_service_adds_second_hour_when_subscription_allows_it() -> None:
    db = FakeReminderSettingsStore()
    db.profile["reminder_schedule"] = [{"weekday": 0, "hour": 9, "status": "enabled"}]

    screen = build_service(db, reminders_per_day=4).handle_action(1, "uk", "m:n:hour:10")

    assert db.profile["reminder_schedule"] == [
        {"weekday": 0, "hour": 9, "status": "enabled"},
        {"weekday": 0, "hour": 10, "status": "enabled"},
    ]
    assert screen.screen_id == "menu:notifications:hours:morning"
    assert "✓ 09:00" in [button.text for button in screen.buttons]
    assert "✓ 10:00" in [button.text for button in screen.buttons]


def test_reminder_settings_service_keeps_free_users_to_one_hour_per_day() -> None:
    db = FakeReminderSettingsStore()
    db.profile["reminder_schedule"] = [{"weekday": 0, "hour": 9, "status": "enabled"}]

    build_service(db, reminders_per_day=1).handle_action(1, "uk", "m:n:hour:10")

    assert db.profile["reminder_schedule"] == [{"weekday": 0, "hour": 9, "status": "enabled"}]


def test_reminder_settings_service_toggles_weekday() -> None:
    db = FakeReminderSettingsStore()

    screen = build_service(db).handle_action(1, "uk", "m:n:d:toggle:0")

    assert db.profile["reminder_weekdays"] == [0]
    assert screen.screen_id == "menu:notifications:days"


def test_reminder_settings_service_requires_weekday_before_save() -> None:
    screen = build_service().handle_action(1, "uk", "m:n:d:save")

    assert screen.screen_id == "menu:notifications:days"
    assert "Оберіть хоча б один день" in screen.text


def test_reminder_settings_service_saves_weekdays_to_menu() -> None:
    db = FakeReminderSettingsStore()
    db.profile["reminder_weekdays"] = [0, 2, 4]

    screen = build_service(db).handle_action(1, "uk", "m:n:d:save")

    assert screen.screen_id == "menu:notifications"
    assert "Пн, Ср, Пт" in screen.text


def test_reminder_settings_service_disables_reminders() -> None:
    db = FakeReminderSettingsStore()
    db.profile["daily_reminder_hour"] = 10
    db.profile["reminder_weekdays"] = [0, 1]

    screen = build_service(db).handle_action(1, "uk", "m:n:disable")

    assert db.profile["daily_reminder_hour"] is None
    assert db.profile["reminder_weekdays"] == []
    assert "вимкнено" in screen.text.lower()


def test_reminder_settings_service_invalid_payloads_fall_back_to_menu() -> None:
    service = build_service()

    assert service.handle_action(1, "uk", "m:n:period:night").screen_id == "menu:notifications"
    assert service.handle_action(1, "uk", "m:n:hour:25").screen_id == "menu:notifications"
    assert service.handle_action(1, "uk", "other") is None
