from __future__ import annotations

from typing import Any

from app.application.client_learning.card_action_service import ClientLearningCardActionService
from app.application.client_learning.ready_action_service import ClientLearningReadyActionService
from app.application.client_learning.resume import should_confirm_resume_choice
from app.application.client_learning.resume_service import ClientLearningResumeService
from app.application.client_learning.session_action_service import (
    ClientLearningSessionActionService,
)
from app.data_access.learning_progress import LearningProgressRepository
from app.data_access.learning_sessions import LearningSessionRepository
from app.data_access.lesson_word_selection import LessonWordSelectionRepository
from app.data_access.user_profiles import UserProfileRepository


def configure_client_learning_action_runtime(service: Any, db: Any) -> None:
    learning_sessions_repo = getattr(db, "learning_sessions", None) or LearningSessionRepository(db)
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)
    learning_progress_repo = getattr(db, "learning_progress", None) or LearningProgressRepository(db)
    lesson_word_selection_repo = getattr(db, "lesson_word_selection", None) or LessonWordSelectionRepository(db, getattr(db, "settings", None))

    service.client_learning_resume_service = ClientLearningResumeService(
        learning_sessions_repo,
        user_profiles_repo,
        build_menu_screen=lambda telegram_user_id,
        locale,
        notice=None,
        clear_chat=False,
        force_resend=False: service.client_learning_menu_screen_service.build_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
            clear_chat=clear_chat,
            force_resend=force_resend,
        ),
        build_resume_choice_screen=lambda telegram_user_id,
        locale,
        session,
        profile: service.client_learning_session_screen_service.build_resume_choice_screen(
            telegram_user_id,
            locale,
            session,
            profile,
        ),
        render_session_screen=lambda session, locale: service.client_learning_session_screen_service.render_session_screen(
            session, locale
        ),
        start_learning=lambda telegram_user_id, locale: service.client_learning_start_service.start_learning(
            telegram_user_id, locale
        ),
        should_confirm_resume_choice=lambda session, profile: should_confirm_resume_choice(
            session, profile
        ),
        continue_ready_stage=lambda telegram_user_id,
        session,
        locale: service.client_learning_ready_action_service.handle_action(
            telegram_user_id,
            session,
            locale,
            str(session.get("current_stage") or ""),
            "yes",
        ),
    )
    service.client_learning_card_action_service = ClientLearningCardActionService(
        learning_sessions_repo,
        learning_progress_repo,
        lesson_word_selection_repo,
        current_time=lambda: service.time_service.now(),
        render_session_screen=lambda session, locale: service.client_learning_session_screen_service.render_session_screen(
            session, locale
        ),
        build_ready_screen=lambda session, locale: service.client_learning_session_screen_service.build_ready_screen(
            session,
            locale,
        ),
    )
    service.client_learning_ready_action_service = ClientLearningReadyActionService(
        build_menu_screen=lambda telegram_user_id,
        locale,
        notice=None,
        clear_chat=False,
        force_resend=False: service.client_learning_menu_screen_service.build_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
            clear_chat=clear_chat,
            force_resend=force_resend,
        ),
        render_session_screen=lambda session, locale: service.client_learning_session_screen_service.render_session_screen(
            session, locale
        ),
        start_next_quiz_stage=lambda telegram_user_id,
        active_session,
        locale: service.client_learning_quiz_action_service.start_next_stage(
            active_session,
            locale,
            telegram_user_id=telegram_user_id,
        ),
    )
    service.client_learning_session_action_service = ClientLearningSessionActionService(
        learning_sessions_repo,
        build_menu_screen=lambda telegram_user_id,
        locale,
        notice=None,
        clear_chat=False,
        force_resend=False: service.client_learning_menu_screen_service.build_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
            clear_chat=clear_chat,
            force_resend=force_resend,
        ),
        render_session_screen=lambda session, locale: service.client_learning_session_screen_service.render_session_screen(
            session, locale
        ),
        handle_card_action=lambda telegram_user_id,
        active_session,
        locale,
        session_word_id,
        card_action: service.client_learning_card_action_service.handle_action(
            active_session,
            locale,
            session_word_id,
            card_action,
            telegram_user_id=telegram_user_id,
        ),
        handle_ready_action=lambda telegram_user_id,
        active_session,
        locale,
        expected_stage,
        decision: service.client_learning_ready_action_service.handle_action(
            telegram_user_id,
            active_session,
            locale,
            expected_stage,
            decision,
        ),
        handle_answer_action=lambda telegram_user_id,
        active_session,
        locale,
        session_word_id,
        option_index: service.client_learning_quiz_action_service.handle_answer_action(
            active_session,
            locale,
            session_word_id,
            option_index,
            telegram_user_id=telegram_user_id,
        ),
    )
