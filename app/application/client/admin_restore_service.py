from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.contracts import ImportDispatchNotificationModel, ScreenModel
from app.helpers.locale import resolve_user_locale
from app.i18n import translate
from app.screen_delivery_policy import with_screen_delivery_policy
from app.time_utils import TimeService


class AdminBotRestoreRepository(Protocol):
    def claim_due_bot_restores(self, *, current_time: datetime, limit: int = 50) -> list[dict[str, Any]]:
        ...

    def mark_bot_restore_failed(self, restore_id: int, *, error_text: str, current_time: datetime) -> None:
        ...


class UserProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class ClientAdminRestoreService:
    def __init__(
        self,
        admin_auth: AdminBotRestoreRepository,
        user_profiles: UserProfileReader,
        time_service: TimeService,
        *,
        build_settings_screen: Callable[[int, str, str], ScreenModel],
        build_user_import_screen: Callable[[int, str, str], ScreenModel],
        build_level_menu_screen: Callable[[int, str, str], ScreenModel],
        build_mode_menu_screen: Callable[[int, str, str], ScreenModel],
        build_notification_menu_screen: Callable[[int, str, str], ScreenModel],
        build_menu_screen: Callable[[int, str, str], ScreenModel],
    ) -> None:
        self.admin_auth = admin_auth
        self.user_profiles = user_profiles
        self.time_service = time_service
        self.build_settings_screen = build_settings_screen
        self.build_user_import_screen = build_user_import_screen
        self.build_level_menu_screen = build_level_menu_screen
        self.build_mode_menu_screen = build_mode_menu_screen
        self.build_notification_menu_screen = build_notification_menu_screen
        self.build_menu_screen = build_menu_screen

    def dispatch_due_admin_bot_restores(self) -> list[ImportDispatchNotificationModel]:
        current_time = self.time_service.now()
        notifications: list[ImportDispatchNotificationModel] = []
        for restore in self.admin_auth.claim_due_bot_restores(current_time=current_time):
            try:
                profile = self.user_profiles.get_profile(int(restore["telegram_user_id"]))
                locale = resolve_user_locale(profile)
                notifications.append(
                    ImportDispatchNotificationModel(
                        telegram_user_id=int(restore["telegram_user_id"]),
                        chat_id=int(restore["chat_id"]),
                        screen=self.build_admin_restore_screen(
                            int(restore["telegram_user_id"]),
                            locale,
                            str(restore.get("previous_screen_id") or ""),
                        ),
                        disable_notification=True,
                    )
                )
            except Exception as error:
                self.admin_auth.mark_bot_restore_failed(
                    int(restore["id"]),
                    error_text=f"{type(error).__name__}: {error}",
                    current_time=current_time,
                )
        return notifications

    def build_admin_restore_screen(self, telegram_user_id: int, locale: str, previous_screen_id: str) -> ScreenModel:
        notice = translate(locale, "admin_login_success_notice")
        if previous_screen_id == "menu:settings":
            return self._with_restore_metadata(self.build_settings_screen(telegram_user_id, locale, notice))
        if previous_screen_id == "menu:import_words":
            return self._with_restore_metadata(self.build_user_import_screen(telegram_user_id, locale, notice))
        if previous_screen_id == "menu:levels":
            return self._with_restore_metadata(self.build_level_menu_screen(telegram_user_id, locale, notice))
        if previous_screen_id == "menu:modes":
            return self._with_restore_metadata(self.build_mode_menu_screen(telegram_user_id, locale, notice))
        if previous_screen_id.startswith("menu:notifications"):
            return self._with_restore_metadata(self.build_notification_menu_screen(telegram_user_id, locale, notice))
        return self._with_restore_metadata(self.build_menu_screen(telegram_user_id, locale, ""))

    def _with_restore_metadata(self, screen: ScreenModel) -> ScreenModel:
        restored = screen.model_copy(update={"metadata": {**screen.metadata, "buttons_per_row": 1}})
        return with_screen_delivery_policy(restored, prefer_edit_active=True)
