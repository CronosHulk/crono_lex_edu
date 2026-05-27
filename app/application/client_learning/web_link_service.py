from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.client_web.auth_gateways import ClientWebAuthTelegramGateway
from app.application.client_web.auth_service import ClientWebAuthService
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.screen_delivery_policy import with_screen_delivery_policy
from app.time_utils import TimeService

ClientWebAuthTelegramGatewayFactory = Callable[[Any], ClientWebAuthTelegramGateway]


class ClientLearningWebLinkService:
    def __init__(
        self,
        db: Any,
        time_service: TimeService,
        *,
        build_telegram_gateway: ClientWebAuthTelegramGatewayFactory,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.build_telegram_gateway = build_telegram_gateway

    def build_settings_link_screen(self, telegram_user_id: int, locale: str) -> ScreenModel:
        screen = ScreenModel(
            screen_id="menu:settings:web",
            text=translate(
                locale,
                "settings_web_link_text",
                ttl_minutes=self.db.settings.app_admin_magic_link_ttl_minutes,
            ),
            buttons=[
                ButtonModel(
                    action="web:settings",
                    text=translate(locale, "settings_web_link_button"),
                    url=self.build_settings_url(telegram_user_id),
                ),
                ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
            ],
            keyboard_type="inline",
            metadata={"buttons_per_row": 1},
        )
        return with_screen_delivery_policy(
            screen,
            force_resend=True,
            auto_advance_after_ms=int(self.db.settings.app_admin_magic_link_ttl_minutes)
            * 60
            * 1000,
            next_action="m:menu",
        )

    def build_settings_url(self, telegram_user_id: int) -> str:
        return self._build_url(telegram_user_id, target_path="/settings")

    def build_import_url(self, telegram_user_id: int) -> str:
        return self._build_url(telegram_user_id, target_path="/import-words")

    def _build_url(self, telegram_user_id: int, *, target_path: str) -> str:
        if hasattr(self.db, "client_web_auth"):
            auth_service = ClientWebAuthService(
                self.db,
                self.time_service,
                self.build_telegram_gateway(self.db.settings),
            )
            return auth_service.create_magic_link_url(
                telegram_user_id=telegram_user_id,
                target_path=target_path,
            )
        return f"{self._base_url()}{target_path}"

    def _base_url(self) -> str:
        return getattr(self.db.settings, "app_web_base_url", "https://cronolex.uno").rstrip("/")
