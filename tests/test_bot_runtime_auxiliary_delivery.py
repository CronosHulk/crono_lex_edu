from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.bot_runtime.auxiliary_delivery import sync_auxiliary_screen_message
from app.bot_runtime.auxiliary_delivery import (
    sync_auxiliary_screen_message as compatibility_sync_auxiliary_screen_message,
)
from app.contracts import ButtonModel


class FakeBot:
    def __init__(self) -> None:
        self.edit_error: Exception | None = None
        self.edit_calls: list[tuple[int, int, str, object]] = []
        self.send_calls: list[tuple[int, str, bool, object]] = []

    async def edit_message_text(self, *, chat_id: int, message_id: int, text: str, reply_markup=None) -> None:
        if self.edit_error is not None:
            raise self.edit_error
        self.edit_calls.append((chat_id, message_id, text, reply_markup))

    async def send_message(self, *, chat_id: int, text: str, disable_notification: bool, reply_markup=None):
        self.send_calls.append((chat_id, text, disable_notification, reply_markup))
        return SimpleNamespace(message_id=700 + len(self.send_calls))


class FakeApiClient:
    def __init__(self) -> None:
        self.track_calls: list[tuple[int, int, int, str]] = []

    async def track_bot_message(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after_hours=None,
    ):
        self.track_calls.append((telegram_user_id, chat_id, message_id, screen_id))
        return SimpleNamespace(id=1700 + len(self.track_calls))


def build_application():
    return SimpleNamespace(bot=FakeBot())


def test_sync_auxiliary_screen_message_sends_and_tracks_new_hint() -> None:
    application = build_application()
    api_client = FakeApiClient()
    user_data: dict[str, object] = {}

    asyncio.run(
        sync_auxiliary_screen_message(
            application=application,
            api_client=api_client,
            chat_id=10,
            user_data=user_data,
            telegram_user_id=77,
            auxiliary_text="hint",
            disable_notification=True,
        )
    )

    assert application.bot.send_calls == [(10, "hint", True, None)]
    assert api_client.track_calls == [(77, 10, 701, "auxiliary:card_hint")]
    assert user_data["auxiliary_screen_message_id"] == 701
    assert user_data["auxiliary_screen_message_log_id"] == 1701


def test_sync_auxiliary_screen_message_sends_hint_with_inline_buttons() -> None:
    application = build_application()
    user_data: dict[str, object] = {}

    asyncio.run(
        sync_auxiliary_screen_message(
            application=application,
            api_client=None,
            chat_id=10,
            user_data=user_data,
            telegram_user_id=77,
            auxiliary_text="settings",
            auxiliary_buttons=[ButtonModel(action="m:settings", text="Settings")],
            disable_notification=True,
        )
    )

    reply_markup = application.bot.send_calls[0][3]
    assert reply_markup.inline_keyboard[0][0].text == "Settings"
    assert reply_markup.inline_keyboard[0][0].callback_data == "m:settings"


def test_sync_auxiliary_screen_message_deletes_existing_hint_when_text_missing(monkeypatch) -> None:
    application = build_application()
    user_data = {"auxiliary_screen_message_id": 701, "auxiliary_screen_message_log_id": 1701}
    clear_calls: list[tuple[int, list[int], list[dict[str, int]]]] = []
    monkeypatch.setattr(
        "app.bot_runtime.auxiliary_delivery.clear_messages",
        lambda chat_id, application, message_ids, message_log_refs: clear_calls.append(
            (chat_id, message_ids, message_log_refs)
        )
        or asyncio.sleep(0),
    )

    asyncio.run(
        sync_auxiliary_screen_message(
            application=application,
            api_client=None,
            chat_id=10,
            user_data=user_data,
            telegram_user_id=77,
            auxiliary_text=None,
            disable_notification=True,
        )
    )

    assert clear_calls == [(10, [701], [{"message_id": 701, "message_log_id": 1701}])]
    assert user_data["auxiliary_screen_message_id"] is None
    assert user_data["auxiliary_screen_message_log_id"] is None


def test_sync_auxiliary_screen_message_edits_existing_hint() -> None:
    application = build_application()
    user_data = {"auxiliary_screen_message_id": 701, "auxiliary_screen_message_log_id": 1701}

    asyncio.run(
        sync_auxiliary_screen_message(
            application=application,
            api_client=None,
            chat_id=10,
            user_data=user_data,
            telegram_user_id=77,
            auxiliary_text="updated",
            disable_notification=True,
        )
    )

    assert application.bot.edit_calls == [(10, 701, "updated", None)]
    assert application.bot.send_calls == []


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("message is not modified"),
        RuntimeError("specified new message content and reply markup are exactly the same"),
    ],
)
def test_sync_auxiliary_screen_message_keeps_not_modified_hint(error: Exception) -> None:
    application = build_application()
    application.bot.edit_error = error
    user_data = {"auxiliary_screen_message_id": 701, "auxiliary_screen_message_log_id": 1701}

    asyncio.run(
        sync_auxiliary_screen_message(
            application=application,
            api_client=None,
            chat_id=10,
            user_data=user_data,
            telegram_user_id=77,
            auxiliary_text="same",
            disable_notification=True,
        )
    )

    assert application.bot.send_calls == []
    assert user_data["auxiliary_screen_message_id"] == 701


def test_sync_auxiliary_screen_message_replaces_uneditable_hint(monkeypatch) -> None:
    application = build_application()
    application.bot.edit_error = RuntimeError("message can't be edited")
    api_client = FakeApiClient()
    user_data = {"auxiliary_screen_message_id": 601, "auxiliary_screen_message_log_id": 1601}
    clear_calls: list[list[int]] = []
    monkeypatch.setattr(
        "app.bot_runtime.auxiliary_delivery.clear_messages",
        lambda chat_id, application, message_ids, message_log_refs: clear_calls.append(message_ids)
        or asyncio.sleep(0),
    )

    asyncio.run(
        sync_auxiliary_screen_message(
            application=application,
            api_client=api_client,
            chat_id=10,
            user_data=user_data,
            telegram_user_id=77,
            auxiliary_text="replacement",
            disable_notification=False,
        )
    )

    assert clear_calls == [[601]]
    assert application.bot.send_calls == [(10, "replacement", False, None)]
    assert user_data["auxiliary_screen_message_id"] == 701
    assert user_data["auxiliary_screen_message_log_id"] == 1701


def test_sync_auxiliary_screen_message_propagates_unexpected_error_and_cancellation() -> None:
    application = build_application()
    user_data = {"auxiliary_screen_message_id": 701, "auxiliary_screen_message_log_id": 1701}

    application.bot.edit_error = RuntimeError("backend down")
    with pytest.raises(RuntimeError):
        asyncio.run(
            sync_auxiliary_screen_message(
                application=application,
                api_client=None,
                chat_id=10,
                user_data=user_data,
                telegram_user_id=77,
                auxiliary_text="hint",
                disable_notification=True,
            )
        )

    application.bot.edit_error = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            sync_auxiliary_screen_message(
                application=application,
                api_client=None,
                chat_id=10,
                user_data=user_data,
                telegram_user_id=77,
                auxiliary_text="hint",
                disable_notification=True,
            )
        )


def test_sync_auxiliary_screen_message_handles_missing_text_without_state() -> None:
    asyncio.run(
        sync_auxiliary_screen_message(
            application=build_application(),
            api_client=None,
            chat_id=10,
            user_data=None,
            telegram_user_id=77,
            auxiliary_text=None,
            disable_notification=True,
        )
    )


def test_auxiliary_delivery_compatibility_import_stays_on_app_bot() -> None:
    assert compatibility_sync_auxiliary_screen_message is sync_auxiliary_screen_message
