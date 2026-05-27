from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.testclient import TestClient

import app.main as main_module
from app.config import Settings
from app.main import create_app


def build_settings() -> Settings:
    return Settings(
        bot_token="token",
        db_host="localhost",
        db_port=5432,
        db_name="cronolex",
        db_user="user",
        db_password="password",
        app_env="test",
        app_timezone="Europe/Kyiv",
        app_host="127.0.0.1",
        app_port=8000,
        app_api_base_url="http://127.0.0.1:8000",
        app_bot_enabled=False,
        app_bot_reminder_poll_minutes=5,
        app_bot_message_cleanup_poll_minutes=60,
        app_bot_message_retention_days=30,
        app_db_pool_min_size=4,
        app_db_pool_max_size=20,
        app_api_workers=1,
        app_word_cooldown_days=2,
        app_review_mix_percent=30,
    )


def test_create_app_registers_api_routes() -> None:
    app = create_app(build_settings())

    assert any(route.path == "/api/v1/health" for route in app.routes)


def test_create_app_stores_runtime_dependencies() -> None:
    app = create_app(build_settings())

    assert app.state.settings.app_api_workers == 1
    assert app.state.db is not None
    assert app.state.time_service is not None
    assert app.state.learning_service is not None


def test_create_app_wires_learning_runtime_factory(monkeypatch) -> None:
    settings = build_settings()
    expected_runtime = object()
    calls: dict[str, object] = {}

    class StubDatabase:
        def __init__(self, received_settings: Settings) -> None:
            calls["db_settings"] = received_settings

    class StubTimeService:
        def __init__(self, timezone_name: str) -> None:
            calls["timezone_name"] = timezone_name

    def stub_build_learning_runtime(
        db: StubDatabase,
        time_service: StubTimeService,
    ) -> object:
        calls["factory_db"] = db
        calls["factory_time_service"] = time_service
        return expected_runtime

    def stub_build_api_router(runtime: object) -> APIRouter:
        calls["router_runtime"] = runtime
        return APIRouter()

    def stub_build_database(received_settings: Settings) -> StubDatabase:
        return StubDatabase(received_settings)

    monkeypatch.setattr(main_module, "build_database", stub_build_database)
    monkeypatch.setattr(main_module, "TimeService", StubTimeService)
    monkeypatch.setattr(main_module, "build_learning_runtime", stub_build_learning_runtime)
    monkeypatch.setattr(main_module, "build_api_router", stub_build_api_router)

    app = create_app(settings)

    assert calls["db_settings"] is settings
    assert calls["timezone_name"] == "Europe/Kyiv"
    assert calls["factory_db"] is app.state.db
    assert calls["factory_time_service"] is app.state.time_service
    assert calls["router_runtime"] is expected_runtime
    assert app.state.db is not None
    assert app.state.time_service is not None
    assert app.state.learning_service is expected_runtime


def test_create_app_lifespan_runs_runtime_startup_shutdown_in_order(monkeypatch) -> None:
    settings = build_settings()
    calls: list[str] = []

    class StubDatabase:
        def __init__(self, received_settings: Settings) -> None:
            self.settings = received_settings

        def connect(self) -> None:
            calls.append("db.connect")

        def run_migrations(self) -> None:
            calls.append("db.migrate")

        def close(self) -> None:
            calls.append("db.close")

    class StubTimeService:
        def __init__(self, timezone_name: str) -> None:
            self.timezone_name = timezone_name

    def stub_build_learning_runtime(
        db: StubDatabase,
        time_service: StubTimeService,
    ) -> object:
        return object()

    def stub_build_api_router(runtime: object) -> APIRouter:
        return APIRouter()

    def stub_build_database(received_settings: Settings) -> StubDatabase:
        return StubDatabase(received_settings)

    monkeypatch.setattr(main_module, "build_database", stub_build_database)
    monkeypatch.setattr(main_module, "TimeService", StubTimeService)
    monkeypatch.setattr(main_module, "build_learning_runtime", stub_build_learning_runtime)
    monkeypatch.setattr(main_module, "build_api_router", stub_build_api_router)

    app = create_app(settings)

    with TestClient(app):
        assert calls == ["db.connect", "db.migrate"]

    assert calls == [
        "db.connect",
        "db.migrate",
        "db.close",
    ]


def test_create_app_serializes_datetime_in_project_format() -> None:
    app = create_app(build_settings())

    @app.get("/probe")
    def probe() -> dict[str, datetime]:
        return {"created": datetime(2026, 12, 1, 0, 1, 2, tzinfo=UTC)}

    response = TestClient(app).get("/probe")

    assert response.json() == {"created": "2026-12-01 02:01:02"}
