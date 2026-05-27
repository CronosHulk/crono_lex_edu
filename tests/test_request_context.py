from __future__ import annotations

from fastapi import Request

from app.api_helpers.request_context import build_request_context


def test_build_request_context_prefers_forwarded_origin_and_client_ip() -> None:
    request = _request(
        path="/api/v1/auth/login",
        headers={
            "host": "internal.local",
            "user-agent": "pytest-agent",
            "x-forwarded-for": "198.51.100.10, 198.51.100.11",
            "x-forwarded-host": "api.cronolex.test",
            "x-forwarded-proto": "https",
        },
    )

    context = build_request_context(request)

    assert context.api_origin == "https://api.cronolex.test"
    assert context.api_path == "/api/v1/auth/login"
    assert context.client_ip == "198.51.100.10"
    assert context.user_agent == "pytest-agent"


def test_build_request_context_uses_real_ip_before_socket_client() -> None:
    request = _request(
        headers={
            "host": "api.cronolex.test",
            "x-real-ip": "203.0.113.24",
        },
        client_host="10.0.0.12",
    )

    context = build_request_context(request)

    assert context.api_origin == "http://api.cronolex.test"
    assert context.client_ip == "203.0.113.24"


def _request(
    *,
    headers: dict[str, str],
    path: str = "/api/v1/ping",
    client_host: str = "203.0.113.9",
) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [
                (name.lower().encode("latin-1"), value.encode("latin-1"))
                for name, value in headers.items()
            ],
            "scheme": "http",
            "server": ("internal.local", 80),
            "client": (client_host, 12345),
        }
    )
