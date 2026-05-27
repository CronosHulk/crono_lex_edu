from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any, Protocol

from app.application.client_learning.card_screens import build_card_screen
from app.application.client_learning.ready_screens import build_ready_screen
from app.application.client_learning.resume import build_resume_choice_screen
from app.contracts import ScreenModel
from app.i18n import translate
from app.reference.learning_flow import QUIZ_STAGE_TO_EXERCISE, READY_STAGES
from app.reference.service import AppReference
from app.screen_delivery_policy import with_screen_delivery_policy

MenuScreenBuilder = Callable[..., ScreenModel]
SummaryScreenBuilder = Callable[..., ScreenModel]
QuizScreenRenderer = Callable[..., ScreenModel]


class LearningSessionProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class LearningSessionRepository(Protocol):
    def get_session_words(self, session_id: int) -> list[dict[str, Any]]:
        ...

    def update_session_state(
        self,
        session_id: int,
        current_stage: str,
        stage_queue: list[int],
        stage_position: int,
    ) -> None:
        ...

    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class ClientLearningSessionScreenService:
    def __init__(
        self,
        user_profiles: LearningSessionProfileReader,
        learning_sessions: LearningSessionRepository,
        reference: AppReference,
        *,
        build_menu_screen: MenuScreenBuilder,
        build_summary_screen: SummaryScreenBuilder,
        render_quiz_screen: QuizScreenRenderer,
    ) -> None:
        self.user_profiles = user_profiles
        self.learning_sessions = learning_sessions
        self.reference = reference
        self.build_menu_screen = build_menu_screen
        self.build_summary_screen = build_summary_screen
        self.render_quiz_screen = render_quiz_screen

    def build_transient_error_screen(
        self,
        locale: str,
        *,
        message: str,
        next_action: str = "m:menu",
    ) -> ScreenModel:
        return with_screen_delivery_policy(
            ScreenModel(
                screen_id="transient:error",
                text=message,
                keyboard_type="inline",
            ),
            force_resend=True,
            auto_advance_after_ms=5000,
            next_action=next_action,
        )

    def build_start_screen(self, telegram_user_id: int, locale: str) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        mention = (
            html.escape(profile["first_name"])
            if profile and profile.get("first_name")
            else translate(locale, "fallback_mention")
        )
        menu_screen = self.build_menu_screen(telegram_user_id, locale)
        metadata = dict(menu_screen.metadata)
        screen = ScreenModel(
            screen_id=menu_screen.screen_id,
            text=menu_screen.text,
            buttons=menu_screen.buttons,
            keyboard_type=menu_screen.keyboard_type,
            clear_chat=menu_screen.clear_chat,
            metadata=metadata,
        )
        return with_screen_delivery_policy(
            screen,
            force_resend=True,
            intro_message_text=translate(locale, "start_title", mention=mention),
        )

    def build_resume_choice_screen(
        self,
        telegram_user_id: int,
        locale: str,
        session: dict[str, Any],
        profile: dict[str, Any] | None,
    ) -> ScreenModel:
        session_level = self._get_level_title(session.get("language_level_id"))
        return build_resume_choice_screen(
            locale=locale,
            session=session,
            profile=profile,
            session_level=session_level,
        )

    def render_session_screen(
        self,
        session: dict[str, Any] | None,
        locale: str,
        notice: str | None = None,
    ) -> ScreenModel:
        if session is None:
            return self.build_menu_screen(0, locale)  # pragma: no cover

        if session["current_stage"] == "card":
            return self.render_card_screen(session, locale)
        if session["current_stage"] in READY_STAGES:
            return self.build_ready_screen(session, locale, paused=False, notice=notice)
        if session["current_stage"] in QUIZ_STAGE_TO_EXERCISE:
            return self.render_quiz_screen(session, locale, notice=notice)
        if session["current_stage"] in {"summary", "completed"}:
            return self.build_summary_screen(session["id"], locale, notice=notice)
        return self.build_menu_screen(int(session.get("telegram_user_id") or 0), locale)

    def render_card_screen(self, session: dict[str, Any], locale: str) -> ScreenModel:
        words = self.learning_sessions.get_session_words(session["id"])
        position = session["stage_position"]
        if position >= len(words):
            self.learning_sessions.update_session_state(session["id"], "ready_en_uk", [], 0)
            telegram_user_id = session.get("telegram_user_id")
            if telegram_user_id is None:
                refreshed = {**session, "current_stage": "ready_en_uk", "stage_queue_json": [], "stage_position": 0}
            else:
                refreshed = self.learning_sessions.get_active_session(int(telegram_user_id))
            if refreshed is None:
                return self.build_menu_screen(int(telegram_user_id or 0), locale)
            refreshed["metadata"] = {"clear_previous_card": True}
            return self.build_ready_screen(refreshed, locale)

        return build_card_screen(session=session, locale=locale, words=words, position=position)

    def build_ready_screen(
        self,
        session: dict[str, Any],
        locale: str,
        paused: bool = False,
        notice: str | None = None,
    ) -> ScreenModel:
        return build_ready_screen(session=session, locale=locale, paused=paused, notice=notice)

    def _get_level_title(self, level_id: int | None) -> str:
        if level_id is None:
            return "—"
        match = self.reference.get_level_by_id(level_id)
        if match is None:
            return "—"
        return str(match["title"])
