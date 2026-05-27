from __future__ import annotations

from app.application.client_learning.content import QuizPayload
from app.application.client_learning.quiz_screens import (
    _build_quiz_screen_text,
    build_quiz_feedback_screen,
    build_quiz_prompt_screen,
)
from app.i18n import translate


def test_build_quiz_prompt_screen_builds_en_uk_progress_prompt() -> None:
    screen = build_quiz_prompt_screen(
        session=_session(current_stage="quiz_en_uk"),
        locale="uk",
        quiz=QuizPayload(
            exercise_type="en_uk",
            prompt_text="learn",
            correct_answer="вивчати",
            options=["читати", "вивчати", "писати"],
        ),
        session_word_id=11,
        queue=[11],
        position=0,
        session_words_by_id={11: _session_word(session_word_id=11)},
    )

    assert screen.screen_id == "quiz_en_uk:11"
    assert [button.action for button in screen.buttons] == [
        "s:77:a:11:0",
        "s:77:a:11:1",
        "s:77:a:11:2",
        "m:menu",
    ]
    assert [button.text for button in screen.buttons] == ["читати", "вивчати", "писати", translate("uk", "menu_back_to_menu")]
    assert screen.metadata["button_row_widths"] == [1, 1, 1, 1]
    assert "●" in screen.text
    assert screen.notice_text is None


def test_build_quiz_prompt_screen_uses_final_stage_progress_prefix() -> None:
    screen = build_quiz_prompt_screen(
        session=_session(current_stage="quiz_gap"),
        locale="uk",
        quiz=QuizPayload(
            exercise_type="gap",
            prompt_text="<b>l_____</b>",
            correct_answer="learn",
            options=["read", "write", "learn", "listen"],
        ),
        session_word_id=11,
        queue=[11],
        position=0,
        session_words_by_id={11: _session_word(session_word_id=11)},
    )

    assert screen.text.startswith("[")
    assert "<b>l_____</b>" in screen.text
    assert screen.metadata["button_row_widths"] == [2, 2, 1]


def test_build_quiz_prompt_screen_preserves_notice_and_auxiliary_text() -> None:
    screen = build_quiz_prompt_screen(
        session=_session(current_stage="quiz_uk_en", queue=[11, 12], position=1),
        locale="uk",
        quiz=QuizPayload(
            exercise_type="uk_en",
            prompt_text="вивчати",
            correct_answer="learn",
            options=["read", "learn", "write"],
        ),
        session_word_id=12,
        queue=[11, 12],
        position=1,
        session_words_by_id={11: _session_word(session_word_id=11), 12: _session_word(session_word_id=12)},
        notice="Notice",
    )

    assert screen.notice_text == "Notice"
    assert screen.metadata["auxiliary_message_text"] == translate("uk", "card_hint_title") + "\n" + translate("uk", "quiz_uk_en_meta")


def test_build_quiz_feedback_screen_marks_correct_selected_answer() -> None:
    screen = build_quiz_feedback_screen(
        session=_session(current_stage="quiz_en_uk"),
        locale="uk",
        quiz=QuizPayload(
            exercise_type="en_uk",
            prompt_text="learn",
            correct_answer="вивчати",
            options=["читати", "вивчати", "писати"],
        ),
        session_word_id=11,
        selected_index=1,
        is_correct=True,
        attempts=1,
        session_word=_session_word(session_word_id=11),
        session_words=[_session_word(session_word_id=11)],
    )

    assert screen.screen_id == "quiz_en_uk:11:feedback"
    assert [button.text for button in screen.buttons] == ["читати", "вивчати ✅", "писати", translate("uk", "menu_back_to_menu")]
    assert [button.action for button in screen.buttons] == ["noop", "noop", "noop", "m:menu"]
    assert screen.metadata["auto_advance_after_ms"] == 1500
    assert screen.metadata["next_action"] == "s:77:next"
    assert screen.metadata["button_row_widths"] == [1, 1, 1, 1]
    assert "●" in screen.text


def test_build_quiz_feedback_screen_marks_wrong_answer_and_correct_option() -> None:
    screen = build_quiz_feedback_screen(
        session=_session(current_stage="quiz_en_uk", queue=[11, 12], position=0),
        locale="uk",
        quiz=QuizPayload(
            exercise_type="en_uk",
            prompt_text="learn",
            correct_answer="вивчати",
            options=["читати", "вивчати", "писати"],
        ),
        session_word_id=11,
        selected_index=0,
        is_correct=False,
        attempts=2,
        session_word=_session_word(session_word_id=11),
        session_words=[_session_word(session_word_id=11), _session_word(session_word_id=12)],
    )

    assert [button.text for button in screen.buttons[:3]] == ["читати ❌", "вивчати ✅", "писати"]
    assert screen.metadata["button_row_widths"] == [1, 1, 1, 1]
    assert screen.metadata["auxiliary_message_text"] == translate("uk", "card_hint_title") + "\n" + translate("uk", "quiz_en_uk_meta")
    assert "●○" in screen.text


def test_build_quiz_feedback_screen_prepends_progress_for_final_stage() -> None:
    screen = build_quiz_feedback_screen(
        session=_session(current_stage="quiz_gap"),
        locale="uk",
        quiz=QuizPayload(
            exercise_type="gap",
            prompt_text="<b>l_____</b>",
            correct_answer="learn",
            options=["read", "write", "learn", "listen"],
        ),
        session_word_id=11,
        selected_index=2,
        is_correct=True,
        attempts=1,
        session_word=_session_word(session_word_id=11),
        session_words=[_session_word(session_word_id=11)],
    )

    assert screen.screen_id == "quiz_gap:11:feedback"
    assert screen.text.startswith("[")
    assert "<b>l_____</b>" in screen.text
    assert screen.metadata["button_row_widths"] == [2, 2, 1]


def test_build_quiz_screen_text_keeps_prompt_raw_for_unknown_stage() -> None:
    assert _build_quiz_screen_text("quiz_custom", "raw prompt", "[●]") == "raw prompt"


def _session(*, current_stage: str, queue: list[int] | None = None, position: int = 0) -> dict[str, object]:
    return {
        "id": 77,
        "current_stage": current_stage,
        "stage_queue_json": queue or [11],
        "stage_position": position,
    }


def _session_word(*, session_word_id: int) -> dict[str, object]:
    return {
        "session_word_id": session_word_id,
        "en_uk_attempts": 0,
        "en_uk_correct": False,
        "uk_en_attempts": 0,
        "uk_en_correct": False,
        "gap_attempts": 0,
        "gap_correct": False,
    }
