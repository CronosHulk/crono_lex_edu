from __future__ import annotations

from typing import Any

from app.application.client_reminders.action_service import ClientReminderActionService
from app.application.client_reminders.dispatch_service import ClientReminderDispatchService
from app.application.client_reminders.display_service import ClientReminderDisplayService
from app.application.client_reminders.settings_service import ClientReminderSettingsService
from app.application.client_runtime.reminder_service import ClientRuntimeReminderService
from app.data_access.training_schedules import TrainingScheduleRepository
from app.data_access.user_learning_settings import UserLearningSettingsRepository
from app.data_access.user_profiles import UserProfileRepository


def configure_client_reminder_runtime(service: Any, db: Any) -> None:
    self = service
    training_schedules_repo = getattr(db, "training_schedules", None) or TrainingScheduleRepository(db)
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)
    user_learning_settings_repo = getattr(db, "user_learning_settings", None) or UserLearningSettingsRepository(db)

    self.client_reminder_display_service = ClientReminderDisplayService(training_schedules_repo)
    self.client_reminder_action_service = ClientReminderActionService(
        training_schedules_repo,
        current_time=lambda: self.time_service.now(),
        build_menu_screen=lambda telegram_user_id,
        locale,
        notice=None,
        clear_chat=False,
        force_resend=False: self.client_learning_menu_screen_service.build_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
            clear_chat=clear_chat,
            force_resend=force_resend,
        ),
        start_learning=lambda telegram_user_id, locale, **kwargs: self.client_learning_start_service.start_learning(
            telegram_user_id,
            locale,
            **kwargs,
        ),
    )
    self.client_reminder_dispatch_service = ClientReminderDispatchService(
        training_schedules_repo,
        self.time_service,
        user_profiles_repo,
    )
    self.client_runtime_reminder_service = ClientRuntimeReminderService(
        self.client_reminder_dispatch_service,
        dispatch_lock=self.dispatch_lock,
    )
    self.client_reminder_settings_service = ClientReminderSettingsService(
        user_profiles_repo,
        user_learning_settings_repo,
        resolve_reminders_per_day=lambda telegram_user_id: self.user_entitlement_resolver.reminders_per_day_for_telegram_user(
            telegram_user_id,
            current_time=self.time_service.now(),
        ),
    )

