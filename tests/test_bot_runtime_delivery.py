from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import BinaryIO

import pytest

from app.bot_runtime.delivery import (
    ensure_reply_keyboard_removed,
    is_message_not_editable_error,
    is_message_not_modified_error,
    send_new_screen_message,
    try_edit_active_screen,
)
from app.bot_runtime.state import ActiveScreenMessage
from app.contracts import ScreenModel


class FakeAudioStorageProvider:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.calls: list[str] = []

    def open_binary(self, audio_path: str | Path | None) -> BinaryIO:
        self.calls.append(str(audio_path))
        payload = self.payloads.get(str(audio_path))
        if payload is None:
            raise FileNotFoundError("Audio not found")
        return BytesIO(payload)


class FakeMessage:
    def __init__(self, message_id: int) -> None:
        self.message_id = message_id


class FakeBot:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.edit_text_error: Exception | None = None
        self.delete_error: Exception | None = None

    async def edit_message_text(self, **kwargs) -> None:
        if self.edit_text_error is not None:
            raise self.edit_text_error
        self.calls.append(("edit_message_text", kwargs))

    async def edit_message_media(self, **kwargs) -> None:
        media = kwargs["media"]
        kwargs["audio_bytes"] = media.media.input_file_content
        kwargs["media_filename"] = media.media.filename
        self.calls.append(("edit_message_media", kwargs))

    async def send_message(self, **kwargs):
        self.calls.append(("send_message", kwargs))
        return FakeMessage(201)

    async def send_audio(self, **kwargs):
        kwargs["audio_bytes"] = kwargs["audio"].read()
        self.calls.append(("send_audio", kwargs))
        return FakeMessage(202)

    async def delete_message(self, **kwargs) -> None:
        if self.delete_error is not None:
            raise self.delete_error
        self.calls.append(("delete_message", kwargs))


def test_try_edit_active_screen_updates_text_message_state() -> None:
    bot = FakeBot()
    active_message = ActiveScreenMessage(message_id=101, has_audio=False, screen_id="old")

    edited = asyncio.run(
        try_edit_active_screen(
            application=SimpleNamespace(bot=bot),
            chat_id=10,
            active_message=active_message,
            screen=ScreenModel(screen_id="menu", text="Меню"),
            keyboard=None,
            screen_text="Меню",
        )
    )

    assert edited is True
    assert active_message.screen_id == "menu"
    assert active_message.has_audio is False
    assert bot.calls[0][0] == "edit_message_text"


def test_try_edit_active_screen_reraises_cancelled_error() -> None:
    bot = FakeBot()
    bot.edit_text_error = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            try_edit_active_screen(
                application=SimpleNamespace(bot=bot),
                chat_id=10,
                active_message=ActiveScreenMessage(message_id=101, has_audio=False),
                screen=ScreenModel(screen_id="menu", text="Меню"),
                keyboard=None,
                screen_text="Меню",
            )
        )


def test_send_new_screen_message_sends_text_message() -> None:
    bot = FakeBot()

    message = asyncio.run(
        send_new_screen_message(
            application=SimpleNamespace(bot=bot),
            chat_id=10,
            screen=ScreenModel(screen_id="menu", text="Меню"),
            keyboard=None,
            screen_text="Меню",
            disable_notification=True,
        )
    )

    assert message.message_id == 201
    assert bot.calls == [
        (
            "send_message",
            {
                "chat_id": 10,
                "text": "Меню",
                "reply_markup": None,
                "parse_mode": "HTML",
                "disable_notification": True,
            },
        )
    ]


def test_send_new_screen_message_sends_audio_from_injected_storage_provider() -> None:
    bot = FakeBot()
    provider = FakeAudioStorageProvider({"audio/0001_word.mp3": b"audio"})

    message = asyncio.run(
        send_new_screen_message(
            application=SimpleNamespace(bot=bot, bot_data={"audio_storage_provider": provider}),
            chat_id=10,
            screen=ScreenModel(screen_id="card", text="Слово", audio_path="audio/0001_word.mp3"),
            keyboard=None,
            screen_text="Слово",
            disable_notification=False,
        )
    )

    assert message.message_id == 202
    assert bot.calls[0][0] == "send_audio"
    assert bot.calls[0][1]["caption"] == "Слово"
    assert bot.calls[0][1]["filename"] == "word.mp3"
    assert bot.calls[0][1]["audio_bytes"] == b"audio"
    assert provider.calls == ["audio/0001_word.mp3"]


def test_send_new_screen_message_requires_configured_audio_storage_provider() -> None:
    bot = FakeBot()

    with pytest.raises(RuntimeError, match="Telegram audio storage provider is not configured"):
        asyncio.run(
            send_new_screen_message(
                application=SimpleNamespace(bot=bot, bot_data={}),
                chat_id=10,
                screen=ScreenModel(screen_id="card", text="Слово", audio_path="audio/0001_word.mp3"),
                keyboard=None,
                screen_text="Слово",
                disable_notification=False,
            )
        )

    assert bot.calls == []


def test_try_edit_active_screen_edits_audio_from_injected_storage_provider() -> None:
    bot = FakeBot()
    provider = FakeAudioStorageProvider({"audio/0001_word.mp3": b"edited-audio"})
    active_message = ActiveScreenMessage(message_id=101, has_audio=True, screen_id="old")

    edited = asyncio.run(
        try_edit_active_screen(
            application=SimpleNamespace(bot=bot, bot_data={"audio_storage_provider": provider}),
            chat_id=10,
            active_message=active_message,
            screen=ScreenModel(screen_id="card", text="Слово", audio_path="audio/0001_word.mp3"),
            keyboard=None,
            screen_text="Слово",
        )
    )

    assert edited is True
    assert bot.calls[0][0] == "edit_message_media"
    assert bot.calls[0][1]["audio_bytes"] == b"edited-audio"
    assert bot.calls[0][1]["media_filename"] == "word.mp3"
    assert provider.calls == ["audio/0001_word.mp3"]


def test_ensure_reply_keyboard_removed_handles_empty_and_existing_state() -> None:
    bot = FakeBot()

    asyncio.run(ensure_reply_keyboard_removed(SimpleNamespace(bot=bot), chat_id=10, user_data=None))
    asyncio.run(
        ensure_reply_keyboard_removed(
            SimpleNamespace(bot=bot),
            chat_id=10,
            user_data={"reply_keyboard_removed": True},
        )
    )

    assert bot.calls == []


def test_ensure_reply_keyboard_removed_sends_and_deletes_cleanup_message() -> None:
    bot = FakeBot()
    user_data: dict[str, object] = {}

    asyncio.run(ensure_reply_keyboard_removed(SimpleNamespace(bot=bot), chat_id=10, user_data=user_data))

    assert user_data["reply_keyboard_removed"] is True
    assert [call[0] for call in bot.calls] == ["send_message", "delete_message"]


def test_ensure_reply_keyboard_removed_reraises_cancelled_delete() -> None:
    bot = FakeBot()
    bot.delete_error = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(ensure_reply_keyboard_removed(SimpleNamespace(bot=bot), chat_id=10, user_data={}))


def test_ensure_reply_keyboard_removed_swallows_delete_failure() -> None:
    bot = FakeBot()
    bot.delete_error = RuntimeError("already gone")
    user_data: dict[str, object] = {}

    asyncio.run(ensure_reply_keyboard_removed(SimpleNamespace(bot=bot), chat_id=10, user_data=user_data))

    assert user_data["reply_keyboard_removed"] is True
    assert [call[0] for call in bot.calls] == ["send_message"]


def test_delivery_error_classifiers_recognize_known_patterns() -> None:
    assert is_message_not_editable_error(RuntimeError("Message can't be edited"))
    assert not is_message_not_editable_error(RuntimeError("Network timeout"))
    assert is_message_not_modified_error(
        RuntimeError("specified new message content and reply markup are exactly the same")
    )
    assert not is_message_not_modified_error(RuntimeError("Message can't be edited"))
