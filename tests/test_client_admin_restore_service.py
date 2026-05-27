from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.client.admin_restore_service import ClientAdminRestoreService
from app.contracts import ScreenModel


class FakeTimeService:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


class FakeAdminRestoreStore:
    def __init__(self) -> None:
        self.restores: list[dict[str, Any]] = []
        self.profiles: dict[int, dict[str, Any] | None] = {}
        self.failed_restores: list[dict[str, Any]] = []
        self.claimed_at: datetime | None = None

    def claim_due_bot_restores(self, *, current_time: datetime, limit: int = 50) -> list[dict[str, Any]]:
        self.claimed_at = current_time
        return self.restores[:limit]

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.profiles.get(telegram_user_id)

    def mark_bot_restore_failed(self, restore_id: int, *, error_text: str, current_time: datetime) -> None:
        self.failed_restores.append(
            {
                "restore_id": restore_id,
                "error_text": error_text,
                "current_time": current_time,
            }
        )


def screen(screen_id: str) -> ScreenModel:
    return ScreenModel(screen_id=screen_id, text=screen_id)


def build_service(
    store: FakeAdminRestoreStore,
    *,
    current_time: datetime | None = None,
    fail_screen_id: str | None = None,
) -> ClientAdminRestoreService:
    def builder(screen_id: str):
        def build(_telegram_user_id: int, _locale: str, _notice: str) -> ScreenModel:
            if fail_screen_id == screen_id:
                raise RuntimeError("screen failed")
            return screen(screen_id)

        return build

    return ClientAdminRestoreService(
        store,
        store,
        FakeTimeService(current_time or datetime(2026, 4, 26, 12, 0, 0)),
        build_settings_screen=builder("settings"),
        build_user_import_screen=builder("import"),
        build_level_menu_screen=builder("levels"),
        build_mode_menu_screen=builder("modes"),
        build_notification_menu_screen=builder("notifications"),
        build_menu_screen=builder("menu"),
    )


def test_build_admin_restore_screen_routes_known_previous_screens() -> None:
    db = FakeAdminRestoreStore()
    service = build_service(db)

    assert service.build_admin_restore_screen(42, "uk", "menu:settings").screen_id == "settings"
    assert service.build_admin_restore_screen(42, "uk", "menu:import_words").screen_id == "import"
    assert service.build_admin_restore_screen(42, "uk", "admin:legacy").screen_id == "menu"
    assert service.build_admin_restore_screen(42, "uk", "menu:levels").screen_id == "levels"
    assert service.build_admin_restore_screen(42, "uk", "menu:modes").screen_id == "modes"
    assert service.build_admin_restore_screen(42, "uk", "menu:notifications:morning").screen_id == "notifications"


def test_build_admin_restore_screen_adds_restore_metadata_to_known_screens() -> None:
    db = FakeAdminRestoreStore()

    restored = build_service(db).build_admin_restore_screen(42, "uk", "menu:settings")

    assert restored.metadata == {"prefer_edit_active": True, "buttons_per_row": 1}


def test_build_admin_restore_screen_falls_back_to_silent_menu_restore_metadata() -> None:
    db = FakeAdminRestoreStore()

    restored = build_service(db).build_admin_restore_screen(42, "uk", "unknown")

    assert restored.screen_id == "menu"
    assert restored.metadata == {"prefer_edit_active": True, "buttons_per_row": 1}


def test_dispatch_due_admin_bot_restores_builds_notifications() -> None:
    current_time = datetime(2026, 4, 26, 12, 0, 0)
    db = FakeAdminRestoreStore()
    db.restores = [
        {"id": 1, "telegram_user_id": 42, "chat_id": 100, "previous_screen_id": "menu:settings"},
        {"id": 2, "telegram_user_id": 43, "chat_id": 101, "previous_screen_id": None},
    ]
    db.profiles = {
        42: {"language_code": "uk"},
        43: None,
    }

    notifications = build_service(db, current_time=current_time).dispatch_due_admin_bot_restores()

    assert db.claimed_at == current_time
    assert [notification.telegram_user_id for notification in notifications] == [42, 43]
    assert [notification.chat_id for notification in notifications] == [100, 101]
    assert [notification.screen.screen_id for notification in notifications] == ["settings", "menu"]
    assert [notification.disable_notification for notification in notifications] == [True, True]
    assert db.failed_restores == []


def test_dispatch_due_admin_bot_restores_marks_failed_restore_and_continues() -> None:
    current_time = datetime(2026, 4, 26, 12, 0, 0)
    db = FakeAdminRestoreStore()
    db.restores = [
        {"id": 1, "telegram_user_id": 42, "chat_id": 100, "previous_screen_id": "menu:settings"},
        {"id": 2, "telegram_user_id": 43, "chat_id": 101, "previous_screen_id": "unknown"},
    ]
    db.profiles = {42: {"language_code": "uk"}, 43: {"language_code": "uk"}}

    notifications = build_service(db, current_time=current_time, fail_screen_id="settings").dispatch_due_admin_bot_restores()

    assert [notification.telegram_user_id for notification in notifications] == [43]
    assert db.failed_restores == [
        {
            "restore_id": 1,
            "error_text": "RuntimeError: screen failed",
            "current_time": current_time,
        }
    ]
