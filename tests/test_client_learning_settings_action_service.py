from __future__ import annotations

from app.application.client_learning.settings_action_service import (
    ClientLearningSettingsActionService,
)
from app.contracts import ScreenModel
from app.subscriptions.plans import FREE_ENTITLEMENTS


class FakeLearningLevels:
    def __init__(self) -> None:
        self.saved_levels: list[tuple[int, str]] = []

    def save_language_level(self, telegram_user_id: int, level: str) -> None:
        self.saved_levels.append((telegram_user_id, level))


class FakeUserLearningSettings:
    def __init__(self) -> None:
        self.saved_counts: list[tuple[int, int]] = []

    def set_words_per_session(self, telegram_user_id: int, count: int) -> None:
        self.saved_counts.append((telegram_user_id, count))


class CaptureCallbacks:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.levels = {"A1": {"title": "A1"}, "B1": {"title": "B1"}}

    def settings_screen(self, telegram_user_id: int, locale: str, notice: str | None = None) -> ScreenModel:
        self.calls.append(("settings", (telegram_user_id, locale, notice)))
        return ScreenModel(screen_id="settings", text=notice or "")

    def menu_screen(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("menu", (telegram_user_id, locale)))
        return ScreenModel(screen_id="menu", text="menu")

    def course_picker(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("course_picker", (telegram_user_id, locale)))
        return ScreenModel(screen_id="course_picker", text="course")

    def start_learning(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("start", (telegram_user_id, locale)))
        return ScreenModel(screen_id="start", text="start")

    def restart_level(self, telegram_user_id: int, level: str) -> None:
        self.calls.append(("restart", (telegram_user_id, level)))

    def get_level(self, level: str):
        self.calls.append(("get_level", (level,)))
        return self.levels.get(level)

    def count_text(self, locale: str, count: int) -> str:
        return f"{count} words"


def build_service(
    learning_levels: FakeLearningLevels,
    user_learning_settings: FakeUserLearningSettings,
    callbacks: CaptureCallbacks,
) -> ClientLearningSettingsActionService:
    return ClientLearningSettingsActionService(
        learning_levels,
        user_learning_settings,
        build_settings_screen=callbacks.settings_screen,
        build_menu_screen=callbacks.menu_screen,
        build_course_repeat_level_picker_screen=callbacks.course_picker,
        start_learning=callbacks.start_learning,
        restart_level_run=callbacks.restart_level,
        get_level_by_title=callbacks.get_level,
        format_count_text=callbacks.count_text,
        words_per_session_options=(10, 20),
    )


def test_learning_settings_action_saves_language_level() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    screen = build_service(learning_levels, user_learning_settings, callbacks).handle_action(11, "uk", "m:l:B1")

    assert screen is not None
    assert screen.screen_id == "settings"
    assert learning_levels.saved_levels == [(11, "B1")]
    assert "B1" in screen.text


def test_learning_settings_action_rejects_unknown_language_level() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    screen = build_service(learning_levels, user_learning_settings, callbacks).handle_action(11, "uk", "m:l:Z9")

    assert screen is not None
    assert screen.screen_id == "settings"
    assert learning_levels.saved_levels == []


def test_learning_settings_action_saves_words_per_session() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    screen = build_service(learning_levels, user_learning_settings, callbacks).handle_action(11, "uk", "m:w:20")

    assert screen is not None
    assert screen.screen_id == "settings"
    assert user_learning_settings.saved_counts == [(11, 20)]
    assert "20 words" in screen.text


def test_learning_settings_action_rejects_invalid_words_per_session() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    screen = build_service(learning_levels, user_learning_settings, callbacks).handle_action(11, "uk", "m:w:999")

    assert screen is not None
    assert screen.screen_id == "settings"
    assert user_learning_settings.saved_counts == []


def test_learning_settings_action_rejects_level_blocked_by_entitlements() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()
    callbacks.levels["B1"] = {"title": "B1"}

    service = ClientLearningSettingsActionService(
        learning_levels,
        user_learning_settings,
        build_settings_screen=callbacks.settings_screen,
        build_menu_screen=callbacks.menu_screen,
        build_course_repeat_level_picker_screen=callbacks.course_picker,
        start_learning=callbacks.start_learning,
        restart_level_run=callbacks.restart_level,
        get_level_by_title=callbacks.get_level,
        format_count_text=callbacks.count_text,
        words_per_session_options=(10, 20),
        resolve_entitlements=lambda telegram_user_id: FREE_ENTITLEMENTS,
    )

    screen = service.handle_action(11, "uk", "m:l:B1")

    assert screen is not None
    assert screen.screen_id == "settings"
    assert learning_levels.saved_levels == []


def test_learning_settings_action_rejects_word_count_blocked_by_entitlements() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    service = ClientLearningSettingsActionService(
        learning_levels,
        user_learning_settings,
        build_settings_screen=callbacks.settings_screen,
        build_menu_screen=callbacks.menu_screen,
        build_course_repeat_level_picker_screen=callbacks.course_picker,
        start_learning=callbacks.start_learning,
        restart_level_run=callbacks.restart_level,
        get_level_by_title=callbacks.get_level,
        format_count_text=callbacks.count_text,
        words_per_session_options=(10, 20),
        resolve_entitlements=lambda telegram_user_id: FREE_ENTITLEMENTS,
    )

    screen = service.handle_action(11, "uk", "m:w:20")

    assert screen is not None
    assert screen.screen_id == "settings"
    assert user_learning_settings.saved_counts == []


def test_learning_settings_action_starts_next_level() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    screen = build_service(learning_levels, user_learning_settings, callbacks).handle_action(11, "uk", "m:level:next:B1")

    assert screen is not None
    assert screen.screen_id == "start"
    assert learning_levels.saved_levels == [(11, "B1")]


def test_learning_settings_action_restarts_repeat_level() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    screen = build_service(learning_levels, user_learning_settings, callbacks).handle_action(11, "uk", "m:level:repeat:A1")

    assert screen is not None
    assert screen.screen_id == "start"
    assert ("restart", (11, "A1")) in callbacks.calls


def test_learning_settings_action_routes_course_repeat_picker() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    screen = build_service(learning_levels, user_learning_settings, callbacks).handle_action(11, "uk", "m:course:repeat")

    assert screen is not None
    assert screen.screen_id == "course_picker"


def test_learning_settings_action_ignores_unrelated_action() -> None:
    learning_levels = FakeLearningLevels()
    user_learning_settings = FakeUserLearningSettings()
    callbacks = CaptureCallbacks()

    assert build_service(learning_levels, user_learning_settings, callbacks).handle_action(11, "uk", "m:r") is None
