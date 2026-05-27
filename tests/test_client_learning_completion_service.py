from __future__ import annotations

from app.application.client_learning.completion_service import ClientLearningCompletionService
from app.contracts import ButtonModel, ScreenModel


class FakeCompletionUserProfiles:
    def __init__(self) -> None:
        self.profile: dict[str, object] | None = {"language_level_title": "B1"}
        self.profile_requests: list[int] = []

    def get_profile(self, telegram_user_id: int) -> dict[str, object] | None:
        self.profile_requests.append(telegram_user_id)
        return self.profile


class FakeCompletionLearningProgress:
    def __init__(self) -> None:
        self.totals: dict[int, int] = {1: 3, 2: 0, 3: 2, 4: 2}
        self.progress: dict[int, dict[str, int]] = {
            1: {"learned_count": 3},
            2: {"learned_count": 0},
            3: {"learned_count": 1},
            4: {"learned_count": 0},
        }

    def get_level_word_totals(self) -> dict[int, int]:
        return self.totals

    def get_user_level_summary(self, telegram_user_id: int, level_id: int) -> dict[str, int]:
        return self.progress.get(level_id, {"learned_count": 0})


class FakeCompletionReference:
    def __init__(self) -> None:
        self.levels = [
            {"id": 1, "title": "A1"},
            {"id": 2, "title": "A2"},
            {"id": 3, "title": "B1"},
            {"id": 4, "title": "B2"},
        ]

    def language_levels(self) -> list[dict[str, object]]:
        return self.levels

    def available_level_titles(self) -> list[str]:
        return [str(level["title"]) for level in self.levels]


def build_menu_screen(telegram_user_id: int, locale: str, notice: str | None) -> ScreenModel:
    return ScreenModel(
        screen_id="menu",
        text=notice or "",
        buttons=[ButtonModel(action="m:menu", text="Menu")],
        keyboard_type="reply",
    )


def build_service(
    user_profiles: FakeCompletionUserProfiles | None = None,
    learning_progress: FakeCompletionLearningProgress | None = None,
) -> ClientLearningCompletionService:
    return ClientLearningCompletionService(
        user_profiles or FakeCompletionUserProfiles(),
        learning_progress or FakeCompletionLearningProgress(),
        FakeCompletionReference(),
        build_menu_screen=build_menu_screen,
    )


def test_completion_snapshot_marks_words_and_completion_state() -> None:
    snapshot = build_service().get_level_completion_snapshot(telegram_user_id=42)

    assert snapshot["A1"]["total_words"] == 3
    assert snapshot["A1"]["has_words"] is True
    assert snapshot["A1"]["is_completed"] is True
    assert snapshot["A2"]["has_words"] is False
    assert snapshot["B1"]["is_completed"] is False


def test_learnable_levels_keep_reference_order_and_skip_empty_levels() -> None:
    assert build_service().get_learnable_level_titles(telegram_user_id=42) == ["A1", "B1", "B2"]


def test_find_next_unfinished_higher_level_skips_empty_and_completed_levels() -> None:
    service = build_service()

    assert service.find_next_unfinished_higher_level(telegram_user_id=42, current_level_title="A1") == "B1"
    assert service.find_next_unfinished_higher_level(telegram_user_id=42, current_level_title="Z9") is None


def test_get_unfinished_lower_levels_returns_only_levels_with_words() -> None:
    service = build_service()

    assert service.get_unfinished_lower_levels(telegram_user_id=42, current_level_title="B2") == ["B1"]
    assert service.get_unfinished_lower_levels(telegram_user_id=42, current_level_title="Z9") == []


def test_build_course_repeat_picker_uses_available_levels_and_profile_level() -> None:
    user_profiles = FakeCompletionUserProfiles()
    service = build_service(user_profiles)

    screen = service.build_course_repeat_level_picker_screen(telegram_user_id=42, locale="uk")

    assert user_profiles.profile_requests == [42]
    assert screen.screen_id == "course:repeat"
    assert "Поточний рівень: B1" in screen.text
    assert [button.action for button in screen.buttons] == [
        "m:course:repeat:A1",
        "m:course:repeat:B1",
        "m:course:repeat:B2",
        "m:menu",
    ]


def test_build_course_repeat_picker_falls_back_to_menu_without_words() -> None:
    learning_progress = FakeCompletionLearningProgress()
    learning_progress.totals = {}
    screen = build_service(learning_progress=learning_progress).build_course_repeat_level_picker_screen(
        telegram_user_id=42,
        locale="uk",
    )

    assert screen.screen_id == "menu"
    assert "не вдалося сформувати підбірку" in screen.text


def test_completion_service_exposes_completion_screens() -> None:
    service = build_service()

    assert service.build_level_completed_screen("uk", current_level="A1", next_level="B1").screen_id == "level:completed"
    assert service.build_course_completed_screen("uk").screen_id == "course:completed"
    assert service.build_lower_levels_suggestion_screen("uk", ["A1"]).screen_id == "course:lower-levels"
