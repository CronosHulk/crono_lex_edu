from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.application.client_learning.session_identity import with_runtime_telegram_user_id
from app.contracts import ScreenModel
from app.reference.learning_flow import READY_STAGES

MenuScreenBuilder = Callable[[int, str], ScreenModel]
ResumeChoiceScreenBuilder = Callable[[int, str, dict[str, Any], dict[str, Any] | None], ScreenModel]
SessionScreenRenderer = Callable[[dict[str, Any], str], ScreenModel]
StartLearningCallback = Callable[[int, str], ScreenModel]
ShouldConfirmResumeChoice = Callable[[dict[str, Any], dict[str, Any] | None], bool]
ReadyStageContinuer = Callable[[int, dict[str, Any], str], ScreenModel]


class LearningResumeSessionReader(Protocol):
    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...

    def claim_active_session(
        self, telegram_user_id: int, active_interface: str
    ) -> dict[str, Any] | None:
        ...


class LearningResumeProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class ClientLearningResumeService:
    def __init__(
        self,
        learning_sessions: LearningResumeSessionReader,
        user_profiles: LearningResumeProfileReader,
        *,
        build_menu_screen: MenuScreenBuilder,
        build_resume_choice_screen: ResumeChoiceScreenBuilder,
        render_session_screen: SessionScreenRenderer,
        start_learning: StartLearningCallback,
        should_confirm_resume_choice: ShouldConfirmResumeChoice,
        continue_ready_stage: ReadyStageContinuer,
    ) -> None:
        self.learning_sessions = learning_sessions
        self.user_profiles = user_profiles
        self.build_menu_screen = build_menu_screen
        self.build_resume_choice_screen = build_resume_choice_screen
        self.render_session_screen = render_session_screen
        self.start_learning = start_learning
        self.should_confirm_resume_choice = should_confirm_resume_choice
        self.continue_ready_stage = continue_ready_stage

    def handle_action(
        self, telegram_user_id: int, locale: str, action: str
    ) -> ScreenModel | None:
        if action == "m:r:continue":
            session = self._claim_or_get_session(telegram_user_id)
            if session is None:
                return self.build_menu_screen(telegram_user_id, locale)
            if self._is_ready_stage(session):
                return self.continue_ready_stage(telegram_user_id, session, locale)
            return self.render_session_screen(session, locale)

        if action == "m:r:restart":
            return self.start_learning(telegram_user_id, locale)

        if action == "m:r":
            session = self._claim_or_get_session(telegram_user_id)
            if session is None:
                return self.build_menu_screen(telegram_user_id, locale)
            if self._is_ready_stage(session):
                return self.continue_ready_stage(telegram_user_id, session, locale)
            profile = self.user_profiles.get_profile(telegram_user_id)
            if self.should_confirm_resume_choice(session, profile):
                return self.build_resume_choice_screen(
                    telegram_user_id, locale, session, profile
                )
            return self.render_session_screen(session, locale)

        return None

    def _claim_or_get_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        claim = getattr(self.learning_sessions, "claim_active_session", None)
        if claim is not None:
            session = claim(telegram_user_id, "telegram_user")
        else:
            session = self.learning_sessions.get_active_session(telegram_user_id)
        return (
            with_runtime_telegram_user_id(session, telegram_user_id)
            if session is not None
            else None
        )

    def _is_ready_stage(self, session: dict[str, Any]) -> bool:
        return str(session.get("current_stage") or "") in READY_STAGES
