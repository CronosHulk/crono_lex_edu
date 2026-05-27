from __future__ import annotations

import httpx

from app.telegram_gateway import TelegramGateway, call_telegram_api


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeHttpxClient:
    calls: list[dict] = []
    payload: dict = {"ok": True, "result": {"message_id": 42}}

    def __init__(self, *, timeout: int) -> None:
        self.timeout = timeout

    def __enter__(self) -> FakeHttpxClient:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def post(self, url: str, *, json: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": self.timeout})
        return FakeResponse(self.payload)


def test_telegram_gateway_sends_message_through_telegram_api(monkeypatch) -> None:
    FakeHttpxClient.calls = []
    FakeHttpxClient.payload = {"ok": True, "result": {"message_id": 42}}
    monkeypatch.setattr("app.telegram_gateway.httpx.Client", FakeHttpxClient)

    message_id = TelegramGateway("token").send_message(chat_id=100, text="hello")

    assert message_id == 42
    assert FakeHttpxClient.calls == [
        {
            "url": "https://api.telegram.org/bottoken/sendMessage",
            "json": {"chat_id": 100, "text": "hello", "disable_notification": False},
            "timeout": 10,
        }
    ]


def test_telegram_gateway_can_send_silent_message(monkeypatch) -> None:
    FakeHttpxClient.calls = []
    FakeHttpxClient.payload = {"ok": True, "result": {"message_id": 43}}
    monkeypatch.setattr("app.telegram_gateway.httpx.Client", FakeHttpxClient)

    message_id = TelegramGateway("token").send_message(chat_id=100, text="menu", disable_notification=True)

    assert message_id == 43
    assert FakeHttpxClient.calls[0]["json"] == {
        "chat_id": 100,
        "text": "menu",
        "disable_notification": True,
    }


def test_telegram_gateway_can_ignore_transport_errors(monkeypatch) -> None:
    def failing_client(*, timeout: int):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr("app.telegram_gateway.httpx.Client", failing_client)

    assert call_telegram_api("token", "sendMessage", {"chat_id": 100}, ignore_errors=True) == {}
