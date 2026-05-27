from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.contracts import ScreenModel, TelegramUserContext


class RuntimeInputUserProfiles(Protocol):
    def upsert_user(self, user_payload: dict[str, Any]) -> None: ...

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def save_user_event(
        self,
        *,
        telegram_user_id: int,
        event_type: str,
        raw_update_json: dict[str, Any],
        callback_data: str,
    ) -> None: ...


class RuntimeInputUserImportScreenBuilder(Protocol):
    def __call__(
        self, telegram_user_id: int, locale: str, notice: str | None = None
    ) -> ScreenModel: ...


class RuntimeInputMenuScreenBuilder(Protocol):
    def __call__(
        self,
        telegram_user_id: int,
        locale: str,
        notice: str | None = None,
        clear_chat: bool = False,
        force_resend: bool = False,
    ) -> ScreenModel: ...


class RuntimeInputImportTextHandler(Protocol):
    def __call__(
        self,
        *,
        user: TelegramUserContext,
        locale: str,
        normalized_text: str,
    ) -> ScreenModel | None: ...


class RuntimeInputActionHandler(Protocol):
    def __call__(
        self,
        telegram_user_id: int,
        locale: str,
        action: str,
    ) -> ScreenModel | None: ...


class ClientRuntimeInputService:
    def __init__(
        self,
        *,
        user_profiles: RuntimeInputUserProfiles,
        build_user_payload: Callable[[TelegramUserContext], dict[str, Any]],
        build_menu_screen: RuntimeInputMenuScreenBuilder,
        build_close_to_menu_screen: Callable[[int, str], ScreenModel],
        build_text_action_map: Callable[[int, str], dict[str, str]],
        start_learning: Callable[[int, str], ScreenModel],
        handle_import_mutation_action: RuntimeInputActionHandler,
        handle_import_read_action: RuntimeInputActionHandler,
        handle_import_text_input: RuntimeInputImportTextHandler,
        handle_reminder_settings_action: RuntimeInputActionHandler,
        handle_learning_resume_action: RuntimeInputActionHandler,
        handle_learning_settings_action: RuntimeInputActionHandler,
        handle_learning_planning_action: RuntimeInputActionHandler,
        handle_reminder_action: RuntimeInputActionHandler,
        handle_learning_session_action: RuntimeInputActionHandler,
        build_web_settings_link_screen: Callable[[int, str], ScreenModel],
        build_user_import_screen: RuntimeInputUserImportScreenBuilder,
        build_text_fallback_screen: Callable[[int, str], ScreenModel],
        resolve_locale: Callable[[Any], str],
    ) -> None:
        self.user_profiles = user_profiles
        self.build_user_payload = build_user_payload
        self.build_menu_screen = build_menu_screen
        self.build_close_to_menu_screen = build_close_to_menu_screen
        self.build_text_action_map = build_text_action_map
        self.start_learning = start_learning
        self.handle_import_mutation_action = handle_import_mutation_action
        self.handle_import_read_action = handle_import_read_action
        self.handle_import_text_input = handle_import_text_input
        self.handle_reminder_settings_action = handle_reminder_settings_action
        self.handle_learning_resume_action = handle_learning_resume_action
        self.handle_learning_settings_action = handle_learning_settings_action
        self.handle_learning_planning_action = handle_learning_planning_action
        self.handle_reminder_action = handle_reminder_action
        self.handle_learning_session_action = handle_learning_session_action
        self.build_web_settings_link_screen = build_web_settings_link_screen
        self.build_user_import_screen = build_user_import_screen
        self.build_text_fallback_screen = build_text_fallback_screen
        self.resolve_locale = resolve_locale

    def handle_action(self, user: TelegramUserContext, action: str) -> ScreenModel:
        self.user_profiles.upsert_user(self.build_user_payload(user))
        locale = self.resolve_locale(
            self.user_profiles.get_profile(user.telegram_user_id) or user
        )
        self.user_profiles.save_user_event(
            telegram_user_id=user.telegram_user_id,
            event_type="callback_action",
            raw_update_json=user.model_dump(mode="json"),
            callback_data=action,
        )

        if action == "m:menu":
            return self.build_menu_screen(
                user.telegram_user_id, locale, clear_chat=True, force_resend=True
            )
        if action == "m:levels":
            return self.build_web_settings_link_screen(user.telegram_user_id, locale)
        if action == "m:modes":
            return self.build_web_settings_link_screen(user.telegram_user_id, locale)
        if action == "m:settings":
            return self.build_web_settings_link_screen(user.telegram_user_id, locale)
        if action == "m:i":
            return self.build_user_import_screen(user.telegram_user_id, locale)
        if action == "billing:close":
            return self.build_close_to_menu_screen(user.telegram_user_id, locale)
        import_mutation_screen = self.handle_import_mutation_action(
            user.telegram_user_id, locale, action
        )
        if import_mutation_screen is not None:
            return import_mutation_screen
        import_read_screen = self.handle_import_read_action(
            user.telegram_user_id, locale, action
        )
        if import_read_screen is not None:
            return import_read_screen
        reminder_settings_screen = self.handle_reminder_settings_action(
            user.telegram_user_id, locale, action
        )
        if reminder_settings_screen is not None:
            return reminder_settings_screen
        if action in {"m:levels", "m:modes"} or action.startswith(("m:l:", "m:w:")):
            return self.build_web_settings_link_screen(user.telegram_user_id, locale)
        if action == "m:s":
            return self.start_learning(user.telegram_user_id, locale)
        resume_screen = self.handle_learning_resume_action(
            user.telegram_user_id, locale, action
        )
        if resume_screen is not None:
            return resume_screen
        learning_settings_screen = self.handle_learning_settings_action(
            user.telegram_user_id, locale, action
        )
        if learning_settings_screen is not None:
            return learning_settings_screen
        planning_screen = self.handle_learning_planning_action(
            user.telegram_user_id, locale, action
        )
        if planning_screen is not None:
            return planning_screen
        reminder_screen = self.handle_reminder_action(
            user.telegram_user_id, locale, action
        )
        if reminder_screen is not None:
            return reminder_screen
        session_screen = self.handle_learning_session_action(
            user.telegram_user_id, locale, action
        )
        if session_screen is not None:
            return session_screen

        return self.build_menu_screen(user.telegram_user_id, locale)

    def handle_text_input(self, user: TelegramUserContext, text: str) -> ScreenModel:
        self.user_profiles.upsert_user(self.build_user_payload(user))
        locale = self.resolve_locale(
            self.user_profiles.get_profile(user.telegram_user_id) or user
        )
        normalized_text = text.strip()
        action = self.build_text_action_map(user.telegram_user_id, locale).get(
            normalized_text
        )
        if action is not None:
            return self.handle_action(user, action)
        import_text_screen = self.handle_import_text_input(
            user=user,
            locale=locale,
            normalized_text=normalized_text,
        )
        if import_text_screen is not None:
            return import_text_screen
        return self.build_text_fallback_screen(user.telegram_user_id, locale)
