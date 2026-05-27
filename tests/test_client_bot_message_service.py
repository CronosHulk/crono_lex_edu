from __future__ import annotations

from datetime import datetime

from app.application.client.bot_message_service import ClientBotMessageService


class FixedTimeService:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


class FakeBotMessageLogRepository:
    def __init__(self) -> None:
        self.created_bot_messages: list[dict] = []
        self.cleanup_results: list[dict] = []

    def create(
        self,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        screen_id: str,
        delete_after,
        current_time,
    ):
        payload = {
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "screen_id": screen_id,
            "delete_after": delete_after,
            "current_time": current_time,
        }
        self.created_bot_messages.append(payload)
        return {"id": len(self.created_bot_messages), **payload}

    def claim_due_cleanup(self, current_time, retry_before):
        return [
            {
                "id": 901,
                "message_id": 501,
                "current_time": current_time,
                "retry_before": retry_before,
            }
        ]

    def get_latest_for_message(self, telegram_user_id: int, chat_id: int, message_id: int):
        for row in reversed(self.created_bot_messages):
            if (
                row["telegram_user_id"] == telegram_user_id
                and row["chat_id"] == chat_id
                and row["message_id"] == message_id
            ):
                return {"id": 901, **row}
        return None

    def list_active(self, telegram_user_id: int, chat_id: int):
        return [
            {"id": 901 + index, **row}
            for index, row in enumerate(self.created_bot_messages)
            if row["telegram_user_id"] == telegram_user_id and row["chat_id"] == chat_id
        ]

    def save_cleanup_result(self, message_log_id: int, *, is_deleted: bool, current_time, error_text=None) -> None:
        self.cleanup_results.append(
            {
                "message_log_id": message_log_id,
                "is_deleted": is_deleted,
                "current_time": current_time,
                "error_text": error_text,
            }
        )


def build_service(repository: FakeBotMessageLogRepository | None = None, *, retention_days: int = 30) -> ClientBotMessageService:
    return ClientBotMessageService(
        repository or FakeBotMessageLogRepository(),
        FixedTimeService(datetime(2026, 4, 26, 10, 0, 0)),
        retention_days=retention_days,
    )


def test_client_bot_message_service_uses_retention_policy() -> None:
    repository = FakeBotMessageLogRepository()
    service = build_service(repository)

    service.track_bot_message(telegram_user_id=1, chat_id=99, message_id=501, screen_id="menu")

    tracked = repository.created_bot_messages[-1]
    assert tracked["screen_id"] == "menu"
    assert (tracked["delete_after"] - tracked["current_time"]).days == 30


def test_client_bot_message_service_respects_delete_after_hours_override() -> None:
    repository = FakeBotMessageLogRepository()
    service = build_service(repository)

    service.track_bot_message(
        telegram_user_id=1,
        chat_id=99,
        message_id=501,
        screen_id="import_words:summary:7",
        delete_after_hours=24,
    )

    tracked = repository.created_bot_messages[-1]
    assert tracked["screen_id"] == "import_words:summary:7"
    assert (tracked["delete_after"] - tracked["current_time"]).total_seconds() == 24 * 60 * 60


def test_client_bot_message_service_returns_due_cleanup_payload() -> None:
    rows = build_service().dispatch_due_bot_message_cleanup()

    assert rows[0]["id"] == 901
    assert rows[0]["message_id"] == 501
    assert (rows[0]["current_time"] - rows[0]["retry_before"]).total_seconds() == 30 * 60


def test_client_bot_message_service_reads_active_rows() -> None:
    repository = FakeBotMessageLogRepository()
    service = build_service(repository)
    service.track_bot_message(telegram_user_id=1, chat_id=99, message_id=501, screen_id="menu")

    row = service.get_bot_message_log(telegram_user_id=1, chat_id=99, message_id=501)
    rows = service.list_active_bot_messages(telegram_user_id=1, chat_id=99)

    assert row is not None
    assert row["screen_id"] == "menu"
    assert rows[0]["message_id"] == 501


def test_client_bot_message_service_passes_cleanup_result_to_db() -> None:
    repository = FakeBotMessageLogRepository()
    service = build_service(repository)

    service.save_bot_message_cleanup_result(message_log_id=901, is_deleted=False, error_text="message not found")

    assert repository.cleanup_results[-1]["message_log_id"] == 901
    assert repository.cleanup_results[-1]["is_deleted"] is False
    assert repository.cleanup_results[-1]["error_text"] == "message not found"
