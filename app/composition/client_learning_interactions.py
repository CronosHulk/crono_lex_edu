from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.client_learning.planning_action_service import (
    ClientLearningPlanningActionService,
)
from app.application.client_learning.quiz_action_service import ClientLearningQuizActionService
from app.application.client_learning.session_identity import with_runtime_telegram_user_id
from app.application.client_learning.session_screen_service import (
    ClientLearningSessionScreenService,
)
from app.application.client_learning.settings_action_service import (
    ClientLearningSettingsActionService,
)
from app.application.client_runtime.text_fallback_service import (
    ClientRuntimeTextFallbackService,
)
from app.data_access.learning_levels import LearningLevelRepository
from app.data_access.learning_progress import LearningProgressRepository
from app.data_access.learning_sessions import LearningSessionRepository
from app.data_access.similar_words import SimilarWordRepository
from app.data_access.user_learning_settings import UserLearningSettingsRepository
from app.data_access.user_profiles import UserProfileRepository
from app.reference.service import format_count_text


def configure_client_learning_interaction_runtime(
    service: Any,
    db: Any,
    *,
    quiz_queue_randomizer: Callable[[list[int]], list[int]] | None = None,
) -> None:
    learning_sessions_repo = getattr(db, "learning_sessions", None) or LearningSessionRepository(db)
    learning_progress_repo = getattr(db, "learning_progress", None) or LearningProgressRepository(db)
    similar_words_repo = getattr(db, "similar_words", None) or SimilarWordRepository(db)
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)
    learning_levels_repo = getattr(db, "learning_levels", None) or LearningLevelRepository(db)
    user_learning_settings_repo = getattr(db, "user_learning_settings", None) or UserLearningSettingsRepository(db)

    quiz_action_kwargs: dict[str, Any] = {}
    if quiz_queue_randomizer is not None:
        quiz_action_kwargs["quiz_queue_randomizer"] = quiz_queue_randomizer

    service.client_learning_quiz_action_service = ClientLearningQuizActionService(
        learning_sessions_repo,
        learning_progress_repo,
        similar_words_repo,
        current_time=lambda: service.time_service.now(),
        render_session_screen=lambda session, locale: service.client_learning_session_screen_service.render_session_screen(
            session, locale
        ),
        build_ready_screen=lambda session, locale: service.client_learning_session_screen_service.build_ready_screen(
            session,
            locale,
        ),
        build_summary_screen=lambda session_id,
        locale,
        notice=None,
        telegram_user_id=None: service.client_learning_summary_service.build_summary_screen(
            session_id,
            locale,
            notice=notice,
            telegram_user_id=telegram_user_id,
        ),
        session_completion=service.client_learning_session_completion_service,
        **quiz_action_kwargs,
    )
    service.client_learning_session_screen_service = ClientLearningSessionScreenService(
        user_profiles_repo,
        learning_sessions_repo,
        service.reference,
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
        build_summary_screen=lambda session_id,
        locale,
        notice=None,
        telegram_user_id=None: service.client_learning_summary_service.build_summary_screen(
            session_id,
            locale,
            notice=notice,
            telegram_user_id=telegram_user_id,
        ),
        render_quiz_screen=lambda session,
        locale,
        notice=None: service.client_learning_quiz_action_service.render_screen(
            session,
            locale,
            notice=notice,
        ),
    )
    service.client_runtime_text_fallback_service = ClientRuntimeTextFallbackService(
        learning_sessions_repo,
        attach_runtime_telegram_user_id=with_runtime_telegram_user_id,
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
        render_session_screen=service.client_learning_session_screen_service.render_session_screen,
    )
    service.client_learning_settings_action_service = ClientLearningSettingsActionService(
        learning_levels_repo,
        user_learning_settings_repo,
        build_settings_screen=service.client_learning_settings_screen_service.build_settings_screen,
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
        build_course_repeat_level_picker_screen=lambda telegram_user_id,
        locale: service.client_learning_completion_service.build_course_repeat_level_picker_screen(
            telegram_user_id,
            locale,
        ),
        start_learning=lambda telegram_user_id, locale: service.client_learning_start_service.start_learning(
            telegram_user_id, locale
        ),
        restart_level_run=service.client_learning_level_run_service.restart_level_run,
        get_level_by_title=service.client_learning_level_run_service.get_level_by_title,
        format_count_text=lambda locale, count: format_count_text(locale, count),
        words_per_session_options=service.reference.words_per_session_options(),
        resolve_entitlements=lambda telegram_user_id: service.user_entitlement_resolver.resolve_optional_for_telegram_user(
            telegram_user_id,
            current_time=service.time_service.now(),
        ),
    )
    service.client_learning_planning_action_service = ClientLearningPlanningActionService(
        build_menu_screen=service.client_learning_menu_screen_service.build_menu_screen,
        build_summary_screen=lambda session_id,
        locale,
        telegram_user_id=None: service.client_learning_summary_service.build_summary_screen(
            session_id,
            locale,
            telegram_user_id=telegram_user_id,
        ),
        build_planning_period_screen=lambda telegram_user_id,
        locale,
        target_day,
        session_id: service.client_learning_planning_service.build_period_screen(
            telegram_user_id,
            locale,
            target_day,
            session_id,
        ),
        build_planning_hour_screen=lambda telegram_user_id,
        locale,
        target_day,
        session_id,
        period_code: service.client_learning_planning_service.build_hour_screen(
            telegram_user_id,
            locale,
            target_day,
            session_id,
            period_code,
        ),
        save_planned_training=lambda telegram_user_id,
        locale,
        target_day,
        session_id,
        period_code,
        hour: service.client_learning_planning_service.save_planned_training(
            telegram_user_id,
            locale,
            target_day,
            session_id,
            period_code,
            hour,
        ),
        get_owned_learning_session=service.client_learning_planning_service.get_owned_learning_session,
    )
