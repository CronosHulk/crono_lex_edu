from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.bot_runtime.message_tracking import (
    clear_messages,
    clear_tracked_messages,
    is_message_already_deleted_error,
    is_sticky_import_report_screen_id,
    is_tracked_message_still_active,
    list_chat_tracked_messages,
    resolve_callback_active_screen_message,
    save_cleanup_deleted_result,
    save_cleanup_failure,
    sweep_chat_tracked_messages,
    track_sent_bot_message,
)
from app.bot_runtime.message_tracking import clear_messages as compatibility_clear_messages
from app.bot_runtime.message_tracking import (
    clear_tracked_messages as compatibility_clear_tracked_messages,
)
from app.bot_runtime.message_tracking import (
    list_chat_tracked_messages as compatibility_list_chat_tracked_messages,
)
from app.bot_runtime.message_tracking import (
    resolve_callback_active_screen_message as compatibility_resolve_callback_active_screen_message,
)
from app.bot_runtime.message_tracking import (
    sweep_chat_tracked_messages as compatibility_sweep_chat_tracked_messages,
)


class FakeBot:
    def __init__(self) -> None:
        self.delete_calls: list[tuple[int, int]] = []
        self.delete_errors: dict[int, Exception] = {}

    async def delete_message(self, *, chat_id: int, message_id: int) -> None:
        error = self.delete_errors.get(message_id)
        if error is not None:
            raise error
        self.delete_calls.append((chat_id, message_id))


class FakeApiClient:
    def __init__(self) -> None:
        self.track_error: Exception | None = None
        self.cleanup_error: Exception | None = None
        self.active_messages: list[object] = []
        self.track_calls: list[tuple[int, int, int, str, int | None]] = []
        self.cleanup_results: list[tuple[int, bool, str | None]] = []
        self.list_active_error: Exception | None = None
        self.lookup_error: Exception | None = None
        self.lookup_result: object | None = None

    async def track_bot_message(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after_hours: int | None = None,
    ):
        if self.track_error is not None:
            raise self.track_error
        self.track_calls.append((telegram_user_id, chat_id, message_id, screen_id, delete_after_hours))
        return SimpleNamespace(id=message_id + 1000, message_id=message_id, screen_id=screen_id)

    async def save_bot_message_cleanup_result(
        self,
        *,
        message_log_id: int,
        is_deleted: bool,
        error_text: str | None = None,
    ) -> None:
        if self.cleanup_error is not None:
            raise self.cleanup_error
        self.cleanup_results.append((message_log_id, is_deleted, error_text))

    async def list_active_bot_messages(self, *, telegram_user_id: int, chat_id: int):
        if self.list_active_error is not None:
            raise self.list_active_error
        return SimpleNamespace(messages=list(self.active_messages))

    async def lookup_bot_message(self, *, telegram_user_id: int, chat_id: int, message_id: int):
        if self.lookup_error is not None:
            raise self.lookup_error
        return self.lookup_result


def build_application(api_client: FakeApiClient | None = None):
    return SimpleNamespace(bot=FakeBot(), bot_data={"api_client": api_client})


def test_clear_tracked_messages_resets_state_and_deletes_active_and_auxiliary(monkeypatch) -> None:
    context = SimpleNamespace(
        application=build_application(FakeApiClient()),
        user_data={
            "bot_message_ids": [100],
            "bot_message_log_refs": [{"message_id": 100, "message_log_id": 900}],
            "active_screen_message_id": 100,
            "active_screen_message_log_id": 900,
            "active_screen_has_audio": True,
            "auxiliary_screen_message_id": 77,
            "auxiliary_screen_message_log_id": 777,
        },
    )
    clear_calls: list[tuple[int, list[int], list[dict[str, int]]]] = []
    monkeypatch.setattr(
        "app.bot_runtime.message_tracking.clear_messages",
        lambda chat_id, application, message_ids, message_log_refs: clear_calls.append(
            (chat_id, message_ids, message_log_refs)
        )
        or asyncio.sleep(0),
    )

    asyncio.run(clear_tracked_messages(10, context))

    assert clear_calls == [
        (
            10,
            [100, 77],
            [{"message_id": 100, "message_log_id": 900}, {"message_id": 77, "message_log_id": 777}],
        )
    ]
    assert context.user_data["bot_message_ids"] == []
    assert context.user_data["active_screen_message_id"] is None
    assert context.user_data["active_screen_has_audio"] is False
    assert context.user_data["auxiliary_screen_message_id"] is None


def test_clear_messages_marks_missing_telegram_message_as_deleted() -> None:
    api_client = FakeApiClient()
    application = build_application(api_client)
    application.bot.delete_errors[100] = RuntimeError("Message to delete not found")

    asyncio.run(clear_messages(10, application, [100], [{"message_id": 100, "message_log_id": 900}]))

    assert api_client.cleanup_results == [(900, True, None)]


def test_clear_messages_saves_failure_for_unexpected_delete_error() -> None:
    api_client = FakeApiClient()
    application = build_application(api_client)
    application.bot.delete_errors[100] = RuntimeError("network down")

    asyncio.run(clear_messages(10, application, [100], [{"message_id": 100, "message_log_id": 900}]))

    assert api_client.cleanup_results == [(900, False, "network down")]


def test_clear_messages_propagates_cancellation() -> None:
    api_client = FakeApiClient()
    application = build_application(api_client)
    application.bot.delete_errors[100] = asyncio.CancelledError()

    try:
        asyncio.run(clear_messages(10, application, [100], [{"message_id": 100, "message_log_id": 900}]))
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("CancelledError was not propagated")

    assert api_client.cleanup_results == []


def test_clear_messages_saves_deleted_result_after_successful_delete() -> None:
    api_client = FakeApiClient()
    application = build_application(api_client)

    asyncio.run(clear_messages(10, application, [100], [{"message_id": 100, "message_log_id": 900}]))

    assert application.bot.delete_calls == [(10, 100)]
    assert api_client.cleanup_results == [(900, True, None)]


def test_resolve_callback_active_screen_message_uses_user_data_log_ref() -> None:
    update = SimpleNamespace(
        callback_query=SimpleNamespace(message=SimpleNamespace(message_id=100, audio=object()))
    )

    message = asyncio.run(
        resolve_callback_active_screen_message(
            update,
            {"bot_message_log_refs": [{"message_id": 100, "message_log_id": 900}]},
            FakeApiClient(),
            77,
            10,
        )
    )

    assert message.message_id == 100
    assert message.message_log_id == 900
    assert message.has_audio is True
    assert message.screen_id is None


def test_resolve_callback_active_screen_message_falls_back_to_backend_lookup() -> None:
    api_client = FakeApiClient()
    api_client.lookup_result = SimpleNamespace(id=901, screen_id="menu")
    update = SimpleNamespace(
        callback_query=SimpleNamespace(message=SimpleNamespace(message_id=100, audio=None))
    )

    message = asyncio.run(
        resolve_callback_active_screen_message(update, {}, api_client, 77, 10)
    )

    assert message.message_id == 100
    assert message.message_log_id == 901
    assert message.has_audio is False
    assert message.screen_id == "menu"


def test_resolve_callback_active_screen_message_returns_none_for_missing_message() -> None:
    assert asyncio.run(
        resolve_callback_active_screen_message(
            SimpleNamespace(callback_query=SimpleNamespace(message=None)),
            {},
            FakeApiClient(),
            77,
            10,
        )
    ) is None
    assert asyncio.run(
        resolve_callback_active_screen_message(
            SimpleNamespace(callback_query=SimpleNamespace(message=SimpleNamespace(message_id="100"))),
            {},
            FakeApiClient(),
            77,
            10,
        )
    ) is None


def test_resolve_callback_active_screen_message_survives_lookup_error() -> None:
    api_client = FakeApiClient()
    api_client.lookup_error = RuntimeError("backend down")
    update = SimpleNamespace(
        callback_query=SimpleNamespace(message=SimpleNamespace(message_id=100, audio=None))
    )

    message = asyncio.run(
        resolve_callback_active_screen_message(update, {}, api_client, 77, 10)
    )

    assert message.message_id == 100
    assert message.message_log_id is None
    assert message.screen_id is None


def test_list_chat_tracked_messages_maps_rows_and_handles_errors() -> None:
    api_client = FakeApiClient()
    api_client.active_messages = [
        SimpleNamespace(id=901, message_id=100, screen_id="card:1"),
        SimpleNamespace(id=902, message_id=101, screen_id="menu"),
    ]

    messages = asyncio.run(list_chat_tracked_messages(api_client, 77, 10))

    assert [(item.message_id, item.message_log_id, item.has_audio, item.screen_id) for item in messages] == [
        (100, 901, True, "card:1"),
        (101, 902, False, "menu"),
    ]

    api_client.list_active_error = RuntimeError("backend down")

    assert asyncio.run(list_chat_tracked_messages(api_client, 77, 10)) == []
    assert asyncio.run(list_chat_tracked_messages(None, 77, 10)) == []


def test_sweep_chat_tracked_messages_deletes_extra_and_keeps_latest_sticky(monkeypatch) -> None:
    api_client = FakeApiClient()
    api_client.active_messages = [
        SimpleNamespace(id=901, message_id=100, screen_id="menu"),
        SimpleNamespace(id=902, message_id=101, screen_id="card:1"),
        SimpleNamespace(id=903, message_id=102, screen_id="import_words:summary:1"),
        SimpleNamespace(id=904, message_id=103, screen_id="import_words:failed:1"),
    ]
    clear_calls: list[tuple[int, list[int], list[dict[str, int]]]] = []
    monkeypatch.setattr(
        "app.bot_runtime.message_tracking.clear_messages",
        lambda chat_id, application, message_ids, message_log_refs: clear_calls.append(
            (chat_id, message_ids, message_log_refs)
        )
        or asyncio.sleep(0),
    )
    user_data = {"active_screen_message_id": 101}

    asyncio.run(
        sweep_chat_tracked_messages(
            application=build_application(api_client),
            api_client=api_client,
            chat_id=10,
            telegram_user_id=77,
            keep_messages=[SimpleNamespace(message_id=101, message_log_id=902, screen_id="card:1")],
            user_data=user_data,
        )
    )

    assert clear_calls == [
        (
            10,
            [100, 102],
            [{"message_id": 100, "message_log_id": 901}, {"message_id": 102, "message_log_id": 903}],
        )
    ]
    assert user_data["bot_message_ids"] == [101]
    assert user_data["bot_message_log_refs"] == [{"message_id": 101, "message_log_id": 902}]


def test_sweep_chat_tracked_messages_handles_no_userdata_and_no_matching_active(monkeypatch) -> None:
    api_client = FakeApiClient()
    api_client.active_messages = [SimpleNamespace(id=901, message_id=100, screen_id="menu")]
    clear_calls: list[list[int]] = []
    monkeypatch.setattr(
        "app.bot_runtime.message_tracking.clear_messages",
        lambda chat_id, application, message_ids, message_log_refs: clear_calls.append(message_ids)
        or asyncio.sleep(0),
    )

    asyncio.run(
        sweep_chat_tracked_messages(
            application=build_application(api_client),
            api_client=api_client,
            chat_id=10,
            telegram_user_id=77,
            keep_messages=[],
            user_data=None,
        )
    )

    assert clear_calls == [[100]]

    user_data = {"active_screen_message_id": 999}
    asyncio.run(
        sweep_chat_tracked_messages(
            application=build_application(api_client),
            api_client=api_client,
            chat_id=10,
            telegram_user_id=77,
            keep_messages=[SimpleNamespace(message_id=100, message_log_id=901, screen_id="menu")],
            user_data=user_data,
        )
    )

    assert user_data["bot_message_ids"] == [100]


def test_sweep_chat_tracked_messages_preserves_intro_and_excludes_auxiliary(monkeypatch) -> None:
    api_client = FakeApiClient()
    api_client.active_messages = [
        SimpleNamespace(id=901, message_id=99, screen_id="menu:intro"),
        SimpleNamespace(id=902, message_id=100, screen_id="menu"),
        SimpleNamespace(id=903, message_id=101, screen_id="menu:settings"),
    ]
    monkeypatch.setattr(
        "app.bot_runtime.message_tracking.clear_messages",
        lambda chat_id, application, message_ids, message_log_refs: asyncio.sleep(0),
    )
    user_data = {"active_screen_message_id": 100, "auxiliary_screen_message_id": 101}

    asyncio.run(
        sweep_chat_tracked_messages(
            application=build_application(api_client),
            api_client=api_client,
            chat_id=10,
            telegram_user_id=77,
            keep_messages=[
                SimpleNamespace(message_id=100, message_log_id=902, screen_id="menu"),
                SimpleNamespace(message_id=101, message_log_id=903, screen_id="menu:settings"),
                SimpleNamespace(message_id=99, message_log_id=901, screen_id="menu:intro"),
            ],
            user_data=user_data,
        )
    )

    assert user_data["bot_message_ids"] == [100, 99]
    assert user_data["bot_message_log_refs"] == [
        {"message_id": 100, "message_log_id": 902},
        {"message_id": 101, "message_log_id": 903},
        {"message_id": 99, "message_log_id": 901},
    ]


def test_save_cleanup_helpers_swallow_backend_errors() -> None:
    api_client = FakeApiClient()
    api_client.cleanup_error = RuntimeError("db unavailable")

    asyncio.run(save_cleanup_failure(api_client, 901, RuntimeError("delete failed")))
    asyncio.run(save_cleanup_deleted_result(api_client, 902))

    assert api_client.cleanup_results == []


def test_track_sent_bot_message_handles_missing_context_and_backend_error() -> None:
    assert asyncio.run(track_sent_bot_message(None, 77, 10, "menu", 101)) is None
    assert asyncio.run(track_sent_bot_message(FakeApiClient(), None, 10, "menu", 101)) is None

    api_client = FakeApiClient()
    api_client.track_error = RuntimeError("db unavailable")

    assert asyncio.run(track_sent_bot_message(api_client, 77, 10, "menu", 101)) is None


def test_track_sent_bot_message_returns_tracked_row() -> None:
    api_client = FakeApiClient()

    tracked = asyncio.run(track_sent_bot_message(api_client, 77, 10, "menu", 101, delete_after_hours=24))

    assert tracked.message_id == 101
    assert api_client.track_calls == [(77, 10, 101, "menu", 24)]


def test_is_tracked_message_still_active_handles_hit_miss_and_backend_error() -> None:
    api_client = FakeApiClient()
    api_client.active_messages = [SimpleNamespace(message_id=101)]

    assert asyncio.run(
        is_tracked_message_still_active(
            api_client=api_client,
            telegram_user_id=77,
            chat_id=10,
            message_id=101,
        )
    )
    assert not asyncio.run(
        is_tracked_message_still_active(
            api_client=api_client,
            telegram_user_id=77,
            chat_id=10,
            message_id=202,
        )
    )

    api_client.list_active_error = RuntimeError("backend down")

    assert asyncio.run(
        is_tracked_message_still_active(
            api_client=api_client,
            telegram_user_id=77,
            chat_id=10,
            message_id=202,
        )
    )


def test_message_tracking_compatibility_imports_stay_on_app_bot() -> None:
    assert compatibility_clear_messages is clear_messages
    assert compatibility_clear_tracked_messages is clear_tracked_messages
    assert compatibility_list_chat_tracked_messages is list_chat_tracked_messages
    assert compatibility_resolve_callback_active_screen_message is resolve_callback_active_screen_message
    assert compatibility_sweep_chat_tracked_messages is sweep_chat_tracked_messages
    assert is_message_already_deleted_error(RuntimeError("Message to delete not found"))
    assert is_sticky_import_report_screen_id("import_words:summary:1")
    assert is_sticky_import_report_screen_id("import_words:failed:1")
    assert not is_sticky_import_report_screen_id("menu")
