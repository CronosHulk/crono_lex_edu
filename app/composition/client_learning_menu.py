from __future__ import annotations

from typing import Any

from app.application.client_learning.completion_service import ClientLearningCompletionService
from app.application.client_learning.level_run_service import ClientLearningLevelRunService
from app.application.client_learning.menu_screen_service import (
    ClientLearningMenuScreenService,
)
from app.application.client_learning.settings_screen_service import (
    ClientLearningSettingsScreenService,
)
from app.application.client_learning.web_link_service import ClientLearningWebLinkService
from app.composition.client_web_provider_adapters import build_client_web_auth_telegram_gateway
from app.data_access.learning_levels import LearningLevelRepository
from app.data_access.learning_progress import LearningProgressRepository
from app.data_access.learning_sessions import LearningSessionRepository
from app.data_access.user_profiles import UserProfileRepository


def configure_client_learning_menu_runtime(service: Any, db: Any) -> None:
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)
    learning_sessions_repo = getattr(db, "learning_sessions", None) or LearningSessionRepository(db)
    learning_progress_repo = getattr(db, "learning_progress", None) or LearningProgressRepository(db)
    learning_levels_repo = getattr(db, "learning_levels", None) or LearningLevelRepository(db)

    service.client_learning_settings_screen_service = ClientLearningSettingsScreenService(
        user_profiles_repo,
        service.reference,
        build_days_suffix=lambda locale,
        reminder_hour,
        reminder_weekdays: service.client_reminder_display_service.build_days_suffix(
            locale,
            reminder_hour,
            reminder_weekdays,
        ),
        resolve_entitlements=lambda telegram_user_id: service.user_entitlement_resolver.resolve_optional_for_telegram_user(
            telegram_user_id,
            current_time=service.time_service.now(),
        ),
    )
    service.client_learning_web_link_service = ClientLearningWebLinkService(
        db,
        service.time_service,
        build_telegram_gateway=build_client_web_auth_telegram_gateway,
    )
    service.client_learning_menu_screen_service = ClientLearningMenuScreenService(
        learning_sessions_repo,
    )
    service.client_learning_completion_service = ClientLearningCompletionService(
        user_profiles_repo,
        learning_progress_repo,
        service.reference,
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
        resolve_entitlements=lambda telegram_user_id: service.user_entitlement_resolver.resolve_optional_for_telegram_user(
            telegram_user_id,
            current_time=service.time_service.now(),
        ),
    )
    service.client_learning_level_run_service = ClientLearningLevelRunService(
        learning_levels_repo, service.reference
    )
