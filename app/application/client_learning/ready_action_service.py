from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.contracts import ScreenModel
from app.i18n import translate
from app.reference.learning_flow import READY_STAGES

MenuScreenBuilder = Callable[..., ScreenModel]
SessionScreenRenderer = Callable[[dict[str, Any], str], ScreenModel]
NextQuizStageStarter = Callable[[int, dict[str, Any], str], ScreenModel]


class ClientLearningReadyActionService:
    def __init__(
        self,
        *,
        build_menu_screen: MenuScreenBuilder,
        render_session_screen: SessionScreenRenderer,
        start_next_quiz_stage: NextQuizStageStarter,
    ) -> None:
        self.build_menu_screen = build_menu_screen
        self.render_session_screen = render_session_screen
        self.start_next_quiz_stage = start_next_quiz_stage

    def handle_action(
        self,
        telegram_user_id: int,
        active_session: dict[str, Any],
        locale: str,
        expected_stage: str | None,
        decision: str | None,
    ) -> ScreenModel:
        if expected_stage not in READY_STAGES:
            return self.render_session_screen(active_session, locale)
        if active_session["current_stage"] != expected_stage:
            return self.render_session_screen(active_session, locale)
        if decision == "no":
            return self.build_menu_screen(
                telegram_user_id,
                locale,
                notice=translate(locale, "ready_pause"),
            )
        if decision != "yes":
            return self.render_session_screen(active_session, locale)
        return self.start_next_quiz_stage(telegram_user_id, active_session, locale)
