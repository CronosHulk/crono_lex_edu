from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.contracts import ScreenModel
from app.i18n import translate
from app.screen_delivery_policy import with_screen_delivery_policy

ImportScreenBuilder = Callable[[int, str, str | None], ScreenModel]
MenuScreenBuilder = Callable[..., ScreenModel]
ImportProcessor = Callable[..., list]
BindingClearer = Callable[[int, datetime], None]
TimeProvider = Callable[[], datetime]


class ClientImportMutationActionService:
    def __init__(
        self,
        *,
        user_profiles: Any,
        is_test_mode_enabled: Callable[[], bool],
        current_time: TimeProvider,
        process_due_user_vocabulary_imports: ImportProcessor,
        clear_import_google_doc_binding: BindingClearer,
        build_import_screen: ImportScreenBuilder,
        build_menu_screen: MenuScreenBuilder,
    ) -> None:
        self.user_profiles = user_profiles
        self.is_test_mode_enabled = is_test_mode_enabled
        self.current_time = current_time
        self.process_due_user_vocabulary_imports = process_due_user_vocabulary_imports
        self.clear_import_google_doc_binding = clear_import_google_doc_binding
        self.build_import_screen = build_import_screen
        self.build_menu_screen = build_menu_screen

    def handle_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel | None:
        if action == "m:i:run-now":
            return self._handle_run_now(telegram_user_id, locale)
        if action == "m:i:unbind":
            self.clear_import_google_doc_binding(telegram_user_id, self.current_time())
            return self.build_import_screen(
                telegram_user_id,
                locale,
                translate(locale, "import_words_unbound_notice"),
            )
        return None

    def _handle_run_now(self, telegram_user_id: int, locale: str) -> ScreenModel:
        access_denied_screen = self._build_access_denied_screen(telegram_user_id, locale)
        if access_denied_screen is not None:
            return access_denied_screen
        if not self.is_test_mode_enabled():
            return self.build_import_screen(
                telegram_user_id,
                locale,
                translate(locale, "import_words_run_now_unavailable_notice"),
            )
        self.process_due_user_vocabulary_imports(
            current_time=self.current_time(),
            emit_notifications=False,
            include_bound_sync=True,
        )
        screen = self.build_import_screen(
            telegram_user_id,
            locale,
            translate(locale, "import_words_run_now_started_notice"),
        )
        return with_screen_delivery_policy(screen, force_resend=True)

    def _build_access_denied_screen(
        self, telegram_user_id: int, locale: str
    ) -> ScreenModel | None:
        if self.user_profiles.can_access(
            telegram_user_id,
            action="imports/run_now",
            environment="telegram_user",
        ):
            return None
        return self.build_menu_screen(
            telegram_user_id,
            locale,
            notice=translate(locale, "import_words_run_now_unavailable_notice"),
        )
