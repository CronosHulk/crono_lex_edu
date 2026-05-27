from __future__ import annotations

from typing import Any

from app.application.client_runtime.text_action_service import ClientTextActionService
from app.i18n import translate


class FakeTextActionSessionReader:
    def __init__(self) -> None:
        self.active_session = None

    def get_active_session(self, telegram_user_id: int):
        return self.active_session


def can_resume_from_menu(session: dict[str, Any] | None) -> bool:
    if session is None:
        return False
    session_words_count = session.get("session_words_count")
    if session_words_count is None:
        return True
    return int(session_words_count) > 0


def build_single_choice_label(label: str, is_selected: bool) -> str:
    return f"✓ {label}" if is_selected else label


def build_service(
    learning_sessions: FakeTextActionSessionReader | None = None,
) -> ClientTextActionService:
    return ClientTextActionService(
        learning_sessions or FakeTextActionSessionReader(),
        level_catalog_provider=lambda: [{"title": "A1"}, {"title": "A2"}],
        count_label_builder=lambda locale, count: translate(
            locale,
            "menu_word_count_option",
            count_text=f"{count} слів",
        ),
        resume_button_text_builder=lambda locale, session: "📊 Відкрити підсумок заняття",
        can_resume_from_menu=can_resume_from_menu,
        single_choice_label_builder=build_single_choice_label,
        words_per_session_options=(10, 15),
    )


def test_text_action_service_maps_static_navigation_labels() -> None:
    action_map = build_service().build_text_action_map(1, "uk")

    assert action_map["Рівень англійської"] == "m:levels"
    assert action_map["Кількість слів"] == "m:modes"
    assert action_map["Щоденні нагадування"] == "m:n"
    assert action_map["Налаштувати час"] == "m:n:pick"


def test_text_action_service_maps_selected_level_count_period_and_hour_labels() -> None:
    action_map = build_service().build_text_action_map(1, "uk")

    assert action_map["A1"] == "m:l:A1"
    assert action_map["✓ A2"] == "m:l:A2"
    assert action_map["15 слів"] == "m:w:15"
    assert action_map["✓ Вечір"] == "m:n:period:evening"
    assert action_map["✓ 19:00"] == "m:n:hour:19"


def test_text_action_service_adds_resume_label_for_active_session() -> None:
    learning_sessions = FakeTextActionSessionReader()
    learning_sessions.active_session = {"current_stage": "completed"}

    action_map = build_service(learning_sessions).build_text_action_map(1, "uk")

    assert action_map["📊 Відкрити підсумок заняття"] == "m:r"


def test_text_action_service_adds_resume_label_for_web_owned_session() -> None:
    learning_sessions = FakeTextActionSessionReader()
    learning_sessions.active_session = {"current_stage": "card", "active_interface": "client_web"}

    action_map = build_service(learning_sessions).build_text_action_map(1, "uk")

    assert action_map["📊 Відкрити підсумок заняття"] == "m:r"


def test_text_action_service_skips_resume_label_for_empty_session() -> None:
    learning_sessions = FakeTextActionSessionReader()
    learning_sessions.active_session = {"current_stage": "card", "session_words_count": 0}

    action_map = build_service(learning_sessions).build_text_action_map(1, "uk")

    assert "📊 Відкрити підсумок заняття" not in action_map
