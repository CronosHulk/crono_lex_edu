from __future__ import annotations

from typing import Any

from app.contracts import ButtonModel
from app.i18n import translate


def build_card_navigation_buttons(locale: str, session_id: int, words: list[dict[str, Any]], position: int) -> list[ButtonModel]:
    current_word = words[position]
    back_action = "noop" if position <= 0 else f"s:{session_id}:c:{current_word['session_word_id']}:back"
    if position >= len(words) - 1:
        forward_action = f"s:{session_id}:c:{current_word['session_word_id']}:quiz"
        forward_text = translate(locale, "card_quiz_short_button")
    else:
        forward_action = f"s:{session_id}:c:{current_word['session_word_id']}:next"
        forward_text = translate(locale, "card_forward_arrow_button")
    return [
        ButtonModel(action=back_action, text=translate(locale, "card_back_arrow_button") if position > 0 else " "),
        ButtonModel(action="noop", text=translate(locale, "card_position_button", current=position + 1, total=len(words))),
        ButtonModel(action=forward_action, text=forward_text),
    ]
