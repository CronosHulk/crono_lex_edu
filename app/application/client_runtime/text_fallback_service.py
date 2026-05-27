from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.contracts import ScreenModel
from app.screen_delivery_policy import with_screen_delivery_policy


class ClientRuntimeTextFallbackService:
    def __init__(
        self,
        learning_sessions: Any,
        *,
        attach_runtime_telegram_user_id: Callable[[dict[str, Any], int], dict[str, Any]],
        build_menu_screen: Callable[..., ScreenModel],
        render_session_screen: Callable[[dict[str, Any], str], ScreenModel],
    ) -> None:
        self.learning_sessions = learning_sessions
        self.attach_runtime_telegram_user_id = attach_runtime_telegram_user_id
        self.build_menu_screen = build_menu_screen
        self.render_session_screen = render_session_screen

    def build_text_fallback_screen(
        self, telegram_user_id: int, locale: str
    ) -> ScreenModel:
        active_session = self.learning_sessions.get_active_session(telegram_user_id)
        if (
            active_session is not None
            and active_session.get("active_interface", "telegram_user") == "telegram_user"
        ):
            screen = self.render_session_screen(
                self.attach_runtime_telegram_user_id(active_session, telegram_user_id),
                locale,
            )
            return with_screen_delivery_policy(screen, force_resend=True)
        return self.build_menu_screen(
            telegram_user_id,
            locale,
            force_resend=True,
        )
