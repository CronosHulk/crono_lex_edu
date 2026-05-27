from __future__ import annotations

from app.helpers.tts_text import build_tts_spoken_text, has_tts_placeholder


def test_build_tts_spoken_text_expands_placeholder_tokens() -> None:
    assert build_tts_spoken_text("play with smb") == "play with somebody"
    assert build_tts_spoken_text("talk about smth") == "talk about something"
    assert build_tts_spoken_text("ask sb for sth") == "ask somebody for something"
    assert build_tts_spoken_text("pull smb's leg") == "pull somebody's leg"


def test_build_tts_spoken_text_keeps_regular_words() -> None:
    assert build_tts_spoken_text("somebody brought something") == "somebody brought something"
    assert build_tts_spoken_text("sthlm is not a placeholder") == "sthlm is not a placeholder"


def test_has_tts_placeholder_detects_only_short_tokens() -> None:
    assert has_tts_placeholder("play with smb") is True
    assert has_tts_placeholder("talk about something") is False
    assert has_tts_placeholder("sthlm is not a placeholder") is False
