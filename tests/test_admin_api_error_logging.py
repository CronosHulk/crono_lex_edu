from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.admin_api.error_logging import (
    admin_request_validation_exception_handler,
    sanitize_validation_errors,
)


class FakeDb:
    def __init__(self) -> None:
        self.error_logs = FakeErrorLogRepository()


class FakeErrorLogRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def create(self, level, text, *, context_json=None) -> None:
        self.rows.append({"level": level, "text": text, "context_json": context_json})


class ProbePayload(BaseModel):
    challenge_id: int = Field(gt=0)
    otp: str = Field(min_length=6)


def test_admin_validation_errors_are_logged_without_request_body() -> None:
    app = FastAPI()
    fake_db = FakeDb()
    app.state.db = fake_db
    app.add_exception_handler(RequestValidationError, admin_request_validation_exception_handler)

    @app.delete("/api/v1/admin/settings/import-data")
    def probe(payload: ProbePayload) -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).request("DELETE", "/api/v1/admin/settings/import-data", json={"otp": "123"})

    assert response.status_code == 422
    assert fake_db.error_logs.rows == [
        {
            "level": "warn",
            "text": [
                "route=/api/v1/admin/settings/import-data",
                "method=DELETE",
                "status_code=422",
                "error_type=RequestValidationError",
            ],
            "context_json": {
                "route": "/api/v1/admin/settings/import-data",
                "method": "DELETE",
                "status_code": 422,
                "validation_errors": [
                    {"loc": "body.challenge_id", "msg": "Field required", "type": "missing"},
                    {
                        "loc": "body.otp",
                        "msg": "String should have at least 6 characters",
                        "type": "string_too_short",
                    },
                ],
            },
        }
    ]
    assert "123" not in str(fake_db.error_logs.rows)


def test_non_admin_validation_errors_are_not_logged() -> None:
    app = FastAPI()
    fake_db = FakeDb()
    app.state.db = fake_db
    app.add_exception_handler(RequestValidationError, admin_request_validation_exception_handler)

    @app.post("/api/v1/client/probe")
    def probe(payload: ProbePayload) -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).post("/api/v1/client/probe", json={"otp": "123"})

    assert response.status_code == 422
    assert fake_db.error_logs.rows == []


def test_sanitize_validation_errors_limits_count_and_lengths() -> None:
    errors = [{"loc": ["body", f"field_{index}"], "msg": "x" * 400, "type": "value_error"} for index in range(25)]

    result = sanitize_validation_errors(errors)

    assert len(result) == 20
    assert result[0]["loc"] == "body.field_0"
    assert len(result[0]["msg"]) == 300
