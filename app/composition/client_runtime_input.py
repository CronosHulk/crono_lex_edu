from __future__ import annotations

from typing import Any

from app.application.client_runtime.input_service import ClientRuntimeInputService
from app.data_access.user_profiles import UserProfileRepository
from app.helpers.locale import resolve_user_locale


def configure_client_runtime_input_runtime(service: Any, db: Any) -> None:
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)
    service.client_runtime_input_service = ClientRuntimeInputService(
        user_profiles=user_profiles_repo,
        build_user_payload=service.client_runtime_bootstrap_service.build_user_payload,
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
        build_close_to_menu_screen=service.client_learning_menu_screen_service.build_close_to_menu_screen,
        build_text_action_map=service.client_text_action_service.build_text_action_map,
        start_learning=service.client_learning_start_service.start_learning,
        handle_import_mutation_action=service.client_import_mutation_action_service.handle_action,
        handle_import_read_action=service.client_import_read_action_service.handle_action,
        handle_import_text_input=service.client_import_text_input_service.handle_text_input,
        handle_reminder_settings_action=service.client_reminder_settings_service.handle_action,
        handle_learning_resume_action=service.client_learning_resume_service.handle_action,
        handle_learning_settings_action=service.client_learning_settings_action_service.handle_action,
        handle_learning_planning_action=service.client_learning_planning_action_service.handle_action,
        handle_reminder_action=service.client_reminder_action_service.handle_action,
        handle_learning_session_action=service.client_learning_session_action_service.handle_action,
        build_web_settings_link_screen=service.client_learning_web_link_service.build_settings_link_screen,
        build_user_import_screen=service.client_import_screen_service.build_user_import_screen,
        build_text_fallback_screen=service.client_runtime_text_fallback_service.build_text_fallback_screen,
        resolve_locale=resolve_user_locale,
    )
