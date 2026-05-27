from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

import app.bot_runtime.application as runtime_application
import app.bot_runtime.handlers as runtime_handlers
import app.bot_runtime.polling as runtime_polling
from app.bot_runtime.auto_advance import (
    calculate_reminder_poll_sleep_seconds,
    cancel_auto_advance_task,
    cancel_reminder_auto_return_task,
    schedule_reminder_auto_return_task,
)
from app.bot_runtime.auto_advance import (
    calculate_reminder_poll_sleep_seconds as runtime_calculate_reminder_poll_sleep_seconds,
)
from app.bot_runtime.auto_advance import (
    cancel_auto_advance_task as runtime_cancel_auto_advance_task,
)
from app.bot_runtime.auto_advance import (
    cancel_reminder_auto_return_task as runtime_cancel_reminder_auto_return_task,
)
from app.bot_runtime.auto_advance import (
    schedule_auto_advance_task as runtime_schedule_auto_advance_task,
)
from app.bot_runtime.auto_advance import (
    schedule_reminder_auto_return_task as runtime_schedule_reminder_auto_return_task,
)
from app.bot_runtime.delivery import (
    is_message_not_editable_error,
    is_message_not_modified_error,
    try_edit_active_screen,
)
from app.bot_runtime.message_tracking import (
    clear_tracked_messages,
    save_cleanup_deleted_result,
    save_cleanup_failure,
    track_sent_bot_message,
)
from app.bot_runtime.polling import bot_message_cleanup_interval_seconds
from app.bot_runtime.rendering import build_keyboard
from app.bot_runtime.screen_delivery import render_screen, send_screen_to_chat
from app.bot_runtime.screen_delivery import render_screen as runtime_render_screen
from app.bot_runtime.screen_delivery import send_screen_to_chat as runtime_send_screen_to_chat
from app.bot_runtime.state import (
    ActiveScreenMessage,
    build_message_log_refs,
    clear_auxiliary_screen_message_state,
    get_active_screen_message,
    get_auxiliary_screen_message,
    read_int,
    save_active_screen_message,
)
from app.bot_runtime.user_context import build_user_context
from app.contracts import (
    ButtonModel,
    ImportDispatchNotificationModel,
    ImportDispatchResponse,
    ReminderDispatchResponse,
    ReminderScreenModel,
    ScreenModel,
)


async def start_handler(update, context) -> None:
    await runtime_handlers.start_handler(update, context, render_screen_func=render_screen)


async def menu_handler(update, context) -> None:
    await runtime_handlers.menu_handler(update, context, render_screen_func=render_screen)


async def text_handler(update, context) -> None:
    await runtime_handlers.text_handler(update, context, render_screen_func=render_screen)


def schedule_auto_advance_task(context, user, chat_id, screen) -> None:
    runtime_schedule_auto_advance_task(
        context,
        user,
        chat_id,
        screen,
        send_screen_to_chat=send_screen_to_chat,
    )


async def callback_handler(update, context) -> None:
    await runtime_handlers.callback_handler(
        update,
        context,
        render_screen_func=render_screen,
        schedule_auto_advance_func=schedule_auto_advance_task,
    )


async def reminder_polling_loop(application) -> None:
    await runtime_polling.reminder_polling_loop(
        application,
        send_screen_to_chat_func=send_screen_to_chat,
        sleep_func=asyncio.sleep,
    )


async def bot_message_cleanup_loop(application) -> None:
    await runtime_polling.bot_message_cleanup_loop(application, sleep_func=asyncio.sleep)


async def user_import_polling_loop(application) -> None:
    await runtime_polling.user_import_polling_loop(
        application,
        send_screen_to_chat_func=send_screen_to_chat,
        sleep_func=asyncio.sleep,
    )


class FakeCallbackQuery:
    def __init__(self, data: str | None = None) -> None:
        self.data = data
        self.answers = 0

    async def answer(self) -> None:
        self.answers += 1


class FakeTelegramObject(SimpleNamespace):
    def to_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


class FakeRuntimeBot:
    def __init__(self) -> None:
        self.delete_calls: list[tuple[int, int]] = []
        self.delete_errors: dict[int, Exception] = {}
        self.edit_text_error: Exception | None = None

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        error = self.delete_errors.get(message_id)
        if error is not None:
            raise error
        self.delete_calls.append((chat_id, message_id))

    async def edit_message_text(self, **kwargs) -> None:
        if self.edit_text_error is not None:
            raise self.edit_text_error


class FakeRuntimeApiClient:
    def __init__(self) -> None:
        self.bootstrap_calls: list[tuple[int, str | None]] = []
        self.action_calls: list[tuple[int, str]] = []
        self.restore_menu_calls: list[int] = []
        self.text_calls: list[tuple[int, str]] = []
        self.track_calls: list[tuple[int, int, int, str]] = []
        self.cleanup_results: list[tuple[int, bool, str | None]] = []
        self.billing_notification_results: list[tuple[int, bool, str | None]] = []
        self.billing_receipt_results: list[tuple[int, bool, str | None]] = []
        self.billing_receipt_admin_alert_results: list[tuple[int, bool, str | None]] = []
        self.dispatch_cleanup_result = SimpleNamespace(messages=[])
        self.dispatch_reminders_result = ReminderDispatchResponse(reminders=[])
        self.dispatch_user_imports_result = ImportDispatchResponse(notifications=[])
        self.track_error: Exception | None = None
        self.cleanup_result_error: Exception | None = None
        self.active_messages: list[object] = []

    async def bootstrap(self, user, message_text):
        self.bootstrap_calls.append((user.telegram_user_id, message_text))
        return SimpleNamespace(screen=ScreenModel(screen_id="start", text="start"))

    async def action(self, user, action):
        self.action_calls.append((user.telegram_user_id, action))
        return SimpleNamespace(screen=ScreenModel(screen_id="menu", text=f"action:{action}"))

    async def restore_menu(self, telegram_user_id):
        self.restore_menu_calls.append(telegram_user_id)
        return SimpleNamespace(
            screen=ScreenModel(
                screen_id="menu",
                text="restored menu",
                metadata={
                    "auxiliary_message_buttons": [
                        ButtonModel(action="m:settings", text="Settings").model_dump()
                    ],
                },
            )
        )

    async def text(self, user, text):
        self.text_calls.append((user.telegram_user_id, text))
        return SimpleNamespace(screen=ScreenModel(screen_id="text", text=f"text:{text}"))

    async def dispatch_reminders(self):
        return self.dispatch_reminders_result

    async def dispatch_bot_message_cleanup(self):
        return self.dispatch_cleanup_result

    async def dispatch_user_imports(self):
        return self.dispatch_user_imports_result

    async def track_bot_message(self, telegram_user_id: int, chat_id: int, message_id: int, screen_id: str, delete_after_hours=None):
        if self.track_error is not None:
            raise self.track_error
        self.track_calls.append((telegram_user_id, chat_id, message_id, screen_id))
        row = SimpleNamespace(id=message_id + 1000, message_id=message_id, screen_id=screen_id)
        self.active_messages.append(row)
        return row

    async def list_active_bot_messages(self, telegram_user_id: int, chat_id: int):
        return SimpleNamespace(messages=list(self.active_messages))

    async def save_bot_message_cleanup_result(self, message_log_id: int, is_deleted: bool, error_text: str | None = None) -> None:
        if self.cleanup_result_error is not None:
            raise self.cleanup_result_error
        self.cleanup_results.append((message_log_id, is_deleted, error_text))
        if is_deleted:
            self.active_messages = [row for row in self.active_messages if getattr(row, "id", None) != message_log_id]

    async def save_billing_notification_delivery_result(
        self,
        notification_id: int,
        *,
        is_sent: bool,
        error_text: str | None = None,
    ) -> None:
        self.billing_notification_results.append((notification_id, is_sent, error_text))

    async def save_billing_receipt_delivery_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None = None,
    ) -> None:
        self.billing_receipt_results.append((receipt_id, is_sent, error_text))

    async def save_billing_receipt_admin_alert_result(
        self,
        receipt_id: int,
        *,
        is_sent: bool,
        error_text: str | None = None,
    ) -> None:
        self.billing_receipt_admin_alert_results.append((receipt_id, is_sent, error_text))


class FakeContext:
    def __init__(self, api_client: FakeRuntimeApiClient | None = None) -> None:
        self.application = SimpleNamespace(bot_data={"api_client": api_client or FakeRuntimeApiClient()}, create_task=asyncio.create_task)
        self.user_data: dict[str, object] = {}
        self.error = RuntimeError("boom")


class FakePollingTask:
    def __init__(self, raise_cancelled: bool = True) -> None:
        self.cancel_calls = 0
        self.raise_cancelled = raise_cancelled

    def cancel(self) -> None:
        self.cancel_calls += 1

    def __await__(self):
        async def wait():
            if self.raise_cancelled:
                raise asyncio.CancelledError()

        return wait().__await__()


class FakeTelegramApplication:
    def __init__(self) -> None:
        self.bot_data: dict[str, object] = {}
        self.handlers: list[object] = []
        self.error_handlers: list[object] = []
        self.created_tasks: list[object] = []

    def create_task(self, coroutine):
        if hasattr(coroutine, "close"):
            coroutine.close()
        task = FakePollingTask()
        self.created_tasks.append(task)
        return task

    def add_handler(self, handler) -> None:
        self.handlers.append(handler)

    def add_error_handler(self, handler) -> None:
        self.error_handlers.append(handler)


class FakeApplicationBuilder:
    def __init__(self) -> None:
        self.token_value: str | None = None
        self.post_init_func = None
        self.post_shutdown_func = None
        self.application = FakeTelegramApplication()

    def token(self, token: str):
        self.token_value = token
        return self

    def post_init(self, callback):
        self.post_init_func = callback
        return self

    def post_shutdown(self, callback):
        self.post_shutdown_func = callback
        return self

    def build(self):
        return self.application


def build_update(
    *,
    text: str | None = None,
    callback_data: str | None = None,
    include_message: bool = True,
    include_chat: bool = True,
    include_user: bool = True,
):
    message = None
    if include_message:
        message = SimpleNamespace(text=text)
    callback_query = FakeCallbackQuery(callback_data)
    return SimpleNamespace(
        message=message,
        callback_query=callback_query,
        effective_chat=FakeTelegramObject(id=55, type="private", username="cronolex", title="CronoLex") if include_chat else None,
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
    )


def test_runtime_application_build_registers_handlers_and_bot_data(monkeypatch) -> None:
    builder = FakeApplicationBuilder()
    api_client = SimpleNamespace()
    settings = SimpleNamespace()
    audio_storage_provider = SimpleNamespace()

    async def fake_update_handler(update, context) -> None:
        return None

    async def fake_polling_loop(application) -> None:
        return None

    async def fake_error_handler(update, context) -> None:
        return None

    monkeypatch.setattr("app.bot_runtime.application.Application.builder", lambda: builder)

    application = runtime_application.build_application(
        api_client,
        "123:ABC",
        settings,
        audio_storage_provider=audio_storage_provider,
        start_handler_func=fake_update_handler,
        menu_handler_func=fake_update_handler,
        text_handler_func=fake_update_handler,
        callback_handler_func=fake_update_handler,
        reminder_polling_loop_func=fake_polling_loop,
        bot_message_cleanup_loop_func=fake_polling_loop,
        user_import_polling_loop_func=fake_polling_loop,
        error_handler_func=fake_error_handler,
    )

    assert application is builder.application
    assert builder.token_value == "123:ABC"
    assert application.bot_data == {
        "api_client": api_client,
        "settings": settings,
        "audio_storage_provider": audio_storage_provider,
    }
    assert [type(handler).__name__ for handler in application.handlers] == [
        "CommandHandler",
        "CommandHandler",
        "MessageHandler",
        "CallbackQueryHandler",
    ]
    assert application.error_handlers == [fake_error_handler]
    assert builder.post_init_func is not None
    assert builder.post_shutdown_func is runtime_application.cancel_polling_tasks
    asyncio.run(builder.post_init_func(application))
    assert {"reminder_task", "cleanup_task", "user_import_task"}.issubset(application.bot_data)


def test_runtime_application_post_init_schedules_polling_tasks() -> None:
    application = FakeTelegramApplication()
    calls: list[str] = []

    async def reminder_polling_loop(application) -> None:
        calls.append("reminder")

    async def cleanup_polling_loop(application) -> None:
        calls.append("cleanup")

    async def user_import_polling_loop(application) -> None:
        calls.append("user_import")

    runtime_application.schedule_polling_tasks(
        application,
        reminder_polling_loop_func=reminder_polling_loop,
        bot_message_cleanup_loop_func=cleanup_polling_loop,
        user_import_polling_loop_func=user_import_polling_loop,
    )

    assert set(application.bot_data) == {"reminder_task", "cleanup_task", "user_import_task"}
    assert len(application.created_tasks) == 3


def test_runtime_application_shutdown_cancels_polling_tasks() -> None:
    tasks = [FakePollingTask(), FakePollingTask()]
    application = SimpleNamespace(
        bot_data={
            "reminder_task": tasks[0],
            "user_import_task": tasks[1],
        }
    )

    asyncio.run(runtime_application.cancel_polling_tasks(application))

    assert [task.cancel_calls for task in tasks] == [1, 1]


def test_runtime_application_error_handler_logs_exception(caplog) -> None:
    context = FakeContext()

    asyncio.run(runtime_application.error_handler("update", context))

    assert "Unhandled telegram bot error" in caplog.text
    assert "RuntimeError: boom" in caplog.text


def test_get_active_screen_message_reads_legacy_state() -> None:
    active_message = get_active_screen_message(
        {
            "bot_message_ids": [100, 101],
            "bot_message_log_refs": [{"message_id": 101, "message_log_id": 901}],
        }
    )

    assert active_message == ActiveScreenMessage(message_id=101, message_log_id=901, has_audio=False)


def test_screen_state_helpers_handle_empty_state() -> None:
    assert get_active_screen_message(None) is None
    assert get_active_screen_message({}) is None
    assert get_auxiliary_screen_message(None) is None
    assert get_auxiliary_screen_message({"auxiliary_screen_message_id": "201"}) is None
    clear_auxiliary_screen_message_state(None)


def test_save_active_screen_message_rewrites_user_data() -> None:
    user_data: dict[str, object] = {}

    save_active_screen_message(user_data, ActiveScreenMessage(message_id=201, message_log_id=1201, has_audio=True))

    assert user_data == {
        "active_screen_message_id": 201,
        "active_screen_message_log_id": 1201,
        "active_screen_has_audio": True,
        "active_screen_screen_id": None,
        "bot_message_ids": [201],
        "bot_message_log_refs": [{"message_id": 201, "message_log_id": 1201}],
    }


def test_build_message_log_refs_skips_untracked_messages() -> None:
    refs = build_message_log_refs(
        [
            ActiveScreenMessage(message_id=1, message_log_id=None),
            ActiveScreenMessage(message_id=2, message_log_id=2002),
        ]
    )

    assert refs == [{"message_id": 2, "message_log_id": 2002}]


def test_read_int_returns_none_for_non_int() -> None:
    assert read_int("10") is None


def test_start_handler_ignores_update_without_message() -> None:
    context = FakeContext()

    asyncio.run(start_handler(SimpleNamespace(message=None), context))

    assert context.application.bot_data["api_client"].bootstrap_calls == []


def test_start_handler_calls_backend_and_render(monkeypatch) -> None:
    context = FakeContext()
    update = build_update(text="/start")
    render_calls: list[str] = []
    monkeypatch.setattr(sys.modules[__name__], "render_screen", lambda update, context, screen: render_calls.append(screen.screen_id) or asyncio.sleep(0))

    asyncio.run(start_handler(update, context))

    assert context.application.bot_data["api_client"].bootstrap_calls == [(77, "/start")]
    assert render_calls == ["start"]


def test_menu_handler_calls_backend_and_render(monkeypatch) -> None:
    context = FakeContext()
    update = build_update(text="/menu")
    render_calls: list[str] = []
    monkeypatch.setattr(sys.modules[__name__], "render_screen", lambda update, context, screen: render_calls.append(screen.text) or asyncio.sleep(0))

    asyncio.run(menu_handler(update, context))

    assert context.application.bot_data["api_client"].action_calls == [(77, "m:menu")]
    assert render_calls == ["action:m:menu"]


def test_text_handler_ignores_empty_text() -> None:
    context = FakeContext()
    update = build_update(text=None)

    asyncio.run(text_handler(update, context))

    assert context.application.bot_data["api_client"].text_calls == []


def test_text_handler_calls_backend_and_render(monkeypatch) -> None:
    context = FakeContext()
    update = build_update(text="hello")
    render_calls: list[str] = []
    monkeypatch.setattr(sys.modules[__name__], "render_screen", lambda update, context, screen: render_calls.append(screen.text) or asyncio.sleep(0))

    asyncio.run(text_handler(update, context))

    assert context.application.bot_data["api_client"].text_calls == [(77, "hello")]
    assert render_calls == ["text:hello"]


def test_callback_handler_uses_default_menu_action_when_callback_data_empty(monkeypatch) -> None:
    context = FakeContext()
    update = build_update(callback_data=None)
    render_calls: list[str] = []
    monkeypatch.setattr(sys.modules[__name__], "render_screen", lambda update, context, screen: render_calls.append(screen.text) or asyncio.sleep(0))

    asyncio.run(callback_handler(update, context))

    assert context.application.bot_data["api_client"].action_calls == [(77, "m:menu")]
    assert update.callback_query.answers == 1
    assert render_calls == ["action:m:menu"]


def test_callback_handler_ignores_noop_callback() -> None:
    context = FakeContext()
    update = build_update(callback_data="noop")
    pending_task = FakePollingTask(raise_cancelled=False)
    context.application.bot_data["reminder_auto_return_tasks"] = {"77:55": pending_task}

    asyncio.run(callback_handler(update, context))

    assert context.application.bot_data["api_client"].action_calls == []
    assert update.callback_query.answers == 1
    assert pending_task.cancel_calls == 1
    assert context.application.bot_data["reminder_auto_return_tasks"] == {}


def test_callback_handler_ignores_update_without_callback_query() -> None:
    context = FakeContext()
    update = build_update(callback_data="noop")
    update.callback_query = None

    asyncio.run(callback_handler(update, context))

    assert context.application.bot_data["api_client"].action_calls == []


def test_callback_handler_answers_before_backend_action(monkeypatch) -> None:
    context = FakeContext()
    update = build_update(callback_data="s:77:ready:ready_en_uk:yes")
    events: list[str] = []

    async def fake_action(user, action):
        events.append(f"action:{action}:answered={update.callback_query.answers}")
        return SimpleNamespace(screen=ScreenModel(screen_id="quiz_en_uk:11", text="quiz"))

    async def fake_render_screen(update_arg, context_arg, screen):
        events.append(f"render:{screen.screen_id}")

    monkeypatch.setattr(context.application.bot_data["api_client"], "action", fake_action)
    monkeypatch.setattr(sys.modules[__name__], "render_screen", fake_render_screen)

    asyncio.run(callback_handler(update, context))

    assert update.callback_query.answers == 1
    assert events == [
        "action:s:77:ready:ready_en_uk:yes:answered=1",
        "render:quiz_en_uk:11",
    ]


def test_render_screen_skips_when_chat_missing() -> None:
    context = FakeContext()
    update = build_update(include_chat=False)

    asyncio.run(render_screen(update, context, ScreenModel(screen_id="menu", text="menu")))

    assert context.user_data == {}


def test_screen_delivery_compatibility_imports_stay_on_app_bot() -> None:
    assert render_screen is runtime_render_screen


def test_reminder_auto_return_compatibility_imports_stay_on_app_bot() -> None:
    assert schedule_reminder_auto_return_task is runtime_schedule_reminder_auto_return_task
    assert cancel_reminder_auto_return_task is runtime_cancel_reminder_auto_return_task
    assert send_screen_to_chat is runtime_send_screen_to_chat


def test_send_screen_to_chat_delete_current_message_only_resets_active_state() -> None:
    api_client = FakeRuntimeApiClient()
    application = SimpleNamespace(bot=FakeRuntimeBot(), bot_data={"api_client": api_client})
    user_data = {
        "bot_message_ids": [501],
        "bot_message_log_refs": [{"message_id": 501, "message_log_id": 1501}],
        "active_screen_message_id": 501,
        "active_screen_message_log_id": 1501,
        "active_screen_has_audio": True,
        "active_screen_screen_id": "import_words:summary:7",
        "reply_keyboard_removed": True,
    }

    asyncio.run(
        runtime_send_screen_to_chat(
            application,
            55,
            ScreenModel(
                screen_id="import_words:dismiss:7",
                text="",
                metadata={"delete_current_message_only": True},
            ),
            user_data=user_data,
            telegram_user_id=77,
        )
    )

    assert application.bot.delete_calls == [(55, 501)]
    assert api_client.cleanup_results == [(1501, True, None)]
    assert user_data["bot_message_ids"] == []
    assert user_data["bot_message_log_refs"] == []
    assert user_data["active_screen_message_id"] is None
    assert user_data["active_screen_has_audio"] is False
    assert user_data["active_screen_screen_id"] is None


def test_send_screen_to_chat_sends_menu_auxiliary_after_active_message() -> None:
    class OrderedSendBot:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def send_message(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(message_id=500 + len(self.calls))

        async def delete_message(self, chat_id: int, message_id: int) -> None:
            self.calls.append({"chat_id": chat_id, "message_id": message_id, "deleted": True})

    bot = OrderedSendBot()
    application = SimpleNamespace(bot=bot, bot_data={"api_client": None})
    user_data = {"reply_keyboard_removed": True}

    asyncio.run(
        runtime_send_screen_to_chat(
            application,
            55,
            ScreenModel(
                screen_id="menu",
                text="first",
                buttons=[ButtonModel(action="m:s", text="Start")],
                metadata={
                    "intro_message_text": "intro",
                    "buttons_per_row": 1,
                    "auxiliary_after_active": True,
                    "auxiliary_message_text": "second",
                    "auxiliary_message_buttons": [ButtonModel(action="m:settings", text="Settings").model_dump()],
                },
            ),
            user_data=user_data,
            telegram_user_id=77,
        )
    )

    assert [call["text"] for call in bot.calls] == ["intro", "first", "second"]
    assert bot.calls[0].get("reply_markup") is None
    assert bot.calls[1]["reply_markup"].inline_keyboard[0][0].callback_data == "m:s"
    assert bot.calls[2]["reply_markup"].inline_keyboard[0][0].callback_data == "m:settings"
    assert user_data["bot_message_ids"] == [501, 502]
    assert user_data["active_screen_message_id"] == 502
    assert user_data["auxiliary_screen_message_id"] == 503


def test_send_screen_to_chat_recreates_menu_auxiliary_after_force_resend() -> None:
    class OrderedSendBot(FakeRuntimeBot):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[dict[str, object]] = []

        async def send_message(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(message_id=600 + len(self.calls))

    bot = OrderedSendBot()
    application = SimpleNamespace(bot=bot, bot_data={"api_client": None})
    user_data = {
        "reply_keyboard_removed": True,
        "active_screen_message_id": 10,
        "active_screen_screen_id": "card:501",
        "auxiliary_screen_message_id": 11,
        "bot_message_ids": [10],
    }

    asyncio.run(
        runtime_send_screen_to_chat(
            application,
            55,
            ScreenModel(
                screen_id="menu",
                text="first",
                buttons=[ButtonModel(action="m:s", text="Start")],
                metadata={
                    "force_resend": True,
                    "buttons_per_row": 1,
                    "auxiliary_after_active": True,
                    "auxiliary_message_text": "second",
                    "auxiliary_message_buttons": [ButtonModel(action="m:settings", text="Settings").model_dump()],
                },
            ),
            user_data=user_data,
            telegram_user_id=77,
        )
    )

    assert bot.delete_calls == [(55, 11), (55, 10)]
    assert [call["text"] for call in bot.calls] == ["first", "second"]
    assert user_data["active_screen_message_id"] == 601
    assert user_data["auxiliary_screen_message_id"] == 602


def test_try_edit_active_screen_returns_false_for_text_to_audio_transition() -> None:
    application = SimpleNamespace(bot=FakeRuntimeBot())
    screen = ScreenModel(screen_id="card", text="audio", audio_path="audio/0001_abandon.mp3")

    edited = asyncio.run(
        try_edit_active_screen(
            application=application,
            chat_id=10,
            active_message=ActiveScreenMessage(message_id=1, has_audio=False),
            screen=screen,
            keyboard=None,
            screen_text="audio",
        )
    )

    assert edited is False


def test_try_edit_active_screen_reraises_unexpected_error() -> None:
    application = SimpleNamespace(bot=FakeRuntimeBot())
    application.bot.edit_text_error = RuntimeError("network broken")

    with pytest.raises(RuntimeError, match="network broken"):
        asyncio.run(
            try_edit_active_screen(
                application=application,
                chat_id=10,
                active_message=ActiveScreenMessage(message_id=1, has_audio=False),
                screen=ScreenModel(screen_id="menu", text="menu"),
                keyboard=None,
                screen_text="menu",
            )
        )


def test_try_edit_active_screen_treats_not_modified_as_success() -> None:
    application = SimpleNamespace(bot=FakeRuntimeBot())
    application.bot.edit_text_error = RuntimeError("Message is not modified")
    active_message = ActiveScreenMessage(message_id=1, has_audio=False, screen_id="menu")

    edited = asyncio.run(
        try_edit_active_screen(
            application=application,
            chat_id=10,
            active_message=active_message,
            screen=ScreenModel(screen_id="menu", text="menu"),
            keyboard=None,
            screen_text="menu",
        )
    )

    assert edited is True
    assert active_message.screen_id == "menu"


def test_schedule_auto_advance_task_requests_next_screen(monkeypatch) -> None:
    context = FakeContext()
    sent_calls: list[str] = []
    context.user_data["active_screen_message_id"] = 501
    context.application.bot_data["api_client"].active_messages = [
        SimpleNamespace(id=1501, message_id=501, screen_id="quiz_en_uk:11:feedback")
    ]

    async def fake_sleep(seconds: float) -> None:
        return None

    async def fake_send_screen_to_chat(application, chat_id, screen, user_data=None, telegram_user_id=None, disable_notification=True):
        sent_calls.append(screen.text)

    monkeypatch.setattr("app.bot_runtime.auto_advance.asyncio.sleep", fake_sleep)
    monkeypatch.setattr(sys.modules[__name__], "send_screen_to_chat", fake_send_screen_to_chat)

    user = build_user_context(build_update(text="/start"))
    screen = ScreenModel(screen_id="feedback", text="feedback", metadata={"auto_advance_after_ms": 1500, "next_action": "s:77:next"})

    async def run_case() -> None:
        schedule_auto_advance_task(context, user, 55, screen)
        task = context.user_data["auto_advance_task"]
        await task

    asyncio.run(run_case())

    assert context.application.bot_data["api_client"].action_calls == [(77, "s:77:next")]
    assert sent_calls == ["action:s:77:next"]


def test_schedule_auto_advance_task_skips_when_source_message_is_no_longer_active(monkeypatch) -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 501
    context.application.bot_data["api_client"].active_messages = [
        SimpleNamespace(id=1602, message_id=602, screen_id="reminder:1")
    ]
    sent_calls: list[str] = []

    async def fake_sleep(seconds: float) -> None:
        return None

    async def fake_send_screen_to_chat(application, chat_id, screen, user_data=None, telegram_user_id=None, disable_notification=True):
        sent_calls.append(screen.text)

    monkeypatch.setattr("app.bot_runtime.auto_advance.asyncio.sleep", fake_sleep)
    monkeypatch.setattr(sys.modules[__name__], "send_screen_to_chat", fake_send_screen_to_chat)

    user = build_user_context(build_update(text="/start"))
    screen = ScreenModel(screen_id="feedback", text="feedback", metadata={"auto_advance_after_ms": 1500, "next_action": "s:77:next"})

    async def run_case() -> None:
        schedule_auto_advance_task(context, user, 55, screen)
        task = context.user_data["auto_advance_task"]
        await task

    asyncio.run(run_case())

    assert context.application.bot_data["api_client"].action_calls == []
    assert sent_calls == []


def test_cancel_auto_advance_task_removes_pending_task() -> None:
    class DummyTask:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    task = DummyTask()
    user_data: dict[str, object] = {"auto_advance_task": task}

    cancel_auto_advance_task(user_data)

    assert "auto_advance_task" not in user_data
    assert task.cancelled is True

    cancel_auto_advance_task(None)


def test_auto_advance_runtime_compatibility_imports_stay_on_app_bot() -> None:
    assert calculate_reminder_poll_sleep_seconds is runtime_calculate_reminder_poll_sleep_seconds
    assert cancel_auto_advance_task is runtime_cancel_auto_advance_task


def test_runtime_schedule_auto_advance_task_skips_without_chat_or_metadata() -> None:
    context = FakeContext()
    user = build_user_context(build_update(text="/start"))

    runtime_schedule_auto_advance_task(
        context,
        user,
        None,
        ScreenModel(screen_id="feedback", text="feedback", metadata={"auto_advance_after_ms": 1500, "next_action": "next"}),
        send_screen_to_chat=lambda *args, **kwargs: asyncio.sleep(0),
    )
    runtime_schedule_auto_advance_task(
        context,
        user,
        55,
        ScreenModel(screen_id="feedback", text="feedback", metadata={"auto_advance_after_ms": "1500", "next_action": "next"}),
        send_screen_to_chat=lambda *args, **kwargs: asyncio.sleep(0),
    )

    assert "auto_advance_task" not in context.user_data


def test_runtime_schedule_auto_advance_task_swallows_action_error(monkeypatch) -> None:
    class FailingApiClient(FakeRuntimeApiClient):
        async def action(self, user, action):
            raise RuntimeError("backend down")

    context = FakeContext(FailingApiClient())
    user = build_user_context(build_update(text="/start"))

    async def fake_sleep(seconds: float) -> None:
        return None

    async def fake_send_screen_to_chat(*args, **kwargs) -> None:
        raise AssertionError("screen should not be sent after action failure")

    monkeypatch.setattr("app.bot_runtime.auto_advance.asyncio.sleep", fake_sleep)

    async def run_case() -> None:
        runtime_schedule_auto_advance_task(
            context,
            user,
            55,
            ScreenModel(screen_id="feedback", text="feedback", metadata={"auto_advance_after_ms": 1500, "next_action": "s:77:next"}),
            send_screen_to_chat=fake_send_screen_to_chat,
        )
        task = context.user_data["auto_advance_task"]
        await task

    asyncio.run(run_case())

    assert "auto_advance_task" not in context.user_data


def test_runtime_schedule_auto_advance_task_propagates_cancellation(monkeypatch) -> None:
    context = FakeContext()
    user = build_user_context(build_update(text="/start"))

    async def fake_sleep(seconds: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr("app.bot_runtime.auto_advance.asyncio.sleep", fake_sleep)

    async def run_case() -> None:
        runtime_schedule_auto_advance_task(
            context,
            user,
            55,
            ScreenModel(screen_id="feedback", text="feedback", metadata={"auto_advance_after_ms": 1500, "next_action": "s:77:next"}),
            send_screen_to_chat=lambda *args, **kwargs: asyncio.sleep(0),
        )
        task = context.user_data["auto_advance_task"]
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_case())

    assert "auto_advance_task" not in context.user_data


def test_clear_tracked_messages_resets_active_screen_state(monkeypatch) -> None:
    context = FakeContext()
    context.application = SimpleNamespace(bot_data={"api_client": context.application.bot_data["api_client"]})
    context.user_data = {
        "bot_message_ids": [100],
        "bot_message_log_refs": [{"message_id": 100, "message_log_id": 900}],
        "active_screen_message_id": 100,
        "active_screen_message_log_id": 900,
        "active_screen_has_audio": True,
        "auxiliary_screen_message_id": 77,
        "auxiliary_screen_message_log_id": 777,
    }
    clear_calls: list[tuple[int, list[int]]] = []
    monkeypatch.setattr(
        "app.bot_runtime.message_tracking.clear_messages",
        lambda chat_id, application, message_ids, message_log_refs: clear_calls.append((chat_id, message_ids)) or asyncio.sleep(0),
    )

    asyncio.run(clear_tracked_messages(10, context))

    assert clear_calls == [(10, [100, 77])]
    assert context.user_data["bot_message_ids"] == []
    assert context.user_data["active_screen_message_id"] is None
    assert context.user_data["active_screen_has_audio"] is False
    assert context.user_data["auxiliary_screen_message_id"] is None


def test_track_sent_bot_message_returns_none_without_tracking_context() -> None:
    tracked = asyncio.run(track_sent_bot_message(None, 77, 10, "menu", 101))

    assert tracked is None


def test_track_sent_bot_message_returns_none_on_backend_error() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.track_error = RuntimeError("db unavailable")

    tracked = asyncio.run(track_sent_bot_message(api_client, 77, 10, "menu", 101))

    assert tracked is None


def test_save_cleanup_failure_swallows_persist_error() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.cleanup_result_error = RuntimeError("db unavailable")

    asyncio.run(save_cleanup_failure(api_client, 901, RuntimeError("delete failed")))

    assert api_client.cleanup_results == []


def test_save_cleanup_deleted_result_swallows_persist_error() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.cleanup_result_error = RuntimeError("db unavailable")

    asyncio.run(save_cleanup_deleted_result(api_client, 901))

    assert api_client.cleanup_results == []


def test_is_message_not_editable_error_recognizes_known_patterns() -> None:
    assert is_message_not_editable_error(RuntimeError("Message can't be edited"))
    assert not is_message_not_editable_error(RuntimeError("Network timeout"))


def test_is_message_not_modified_error_recognizes_known_patterns() -> None:
    assert is_message_not_modified_error(
        RuntimeError("specified new message content and reply markup are exactly the same")
    )
    assert not is_message_not_modified_error(RuntimeError("Message can't be edited"))


def test_build_user_context_raises_when_user_missing() -> None:
    update = build_update(include_user=False)

    with pytest.raises(RuntimeError, match="Telegram user is required"):
        build_user_context(update)


def test_build_user_context_serializes_user_and_chat(monkeypatch) -> None:
    update = build_update(text="/start")
    monkeypatch.setattr("app.bot_runtime.user_context.serialize_telegram_payload", lambda user, chat: '{"ok": true}')

    context = build_user_context(update)

    assert context.telegram_user_id == 77
    assert context.chat_id == 55
    assert context.raw_telegram_json == '{"ok": true}'


def test_reminder_polling_loop_dispatches_reminders(monkeypatch) -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_reminders_result = ReminderDispatchResponse(
        reminders=[
            ReminderScreenModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="reminder:1", text="reminder"),
            )
        ]
    )
    application = SimpleNamespace(bot_data={"api_client": api_client})
    sent_calls: list[tuple[int, str, int]] = []

    async def fake_send_screen_to_chat(application, chat_id, screen, user_data=None, telegram_user_id=None, disable_notification=True):
        sent_calls.append((chat_id, screen.screen_id, telegram_user_id, disable_notification))

    async def stop_after_first_sleep(seconds: float) -> None:
        raise asyncio.CancelledError()

    monkeypatch.setattr(sys.modules[__name__], "send_screen_to_chat", fake_send_screen_to_chat)
    monkeypatch.setattr(asyncio, "sleep", stop_after_first_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(reminder_polling_loop(application))

    assert sent_calls == [(55, "reminder:1", 77, False)]


def test_runtime_reminder_polling_loop_survives_dispatch_send_failure() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_reminders_result = ReminderDispatchResponse(
        reminders=[
            ReminderScreenModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="reminder:1", text="reminder"),
            )
        ]
    )
    application = SimpleNamespace(bot_data={"api_client": api_client})
    sleep_calls: list[float] = []

    async def failing_send_screen_to_chat(*args, **kwargs) -> None:
        raise RuntimeError("send failed")

    async def stop_after_first_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runtime_polling.reminder_polling_loop(
                application,
                send_screen_to_chat_func=failing_send_screen_to_chat,
                sleep_func=stop_after_first_sleep,
                now_func=lambda: datetime(2026, 4, 27, 10, 1, 30),
            )
        )

    assert sleep_calls == [210.0]


def test_runtime_reminder_polling_loop_reraises_cancellation() -> None:
    api_client = FakeRuntimeApiClient()

    async def cancelled_dispatch_reminders():
        raise asyncio.CancelledError()

    api_client.dispatch_reminders = cancelled_dispatch_reminders
    application = SimpleNamespace(bot_data={"api_client": api_client})

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runtime_polling.reminder_polling_loop(
                application,
                send_screen_to_chat_func=lambda *args, **kwargs: asyncio.sleep(0),
            )
        )


def test_schedule_reminder_auto_return_restores_menu_silently() -> None:
    api_client = FakeRuntimeApiClient()
    application = SimpleNamespace(bot_data={"api_client": api_client}, create_task=asyncio.create_task)
    sent_calls: list[tuple[int, str, int, bool, list[str]]] = []
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    async def fake_send_screen_to_chat(application, chat_id, screen, user_data=None, telegram_user_id=None, disable_notification=True):
        sent_calls.append((
            chat_id,
            screen.screen_id,
            telegram_user_id,
            disable_notification,
            [button["action"] for button in screen.metadata.get("auxiliary_message_buttons", [])],
        ))

    async def run_scenario() -> None:
        reminder = ReminderScreenModel(
            telegram_user_id=77,
            chat_id=55,
            screen=ScreenModel(screen_id="reminder:1", text="reminder", metadata={"auto_return_after_ms": 1000}),
        )
        schedule_reminder_auto_return_task(
            application,
            reminder,
            send_screen_to_chat=fake_send_screen_to_chat,
            sleep_func=fake_sleep,
        )
        await asyncio.sleep(0)

    asyncio.run(run_scenario())

    assert sleep_calls == [1.0]
    assert api_client.restore_menu_calls == [77]
    assert sent_calls == [(55, "menu", 77, True, ["m:settings"])]
    assert application.bot_data["reminder_auto_return_tasks"] == {}


def test_runtime_bot_message_cleanup_loop_survives_dispatch_failure() -> None:
    api_client = FakeRuntimeApiClient()

    async def failing_dispatch_bot_message_cleanup():
        raise RuntimeError("dispatch failed")

    api_client.dispatch_bot_message_cleanup = failing_dispatch_bot_message_cleanup
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_message_cleanup_poll_minutes=0),
        },
        bot=FakeRuntimeBot(),
    )
    sleep_calls: list[float] = []

    async def stop_after_first_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(runtime_polling.bot_message_cleanup_loop(application, sleep_func=stop_after_first_sleep))

    assert sleep_calls == [60]


def test_bot_message_cleanup_interval_prefers_seconds_setting() -> None:
    assert bot_message_cleanup_interval_seconds(
        SimpleNamespace(app_bot_message_cleanup_poll_seconds=5, app_bot_message_cleanup_poll_minutes=60)
    ) == 5
    assert bot_message_cleanup_interval_seconds(SimpleNamespace(app_bot_message_cleanup_poll_minutes=1)) == 60


def test_runtime_bot_message_cleanup_loop_reraises_delete_cancellation() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_cleanup_result = SimpleNamespace(messages=[SimpleNamespace(id=1, chat_id=10, message_id=100)])
    bot = FakeRuntimeBot()

    async def cancelled_delete_message(chat_id: int, message_id: int) -> None:
        raise asyncio.CancelledError()

    bot.delete_message = cancelled_delete_message
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_message_cleanup_poll_minutes=1),
        },
        bot=bot,
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(runtime_polling.bot_message_cleanup_loop(application))


def test_bot_message_cleanup_loop_processes_success_missing_and_failure(monkeypatch, caplog) -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_cleanup_result = SimpleNamespace(
        messages=[
            SimpleNamespace(id=1, chat_id=10, message_id=100),
            SimpleNamespace(id=2, chat_id=10, message_id=101),
            SimpleNamespace(id=3, chat_id=10, message_id=102),
        ]
    )
    bot = FakeRuntimeBot()
    bot.delete_errors = {
        101: RuntimeError("Message to delete not found"),
        102: RuntimeError("Forbidden"),
    }
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_message_cleanup_poll_minutes=1),
        },
        bot=bot,
    )

    async def stop_after_first_sleep(seconds: float) -> None:
        raise asyncio.CancelledError()

    monkeypatch.setattr(asyncio, "sleep", stop_after_first_sleep)
    caplog.set_level(logging.INFO, logger=runtime_polling.LOGGER.name)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(bot_message_cleanup_loop(application))

    assert bot.delete_calls == [(10, 100)]
    assert api_client.cleanup_results == [
        (1, True, None),
        (2, True, None),
        (3, False, "Forbidden"),
    ]
    assert "Bot message cleanup claimed 3 due messages" in caplog.text
    assert "Bot message cleanup finished: claimed=3 deleted=2 failed=1" in caplog.text


def test_user_import_polling_loop_dispatches_notifications(monkeypatch) -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_user_imports_result = ImportDispatchResponse(
        notifications=[
            ImportDispatchNotificationModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="import_words:summary", text="done"),
            )
        ]
    )
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_user_import_poll_minutes=60),
        }
    )
    sent_calls: list[tuple[int, str, int]] = []

    async def fake_send_screen_to_chat(application, chat_id, screen, user_data=None, telegram_user_id=None, disable_notification=True):
        sent_calls.append((chat_id, screen.screen_id, telegram_user_id, disable_notification))

    async def stop_after_first_sleep(seconds: float) -> None:
        raise asyncio.CancelledError()

    monkeypatch.setattr(sys.modules[__name__], "send_screen_to_chat", fake_send_screen_to_chat)
    monkeypatch.setattr(asyncio, "sleep", stop_after_first_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(user_import_polling_loop(application))

    assert sent_calls == [(55, "import_words:summary", 77, True)]


def test_runtime_user_import_polling_loop_survives_send_failure() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_user_imports_result = ImportDispatchResponse(
        notifications=[
            ImportDispatchNotificationModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="import_words:summary", text="summary"),
                disable_notification=False,
            )
        ]
    )
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_user_import_poll_minutes=0),
        }
    )
    sleep_calls: list[float] = []

    async def failing_send_screen_to_chat(*args, **kwargs) -> None:
        raise RuntimeError("send failed")

    async def stop_after_first_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runtime_polling.user_import_polling_loop(
                application,
                send_screen_to_chat_func=failing_send_screen_to_chat,
                sleep_func=stop_after_first_sleep,
            )
        )

    assert sleep_calls == [60]


def test_user_import_polling_loop_saves_billing_delivery_success() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_user_imports_result = ImportDispatchResponse(
        notifications=[
            ImportDispatchNotificationModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="billing:payment:7", text="paid"),
                delivery_kind="billing_bot_notification",
                delivery_id=7,
            )
        ]
    )
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_user_import_poll_minutes=60),
        }
    )

    async def send_screen_to_chat(*args, **kwargs) -> None:
        return None

    async def stop_after_first_sleep(seconds: float) -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runtime_polling.user_import_polling_loop(
                application,
                send_screen_to_chat_func=send_screen_to_chat,
                sleep_func=stop_after_first_sleep,
            )
        )

    assert api_client.billing_notification_results == [(7, True, None)]


def test_user_import_polling_loop_saves_billing_delivery_failure() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_user_imports_result = ImportDispatchResponse(
        notifications=[
            ImportDispatchNotificationModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="billing:payment:7", text="paid"),
                delivery_kind="billing_bot_notification",
                delivery_id=7,
            )
        ]
    )
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_user_import_poll_minutes=60),
        }
    )

    async def failing_send_screen_to_chat(*args, **kwargs) -> None:
        raise RuntimeError("send failed")

    async def stop_after_first_sleep(seconds: float) -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runtime_polling.user_import_polling_loop(
                application,
                send_screen_to_chat_func=failing_send_screen_to_chat,
                sleep_func=stop_after_first_sleep,
            )
        )

    assert api_client.billing_notification_results == [(7, False, "RuntimeError: send failed")]


def test_user_import_polling_loop_saves_billing_receipt_delivery_success() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_user_imports_result = ImportDispatchResponse(
        notifications=[
            ImportDispatchNotificationModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="billing:receipt:9", text="receipt"),
                delivery_kind="billing_receipt_delivery",
                delivery_id=9,
            )
        ]
    )
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_user_import_poll_minutes=60),
        }
    )

    async def send_screen_to_chat(*args, **kwargs) -> None:
        return None

    async def stop_after_first_sleep(seconds: float) -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runtime_polling.user_import_polling_loop(
                application,
                send_screen_to_chat_func=send_screen_to_chat,
                sleep_func=stop_after_first_sleep,
            )
        )

    assert api_client.billing_receipt_results == [(9, True, None)]


def test_user_import_polling_loop_saves_billing_receipt_admin_alert_failure() -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_user_imports_result = ImportDispatchResponse(
        notifications=[
            ImportDispatchNotificationModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="billing:receipt-alert:9", text="alert"),
                delivery_kind="billing_receipt_admin_alert",
                delivery_id=9,
            )
        ]
    )
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_user_import_poll_minutes=60),
        }
    )

    async def failing_send_screen_to_chat(*args, **kwargs) -> None:
        raise RuntimeError("send failed")

    async def stop_after_first_sleep(seconds: float) -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runtime_polling.user_import_polling_loop(
                application,
                send_screen_to_chat_func=failing_send_screen_to_chat,
                sleep_func=stop_after_first_sleep,
            )
        )

    assert api_client.billing_receipt_admin_alert_results == [(9, False, "RuntimeError: send failed")]


def test_runtime_user_import_polling_loop_reraises_cancellation() -> None:
    api_client = FakeRuntimeApiClient()

    async def cancelled_dispatch_user_imports():
        raise asyncio.CancelledError()

    api_client.dispatch_user_imports = cancelled_dispatch_user_imports
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_user_import_poll_minutes=1),
        }
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            runtime_polling.user_import_polling_loop(
                application,
                send_screen_to_chat_func=lambda *args, **kwargs: asyncio.sleep(0),
            )
        )


def test_build_keyboard_supports_url_buttons() -> None:
    keyboard = build_keyboard(
        ScreenModel(
            screen_id="admin:notification",
            text="notification",
            buttons=[
                {"action": "admin:open-web", "text": "Відкрити", "url": "https://cronolex.local/admin/auth/magic?token=abc"},
            ],
        )
    )

    assert keyboard.inline_keyboard[0][0].url == "https://cronolex.local/admin/auth/magic?token=abc"
    assert keyboard.inline_keyboard[0][0].callback_data is None


def test_user_import_polling_loop_passes_notification_sound_preference(monkeypatch) -> None:
    api_client = FakeRuntimeApiClient()
    api_client.dispatch_user_imports_result = ImportDispatchResponse(
        notifications=[
            ImportDispatchNotificationModel(
                telegram_user_id=77,
                chat_id=55,
                screen=ScreenModel(screen_id="import_words:summary", text="summary"),
                disable_notification=False,
            )
        ]
    )
    application = SimpleNamespace(
        bot_data={
            "api_client": api_client,
            "settings": SimpleNamespace(app_bot_user_import_poll_minutes=60),
        }
    )
    sent_calls: list[tuple[int, str, int, bool]] = []

    async def fake_send_screen_to_chat(application, chat_id, screen, user_data=None, telegram_user_id=None, disable_notification=True):
        sent_calls.append((chat_id, screen.screen_id, telegram_user_id, disable_notification))

    async def stop_after_first_sleep(seconds: float) -> None:
        raise asyncio.CancelledError()

    monkeypatch.setattr(sys.modules[__name__], "send_screen_to_chat", fake_send_screen_to_chat)
    monkeypatch.setattr(asyncio, "sleep", stop_after_first_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(user_import_polling_loop(application))

    assert sent_calls == [(55, "import_words:summary", 77, False)]
