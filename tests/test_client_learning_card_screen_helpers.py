from __future__ import annotations

from app.application.client_learning.card_screens import build_card_screen
from app.i18n import translate


def test_build_card_screen_renders_word_audio_and_actions() -> None:
    words = [_word(11, "learn"), _word(12, "read")]

    screen = build_card_screen(session={"id": 77, "words_target_count": 5}, locale="uk", words=words, position=0)

    assert screen.screen_id == "card:11"
    assert "<b>learn</b>" in screen.text
    assert "вивчати" in screen.text
    assert screen.audio_path == "audio/learn.mp3"
    assert screen.clear_chat is True
    assert screen.keyboard_type == "inline"
    assert [button.action for button in screen.buttons] == [
        "noop",
        "noop",
        "s:77:c:11:next",
        "s:77:c:11:known",
        "m:menu",
    ]
    assert [button.text for button in screen.buttons[-2:]] == [
        translate("uk", "card_known_button"),
        translate("uk", "menu_back_to_menu"),
    ]
    assert [button.text for button in screen.buttons[:3]] == [" ", "1/2", "→"]
    assert screen.metadata["button_row_widths"] == [3, 1, 1]
    assert translate("uk", "card_hint_title") in screen.metadata["auxiliary_message_text"]
    assert "[" not in screen.metadata["auxiliary_message_text"]


def test_build_card_screen_uses_compact_navigation_and_hint() -> None:
    words = [_word(11, "learn"), _word(12, "read")]

    screen = build_card_screen(session={"id": 77, "words_target_count": 1}, locale="uk", words=words, position=1)

    assert "Підказка:" in screen.metadata["auxiliary_message_text"]
    assert "Вибрано" not in screen.metadata["auxiliary_message_text"]
    assert [button.action for button in screen.buttons[:3]] == [
        "s:77:c:12:back",
        "noop",
        "s:77:c:12:quiz",
    ]
    assert [button.text for button in screen.buttons[:3]] == ["←", "2/2", "До вправ"]


def test_build_card_screen_preserves_empty_audio_path() -> None:
    word = _word(11, "learn")
    word["audio_path"] = ""

    screen = build_card_screen(session={"id": 77}, locale="uk", words=[word], position=0)

    assert screen.audio_path == ""


def _word(session_word_id: int, word: str) -> dict[str, object]:
    return {
        "session_word_id": session_word_id,
        "word": word,
        "phonetic_us": "/lɜːrn/" if word == "learn" else "/riːd/",
        "translation_uk": "вивчати" if word == "learn" else "читати",
        "translation_ru": "",
        "translation_pl": "",
        "examples_json": [f"I {word} daily."],
        "categories": ["general"],
        "parts_of_speech": ["verb"],
        "audio_path": f"audio/{word}.mp3",
    }
