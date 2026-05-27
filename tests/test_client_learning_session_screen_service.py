from __future__ import annotations

from typing import Any

from app.application.client_learning.session_screen_service import (
    ClientLearningSessionScreenService,
)
from app.contracts import ButtonModel, ScreenModel


class FakeSessionProfileReader:
    def __init__(self) -> None:
        self.profile = {"first_name": "<Олена>"}

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        return self.profile


class FakeLearningSessionRepository:
    def __init__(self) -> None:
        self.active_session = {
            "id": 77,
            "telegram_user_id": 1,
            "current_stage": "card",
            "stage_position": 0,
            "language_level_id": 3,
        }
        self.session_words = [
            {
                "session_word_id": 501,
                "word": "learn",
                "translation_uk": "вивчати",
                "part_of_speech": "verb",
                "parts_of_speech": ["verb"],
                "phonetic_us": "/lurn/",
                "audio_path": "runtime/audio/learn.mp3",
                "examples_json": ["We learn daily."],
                "card_status": "new",
            }
        ]
        self.state_updates: list[dict[str, Any]] = []

    def get_session_words(self, session_id: int) -> list[dict[str, Any]]:
        return self.session_words

    def update_session_state(
        self,
        session_id: int,
        current_stage: str,
        stage_queue: list[int],
        stage_position: int,
    ) -> None:
        self.active_session.update(
            {
                "current_stage": current_stage,
                "stage_queue_json": stage_queue,
                "stage_position": stage_position,
            }
        )
        self.state_updates.append(
            {
                "session_id": session_id,
                "current_stage": current_stage,
                "stage_queue": stage_queue,
                "stage_position": stage_position,
            }
        )

    def get_active_session(self, telegram_user_id: int) -> dict[str, Any]:
        return self.active_session


class FakeReference:
    def __init__(self) -> None:
        self.levels = {3: {"id": 3, "title": "B1"}}

    def get_level_by_id(self, level_id: int) -> dict[str, Any] | None:
        return self.levels.get(level_id)


class ScreenCallbacks:
    def __init__(self) -> None:
        self.menus: list[dict[str, Any]] = []
        self.summaries: list[dict[str, Any]] = []
        self.quizzes: list[dict[str, Any]] = []

    def build_menu(self, telegram_user_id: int, locale: str, **kwargs: Any) -> ScreenModel:
        self.menus.append({"telegram_user_id": telegram_user_id, "locale": locale, **kwargs})
        return ScreenModel(
            screen_id="menu",
            text="menu text",
            buttons=[ButtonModel(text="Menu", action="m:menu")],
            metadata={"menu": True},
        )

    def build_summary(self, session_id: int, locale: str, notice: str | None = None) -> ScreenModel:
        self.summaries.append({"session_id": session_id, "locale": locale, "notice": notice})
        return ScreenModel(screen_id="summary", text=notice or "summary")

    def render_quiz(self, session: dict[str, Any], locale: str, notice: str | None = None) -> ScreenModel:
        self.quizzes.append({"session": session, "locale": locale, "notice": notice})
        return ScreenModel(screen_id="quiz", text=notice or "quiz")


def build_service(
    user_profiles: FakeSessionProfileReader | None = None,
    learning_sessions: FakeLearningSessionRepository | None = None,
    reference: FakeReference | None = None,
    callbacks: ScreenCallbacks | None = None,
) -> tuple[ClientLearningSessionScreenService, FakeSessionProfileReader, FakeLearningSessionRepository, FakeReference, ScreenCallbacks]:
    user_profiles = user_profiles or FakeSessionProfileReader()
    learning_sessions = learning_sessions or FakeLearningSessionRepository()
    reference = reference or FakeReference()
    callbacks = callbacks or ScreenCallbacks()
    service = ClientLearningSessionScreenService(
        user_profiles,
        learning_sessions,
        reference,
        build_menu_screen=callbacks.build_menu,
        build_summary_screen=callbacks.build_summary,
        render_quiz_screen=callbacks.render_quiz,
    )
    return service, user_profiles, learning_sessions, reference, callbacks


def test_build_transient_error_screen_sets_auto_advance_metadata() -> None:
    service, _, _, _, _ = build_service()

    screen = service.build_transient_error_screen("uk", message="Помилка", next_action="m:test")

    assert screen.screen_id == "transient:error"
    assert screen.text == "Помилка"
    assert screen.metadata == {
        "force_resend": True,
        "auto_advance_after_ms": 5000,
        "next_action": "m:test",
    }


def test_build_start_screen_escapes_name_and_preserves_menu() -> None:
    service, _, _, _, _ = build_service()

    screen = service.build_start_screen(1, "uk")

    assert screen.screen_id == "menu"
    assert screen.text == "menu text"
    assert screen.buttons[0].action == "m:menu"
    assert "&lt;Олена&gt;" in screen.metadata["intro_message_text"]
    assert screen.metadata == {
        "menu": True,
        "force_resend": True,
        "intro_message_text": screen.metadata["intro_message_text"],
    }


def test_build_start_screen_uses_fallback_mention() -> None:
    user_profiles = FakeSessionProfileReader()
    user_profiles.profile = {}
    service, _, _, _, _ = build_service(user_profiles=user_profiles)

    screen = service.build_start_screen(1, "uk")

    assert "користувачу" in screen.metadata["intro_message_text"]


def test_render_session_screen_routes_card_ready_quiz_summary_and_fallback() -> None:
    service, _, learning_sessions, _, callbacks = build_service()

    card_screen = service.render_session_screen({**learning_sessions.active_session, "current_stage": "card"}, "uk")
    ready_screen = service.render_session_screen({**learning_sessions.active_session, "current_stage": "ready_en_uk"}, "uk", notice="ready")
    quiz_screen = service.render_session_screen({**learning_sessions.active_session, "current_stage": "quiz_en_uk"}, "uk", notice="quiz notice")
    summary_screen = service.render_session_screen({**learning_sessions.active_session, "current_stage": "summary"}, "uk", notice="summary notice")
    fallback_screen = service.render_session_screen({**learning_sessions.active_session, "current_stage": "unknown"}, "uk")

    assert card_screen.screen_id == "card:501"
    assert ready_screen.screen_id == "ready_en_uk"
    assert ready_screen.notice_text == "ready"
    assert quiz_screen.screen_id == "quiz"
    assert callbacks.quizzes[0]["notice"] == "quiz notice"
    assert summary_screen.screen_id == "summary"
    assert callbacks.summaries == [{"session_id": 77, "locale": "uk", "notice": "summary notice"}]
    assert fallback_screen.screen_id == "menu"
    assert callbacks.menus[-1]["telegram_user_id"] == 1


def test_render_card_screen_overflow_opens_ready_and_clears_previous_card() -> None:
    service, _, learning_sessions, _, _ = build_service()
    learning_sessions.active_session["stage_position"] = 1

    screen = service.render_card_screen(learning_sessions.active_session, "uk")

    assert screen.screen_id == "ready_en_uk"
    assert learning_sessions.state_updates == [
        {
            "session_id": 77,
            "current_stage": "ready_en_uk",
            "stage_queue": [],
            "stage_position": 0,
        }
    ]
    assert learning_sessions.active_session["metadata"] == {"clear_previous_card": True}


def test_render_card_screen_overflow_without_session_telegram_id_still_opens_ready() -> None:
    service, _, learning_sessions, _, _ = build_service()
    learning_sessions.active_session["stage_position"] = 1
    session = {key: value for key, value in learning_sessions.active_session.items() if key != "telegram_user_id"}

    screen = service.render_card_screen(session, "uk")

    assert screen.screen_id == "ready_en_uk"


def test_render_card_screen_overflow_falls_back_to_menu_without_refreshed_session() -> None:
    service, _, learning_sessions, _, callbacks = build_service()
    learning_sessions.active_session["stage_position"] = 1
    learning_sessions.get_active_session = lambda telegram_user_id: None

    screen = service.render_card_screen(learning_sessions.active_session, "uk")

    assert screen.screen_id == "menu"
    assert callbacks.menus[-1]["telegram_user_id"] == 1


def test_build_resume_choice_screen_uses_reference_level_title_and_fallback() -> None:
    service, _, _, reference, _ = build_service()
    session = {
        "id": 77,
        "current_stage": "card",
        "session_type": "regular",
        "language_level_id": 3,
    }
    profile = {"language_level_title": "A1"}

    screen = service.build_resume_choice_screen(1, "uk", session, profile)

    assert "B1" in screen.text
    reference.levels = {}
    fallback_screen = service.build_resume_choice_screen(1, "uk", session, profile)
    assert "—" in fallback_screen.text
    assert service._get_level_title(None) == "—"
