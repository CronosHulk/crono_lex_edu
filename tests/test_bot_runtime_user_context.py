from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.bot_runtime.user_context import build_user_context


class FakeTelegramObject(SimpleNamespace):
    def to_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


def build_update(*, include_user: bool = True, include_chat: bool = True):
    return SimpleNamespace(
        effective_user=(
            FakeTelegramObject(
                id=77,
                is_bot=False,
                first_name="Іра",
                last_name="Тест",
                username="ira",
                language_code="uk",
                is_premium=True,
            )
            if include_user
            else None
        ),
        effective_chat=(
            FakeTelegramObject(id=55, type="private", username="cronolex", title="CronoLex")
            if include_chat
            else None
        ),
    )


def test_build_user_context_serializes_user_and_chat() -> None:
    context = build_user_context(build_update())
    payload = json.loads(context.raw_telegram_json)

    assert context.telegram_user_id == 77
    assert context.chat_id == 55
    assert context.is_premium is True
    assert payload["user"]["first_name"] == "Іра"
    assert payload["chat"]["type"] == "private"


def test_build_user_context_allows_missing_chat() -> None:
    context = build_user_context(build_update(include_chat=False))
    payload = json.loads(context.raw_telegram_json)

    assert context.chat_id is None
    assert context.chat_type is None
    assert payload["chat"] is None


def test_build_user_context_raises_when_user_missing() -> None:
    with pytest.raises(RuntimeError, match="Telegram user is required"):
        build_user_context(build_update(include_user=False))
