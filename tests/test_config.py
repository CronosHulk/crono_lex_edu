from __future__ import annotations

from app.config import load_settings


def test_load_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("DB_NAME", "cronolex")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "password")
    monkeypatch.setenv("APP__HOST", "127.0.0.1")
    monkeypatch.setenv("APP__PORT", "8100")
    monkeypatch.setenv("APP__BOT_ENABLED", "false")
    monkeypatch.setenv("APP__BOT_MESSAGE_CLEANUP_POLL_MINUTES", "45")
    monkeypatch.setenv("APP__BOT_MESSAGE_CLEANUP_POLL_SECONDS", "5")
    monkeypatch.setenv("APP__BOT_MESSAGE_RETENTION_DAYS", "20")
    monkeypatch.setenv("APP__DB_POOL_MIN_SIZE", "3")
    monkeypatch.setenv("APP__DB_POOL_MAX_SIZE", "9")
    monkeypatch.setenv("APP__API_WORKERS", "4")
    monkeypatch.setenv("APP__WEB_BASE_URL", "https://cronolex.local")
    monkeypatch.setenv("APP__BOT_WEBHOOK_LISTEN_HOST", "127.0.0.1")
    monkeypatch.setenv("APP__BOT_WEBHOOK_PORT", "9090")
    monkeypatch.setenv("APP__BOT_WEBHOOK_PATH", "/telegram/custom-webhook/")
    monkeypatch.setenv("APP__BOT_WEBHOOK_URL", "https://cronolex.local/telegram/custom-webhook")
    monkeypatch.setenv("APP__BOT_WEBHOOK_SECRET_TOKEN", "secret-token")
    monkeypatch.setenv("APP__WORD_COOLDOWN_DAYS", "5")
    monkeypatch.setenv("APP__REVIEW_MIX_PERCENT", "25")
    monkeypatch.setenv("APP__USER_IMPORT_AUDIO_DIR", "word_base/user")
    monkeypatch.setenv("APP__DICTIONARY_AUDIO_DIR", "word_base/base")
    monkeypatch.setenv("APP__USER_IMPORT_MAX_WORDS_PER_BIND", "100")
    monkeypatch.setenv("APP__USER_IMPORT_AUDIO_BUILD_HOUR", "10")
    monkeypatch.setenv("APP__USER_IMPORT_TEST_MODE", "true")
    monkeypatch.setenv("APP__USER_IMPORT_WORD_DETAILS_PROVIDER", "openai")
    monkeypatch.setenv("APP__USER_IMPORT_WORD_AUDIO_PROVIDER", "google_tts")
    monkeypatch.setenv("APP__AUDIO_STORAGE_PROVIDER", "filesystem")
    monkeypatch.setenv("APP__USER_IMPORT_GOOGLE_TTS_LANGUAGE_CODE", "en-US")
    monkeypatch.setenv("APP__USER_IMPORT_GOOGLE_TTS_VOICE_NAME", "en-US-Neural2-F")
    monkeypatch.setenv("APP__USER_IMPORT_OPENAI_REFINE_ENABLED", "true")
    monkeypatch.setenv("APP__USER_IMPORT_OPENAI_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("APP__USER_IMPORT_OPENAI_API_URL", "https://api.openai.com/v1/responses")

    settings = load_settings()

    assert settings.bot_token == "token"
    assert settings.db_name == "cronolex"
    assert settings.db_user == "user"
    assert settings.db_password == "password"
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8100
    assert settings.app_bot_enabled is False
    assert settings.app_bot_message_cleanup_poll_minutes == 45
    assert settings.app_bot_message_cleanup_poll_seconds == 5
    assert settings.app_bot_message_retention_days == 20
    assert settings.app_db_pool_min_size == 3
    assert settings.app_db_pool_max_size == 9
    assert settings.app_api_workers == 4
    assert settings.app_web_base_url == "https://cronolex.local"
    assert settings.app_bot_webhook_listen_host == "127.0.0.1"
    assert settings.app_bot_webhook_port == 9090
    assert settings.app_bot_webhook_path == "/telegram/custom-webhook/"
    assert settings.app_bot_webhook_url == "https://cronolex.local/telegram/custom-webhook"
    assert settings.app_bot_webhook_secret_token == "secret-token"
    assert settings.app_word_cooldown_days == 5
    assert settings.app_review_mix_percent == 25
    assert settings.app_user_import_audio_dir == "word_base/user"
    assert settings.app_dictionary_audio_dir == "word_base/base"
    assert settings.app_user_import_max_words_per_bind == 100
    assert settings.app_user_import_audio_build_hour == 10
    assert settings.app_user_import_test_mode is True
    assert settings.app_user_import_word_details_provider == "openai"
    assert settings.app_user_import_word_audio_provider == "google_tts"
    assert settings.app_audio_storage_provider == "filesystem"
    assert settings.app_user_import_google_tts_language_code == "en-US"
    assert settings.app_user_import_google_tts_voice_name == "en-US-Neural2-F"
    assert settings.app_user_import_openai_refine_enabled is True
    assert settings.app_user_import_openai_model == "gpt-5.4-mini"
    assert settings.app_user_import_openai_api_url == "https://api.openai.com/v1/responses"


def test_load_settings_allows_missing_bot_token(monkeypatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("DB_NAME", "cronolex")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "password")

    settings = load_settings()

    assert settings.bot_token == ""


def set_required_settings(monkeypatch) -> None:
    monkeypatch.setenv("DB_NAME", "cronolex")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "password")


def test_load_settings_reads_from_env_file_variables(monkeypatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    project_env_content = """
    BOT_TOKEN=token-from-env-var
    DB_NAME=db-from-env-var
    """
    app_env_content = """
    DB_USER=user-from-env-var
    DB_PASSWORD=password-from-env-var
    """

    monkeypatch.setenv("PROJECT_ENV_FILE", project_env_content)
    monkeypatch.setenv("APP_ENV_FILE", app_env_content)

    settings = load_settings()

    assert settings.bot_token == "token-from-env-var"
    assert settings.db_name == "db-from-env-var"
    assert settings.db_user == "user-from-env-var"
    assert settings.db_password == "password-from-env-var"

