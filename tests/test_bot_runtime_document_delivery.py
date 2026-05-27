from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from app.bot_runtime.document_delivery import send_screen_documents
from app.bot_runtime.document_delivery import (
    send_screen_documents as compatibility_send_screen_documents,
)
from app.contracts import ScreenModel


class FakeBot:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def send_document(self, **kwargs):
        content = kwargs["document"].read()
        self.calls.append({**kwargs, "document": content})
        return SimpleNamespace(message_id=500 + len(self.calls))


class FakeApiClient:
    def __init__(self) -> None:
        self.track_calls: list[tuple[int, int, int, str, int | None]] = []

    async def track_bot_message(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after_hours: int | None = None,
    ):
        self.track_calls.append((telegram_user_id, chat_id, message_id, screen_id, delete_after_hours))
        return SimpleNamespace(id=900 + len(self.track_calls))


def build_application(api_client: FakeApiClient | None = None):
    return SimpleNamespace(bot=FakeBot(), bot_data={"api_client": api_client})


def test_send_screen_documents_sends_existing_documents_and_tracks_user_state(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.txt"
    document_path = tmp_path / "report.txt"
    document_path.write_text("hello", encoding="utf-8")
    api_client = FakeApiClient()
    application = build_application(api_client)
    user_data: dict[str, object] = {}
    screen = ScreenModel(
        screen_id="import_words:documents:7",
        text="",
        parse_mode="HTML",
        documents=[
            {"path": str(missing_path), "filename": "missing.txt", "caption": "missing"},
            {"path": str(document_path), "filename": "report.txt", "caption": "ready"},
        ],
        metadata={"delete_after_hours": 3},
    )

    asyncio.run(
        send_screen_documents(
            application=application,
            chat_id=10,
            screen=screen,
            user_data=user_data,
            telegram_user_id=77,
            disable_notification=False,
        )
    )

    assert application.bot.calls == [
        {
            "chat_id": 10,
            "document": b"hello",
            "caption": "ready",
            "parse_mode": "HTML",
            "filename": "report.txt",
            "disable_notification": False,
        }
    ]
    assert api_client.track_calls == [(77, 10, 501, "attachment:import_words:documents:7:2", 3)]
    assert user_data["bot_message_ids"] == [501]
    assert user_data["bot_message_log_refs"] == [{"message_id": 501, "message_log_id": 901}]


def test_send_screen_documents_handles_no_documents_or_user_state(tmp_path: Path) -> None:
    document_path = tmp_path / "report.txt"
    document_path.write_text("hello", encoding="utf-8")
    application = build_application(None)

    asyncio.run(
        send_screen_documents(
            application=application,
            chat_id=10,
            screen=ScreenModel(screen_id="empty", text=""),
            user_data=None,
            telegram_user_id=77,
            disable_notification=True,
        )
    )
    asyncio.run(
        send_screen_documents(
            application=application,
            chat_id=10,
            screen=ScreenModel(
                screen_id="docs",
                text="",
                documents=[{"path": str(document_path), "filename": "report.txt", "caption": None}],
            ),
            user_data=None,
            telegram_user_id=77,
            disable_notification=True,
        )
    )

    assert len(application.bot.calls) == 1
    assert application.bot.calls[0]["disable_notification"] is True


def test_document_delivery_compatibility_import_stays_on_app_bot() -> None:
    assert compatibility_send_screen_documents is send_screen_documents
