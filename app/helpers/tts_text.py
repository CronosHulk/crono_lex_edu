from __future__ import annotations

import re

TTS_PLACEHOLDER_SPOKEN_FORMS = {
    "sb": "somebody",
    "smb": "somebody",
    "sth": "something",
    "smth": "something",
}

_PLACEHOLDER_PATTERN = re.compile(r"(?<![A-Za-z])(?P<token>sb|smb|sth|smth)(?P<possessive>'s)?(?![A-Za-z])", re.IGNORECASE)


def build_tts_spoken_text(text: str) -> str:
    def replace_placeholder(match: re.Match[str]) -> str:
        spoken = TTS_PLACEHOLDER_SPOKEN_FORMS[match.group("token").lower()]
        if match.group("possessive"):
            return f"{spoken}'s"
        return spoken

    return _PLACEHOLDER_PATTERN.sub(replace_placeholder, text)


def has_tts_placeholder(text: str) -> bool:
    return _PLACEHOLDER_PATTERN.search(text) is not None
