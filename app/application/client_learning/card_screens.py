from __future__ import annotations

from typing import Any

from app.application.client_learning.content import resolve_translation_for_locale
from app.application.client_learning.display import (
    build_card_caption,
    build_card_hint_text_for_count,
    normalize_phonetic,
)
from app.application.client_learning.navigation import build_card_navigation_buttons
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.screen_delivery_policy import with_screen_delivery_policy


def build_card_screen(
    *,
    session: dict[str, Any],
    locale: str,
    words: list[dict[str, Any]],
    position: int,
) -> ScreenModel:
    word = words[position]
    resolved_translation = resolve_translation_for_locale(locale, word)
    text = build_card_caption(
        locale=locale,
        word=word["word"],
        parts_of_speech=word.get("parts_of_speech") or [],
        phonetic=normalize_phonetic(word["phonetic_us"]),
        translation=resolved_translation,
        examples=word["examples_json"] or [],
        categories=word.get("categories") or [],
    )
    navigation_buttons = build_card_navigation_buttons(locale, session["id"], words, position)
    screen = ScreenModel(
        screen_id=f"card:{word['session_word_id']}",
        text=text,
        buttons=[
            *navigation_buttons,
            ButtonModel(action=f"s:{session['id']}:c:{word['session_word_id']}:known", text=translate(locale, "card_known_button")),
            ButtonModel(
                action="m:menu",
                text=translate(locale, "menu_back_to_menu"),
            ),
        ],
        keyboard_type="inline",
        clear_chat=True,
        audio_path=word["audio_path"],
        metadata={
            "button_row_widths": [3, 1, 1],
        },
    )
    return with_screen_delivery_policy(
        screen,
        auxiliary_message_text=build_card_hint_text_for_count(
            locale,
            selected_words_count=int(session.get("words_target_count") or len(words)),
        ),
    )
