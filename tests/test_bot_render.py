from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from app.bot_runtime.message_tracking import clear_messages
from app.bot_runtime.screen_delivery import render_screen, send_screen_to_chat
from app.contracts import ButtonModel, ScreenModel


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
        self.calls: list[str] = []
        self.next_message_id = 201
        self.delete_errors: dict[int, Exception] = {}
        self.edit_text_errors: dict[int, Exception] = {}
        self.edit_media_errors: dict[int, Exception] = {}

    async def send_audio(self, **kwargs):
        self.calls.append(f"send_audio:{kwargs['caption']}:{kwargs.get('disable_notification')}")
        message = FakeMessage(self.next_message_id)
        self.next_message_id += 1
        return message

    async def send_document(self, **kwargs):
        caption = kwargs.get("caption")
        self.calls.append(
            f"send_document:{kwargs['filename']}:{caption if caption is not None else ''}:{kwargs.get('disable_notification')}"
        )
        message = FakeMessage(self.next_message_id)
        self.next_message_id += 1
        return message

    async def send_message(self, **kwargs):
        reply_markup = kwargs.get("reply_markup")
        if reply_markup is not None and reply_markup.__class__.__name__ == "ReplyKeyboardRemove":
            self.calls.append(f"remove_reply_keyboard:{kwargs['text']}:{kwargs.get('disable_notification')}")
        else:
            self.calls.append(f"send_message:{kwargs['text']}:{kwargs.get('disable_notification')}")
        message = FakeMessage(self.next_message_id)
        self.next_message_id += 1
        return message

    async def edit_message_text(self, **kwargs):
        message_id = kwargs["message_id"]
        error = self.edit_text_errors.get(message_id)
        if error is not None:
            raise error
        self.calls.append(f"edit_text:{message_id}:{kwargs['text']}")

    async def edit_message_media(self, **kwargs):
        message_id = kwargs["message_id"]
        error = self.edit_media_errors.get(message_id)
        if error is not None:
            raise error
        self.calls.append(f"edit_media:{message_id}:{kwargs['media'].caption}")

    async def delete_message(self, **kwargs):
        message_id = kwargs["message_id"]
        error = self.delete_errors.get(message_id)
        if error is not None:
            raise error
        self.calls.append(f"delete:{kwargs['message_id']}")


class FakeChat:
    id = 10


class FakeContext:
    def __init__(self) -> None:
        self.bot = FakeBot()
        self.user_data = {
            "bot_message_ids": [100, 101],
            "bot_message_log_refs": [
                {"message_id": 100, "message_log_id": 900},
                {"message_id": 101, "message_log_id": 901},
            ],
        }
        self.application = self
        self.bot_data = {"api_client": FakeApiClient()}


class FakeUpdate:
    effective_chat = FakeChat()
    effective_user = type("User", (), {"id": 77})()
    callback_query = None


class FakeCallbackMessage:
    def __init__(self, message_id: int, *, has_audio: bool = False) -> None:
        self.message_id = message_id
        self.audio = object() if has_audio else None


class FakeCallbackQuery:
    def __init__(self, message_id: int, *, has_audio: bool = False) -> None:
        self.message = FakeCallbackMessage(message_id, has_audio=has_audio)


class FakeCallbackUpdate(FakeUpdate):
    def __init__(self, message_id: int, *, has_audio: bool = False) -> None:
        self.callback_query = FakeCallbackQuery(message_id, has_audio=has_audio)


class FakeApiClient:
    def __init__(self) -> None:
        self.tracked_messages: list[tuple[int, int, int, str]] = []
        self.cleanup_results: list[tuple[int, bool, str | None]] = []
        self.fail_deleted_result = False
        self.lookup_rows: dict[tuple[int, int, int], object] = {}
        self.active_messages = [
            type("TrackRow", (), {"id": 900, "message_id": 100, "screen_id": "legacy:100"})(),
            type("TrackRow", (), {"id": 901, "message_id": 101, "screen_id": "legacy:101"})(),
        ]

    async def track_bot_message(self, telegram_user_id: int, chat_id: int, message_id: int, screen_id: str, delete_after_hours=None):
        self.tracked_messages.append((telegram_user_id, chat_id, message_id, screen_id))
        row = type("TrackRow", (), {"id": message_id + 1000, "message_id": message_id, "screen_id": screen_id})()
        self.active_messages.append(row)
        return row

    async def lookup_bot_message(self, telegram_user_id: int, chat_id: int, message_id: int):
        return self.lookup_rows.get((telegram_user_id, chat_id, message_id))

    async def list_active_bot_messages(self, telegram_user_id: int, chat_id: int):
        return type("Response", (), {"messages": list(self.active_messages)})()

    async def save_bot_message_cleanup_result(
        self,
        message_log_id: int,
        is_deleted: bool,
        error_text: str | None = None,
    ) -> None:
        if is_deleted and self.fail_deleted_result:
            raise RuntimeError("backend unavailable")
        self.cleanup_results.append((message_log_id, is_deleted, error_text))
        if is_deleted:
            self.active_messages = [row for row in self.active_messages if getattr(row, "id", None) != message_log_id]


def test_render_screen_clears_previous_messages_after_success() -> None:
    context = FakeContext()
    context.bot_data["audio_storage_provider"] = FakeAudioStorageProvider(
        {"audio/0001_abandon.mp3": b"fake-audio"}
    )
    screen = ScreenModel(
        screen_id="card:11",
        text="caption",
        buttons=[
            ButtonModel(action="known", text="Я вже знаю слово"),
            ButtonModel(action="next", text="Наступне слово"),
        ],
        keyboard_type="inline",
            audio_path="audio/0001_abandon.mp3",
        clear_chat=True,
        metadata={"auxiliary_message_text": "Підказка:\n«Я вже знаю слово» — ..."},
    )

    asyncio.run(render_screen(FakeUpdate(), context, screen))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "send_message:Підказка:\n«Я вже знаю слово» — ...:True",
        "delete:101",
        "send_audio:caption:True",
        "delete:100",
    ]
    assert context.user_data["bot_message_ids"] == [203]
    assert context.user_data["bot_message_log_refs"] == [
        {"message_id": 203, "message_log_id": 1203},
        {"message_id": 202, "message_log_id": 1202},
    ]
    assert context.user_data["active_screen_message_id"] == 203
    assert context.user_data["active_screen_has_audio"] is True
    assert context.user_data["auxiliary_screen_message_id"] == 202
    assert context.user_data["reply_keyboard_removed"] is True
    assert context.bot_data["api_client"].tracked_messages == [
        (77, 10, 202, "auxiliary:card_hint"),
        (77, 10, 203, "card:11"),
    ]
    assert context.bot_data["api_client"].cleanup_results == [
        (901, True, None),
        (900, True, None),
    ]


def test_render_screen_edits_existing_active_text_message() -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    screen = ScreenModel(
        screen_id="quiz_en_uk:11",
        text="Основне повідомлення",
        notice_text="Вірно.",
    )

    asyncio.run(render_screen(FakeUpdate(), context, screen))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "edit_text:101:Вірно.\n\nОсновне повідомлення",
        "delete:100",
    ]
    assert context.user_data["bot_message_ids"] == [101]
    assert context.user_data["bot_message_log_refs"] == [{"message_id": 101, "message_log_id": 901}]
    assert context.bot_data["api_client"].tracked_messages == []
    assert context.bot_data["api_client"].cleanup_results == [(900, True, None)]


def test_render_screen_replaces_uneditable_message_with_fresh_one() -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    context.bot.edit_text_errors[101] = RuntimeError("Message to edit not found")
    screen = ScreenModel(screen_id="menu", text="Головний екран")

    asyncio.run(render_screen(FakeUpdate(), context, screen))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "send_message:Головний екран:True",
        "delete:100",
        "delete:101",
    ]
    assert context.user_data["bot_message_ids"] == [202]
    assert context.user_data["active_screen_message_id"] == 202
    assert context.bot_data["api_client"].tracked_messages == [(77, 10, 202, "menu")]


def test_send_screen_to_chat_forces_menu_to_silent_even_when_caller_requests_push() -> None:
    context = FakeContext()
    context.user_data = {}

    asyncio.run(
        send_screen_to_chat(
            context,
            10,
            ScreenModel(screen_id="menu", text="Головний екран"),
            user_data=context.user_data,
            telegram_user_id=77,
            disable_notification=False,
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "send_message:Головний екран:True",
        "delete:100",
        "delete:101",
    ]


def test_send_screen_to_chat_allows_push_only_for_primary_reminder_message() -> None:
    context = FakeContext()
    context.user_data = {}
    screen = ScreenModel(
        screen_id="reminder:1",
        text="Час тренуватись",
        metadata={
            "auxiliary_after_active": True,
            "auxiliary_message_text": "Повернутися в меню",
        },
    )

    asyncio.run(
        send_screen_to_chat(
            context,
            10,
            screen,
            user_data=context.user_data,
            telegram_user_id=77,
            disable_notification=False,
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "send_message:Час тренуватись:False",
        "send_message:Повернутися в меню:True",
        "delete:100",
        "delete:101",
    ]


def test_render_screen_force_resend_replaces_active_screen_with_new_message() -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    screen = ScreenModel(
        screen_id="menu:import_words",
        text="Google Doc зі словами",
        metadata={"force_resend": True},
    )

    asyncio.run(render_screen(FakeUpdate(), context, screen))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "delete:101",
        "send_message:Google Doc зі словами:True",
        "delete:100",
    ]
    assert context.user_data["bot_message_ids"] == [202]
    assert context.user_data["bot_message_log_refs"] == [{"message_id": 202, "message_log_id": 1202}]
    assert context.user_data["active_screen_message_id"] == 202
    assert context.bot_data["api_client"].tracked_messages == [(77, 10, 202, "menu:import_words")]


def test_render_screen_sends_summary_documents_after_main_message(monkeypatch, tmp_path: Path) -> None:
    queued_path = tmp_path / "queued_words.txt"
    queued_path.write_text("take over\ncarry on\n", encoding="utf-8")
    existing_path = tmp_path / "existing_words.txt"
    existing_path.write_text("speak - говорити\nwrite - писати\n", encoding="utf-8")

    context = FakeContext()
    screen = ScreenModel(
        screen_id="import_words:summary:7",
        text="Інтейк власних слів зафіксовано.",
        documents=[
            {"path": str(queued_path), "filename": queued_path.name, "caption": "queued"},
            {"path": str(existing_path), "filename": existing_path.name, "caption": "existing"},
        ],
    )

    asyncio.run(render_screen(FakeUpdate(), context, screen))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "edit_text:101:Інтейк власних слів зафіксовано.",
        "delete:100",
        "send_document:queued_words.txt:queued:True",
        "send_document:existing_words.txt:existing:True",
    ]
    assert context.user_data["bot_message_ids"] == [101, 202, 203]
    assert context.bot_data["api_client"].tracked_messages == [
        (77, 10, 202, "attachment:import_words:summary:7:1"),
        (77, 10, 203, "attachment:import_words:summary:7:2"),
    ]


def test_render_screen_documents_only_sends_documents_without_main_message(tmp_path: Path) -> None:
    queued_path = tmp_path / "queued_words.txt"
    queued_path.write_text("take over\n", encoding="utf-8")

    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    screen = ScreenModel(
        screen_id="import_words:documents:queued:7",
        text="",
        documents=[{"path": str(queued_path), "filename": queued_path.name, "caption": "queued"}],
        metadata={"documents_only": True},
    )

    asyncio.run(render_screen(FakeUpdate(), context, screen))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "delete:100",
        "send_document:queued_words.txt:queued:True",
    ]
    assert context.user_data["active_screen_message_id"] == 101
    assert context.user_data["bot_message_ids"] == [101, 202]


def test_render_screen_edits_existing_audio_message() -> None:
    context = FakeContext()
    context.bot_data["audio_storage_provider"] = FakeAudioStorageProvider(
        {"audio/0001_abandon.mp3": b"fake-audio"}
    )
    context.user_data["bot_message_ids"] = [100]
    context.user_data["bot_message_log_refs"] = [{"message_id": 100, "message_log_id": 900}]
    context.user_data["active_screen_message_id"] = 100
    context.user_data["active_screen_message_log_id"] = 900
    context.user_data["active_screen_has_audio"] = True
    screen = ScreenModel(
        screen_id="card:12",
        text="Нова картка",
        audio_path="audio/0001_abandon.mp3",
        metadata={"auxiliary_message_text": "Підказка:\n«Я вже знаю слово» — ..."},
    )
    context.user_data["auxiliary_screen_message_id"] = 77
    context.user_data["auxiliary_screen_message_log_id"] = 777

    asyncio.run(render_screen(FakeUpdate(), context, screen))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "edit_text:77:Підказка:\n«Я вже знаю слово» — ...",
        "edit_media:100:Нова картка",
        "delete:101",
    ]
    assert context.user_data["active_screen_message_id"] == 100
    assert context.user_data["active_screen_has_audio"] is True
    assert context.user_data["auxiliary_screen_message_id"] == 77


def test_render_screen_sweeps_legacy_tracked_message_not_present_in_user_data() -> None:
    context = FakeContext()
    context.user_data["bot_message_ids"] = [101]
    context.user_data["bot_message_log_refs"] = [{"message_id": 101, "message_log_id": 901}]
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    context.bot_data["api_client"].active_messages.append(
        type("TrackRow", (), {"id": 999, "message_id": 555, "screen_id": "legacy:555"})()
    )

    asyncio.run(render_screen(FakeUpdate(), context, ScreenModel(screen_id="menu", text="Оновлене меню")))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "edit_text:101:Оновлене меню",
        "delete:100",
        "delete:555",
    ]
    assert context.bot_data["api_client"].cleanup_results == [(900, True, None), (999, True, None)]


def test_render_screen_keeps_sticky_import_report_when_sending_non_import_screen() -> None:
    context = FakeContext()
    context.user_data = {}
    context.bot_data["api_client"].active_messages = [
        type("TrackRow", (), {"id": 955, "message_id": 555, "screen_id": "import_words:summary:7"})(),
    ]

    asyncio.run(render_screen(FakeUpdate(), context, ScreenModel(screen_id="reminder:1", text="Час тренуватись")))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "send_message:Час тренуватись:True",
    ]
    assert context.bot_data["api_client"].cleanup_results == []


def test_render_screen_keeps_only_latest_sticky_import_report_when_multiple_are_tracked() -> None:
    context = FakeContext()
    context.user_data = {}
    context.bot_data["api_client"].active_messages = [
        type("TrackRow", (), {"id": 955, "message_id": 555, "screen_id": "import_words:summary:7"})(),
        type("TrackRow", (), {"id": 956, "message_id": 556, "screen_id": "import_words:failed:8"})(),
    ]

    asyncio.run(render_screen(FakeUpdate(), context, ScreenModel(screen_id="reminder:1", text="Час тренуватись")))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "send_message:Час тренуватись:True",
        "delete:555",
    ]
    assert context.bot_data["api_client"].cleanup_results == [(955, True, None)]


def test_render_screen_keeps_tracked_sticky_import_report_when_sending_non_import_screen() -> None:
    context = FakeContext()
    context.user_data["bot_message_ids"] = [555]
    context.user_data["bot_message_log_refs"] = [{"message_id": 555, "message_log_id": 1555}]
    context.user_data["active_screen_message_id"] = 555
    context.user_data["active_screen_message_log_id"] = 1555
    context.user_data["active_screen_screen_id"] = "import_words:summary:7"
    context.bot_data["api_client"].active_messages = [
        type("TrackRow", (), {"id": 1555, "message_id": 555, "screen_id": "import_words:summary:7"})(),
    ]

    asyncio.run(render_screen(FakeUpdate(), context, ScreenModel(screen_id="reminder:1", text="Час тренуватись")))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "send_message:Час тренуватись:True",
    ]
    assert context.user_data["active_screen_message_id"] == 202
    assert context.user_data["active_screen_screen_id"] == "reminder:1"
    assert context.bot_data["api_client"].cleanup_results == []


def test_render_screen_force_resend_when_leaving_sticky_import_report_to_menu() -> None:
    context = FakeContext()
    context.user_data = {}
    context.bot_data["api_client"].lookup_rows[(77, 10, 555)] = type(
        "TrackRow", (), {"id": 1555, "screen_id": "import_words:summary:7"}
    )()
    context.bot_data["api_client"].active_messages = [
        type("TrackRow", (), {"id": 1555, "message_id": 555, "screen_id": "import_words:summary:7"})(),
    ]

    asyncio.run(
        render_screen(
            FakeCallbackUpdate(555),
            context,
            ScreenModel(screen_id="menu", text="Головний екран", metadata={"force_resend": True}),
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "delete:555",
        "send_message:Головний екран:True",
    ]
    assert context.bot_data["api_client"].cleanup_results == [(1555, True, None)]


def test_render_screen_delete_current_message_only_dismisses_import_report() -> None:
    context = FakeContext()
    context.user_data = {}
    context.bot_data["api_client"].lookup_rows[(77, 10, 555)] = type(
        "TrackRow", (), {"id": 1555, "screen_id": "import_words:summary:7"}
    )()

    asyncio.run(
        render_screen(
            FakeCallbackUpdate(555),
            context,
            ScreenModel(screen_id="import_words:delete", text="", metadata={"delete_current_message_only": True}),
        )
    )

    assert context.bot.calls == ["remove_reply_keyboard:Оновлюю інтерфейс…:True", "delete:201", "delete:555"]
    assert context.bot_data["api_client"].cleanup_results == [(1555, True, None)]


def test_render_screen_close_to_menu_deletes_notification_and_cached_active_screen() -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    context.user_data["active_screen_screen_id"] = "menu"
    context.bot_data["api_client"].lookup_rows[(77, 10, 555)] = type(
        "TrackRow", (), {"id": 1555, "screen_id": "billing:payment:7"}
    )()

    asyncio.run(
        render_screen(
            FakeCallbackUpdate(555),
            context,
            ScreenModel(
                screen_id="menu",
                text="menu",
                metadata={
                    "force_resend": True,
                    "delete_cached_active_screen": True,
                },
            ),
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "delete:555",
        "send_message:menu:True",
        "delete:100",
        "delete:101",
    ]
    assert context.bot_data["api_client"].cleanup_results == [
        (1555, True, None),
        (900, True, None),
        (901, True, None),
    ]
    assert context.user_data["active_screen_message_id"] == 202


def test_render_screen_deletes_auxiliary_hint_when_leaving_card_flow() -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    context.user_data["active_screen_has_audio"] = True
    context.user_data["auxiliary_screen_message_id"] = 77
    context.user_data["auxiliary_screen_message_log_id"] = 777

    asyncio.run(render_screen(FakeUpdate(), context, ScreenModel(screen_id="ready_en_uk", text="Готові?")))

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "delete:77",
        "send_message:Готові?:True",
        "delete:100",
        "delete:101",
    ]
    assert context.user_data["auxiliary_screen_message_id"] is None


def test_render_screen_keeps_edit_history_for_later_cleanup() -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901

    asyncio.run(render_screen(FakeUpdate(), context, ScreenModel(screen_id="menu", text="Оновлене меню")))
    asyncio.run(
        render_screen(
            FakeUpdate(),
            context,
            ScreenModel(screen_id="menu:import_words", text="Імпорт", metadata={"force_resend": True}),
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "edit_text:101:Оновлене меню",
        "delete:100",
        "delete:101",
        "send_message:Імпорт:True",
    ]


def test_render_screen_removes_reply_keyboard_only_once() -> None:
    context = FakeContext()
    context.user_data["reply_keyboard_removed"] = True
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    screen = ScreenModel(screen_id="menu", text="Головний екран")

    asyncio.run(render_screen(FakeUpdate(), context, screen))

    assert context.bot.calls == ["edit_text:101:Головний екран", "delete:100"]


def test_render_screen_edits_callback_message_when_user_data_has_no_active_screen() -> None:
    context = FakeContext()
    context.user_data = {}
    context.bot_data["api_client"].lookup_rows[(77, 10, 555)] = type("TrackRow", (), {"id": 1555})()

    asyncio.run(
        render_screen(
            FakeCallbackUpdate(555),
            context,
            ScreenModel(screen_id="import_words:failed:9", text="Неуспішні слова"),
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "edit_text:555:Неуспішні слова",
        "delete:100",
        "delete:101",
    ]
    assert context.user_data["active_screen_message_id"] == 555
    assert context.user_data["active_screen_message_log_id"] == 1555
    assert context.bot_data["api_client"].tracked_messages == []


def test_render_screen_force_resend_deletes_callback_message_when_user_data_has_no_active_screen() -> None:
    context = FakeContext()
    context.user_data = {}
    context.bot_data["api_client"].lookup_rows[(77, 10, 777)] = type("TrackRow", (), {"id": 1777})()

    asyncio.run(
        render_screen(
            FakeCallbackUpdate(777),
            context,
            ScreenModel(screen_id="menu", text="Головний екран", metadata={"force_resend": True}),
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "delete:777",
        "send_message:Головний екран:True",
        "delete:100",
        "delete:101",
    ]
    assert context.user_data["active_screen_message_id"] == 202
    assert context.bot_data["api_client"].tracked_messages == [(77, 10, 202, "menu")]
    assert context.bot_data["api_client"].cleanup_results == [(1777, True, None), (900, True, None), (901, True, None)]


def test_send_screen_to_chat_prefers_editing_active_tracked_message_for_silent_restore() -> None:
    context = FakeContext()

    asyncio.run(
        send_screen_to_chat(
            context,
            10,
            ScreenModel(screen_id="menu", text="Головний екран", metadata={"prefer_edit_active": True}),
            user_data=None,
            telegram_user_id=77,
        )
    )

    assert context.bot.calls == [
        "edit_text:101:Головний екран",
        "delete:100",
    ]
    assert context.bot_data["api_client"].tracked_messages == [(77, 10, 101, "menu")]
    assert context.bot_data["api_client"].cleanup_results == [(901, True, None), (900, True, None)]


def test_render_screen_callback_message_overrides_cached_active_screen() -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901

    asyncio.run(
        render_screen(
            FakeCallbackUpdate(333),
            context,
            ScreenModel(screen_id="import_words:failed:9", text="Неуспішні слова"),
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "edit_text:333:Неуспішні слова",
        "delete:100",
        "delete:101",
    ]
    assert context.user_data["active_screen_message_id"] == 333
    assert context.user_data["bot_message_ids"] == [333]
    assert context.bot_data["api_client"].cleanup_results == [
        (900, True, None),
        (901, True, None),
    ]


def test_render_screen_keeps_edited_old_callback_message_when_it_was_tracked() -> None:
    context = FakeContext()
    context.user_data["active_screen_message_id"] = 101
    context.user_data["active_screen_message_log_id"] = 901
    context.user_data["bot_message_ids"] = [100, 101]
    context.user_data["bot_message_log_refs"] = [
        {"message_id": 100, "message_log_id": 900},
        {"message_id": 101, "message_log_id": 901},
    ]

    asyncio.run(
        render_screen(
            FakeCallbackUpdate(100),
            context,
            ScreenModel(screen_id="import_words:failed:9", text="Неуспішні слова"),
        )
    )

    assert context.bot.calls == [
        "remove_reply_keyboard:Оновлюю інтерфейс…:True",
        "delete:201",
        "edit_text:100:Неуспішні слова",
        "delete:101",
    ]
    assert context.user_data["active_screen_message_id"] == 100
    assert context.user_data["bot_message_ids"] == [100]
    assert context.bot_data["api_client"].cleanup_results == [(901, True, None)]


def test_clear_messages_treats_missing_telegram_message_as_deleted() -> None:
    context = FakeContext()
    context.bot.delete_errors[100] = RuntimeError("Message to delete not found")

    asyncio.run(
        clear_messages(
            10,
            context.application,
            [100],
            [{"message_id": 100, "message_log_id": 900}],
        )
    )

    assert context.bot_data["api_client"].cleanup_results == [(900, True, None)]


def test_clear_messages_does_not_report_failure_when_deleted_ack_fails() -> None:
    context = FakeContext()
    context.bot_data["api_client"].fail_deleted_result = True

    asyncio.run(
        clear_messages(
            10,
            context.application,
            [100],
            [{"message_id": 100, "message_log_id": 900}],
        )
    )

    assert context.bot.calls == ["delete:100"]
    assert context.bot_data["api_client"].cleanup_results == []
