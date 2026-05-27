from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.application.client_learning.action_payload import parse_int_or_none
from app.application.client_learning.session_identity import with_runtime_telegram_user_id
from app.contracts import ScreenModel
from app.i18n import translate

TimeProvider = Callable[[], datetime]
MenuScreenBuilder = Callable[..., ScreenModel]
SessionScreenRenderer = Callable[[dict[str, Any], str], ScreenModel]
TransientErrorScreenBuilder = Callable[..., ScreenModel]
OwnedSessionGetter = Callable[[int, int], dict[str, Any] | None]


class LearningLevelRepository(Protocol):
    def get_active(self, telegram_user_id: int, level_id: int) -> dict[str, Any] | None:
        ...

    def get_latest(self, telegram_user_id: int, level_id: int) -> dict[str, Any] | None:
        ...

    def create(self, telegram_user_id: int, level_id: int) -> dict[str, Any]:
        ...

    def complete(self, level_run_id: int, current_time: datetime | None = None) -> None:
        ...


class StartUserProfileRepository(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class StartTrainingScheduleRepository(Protocol):
    def complete_due(
        self,
        telegram_user_id: int,
        current_time: datetime,
        *,
        exclude_schedule_id: int | None = None,
    ) -> None:
        ...

    def update_status(self, schedule_id: int, status: str) -> None:
        ...


class StartLessonWordSelector(Protocol):
    def select_lesson_words(
        self,
        *,
        telegram_user_id: int,
        level_id: int,
        words_limit: int,
    ) -> list[dict[str, Any]]:
        ...

    def select_followup_words(self, source_session_id: int) -> list[dict[str, Any]]:
        ...


class StartLearningSessionRepository(Protocol):
    def cancel_active_sessions(self, telegram_user_id: int) -> None:
        ...

    def create_session(
        self,
        *,
        telegram_user_id: int,
        level_id: int,
        level_run_id: int | None,
        words_target_count: int,
        words: list[dict[str, Any]],
        session_type: str = "regular",
        source_session_id: int | None = None,
    ) -> dict[str, Any]:
        ...


class LearningCompletionService(Protocol):
    def get_level_completion_snapshot(self, telegram_user_id: int) -> dict[str, dict[str, Any]]:
        ...

    def find_next_unfinished_higher_level(self, telegram_user_id: int, current_level_title: str) -> str | None:
        ...

    def get_unfinished_lower_levels(self, telegram_user_id: int, current_level_title: str) -> list[str]:
        ...

    def build_level_completed_screen(self, locale: str, current_level: str, next_level: str) -> ScreenModel:
        ...

    def build_lower_levels_suggestion_screen(self, locale: str, levels: list[str]) -> ScreenModel:
        ...

    def build_course_completed_screen(self, locale: str) -> ScreenModel:
        ...


class ClientLearningStartService:
    def __init__(
        self,
        user_profiles: StartUserProfileRepository,
        training_schedules: StartTrainingScheduleRepository,
        lesson_word_selection: StartLessonWordSelector,
        learning_sessions: StartLearningSessionRepository,
        learning_levels: LearningLevelRepository,
        completion_service: LearningCompletionService,
        *,
        current_time: TimeProvider,
        build_menu_screen: MenuScreenBuilder,
        build_transient_error_screen: TransientErrorScreenBuilder,
        render_session_screen: SessionScreenRenderer,
        get_owned_learning_session: OwnedSessionGetter,
    ) -> None:
        self.user_profiles = user_profiles
        self.training_schedules = training_schedules
        self.lesson_word_selection = lesson_word_selection
        self.learning_sessions = learning_sessions
        self.learning_levels = learning_levels
        self.completion_service = completion_service
        self.current_time = current_time
        self.build_menu_screen = build_menu_screen
        self.build_transient_error_screen = build_transient_error_screen
        self.render_session_screen = render_session_screen
        self.get_owned_learning_session = get_owned_learning_session

    def start_learning(
        self,
        telegram_user_id: int,
        locale: str,
        *,
        schedule: dict[str, Any] | None = None,
    ) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        if profile is None or profile.get("language_level_id") is None:
            return self.build_transient_error_screen(
                locale,
                message=translate(locale, "transient_validation_need_level"),
            )

        self.training_schedules.complete_due(
            telegram_user_id,
            self.current_time(),
            exclude_schedule_id=parse_int_or_none(str(schedule["id"])) if schedule is not None and schedule.get("id") is not None else None,
        )
        session_type = "regular"
        source_session_id: int | None = None
        level_run_id: int | None = None
        if schedule is not None and schedule.get("schedule_type") == "followup" and schedule.get("source_session_id") is not None:
            source_session_id = int(schedule["source_session_id"])
            source_session = self.get_owned_learning_session(telegram_user_id, source_session_id)
            if source_session is None:
                return self._build_no_words_menu(telegram_user_id, locale)
            session_type = "followup"
            level_run_id = source_session.get("level_run_id")
            words = self.lesson_word_selection.select_followup_words(source_session_id)
        else:
            level_run_id = self._get_or_create_level_run(telegram_user_id, profile, locale)
            if isinstance(level_run_id, ScreenModel):
                return level_run_id
            words = self.lesson_word_selection.select_lesson_words(
                telegram_user_id=telegram_user_id,
                level_id=profile["language_level_id"],
                words_limit=profile["words_per_session"],
            )
        if not words:
            return self._build_no_words_result(
                telegram_user_id=telegram_user_id,
                locale=locale,
                profile=profile,
                session_type=session_type,
                level_run_id=level_run_id,
            )

        self.learning_sessions.cancel_active_sessions(telegram_user_id)
        session = self.learning_sessions.create_session(
            telegram_user_id=telegram_user_id,
            level_id=profile["language_level_id"],
            level_run_id=level_run_id,
            words_target_count=len(words) if session_type == "followup" else profile["words_per_session"],
            words=words,
            session_type=session_type,
            source_session_id=source_session_id,
        )
        if schedule is not None:
            self.training_schedules.update_status(int(schedule["id"]), "completed")
        return self.render_session_screen(with_runtime_telegram_user_id(session, telegram_user_id), locale)

    def _get_or_create_level_run(
        self,
        telegram_user_id: int,
        profile: dict[str, Any],
        locale: str,
    ) -> int | ScreenModel:
        active_level_run = self.learning_levels.get_active(telegram_user_id, profile["language_level_id"])
        if active_level_run is not None:
            return int(active_level_run["id"])

        latest_level_run = self.learning_levels.get_latest(telegram_user_id, profile["language_level_id"])
        current_level_title = str(profile.get("language_level_title") or "")
        snapshot = self.completion_service.get_level_completion_snapshot(telegram_user_id)
        current_state = snapshot.get(current_level_title)
        if latest_level_run is not None and current_state is not None and current_state["is_completed"]:
            return self._build_completed_level_result(telegram_user_id, locale, current_level_title)
        return int(self.learning_levels.create(telegram_user_id, profile["language_level_id"])["id"])

    def _build_no_words_result(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        profile: dict[str, Any],
        session_type: str,
        level_run_id: int | None,
    ) -> ScreenModel:
        if session_type == "followup":
            return self._build_no_words_menu(telegram_user_id, locale)
        current_level_title = str(profile.get("language_level_title") or "")
        snapshot = self.completion_service.get_level_completion_snapshot(telegram_user_id)
        current_state = snapshot.get(current_level_title)
        if current_state is not None and current_state["is_completed"]:
            if level_run_id is not None:
                self.learning_levels.complete(level_run_id, self.current_time())
            return self._build_completed_level_result(telegram_user_id, locale, current_level_title)
        return self._build_no_words_menu(telegram_user_id, locale)

    def _build_completed_level_result(
        self,
        telegram_user_id: int,
        locale: str,
        current_level_title: str,
    ) -> ScreenModel:
        next_level = self.completion_service.find_next_unfinished_higher_level(
            telegram_user_id,
            current_level_title,
        )
        if next_level is not None:
            return self.completion_service.build_level_completed_screen(
                locale,
                current_level=current_level_title,
                next_level=next_level,
            )
        lower_levels = self.completion_service.get_unfinished_lower_levels(
            telegram_user_id,
            current_level_title,
        )
        if lower_levels:
            return self.completion_service.build_lower_levels_suggestion_screen(locale, lower_levels)
        return self.completion_service.build_course_completed_screen(locale)

    def _build_no_words_menu(self, telegram_user_id: int, locale: str) -> ScreenModel:
        return self.build_menu_screen(
            telegram_user_id,
            locale,
            notice=translate(locale, "menu_no_words"),
        )
