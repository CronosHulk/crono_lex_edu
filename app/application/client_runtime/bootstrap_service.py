from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.contracts import ScreenModel, TelegramUserContext
from app.screen_delivery_policy import with_menu_restore_delivery


class ClientRuntimeBootstrapService:
    def __init__(
        self,
        bootstrap_service: Any,
        *,
        user_profiles: Any,
        resolve_locale: Callable[[Any], str],
        build_menu_screen: Callable[[int, str], ScreenModel],
    ) -> None:
        self.bootstrap_service = bootstrap_service
        self.user_profiles = user_profiles
        self.resolve_locale = resolve_locale
        self.build_menu_screen = build_menu_screen

    def bootstrap(
        self,
        user: TelegramUserContext,
        message_text: str | None = None,
    ) -> ScreenModel:
        return self.bootstrap_service.bootstrap(user, message_text)

    def build_unexpected_error_screen(self, user: TelegramUserContext) -> ScreenModel:
        return self.bootstrap_service.build_unexpected_error_screen(user)

    def log_unexpected_error(
        self,
        *,
        route: str,
        user: TelegramUserContext | None,
        error: Exception,
        details: str,
    ) -> None:
        self.bootstrap_service.log_unexpected_error(
            route=route,
            user=user,
            error=error,
            details=details,
        )

    def build_main_menu_restore_screen(self, telegram_user_id: int) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        locale = self.resolve_locale(profile)
        screen = self.build_menu_screen(telegram_user_id, locale)
        return with_menu_restore_delivery(screen)

    def build_user_payload(self, user: TelegramUserContext) -> dict[str, Any]:
        return self.bootstrap_service.build_user_payload(user)
