from __future__ import annotations

from app.application.client_learning.navigation import build_card_navigation_buttons


def test_build_card_navigation_buttons_disables_back_on_first_card() -> None:
    buttons = build_card_navigation_buttons(
        "uk",
        77,
        [{"session_word_id": 11}, {"session_word_id": 12}],
        0,
    )

    assert [button.action for button in buttons] == ["noop", "noop", "s:77:c:11:next"]
    assert [button.text for button in buttons] == [" ", "1/2", "→"]


def test_build_card_navigation_buttons_starts_quiz_on_last_card() -> None:
    buttons = build_card_navigation_buttons(
        "uk",
        77,
        [{"session_word_id": 11}, {"session_word_id": 12}],
        1,
    )

    assert [button.action for button in buttons] == ["s:77:c:12:back", "noop", "s:77:c:12:quiz"]
    assert [button.text for button in buttons] == ["←", "2/2", "До вправ"]
