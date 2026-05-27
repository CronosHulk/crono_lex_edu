from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FactoryLady:
    counters: dict[str, int] = field(default_factory=dict)

    def _next(self, key: str) -> int:
        current = self.counters.get(key, 0) + 1
        self.counters[key] = current
        return current

    def create_user(self, **overrides: Any) -> dict[str, Any]:
        number = self._next("user")
        payload = {
            "telegram_user_id": 1000 + number,
            "first_name": f"User{number}",
            "status": "active",
            "created": datetime(2026, 4, 6, 10, 0, 0),
            "updated": datetime(2026, 4, 6, 10, 0, 0),
        }
        payload.update(overrides)
        return payload

    def create_language_level(self, **overrides: Any) -> dict[str, Any]:
        number = self._next("level")
        payload = {
            "id": number,
            "title": f"A{number}",
            "description": None,
        }
        payload.update(overrides)
        return payload

    def create_word(self, **overrides: Any) -> dict[str, Any]:
        number = self._next("word")
        translation_uk = overrides.pop("translation_uk", None)
        payload = {
            "id": 5000 + number,
            "word": f"word_{number}",
            "part_of_speech": "noun",
            "translation_uk": {
                "text": f"переклад_{number}",
            },
            "examples_json": [f"Example sentence {number}."],
            "audio_path": f"word_base/word_audio/{number:04d}_word.mp3",
        }
        if translation_uk is not None:
            payload["translation_uk"].update(translation_uk)
        payload.update(overrides)
        return payload
