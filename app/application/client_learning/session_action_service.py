from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.application.client_learning.action_payload import parse_session_action
from app.application.client_learning.session_identity import with_runtime_telegram_user_id
from app.contracts import ScreenModel

MenuScreenBuilder = Callable[[int, str], ScreenModel]
SessionScreenRenderer = Callable[[dict[str, Any] | None, str], ScreenModel]
CardActionHandler = Callable[[int, dict[str, Any], str, int | None, str | None], ScreenModel]
ReadyActionHandler = Callable[[int, dict[str, Any], str, str | None, str | None], ScreenModel]
AnswerActionHandler = Callable[[int, dict[str, Any], str, int | None, int | None], ScreenModel]


class SessionActionReader(Protocol):
    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class ClientLearningSessionActionService:
    def __init__(
        self,
        learning_sessions: SessionActionReader,
        *,
        build_menu_screen: MenuScreenBuilder,
        render_session_screen: SessionScreenRenderer,
        handle_card_action: CardActionHandler,
        handle_ready_action: ReadyActionHandler,
        handle_answer_action: AnswerActionHandler,
    ) -> None:
        self.learning_sessions = learning_sessions
        self.build_menu_screen = build_menu_screen
        self.render_session_screen = render_session_screen
        self.handle_card_action = handle_card_action
        self.handle_ready_action = handle_ready_action
        self.handle_answer_action = handle_answer_action

    def handle_action(
        self, telegram_user_id: int, locale: str, action: str
    ) -> ScreenModel | None:
        if not action.startswith("s:"):
            return None
        session_action = parse_session_action(action)
        if session_action is None:
            return self.build_menu_screen(telegram_user_id, locale)

        active_session = self.learning_sessions.get_active_session(telegram_user_id)
        if active_session is None or active_session["id"] != session_action.session_id:
            return self.build_menu_screen(telegram_user_id, locale)
        if active_session.get("active_interface", "telegram_user") != "telegram_user":
            return self.build_menu_screen(telegram_user_id, locale)
        active_session = with_runtime_telegram_user_id(active_session, telegram_user_id)

        if session_action.action_type == "next":
            refreshed = self.learning_sessions.get_active_session(telegram_user_id)
            return self.render_session_screen(
                with_runtime_telegram_user_id(refreshed, telegram_user_id)
                if refreshed is not None
                else None,
                locale,
            )
        if session_action.action_type == "c":
            return self.handle_card_action(
                telegram_user_id,
                active_session,
                locale,
                session_action.session_word_id,
                session_action.card_action,
            )
        if session_action.action_type == "ready":
            return self.handle_ready_action(
                telegram_user_id,
                active_session,
                locale,
                session_action.expected_stage,
                session_action.decision,
            )
        if session_action.action_type == "a":
            return self.handle_answer_action(
                telegram_user_id,
                active_session,
                locale,
                session_action.session_word_id,
                session_action.option_index,
            )
        return self.render_session_screen(active_session, locale)
