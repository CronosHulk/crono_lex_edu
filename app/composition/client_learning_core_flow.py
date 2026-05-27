from __future__ import annotations

from typing import Any

from app.application.client.bootstrap_service import ClientBootstrapService
from app.application.client_learning.planning_service import ClientLearningPlanningService
from app.application.client_learning.session_completion_service import (
    ClientLearningSessionCompletionService,
)
from app.application.client_learning.start_service import ClientLearningStartService
from app.application.client_learning.summary_service import ClientLearningSummaryService
from app.application.client_runtime.bootstrap_service import ClientRuntimeBootstrapService
from app.data_access.error_logs import ErrorLogRepository
from app.data_access.learning_levels import LearningLevelRepository
from app.data_access.learning_progress import LearningProgressRepository
from app.data_access.learning_sessions import LearningSessionRepository
from app.data_access.lesson_word_selection import LessonWordSelectionRepository
from app.data_access.training_schedules import TrainingScheduleRepository
from app.data_access.user_profiles import UserProfileRepository
from app.helpers.locale import resolve_user_locale


def configure_client_learning_core_flow_runtime(service: Any, db: Any) -> None:
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)
    error_logs_repo = getattr(db, "error_logs", None) or ErrorLogRepository(db)
    learning_sessions_repo = getattr(db, "learning_sessions", None) or LearningSessionRepository(db)
    training_schedules_repo = getattr(db, "training_schedules", None) or TrainingScheduleRepository(db)
    lesson_word_selection_repo = getattr(db, "lesson_word_selection", None) or LessonWordSelectionRepository(db, getattr(db, "settings", None))
    learning_levels_repo = getattr(db, "learning_levels", None) or LearningLevelRepository(db)
    learning_progress_repo = getattr(db, "learning_progress", None) or LearningProgressRepository(db)

    service.client_bootstrap_service = ClientBootstrapService(
        user_profiles_repo,
        error_logs_repo,
        build_start_screen=lambda telegram_user_id,
        locale: service.client_learning_session_screen_service.build_start_screen(
            telegram_user_id,
            locale,
        ),
        teacher_student_links=getattr(db, "teacher_student_links", None),
        current_time=lambda: service.time_service.now(),
    )
    service.client_runtime_bootstrap_service = ClientRuntimeBootstrapService(
        service.client_bootstrap_service,
        user_profiles=user_profiles_repo,
        resolve_locale=resolve_user_locale,
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
    )
    service.client_learning_planning_service = ClientLearningPlanningService(
        learning_sessions_repo,
        training_schedules_repo,
        service.time_service,
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
        build_summary_screen=lambda session_id,
        locale,
        notice,
        telegram_user_id=None: service.client_learning_summary_service.build_summary_screen(
            session_id,
            locale,
            notice=notice,
            telegram_user_id=telegram_user_id,
        ),
        resolve_user_uuid=lambda telegram_user_id: (
            user_profiles_repo.get_profile(telegram_user_id) or {}
        ).get("user_id"),
    )
    service.client_learning_start_service = ClientLearningStartService(
        user_profiles_repo,
        training_schedules_repo,
        lesson_word_selection_repo,
        learning_sessions_repo,
        learning_levels_repo,
        service.client_learning_completion_service,
        current_time=lambda: service.time_service.now(),
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
        build_transient_error_screen=lambda locale,
        **kwargs: service.client_learning_session_screen_service.build_transient_error_screen(
            locale,
            **kwargs,
        ),
        render_session_screen=lambda session, locale: service.client_learning_session_screen_service.render_session_screen(
            session, locale
        ),
        get_owned_learning_session=service.client_learning_planning_service.get_owned_learning_session,
    )
    service.client_learning_summary_service = ClientLearningSummaryService(
        learning_sessions_repo,
        user_profiles_repo,
        learning_progress_repo,
        service.time_service,
        service.client_reminder_display_service,
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
    )
    service.client_learning_session_completion_service = ClientLearningSessionCompletionService(
        learning_sessions_repo,
        learning_progress_repo,
        current_time=lambda: service.time_service.now(),
    )
