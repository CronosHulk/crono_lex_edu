from __future__ import annotations

from typing import Any, Protocol

from app.application.client_learning.menu_screens import build_main_menu_screen
from app.contracts import ScreenModel
from app.screen_delivery_policy import with_close_to_menu_delivery


class LearningMenuSessionReader(Protocol):
    def get_active_session(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class ClientLearningMenuScreenService:
    def __init__(
        self,
        learning_sessions: LearningMenuSessionReader,
    ) -> None:
        self.learning_sessions = learning_sessions

    def build_menu_screen(
        self,
        telegram_user_id: int,
        locale: str,
        notice: str | None = None,
        clear_chat: bool = False,
        force_resend: bool = False,
    ) -> ScreenModel:
        active_session = self.learning_sessions.get_active_session(telegram_user_id)
        return build_main_menu_screen(
            locale=locale,
            active_session=active_session,
            notice=notice,
            clear_chat=clear_chat,
            force_resend=force_resend,
        )

    def build_close_to_menu_screen(
        self, telegram_user_id: int, locale: str
    ) -> ScreenModel:
        screen = self.build_menu_screen(
            telegram_user_id,
            locale,
            clear_chat=True,
            force_resend=True,
        )
        return with_close_to_menu_delivery(screen)
