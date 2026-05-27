from __future__ import annotations

import asyncio

import httpx

from app.bot_api_client import BotApiClient
from app.bot_http_transport import BackendBotApiTransport


class FakeTransport:
    def __init__(self, responses: list) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    async def post(self, path: str, *, json: dict | None = None, timeout: float = 30.0):
        self.calls.append({"path": path, "json": json, "timeout": timeout})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeAsyncResponse:
    def __init__(self, payload, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


class FakeAsyncHttpClient:
    calls: list[dict] = []
    response: FakeAsyncResponse = FakeAsyncResponse({"ok": True})

    def __init__(self, *, base_url: str, timeout: float) -> None:
        self.base_url = base_url
        self.timeout = timeout

    async def __aenter__(self) -> FakeAsyncHttpClient:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def post(
        self,
        path: str,
        *,
        json: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeAsyncResponse:
        self.calls.append(
            {
                "base_url": self.base_url,
                "path": path,
                "json": json,
                "headers": headers,
                "timeout": self.timeout,
            }
        )
        return self.response


def test_backend_bot_api_transport_posts_and_returns_json(monkeypatch) -> None:
    FakeAsyncHttpClient.calls = []
    FakeAsyncHttpClient.response = FakeAsyncResponse({"ok": True})
    monkeypatch.setattr("app.bot_http_transport.httpx.AsyncClient", FakeAsyncHttpClient)
    transport = BackendBotApiTransport("https://api.local/")

    result = asyncio.run(transport.post("/api/v1/demo", json={"a": 1}, timeout=12.5))

    assert result == {"ok": True}
    assert FakeAsyncHttpClient.calls == [
        {
            "base_url": "https://api.local",
            "path": "/api/v1/demo",
            "json": {"a": 1},
            "headers": None,
            "timeout": 12.5,
        }
    ]


def test_backend_bot_api_transport_sends_internal_token_header(monkeypatch) -> None:
    FakeAsyncHttpClient.calls = []
    FakeAsyncHttpClient.response = FakeAsyncResponse({"ok": True})
    monkeypatch.setattr("app.bot_http_transport.httpx.AsyncClient", FakeAsyncHttpClient)
    transport = BackendBotApiTransport("https://api.local/", internal_api_token=" internal-token ")

    result = asyncio.run(transport.post("/api/v1/demo"))

    assert result == {"ok": True}
    assert FakeAsyncHttpClient.calls == [
        {
            "base_url": "https://api.local",
            "path": "/api/v1/demo",
            "json": None,
            "headers": {"X-CronoLex-Internal-Token": "internal-token"},
            "timeout": 30.0,
        }
    ]


def test_backend_bot_api_transport_propagates_status_errors(monkeypatch) -> None:
    request = httpx.Request("POST", "https://api.local/api/v1/demo")
    response = httpx.Response(500, request=request)
    error = httpx.HTTPStatusError("server error", request=request, response=response)
    FakeAsyncHttpClient.calls = []
    FakeAsyncHttpClient.response = FakeAsyncResponse({"detail": "failed"}, error=error)
    monkeypatch.setattr("app.bot_http_transport.httpx.AsyncClient", FakeAsyncHttpClient)
    transport = BackendBotApiTransport("https://api.local")

    try:
        asyncio.run(transport.post("/api/v1/demo"))
    except httpx.HTTPStatusError as raised:
        assert raised.response.status_code == 500
    else:  # pragma: no cover
        raise AssertionError("HTTPStatusError was expected")


def test_bot_api_client_tracks_bot_message_with_typed_payload() -> None:
    transport = FakeTransport(
        [
            {
                "id": 9,
                "telegram_user_id": 1,
                "chat_id": 10,
                "message_id": 11,
                "screen_id": "menu",
            }
        ]
    )
    client = BotApiClient("https://api.local", transport=transport)

    result = asyncio.run(
        client.track_bot_message(
            telegram_user_id=1,
            chat_id=10,
            message_id=11,
            screen_id="menu",
            delete_after_hours=2,
        )
    )

    assert result.id == 9
    assert transport.calls == [
        {
            "path": "/api/v1/bot/messages/track",
            "json": {
                "telegram_user_id": 1,
                "chat_id": 10,
                "message_id": 11,
                "screen_id": "menu",
                "delete_after_hours": 2,
            },
            "timeout": 30.0,
        }
    ]


def test_bot_api_client_lookup_returns_none_for_missing_message() -> None:
    transport = FakeTransport([None])
    client = BotApiClient("https://api.local", transport=transport)

    result = asyncio.run(client.lookup_bot_message(telegram_user_id=1, chat_id=10, message_id=11))

    assert result is None
    assert transport.calls[0]["path"] == "/api/v1/bot/messages/lookup"


def test_bot_api_client_restores_menu_with_typed_payload() -> None:
    transport = FakeTransport([{"screen": {"screen_id": "menu", "text": "menu"}}])
    client = BotApiClient("https://api.local", transport=transport)

    result = asyncio.run(client.restore_menu(telegram_user_id=1))

    assert result.screen.screen_id == "menu"
    assert transport.calls == [
        {
            "path": "/api/v1/menu/restore",
            "json": {"telegram_user_id": 1},
            "timeout": 30.0,
        }
    ]


def test_bot_api_client_dispatch_user_imports_uses_long_timeout() -> None:
    transport = FakeTransport([{"notifications": []}])
    client = BotApiClient("https://api.local", transport=transport)

    result = asyncio.run(client.dispatch_user_imports())

    assert result.notifications == []
    assert transport.calls == [{"path": "/api/v1/imports/process", "json": None, "timeout": 60.0}]


def test_bot_api_client_saves_billing_notification_delivery_result() -> None:
    transport = FakeTransport([{"status": "ok"}])
    client = BotApiClient("https://api.local", transport=transport)

    asyncio.run(
        client.save_billing_notification_delivery_result(
            77,
            is_sent=False,
            error_text="send failed",
        )
    )

    assert transport.calls == [
        {
            "path": "/api/v1/billing/notifications/77/delivery-result",
            "json": {"is_sent": False, "error_text": "send failed"},
            "timeout": 30.0,
        }
    ]


def test_bot_api_client_saves_billing_receipt_delivery_result() -> None:
    transport = FakeTransport([{"status": "ok"}])
    client = BotApiClient("https://api.local", transport=transport)

    asyncio.run(
        client.save_billing_receipt_delivery_result(
            88,
            is_sent=True,
        )
    )

    assert transport.calls == [
        {
            "path": "/api/v1/billing/receipts/88/delivery-result",
            "json": {"is_sent": True, "error_text": None},
            "timeout": 30.0,
        }
    ]


def test_bot_api_client_saves_billing_receipt_admin_alert_result() -> None:
    transport = FakeTransport([{"status": "ok"}])
    client = BotApiClient("https://api.local", transport=transport)

    asyncio.run(
        client.save_billing_receipt_admin_alert_result(
            89,
            is_sent=False,
            error_text="send failed",
        )
    )

    assert transport.calls == [
        {
            "path": "/api/v1/billing/receipts/89/admin-alert-result",
            "json": {"is_sent": False, "error_text": "send failed"},
            "timeout": 30.0,
        }
    ]


def test_bot_api_client_propagates_transport_status_errors() -> None:
    request = httpx.Request("POST", "https://api.local/api/v1/action")
    response = httpx.Response(500, request=request)
    error = httpx.HTTPStatusError("server error", request=request, response=response)
    transport = FakeTransport([error])
    client = BotApiClient("https://api.local", transport=transport)

    try:
        asyncio.run(client.dispatch_reminders())
    except httpx.HTTPStatusError as raised:
        assert raised.response.status_code == 500
    else:  # pragma: no cover
        raise AssertionError("HTTPStatusError was expected")
