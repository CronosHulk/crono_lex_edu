from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api_error_logging import (
    api_http_exception_handler,
    api_unhandled_exception_handler,
    sanitize_error_text,
)


class FakeDb:
    def __init__(self) -> None:
        self.error_logs = FakeErrorLogRepository()


class FakeErrorLogRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create(self, level, text, *, context_json=None) -> None:
        self.rows.append({"level": level, "text": text, "context_json": context_json})


def build_app(fake_db: FakeDb) -> FastAPI:
    app = FastAPI()
    app.state.db = fake_db
    app.add_exception_handler(StarletteHTTPException, api_http_exception_handler)
    app.add_exception_handler(Exception, api_unhandled_exception_handler)
    return app


def test_unhandled_api_exception_is_logged() -> None:
    fake_db = FakeDb()
    app = build_app(fake_db)

    @app.post("/api/v1/client-web/imports")
    def probe() -> dict[str, str]:
        raise RuntimeError("provider exploded?api_key=secret")

    response = TestClient(app, raise_server_exceptions=False).post("/api/v1/client-web/imports")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert fake_db.error_logs.rows[0]["level"] == "fatal"
    assert fake_db.error_logs.rows[0]["context_json"] == {
        "route": "/api/v1/client-web/imports",
        "method": "POST",
        "status_code": 500,
        "error_type": "RuntimeError",
        "detail": "provider exploded?api_key=[redacted]",
    }
    assert "RuntimeError: provider exploded?api_key=[redacted]" in fake_db.error_logs.rows[0]["text"][-1]
    assert "secret" not in str(fake_db.error_logs.rows)


def test_http_5xx_api_exception_is_logged_with_detail() -> None:
    fake_db = FakeDb()
    app = build_app(fake_db)

    @app.post("/api/v1/client-web/imports")
    def probe() -> dict[str, str]:
        raise HTTPException(status_code=502, detail="AI import validation failed (HTTP 500)")

    response = TestClient(app).post("/api/v1/client-web/imports")

    assert response.status_code == 502
    assert response.json() == {"detail": "AI import validation failed (HTTP 500)"}
    assert fake_db.error_logs.rows[0]["context_json"] == {
        "route": "/api/v1/client-web/imports",
        "method": "POST",
        "status_code": 502,
        "error_type": "HTTPException",
        "detail": "AI import validation failed (HTTP 500)",
    }


def test_http_4xx_api_exception_is_not_logged() -> None:
    fake_db = FakeDb()
    app = build_app(fake_db)

    @app.post("/api/v1/client-web/imports")
    def probe() -> dict[str, str]:
        raise HTTPException(status_code=400, detail="Bad import")

    response = TestClient(app).post("/api/v1/client-web/imports")

    assert response.status_code == 400
    assert fake_db.error_logs.rows == []


def test_sanitize_error_text_redacts_common_secret_shapes() -> None:
    value = "url?token=secret Authorization: Bearer abc123 DeepL-Auth-Key deepl-secret"

    assert sanitize_error_text(value) == "url?token=[redacted] Authorization: Bearer [redacted] DeepL-Auth-Key [redacted]"
