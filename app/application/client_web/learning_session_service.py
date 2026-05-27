from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

from app.application.client_learning.content import build_quiz_payload
from app.application.client_learning.display import (
    build_card_progress_bar,
    build_quiz_progress_bar,
)
from app.application.client_web.learning_errors import (
    ClientWebLearningConflictError,
    ClientWebLearningNotFoundError,
    ClientWebLearningValidationError,
)
from app.application.client_web.learning_markup import telegram_html_to_text
from app.application.client_web.learning_words_service import localized_learning_translation
from app.contracts import ScreenModel
from app.helpers.locale import resolve_user_locale
from app.helpers.telegram_transient import WEB_LEARNING_CLAIM_RESTORE_MINUTES
from app.i18n import translate
from app.reference.learning_flow import (
    FINAL_QUIZ_STAGE,
    NEXT_READY_STAGE,
    QUIZ_STAGE_META_I18N_KEYS,
    READY_STAGE_INTRO_I18N_KEYS,
    READY_STAGES,
)

WEB_LEARNING_CLAIM_SCREEN_ID = "web:learning_claim"


class ClientWebLearningSessionTimeService(Protocol):
    def now(self) -> datetime: ...


class ClientWebLearningSessionStartService(Protocol):
    def start_learning(self, telegram_user_id: int, locale: str) -> ScreenModel: ...


class ClientWebLearningSessionDatabasePort(Protocol):
    learning_sessions: Any
    similar_words: Any
    teacher_student_links: Any
    admin_auth: Any
    bot_message_logs: Any


class ClientWebLearningSessionRuntime(Protocol):
    db: ClientWebLearningSessionDatabasePort
    time_service: ClientWebLearningSessionTimeService
    client_learning_card_action_service: Any
    client_learning_quiz_action_service: Any
    client_learning_ready_action_service: Any
    client_learning_session_completion_service: Any
    client_learning_start_service: ClientWebLearningSessionStartService
    client_learning_summary_service: Any


class ClientWebLearningTelegramGateway(Protocol):
    def send_message(
        self,
        *,
        chat_id: int | str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        disable_notification: bool = False,
        ignore_errors: bool = False,
    ) -> int | None: ...

    def delete_message(self, *, chat_id: int | str, message_id: int | str, ignore_errors: bool = False) -> bool: ...


class NoOpClientWebLearningTelegramGateway:
    def send_message(
        self,
        *,
        chat_id: int | str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        disable_notification: bool = False,
        ignore_errors: bool = False,
    ) -> int | None:
        return None

    def delete_message(self, *, chat_id: int | str, message_id: int | str, ignore_errors: bool = False) -> bool:
        return False


class ClientWebLearningSessionService:
    def __init__(
        self,
        learning_service: ClientWebLearningSessionRuntime,
        db: ClientWebLearningSessionDatabasePort,
        telegram_gateway: ClientWebLearningTelegramGateway,
    ) -> None:
        self.learning_service = learning_service
        self.db = db
        self.telegram_gateway = telegram_gateway

    def state(self, user: dict[str, Any]) -> dict[str, Any]:
        session = self.db.learning_sessions.get_resumable_session(int(user["telegram_user_id"]))
        return {
            "active_session": self._session_state(session, user) if session is not None else None,
            "has_teacher_link": self._has_teacher_link(int(user["telegram_user_id"])),
        }

    def start(self, user: dict[str, Any]) -> dict[str, Any]:
        screen = self.learning_service.client_learning_start_service.start_learning(
            int(user["telegram_user_id"]),
            resolve_user_locale(user),
        )
        session = self.db.learning_sessions.claim_active_session(int(user["telegram_user_id"]), "client_web")
        self._notify_telegram_web_claim(user, session)
        return {
            "screen": screen.model_dump(mode="json"),
            "active_session": self._session_state(session, user) if session else None,
        }

    def continue_session(self, user: dict[str, Any]) -> dict[str, Any]:
        telegram_user_id = int(user["telegram_user_id"])
        session = self.db.learning_sessions.claim_resumable_session(telegram_user_id, "client_web")
        if session is None:
            return self.start(user)
        if session.get("current_stage") in READY_STAGES:
            self.learning_service.client_learning_ready_action_service.handle_action(
                telegram_user_id,
                session,
                resolve_user_locale(user),
                str(session.get("current_stage") or ""),
                "yes",
            )
            session = self.db.learning_sessions.get_active_session(telegram_user_id)
        if session is not None and session.get("status") == "active":
            self._notify_telegram_web_claim(user, session)
        return {"active_session": self._session_state(session, user) if session else None}

    def answer(self, user: dict[str, Any], *, session_word_id: int, option_index: int) -> dict[str, Any]:
        telegram_user_id = int(user["telegram_user_id"])
        session = self.db.learning_sessions.get_active_session(telegram_user_id)
        if session is None:
            raise ClientWebLearningNotFoundError("Active training session not found")
        if session.get("active_interface") != "client_web":
            raise ClientWebLearningConflictError("Training session is active in another interface")
        screen = self.learning_service.client_learning_quiz_action_service.handle_answer(
            session,
            resolve_user_locale(user),
            session_word_id,
            option_index,
            max_options=4,
            telegram_user_id=telegram_user_id,
        )
        refreshed = self.db.learning_sessions.get_resumable_session(telegram_user_id)
        return {
            "screen": screen.model_dump(mode="json"),
            "feedback_options": self._feedback_options(screen),
            "active_session": self._session_state(refreshed, user) if refreshed else None,
        }

    def card_action(self, user: dict[str, Any], *, session_word_id: int, action: str) -> dict[str, Any]:
        telegram_user_id = int(user["telegram_user_id"])
        session = self.db.learning_sessions.get_active_session(telegram_user_id)
        if session is None:
            raise ClientWebLearningNotFoundError("Active training session not found")
        if session.get("active_interface") != "client_web":
            raise ClientWebLearningConflictError("Training session is active in another interface")
        screen = self.learning_service.client_learning_card_action_service.handle_action(
            session,
            resolve_user_locale(user),
            session_word_id,
            action,
            telegram_user_id=telegram_user_id,
        )
        refreshed = self.db.learning_sessions.get_active_session(telegram_user_id)
        return {
            "screen": screen.model_dump(mode="json"),
            "active_session": self._session_state(refreshed, user) if refreshed else None,
        }

    def ready_action(self, user: dict[str, Any], *, expected_stage: str, decision: str) -> dict[str, Any]:
        telegram_user_id = int(user["telegram_user_id"])
        session = self.db.learning_sessions.get_active_session(telegram_user_id)
        if session is None:
            raise ClientWebLearningNotFoundError("Active training session not found")
        if session.get("active_interface") != "client_web":
            raise ClientWebLearningConflictError("Training session is active in another interface")
        screen = self.learning_service.client_learning_ready_action_service.handle_action(
            telegram_user_id,
            session,
            resolve_user_locale(user),
            expected_stage,
            decision,
        )
        refreshed = self.db.learning_sessions.get_active_session(telegram_user_id)
        return {
            "screen": screen.model_dump(mode="json"),
            "active_session": self._session_state(refreshed, user) if refreshed else None,
        }

    def finish(self, user: dict[str, Any]) -> dict[str, Any]:
        telegram_user_id = int(user["telegram_user_id"])
        session = self.db.learning_sessions.get_resumable_session(telegram_user_id)
        if session is None:
            return {"active_session": None}
        if session.get("active_interface") != "client_web":
            raise ClientWebLearningConflictError("Training session is active in another interface")
        if session.get("status") != "completed" or session.get("current_stage") not in {"summary", "completed"}:
            raise ClientWebLearningValidationError("Training session is not ready to finish")
        self.db.learning_sessions.finish_completed_summary(int(session["id"]))
        return {"active_session": None}

    def audio_path(self, user: dict[str, Any], *, session_word_id: int) -> str | None:
        session = self.db.learning_sessions.get_active_session(int(user["telegram_user_id"]))
        if session is None:
            raise ClientWebLearningNotFoundError("Active training session not found")
        word = self.db.learning_sessions.get_session_word(session_word_id)
        if word is None or word.get("session_id") != session["id"]:
            raise ClientWebLearningNotFoundError("Audio not found")
        return word.get("audio_path")

    def _session_state(self, session: dict[str, Any] | None, user: dict[str, Any]) -> dict[str, Any] | None:
        if session is None:
            return None
        telegram_user_id = int(user["telegram_user_id"])
        exercise = (
            self._exercise(session, resolve_user_locale(user), telegram_user_id=telegram_user_id)
            if session.get("active_interface") == "client_web"
            else None
        )
        payload = {
            "id": session["id"],
            "status": session["status"],
            "current_stage": session["current_stage"],
            "stage_position": session["stage_position"],
            "active_interface": session.get("active_interface", "telegram_user"),
            "interface_revision": session.get("interface_revision", 0),
            "is_owned_by_web": session.get("active_interface") == "client_web",
        }
        if session.get("active_interface") == "client_web":
            payload["exercise"] = exercise
        return payload

    def _exercise(self, session: dict[str, Any], locale: str, *, telegram_user_id: int) -> dict[str, Any] | None:
        if session["current_stage"] == "card":
            words = self.db.learning_sessions.get_session_words(int(session["id"]))
            position = int(session.get("stage_position") or 0)
            if position >= len(words):
                return None
            word = words[position]
            total_count = len(words)
            return {
                "type": "card",
                "session_word_id": word["session_word_id"],
                "word": word["word"],
                "translation": localized_learning_translation(locale, word),
                "translation_uk": word["translation_uk"],
                "transcription": word.get("phonetic_us"),
                "examples": word.get("examples_json") or [],
                "categories": word.get("categories") or [],
                "audio_url": f"/api/v1/client-web/learning/session-words/{word['session_word_id']}/audio"
                if word.get("audio_path")
                else None,
                "position": position + 1,
                "total": total_count,
                "progress_bar": build_card_progress_bar(position + 1, total_count),
                "can_go_back": position > 0,
                "can_go_forward": position < total_count - 1,
                "next_action": "next" if position < total_count - 1 else "quiz",
            }
        if session["current_stage"] in READY_STAGES:
            stage = str(session["current_stage"])
            return {
                "type": "ready",
                "stage": stage,
                "title": translate(locale, READY_STAGE_INTRO_I18N_KEYS[stage]),
                "prompt": translate(locale, "ready_prompt"),
            }
        if session["current_stage"] in {"summary", "completed"}:
            return self._summary_exercise(int(session["id"]), locale, telegram_user_id=telegram_user_id)
        if session["current_stage"] not in {"quiz_en_uk", "quiz_uk_en", "quiz_gap"}:
            return None
        queue = list(session.get("stage_queue_json") or [])
        position = int(session.get("stage_position") or 0)
        if position >= len(queue):
            if session["current_stage"] == FINAL_QUIZ_STAGE:
                self.learning_service.client_learning_session_completion_service.complete_session(
                    telegram_user_id,
                    session,
                )
                return self._summary_exercise(int(session["id"]), locale, telegram_user_id=telegram_user_id)
            next_ready_stage = NEXT_READY_STAGE.get(str(session["current_stage"]))
            if next_ready_stage:
                self.db.learning_sessions.update_session_state(int(session["id"]), next_ready_stage, [], 0)
                session["current_stage"] = next_ready_stage
                session["stage_queue_json"] = []
                session["stage_position"] = 0
                return {
                    "type": "ready",
                    "stage": next_ready_stage,
                    "title": translate(locale, READY_STAGE_INTRO_I18N_KEYS[next_ready_stage]),
                    "prompt": translate(locale, "ready_prompt"),
                }
            return None
        session_word = self.db.learning_sessions.get_session_word(int(queue[position]))
        if session_word is None:
            return None
        distractors = self.db.similar_words.find_similar_words(
            int(session_word["word_id"]),
            int(session_word["level_id"]),
            excluded_word_ids=[int(session_word["word_id"])],
            limit=8,
            word_source=session_word.get("word_source", "core"),
            telegram_user_id=telegram_user_id,
        )
        quiz = build_quiz_payload(
            stage=str(session["current_stage"]),
            session_word=session_word,
            locale=locale,
            distractors=distractors,
            max_options=4,
        )
        session_words = self.db.learning_sessions.get_session_words(int(session["id"]))
        session_words_by_id = {row["session_word_id"]: row for row in session_words}
        attempts_field = f"{quiz.exercise_type}_attempts"
        is_repeat = bool(int(session_word.get(attempts_field) or 0) > 0)
        return {
            "type": "quiz",
            "stage": str(session["current_stage"]),
            "title": translate(locale, QUIZ_STAGE_META_I18N_KEYS[str(session["current_stage"])]),
            "session_word_id": session_word["session_word_id"],
            "prompt": telegram_html_to_text(quiz.prompt_text),
            "options": quiz.options,
            "position": min(position + 1, len(queue)),
            "total": len(queue),
            "progress_bar": build_quiz_progress_bar(queue, position, session_words_by_id, quiz.exercise_type),
            "is_repeat": is_repeat,
        }

    def _summary_exercise(self, session_id: int, locale: str, *, telegram_user_id: int) -> dict[str, Any]:
        summary_screen = self.learning_service.client_learning_summary_service.build_summary_screen(
            session_id,
            locale,
            telegram_user_id=telegram_user_id,
        )
        summary_title = translate(locale, "summary_title")
        return {
            "type": "summary",
            "title": summary_title,
            "prompt": _strip_summary_title(telegram_html_to_text(summary_screen.text), summary_title),
            "finish_label": translate(locale, "summary_finish_training_button"),
        }

    def _has_teacher_link(self, telegram_user_id: int) -> bool:
        return self.db.teacher_student_links.has_active_teacher(telegram_user_id)

    def _feedback_options(self, screen: Any) -> list[str]:
        return [button.text for button in screen.buttons if button.action == "noop"]

    def _notify_telegram_web_claim(self, user: dict[str, Any], session: dict[str, Any] | None) -> None:
        chat_id = user.get("chat_id")
        if not chat_id or session is None:
            return
        telegram_user_id = user.get("telegram_user_id")
        if telegram_user_id is None:
            return
        locale = resolve_user_locale(user)
        current_time = self.learning_service.time_service.now()
        self._clear_active_telegram_screens(
            telegram_user_id=int(telegram_user_id),
            chat_id=int(chat_id),
            current_time=current_time,
        )
        buttons = [
            [{"text": translate(locale, "menu_resume_learning"), "callback_data": "m:r"}],
            [{"text": translate(locale, "menu_back_to_menu"), "callback_data": "m:menu"}],
        ]
        message_id = self.telegram_gateway.send_message(
            chat_id=int(chat_id),
            text=translate(locale, "web_learning_claim_notice"),
            reply_markup={"inline_keyboard": buttons},
            ignore_errors=True,
        )
        if message_id is not None:
            self._track_telegram_claim_message(
                telegram_user_id=int(telegram_user_id),
                chat_id=int(chat_id),
                message_id=message_id,
                current_time=current_time,
            )
        self.db.admin_auth.schedule_bot_restore(
            telegram_user_id=int(telegram_user_id),
            chat_id=int(chat_id),
            previous_screen_id=None,
            scheduled_for=current_time + timedelta(minutes=WEB_LEARNING_CLAIM_RESTORE_MINUTES),
            current_time=current_time,
        )

    def _clear_active_telegram_screens(self, *, telegram_user_id: int, chat_id: int, current_time: datetime) -> None:
        for message in self.db.bot_message_logs.list_active(telegram_user_id, chat_id):
            is_deleted = self.telegram_gateway.delete_message(
                chat_id=chat_id,
                message_id=int(message["message_id"]),
                ignore_errors=True,
            )
            self.db.bot_message_logs.save_cleanup_result(
                int(message["id"]),
                is_deleted=is_deleted,
                current_time=current_time,
            )

    def _track_telegram_claim_message(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        current_time: datetime,
    ) -> None:
        self.db.bot_message_logs.create(
            telegram_user_id,
            chat_id,
            message_id,
            WEB_LEARNING_CLAIM_SCREEN_ID,
            current_time + timedelta(minutes=WEB_LEARNING_CLAIM_RESTORE_MINUTES),
            current_time,
        )


def _strip_summary_title(text: str, title: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == title:
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return "\n".join(lines)
