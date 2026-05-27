from __future__ import annotations

from typing import Any

from app.application.client_learning.content import (
    QuizPayload,
    build_quiz_button_row_widths,
    build_quiz_progress_counts,
)
from app.application.client_learning.display import (
    build_quiz_auxiliary_text,
    build_quiz_progress_bar,
    build_quiz_prompt_text,
    prepend_progress_bar_to_prompt_text,
)
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.reference.learning_flow import (
    FINAL_QUIZ_STAGE,
    QUIZ_PROMPT_PROGRESS_STAGES,
    QUIZ_STAGE_META_I18N_KEYS,
)
from app.screen_delivery_policy import with_screen_delivery_policy


def build_quiz_prompt_screen(
    *,
    session: dict[str, Any],
    locale: str,
    quiz: QuizPayload,
    session_word_id: int,
    queue: list[int],
    position: int,
    session_words_by_id: dict[int, dict[str, Any]],
    notice: str | None = None,
) -> ScreenModel:
    progress_bar = build_quiz_progress_bar(queue, position, session_words_by_id, quiz.exercise_type)
    progress_counts = build_quiz_progress_counts(queue, position)
    return ScreenModel(
        screen_id=f"{session['current_stage']}:{session_word_id}",
        text=_build_quiz_screen_text(session["current_stage"], quiz.prompt_text, progress_bar),
        buttons=[
            ButtonModel(action=f"s:{session['id']}:a:{session_word_id}:{index}", text=option)
            for index, option in enumerate(quiz.options)
        ] + [ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu"))],
        keyboard_type="inline",
        metadata=_build_quiz_screen_metadata(
            current_stage=session["current_stage"],
            locale=locale,
            option_count=len(quiz.options),
            progress_bar=progress_bar,
            progress_counts=progress_counts,
        ),
        notice_text=notice,
    )


def build_quiz_feedback_screen(
    *,
    session: dict[str, Any],
    locale: str,
    quiz: QuizPayload,
    session_word_id: int,
    selected_index: int,
    is_correct: bool,
    attempts: int,
    session_word: dict[str, Any] | None,
    session_words: list[dict[str, Any]],
) -> ScreenModel:
    queue = list(session["stage_queue_json"])
    if not is_correct:
        queue.append(session_word_id)
    session_words_by_id = {row["session_word_id"]: row for row in session_words}
    if session_word is not None:
        attempts_field = f"{quiz.exercise_type}_attempts"
        correct_field = f"{quiz.exercise_type}_correct"
        updated_session_word = dict(session_word)
        updated_session_word[attempts_field] = attempts
        updated_session_word[correct_field] = is_correct
        session_words_by_id[session_word_id] = updated_session_word
    progress_bar = build_quiz_progress_bar(
        queue,
        int(session.get("stage_position", 0)),
        session_words_by_id,
        quiz.exercise_type,
    )
    progress_current, progress_total, repeat_index, total_errors = build_quiz_progress_counts(
        queue,
        int(session.get("stage_position", 0)),
    )
    progress_counts = (progress_current, progress_total, repeat_index, total_errors)
    buttons = [
        ButtonModel(action="noop", text=_build_feedback_option_label(quiz, index, option, selected_index, is_correct))
        for index, option in enumerate(quiz.options)
    ]

    metadata = _build_quiz_screen_metadata(
        current_stage=session["current_stage"],
        locale=locale,
        option_count=len(quiz.options),
        progress_bar=progress_bar,
        progress_counts=progress_counts,
    )
    screen = ScreenModel(
        screen_id=f"{session['current_stage']}:{session_word_id}:feedback",
        text=_build_quiz_screen_text(session["current_stage"], quiz.prompt_text, progress_bar),
        buttons=buttons + [ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu"))],
        keyboard_type="inline",
        metadata={"button_row_widths": metadata["button_row_widths"]},
    )
    return with_screen_delivery_policy(
        screen,
        auto_advance_after_ms=1500,
        next_action=f"s:{session['id']}:next",
        auxiliary_message_text=metadata["auxiliary_message_text"],
    )


def _build_feedback_option_label(
    quiz: QuizPayload,
    index: int,
    option: str,
    selected_index: int,
    is_correct: bool,
) -> str:
    if index == selected_index:
        return f"{option} {'✅' if is_correct else '❌'}"
    if option == quiz.correct_answer:
        return f"{option} ✅"
    return option


def _build_quiz_screen_text(current_stage: str, prompt_text: str, progress_bar: str) -> str:
    if current_stage in QUIZ_PROMPT_PROGRESS_STAGES:
        return build_quiz_prompt_text(prompt_text, progress_bar=progress_bar)
    if current_stage == FINAL_QUIZ_STAGE:
        return prepend_progress_bar_to_prompt_text(prompt_text, progress_bar=progress_bar)
    return prompt_text


def _build_quiz_screen_metadata(
    *,
    current_stage: str,
    locale: str,
    option_count: int,
    progress_bar: str,
    progress_counts: tuple[int, int, int, int],
) -> dict[str, Any]:
    progress_current, progress_total, repeat_index, total_errors = progress_counts
    return {
        "auxiliary_message_text": build_quiz_auxiliary_text(
            locale,
            stage_title=translate(locale, QUIZ_STAGE_META_I18N_KEYS[current_stage]),
            progress_bar=progress_bar,
            current_position=progress_current,
            total_count=progress_total,
            total_errors=total_errors,
            repeat_progress_current=repeat_index,
            repeat_progress_total=total_errors,
        ),
        "button_row_widths": build_quiz_button_row_widths(option_count),
    }
