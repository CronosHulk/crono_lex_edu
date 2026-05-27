from __future__ import annotations

from dataclasses import replace

import pytest

from app.bot_main import build_webhook_url, main, normalize_webhook_path, run_webhook
from app.config import Settings

ALLOWED_UPDATES = ["message", "callback_query"]


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
        app_bot_enabled=True,
        app_bot_webhook_secret_token="secret-token",
        app_bot_reminder_poll_minutes=5,
        app_bot_message_cleanup_poll_minutes=60,
        app_bot_message_retention_days=30,
        app_db_pool_min_size=4,
        app_db_pool_max_size=20,
        app_api_workers=2,
        app_word_cooldown_days=2,
        app_review_mix_percent=30,
    )


class FakeApplication:
    def __init__(self) -> None:
        self.run_polling_kwargs: list[dict] = []
        self.run_webhook_kwargs: list[dict] = []

    def run_polling(self, **kwargs) -> None:
        self.run_polling_kwargs.append(kwargs)

    def run_webhook(self, **kwargs) -> None:
        self.run_webhook_kwargs.append(kwargs)


def test_bot_main_runs_webhook_by_default(monkeypatch) -> None:
    application = FakeApplication()
    audio_storage_provider = object()
    tokens: list[str] = []
    app_envs: list[str] = []
    audio_storage_providers: list[object] = []

    monkeypatch.setattr("app.bot_main.load_settings", build_settings)
    monkeypatch.setattr(
        "app.bot_main.build_audio_storage_provider",
        lambda _settings: audio_storage_provider,
    )

    def fake_build_application(api_client, token, settings, *, audio_storage_provider):
        tokens.append(token)
        app_envs.append(settings.app_env)
        audio_storage_providers.append(audio_storage_provider)
        return application

    monkeypatch.setattr(
        "app.bot_main.build_application",
        fake_build_application,
    )

    main([])

    assert application.run_polling_kwargs == []
    assert application.run_webhook_kwargs == [
        {
            "listen": "0.0.0.0",
            "port": 8080,
            "url_path": "telegram/webhook",
            "webhook_url": "https://cronolex.uno/telegram/webhook",
            "secret_token": "secret-token",
            "allowed_updates": ALLOWED_UPDATES,
        }
    ]
    assert tokens == ["token"]
    assert app_envs == ["test"]
    assert audio_storage_providers == [audio_storage_provider]


def test_bot_main_enabled_non_local_requires_webhook_secret_before_build(monkeypatch) -> None:
    application = FakeApplication()
    build_application_calls: list[tuple] = []

    monkeypatch.setattr(
        "app.bot_main.load_settings",
        lambda: replace(build_settings(), app_bot_webhook_secret_token=" "),
    )
    monkeypatch.setattr(
        "app.bot_main.build_application",
        lambda *args: build_application_calls.append(args) or application,
    )

    with pytest.raises(RuntimeError, match="APP__BOT_WEBHOOK_SECRET_TOKEN"):
        main([])

    assert build_application_calls == []
    assert application.run_polling_kwargs == []
    assert application.run_webhook_kwargs == []


def test_bot_main_enabled_non_local_requires_bot_token_before_build(monkeypatch) -> None:
    application = FakeApplication()
    build_application_calls: list[tuple] = []

    monkeypatch.setattr(
        "app.bot_main.load_settings",
        lambda: replace(build_settings(), bot_token=" "),
    )
    monkeypatch.setattr(
        "app.bot_main.build_application",
        lambda *args: build_application_calls.append(args) or application,
    )

    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        main([])

    assert build_application_calls == []
    assert application.run_polling_kwargs == []
    assert application.run_webhook_kwargs == []


def test_bot_main_exits_when_bot_is_disabled(monkeypatch) -> None:
    application = FakeApplication()
    build_application_calls: list[tuple] = []

    monkeypatch.setattr(
        "app.bot_main.load_settings",
        lambda: replace(
            build_settings(),
            app_bot_enabled=False,
            bot_token="",
            app_bot_webhook_secret_token="",
        ),
    )
    monkeypatch.setattr(
        "app.bot_main.build_application",
        lambda *args: build_application_calls.append(args) or application,
    )

    main([])

    assert build_application_calls == []
    assert application.run_polling_kwargs == []
    assert application.run_webhook_kwargs == []


def test_bot_main_local_flag_uses_local_bot_token_even_when_bot_is_disabled(monkeypatch) -> None:
    application = FakeApplication()
    audio_storage_provider = object()
    tokens: list[str] = []
    app_envs: list[str] = []
    audio_storage_providers: list[object] = []

    monkeypatch.setenv("LOCAL_BOT_TOKEN", "local-token")
    monkeypatch.setattr(
        "app.bot_main.load_settings",
        lambda: replace(build_settings(), app_bot_enabled=False),
    )
    monkeypatch.setattr(
        "app.bot_main.build_audio_storage_provider",
        lambda _settings: audio_storage_provider,
    )

    def fake_build_application(api_client, token, settings, *, audio_storage_provider):
        tokens.append(token)
        app_envs.append(settings.app_env)
        audio_storage_providers.append(audio_storage_provider)
        return application

    monkeypatch.setattr(
        "app.bot_main.build_application",
        fake_build_application,
    )

    main(["--local"])

    assert application.run_polling_kwargs == [{"allowed_updates": ALLOWED_UPDATES}]
    assert application.run_webhook_kwargs == []
    assert tokens == ["local-token"]
    assert app_envs == ["local"]
    assert audio_storage_providers == [audio_storage_provider]


def test_bot_main_local_flag_requires_local_bot_token(monkeypatch) -> None:
    monkeypatch.delenv("LOCAL_BOT_TOKEN", raising=False)
    monkeypatch.setattr("app.bot_main.load_settings", build_settings)

    try:
        main(["--local"])
    except RuntimeError as error:
        assert "LOCAL_BOT_TOKEN" in str(error)
    else:  # pragma: no cover
        raise AssertionError("Expected RuntimeError")


def test_bot_main_local_flag_uses_real_settings_without_bot_token(monkeypatch) -> None:
    application = FakeApplication()
    audio_storage_provider = object()
    tokens: list[str] = []
    app_envs: list[str] = []
    audio_storage_providers: list[object] = []

    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("APP__BOT_WEBHOOK_SECRET_TOKEN", raising=False)
    monkeypatch.setenv("LOCAL_BOT_TOKEN", "local-token")
    monkeypatch.setenv("DB_NAME", "cronolex")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "password")
    monkeypatch.setenv("APP__BOT_ENABLED", "true")
    monkeypatch.setattr(
        "app.bot_main.build_audio_storage_provider",
        lambda _settings: audio_storage_provider,
    )

    def fake_build_application(api_client, token, settings, *, audio_storage_provider):
        tokens.append(token)
        app_envs.append(settings.app_env)
        audio_storage_providers.append(audio_storage_provider)
        return application

    monkeypatch.setattr(
        "app.bot_main.build_application",
        fake_build_application,
    )

    main(["--local"])

    assert application.run_polling_kwargs == [{"allowed_updates": ALLOWED_UPDATES}]
    assert application.run_webhook_kwargs == []
    assert tokens == ["local-token"]
    assert app_envs == ["local"]
    assert audio_storage_providers == [audio_storage_provider]


def test_normalize_webhook_path_strips_outer_slashes_and_whitespace() -> None:
    assert normalize_webhook_path(" /telegram/webhook/ ") == "telegram/webhook"


def test_build_webhook_url_uses_configured_url_override() -> None:
    settings = replace(build_settings(), app_bot_webhook_url=" https://hooks.example.test/bot ")

    assert build_webhook_url(settings) == "https://hooks.example.test/bot"


def test_build_webhook_url_combines_base_url_and_normalized_path() -> None:
    settings = replace(
        build_settings(),
        app_web_base_url="https://cronolex.example/",
        app_bot_webhook_path="/telegram/webhook/",
    )

    assert build_webhook_url(settings) == "https://cronolex.example/telegram/webhook"


def test_run_webhook_passes_secret_token_when_configured() -> None:
    application = FakeApplication()
    settings = replace(build_settings(), app_bot_webhook_secret_token=" secret-token ")

    run_webhook(application, settings)

    assert application.run_webhook_kwargs == [
        {
            "listen": "0.0.0.0",
            "port": 8080,
            "url_path": "telegram/webhook",
            "webhook_url": "https://cronolex.uno/telegram/webhook",
            "secret_token": "secret-token",
            "allowed_updates": ALLOWED_UPDATES,
        }
    ]
    assert application.run_polling_kwargs == []
