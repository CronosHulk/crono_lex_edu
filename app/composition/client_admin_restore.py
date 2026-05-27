from __future__ import annotations

from typing import Any

from app.application.client.admin_restore_service import ClientAdminRestoreService
from app.data_access.admin_auth import AdminAuthRepository
from app.data_access.user_profiles import UserProfileRepository


def configure_client_admin_restore_runtime(service: Any, db: Any) -> None:
    self = service
    admin_auth_repo = getattr(db, "admin_auth", None) or AdminAuthRepository(db)
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)
    self.client_admin_restore_service = ClientAdminRestoreService(
        admin_auth_repo,
        user_profiles_repo,
        self.time_service,
        build_settings_screen=lambda telegram_user_id,
        locale,
        notice: self.client_learning_settings_screen_service.build_settings_screen(
            telegram_user_id,
            locale,
            notice,
        ),
        build_user_import_screen=lambda telegram_user_id,
        locale,
        notice: self.client_import_screen_service.build_user_import_screen(
            telegram_user_id,
            locale,
            notice=notice,
        ),
        build_level_menu_screen=lambda telegram_user_id,
        locale,
        notice: self.client_learning_settings_screen_service.build_level_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
        ),
        build_mode_menu_screen=lambda telegram_user_id,
        locale,
        notice: self.client_learning_settings_screen_service.build_mode_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
        ),
        build_notification_menu_screen=lambda telegram_user_id,
        locale,
        notice: self.client_reminder_settings_service.build_notification_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
        ),
        build_menu_screen=lambda telegram_user_id,
        locale,
        notice: self.client_learning_menu_screen_service.build_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
            force_resend=True,
        ),
    )
