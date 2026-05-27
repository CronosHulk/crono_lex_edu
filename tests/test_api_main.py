from __future__ import annotations

from app.api_main import main
from app.config import Settings


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
        app_api_workers=3,
        app_word_cooldown_days=2,
        app_review_mix_percent=30,
    )


def test_api_main_runs_uvicorn_with_workers(monkeypatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr("app.api_main.load_settings", build_settings)
    monkeypatch.setattr("app.api_main.uvicorn.run", lambda *args, **kwargs: captured.update({"args": args, "kwargs": kwargs}))

    main()

    assert captured["args"] == ("app.main:create_app",)
    assert captured["kwargs"]["factory"] is True
    assert captured["kwargs"]["workers"] == 3
