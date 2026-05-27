from __future__ import annotations

import os
from dataclasses import dataclass

from app.domain.provider_settings import (
    DEFAULT_OPENAI_API_URL,
    DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
    DEFAULT_USER_IMPORT_OPENAI_MODEL,
)
from app.reference.telegram_timing import (
    TELEGRAM_LONG_WAIT_MINUTES,
    TELEGRAM_SCHEDULER_INTERVAL_MINUTES,
)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    app_env: str
    app_timezone: str
    app_host: str
    app_port: int
    app_api_base_url: str = "http://127.0.0.1:8000"
    app_web_base_url: str = "https://cronolex.uno"
    app_bot_username: str = ""
    app_bot_enabled: bool = True
    app_bot_webhook_listen_host: str = "0.0.0.0"
    app_bot_webhook_port: int = 8080
    app_bot_webhook_path: str = "telegram/webhook"
    app_bot_webhook_url: str = ""
    app_bot_webhook_secret_token: str = ""
    app_bot_reminder_poll_minutes: int = TELEGRAM_SCHEDULER_INTERVAL_MINUTES
    app_bot_message_cleanup_poll_minutes: int = 60
    app_bot_message_cleanup_poll_seconds: int = 10
    app_bot_user_import_poll_minutes: int = 60
    app_bot_message_retention_days: int = 30
    app_db_pool_min_size: int = 4
    app_db_pool_max_size: int = 20
    app_api_workers: int = 1
    app_word_cooldown_days: int = 2
    app_review_mix_percent: int = 30
    app_user_import_storage_dir: str = "runtime/user_vocabulary_imports"
    app_user_import_audio_dir: str = "word_base/user"
    app_dictionary_audio_dir: str = "word_base/base"
    app_exercise_text_audio_dir: str = "word_base/exercise_texts/audio"
    app_billing_receipt_storage_dir: str = "runtime/billing_receipts"
    app_audio_storage_provider: str = "filesystem"
    app_user_import_max_words_per_bind: int = 100
    app_user_import_wordnik_limit_per_run: int = 90
    app_user_import_audio_build_hour: int = 10
    app_user_import_embedding_build_hour: int = 11
    app_user_import_test_mode: bool = False
    app_user_import_word_details_provider: str = "openai"
    app_user_import_word_audio_provider: str = "google_tts"
    app_user_import_google_tts_language_code: str = "en-US"
    app_user_import_google_tts_voice_name: str = "en-US-Neural2-F"
    app_user_import_openai_refine_enabled: bool = True
    app_user_import_openai_model: str = DEFAULT_USER_IMPORT_OPENAI_MODEL
    app_user_import_openai_api_url: str = DEFAULT_OPENAI_API_URL
    app_user_import_embeddings_model: str = DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL
    app_user_import_embeddings_device: str = "cpu"
    app_google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_token_secret: str = ""
    app_google_oauth_redirect_uri: str = ""
    app_admin_dev_login_enabled: bool = False
    app_admin_cookie_secure: bool = True
    app_admin_session_hours: int = 12
    app_admin_otp_ttl_minutes: int = 5
    app_admin_magic_link_ttl_minutes: int = TELEGRAM_LONG_WAIT_MINUTES
    app_internal_api_token: str = ""
    monobank_token_test: str = ""
    monobank_token: str = ""


def load_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.environ["DB_NAME"],
        db_user=os.environ["DB_USER"],
        db_password=os.environ["DB_PASSWORD"],
        app_env=os.getenv("APP__ENV", "development"),
        app_timezone=os.getenv("APP__TIMEZONE", "Europe/Kyiv"),
        app_host=os.getenv("APP__HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP__PORT", "8000")),
        app_api_base_url=os.getenv("APP__API_BASE_URL", "http://127.0.0.1:8000"),
        app_web_base_url=os.getenv("APP__WEB_BASE_URL", "https://cronolex.uno"),
        app_bot_username=os.getenv("APP__BOT_USERNAME", ""),
        app_bot_enabled=os.getenv("APP__BOT_ENABLED", "true").lower() == "true",
        app_bot_webhook_listen_host=os.getenv("APP__BOT_WEBHOOK_LISTEN_HOST", "0.0.0.0"),
        app_bot_webhook_port=int(os.getenv("APP__BOT_WEBHOOK_PORT", "8080")),
        app_bot_webhook_path=os.getenv("APP__BOT_WEBHOOK_PATH", "telegram/webhook"),
        app_bot_webhook_url=os.getenv("APP__BOT_WEBHOOK_URL", ""),
        app_bot_webhook_secret_token=os.getenv("APP__BOT_WEBHOOK_SECRET_TOKEN", ""),
        app_bot_reminder_poll_minutes=int(
            os.getenv("APP__BOT_REMINDER_POLL_MINUTES", str(TELEGRAM_SCHEDULER_INTERVAL_MINUTES))
        ),
        app_bot_message_cleanup_poll_minutes=int(os.getenv("APP__BOT_MESSAGE_CLEANUP_POLL_MINUTES", "60")),
        app_bot_message_cleanup_poll_seconds=int(os.getenv("APP__BOT_MESSAGE_CLEANUP_POLL_SECONDS", "10")),
        app_bot_user_import_poll_minutes=int(os.getenv("APP__BOT_USER_IMPORT_POLL_MINUTES", "60")),
        app_bot_message_retention_days=int(os.getenv("APP__BOT_MESSAGE_RETENTION_DAYS", "30")),
        app_db_pool_min_size=int(os.getenv("APP__DB_POOL_MIN_SIZE", "4")),
        app_db_pool_max_size=int(os.getenv("APP__DB_POOL_MAX_SIZE", "20")),
        app_api_workers=int(os.getenv("APP__API_WORKERS", "1")),
        app_word_cooldown_days=int(os.getenv("APP__WORD_COOLDOWN_DAYS", "2")),
        app_review_mix_percent=int(os.getenv("APP__REVIEW_MIX_PERCENT", "30")),
        app_user_import_storage_dir=os.getenv("APP__USER_IMPORT_STORAGE_DIR", "runtime/user_vocabulary_imports"),
        app_user_import_audio_dir=os.getenv("APP__USER_IMPORT_AUDIO_DIR", "word_base/user"),
        app_dictionary_audio_dir=os.getenv("APP__DICTIONARY_AUDIO_DIR", "word_base/base"),
        app_exercise_text_audio_dir=os.getenv("APP__EXERCISE_TEXT_AUDIO_DIR", "word_base/exercise_texts/audio"),
        app_billing_receipt_storage_dir=os.getenv(
            "APP__BILLING_RECEIPT_STORAGE_DIR",
            "runtime/billing_receipts",
        ),
        app_audio_storage_provider=os.getenv("APP__AUDIO_STORAGE_PROVIDER", "filesystem"),
        app_user_import_max_words_per_bind=int(os.getenv("APP__USER_IMPORT_MAX_WORDS_PER_BIND", "100")),
        app_user_import_wordnik_limit_per_run=int(os.getenv("APP__USER_IMPORT_WORDNIK_LIMIT_PER_RUN", "90")),
        app_user_import_audio_build_hour=int(os.getenv("APP__USER_IMPORT_AUDIO_BUILD_HOUR", "10")),
        app_user_import_embedding_build_hour=int(os.getenv("APP__USER_IMPORT_EMBEDDING_BUILD_HOUR", "11")),
        app_user_import_test_mode=os.getenv("APP__USER_IMPORT_TEST_MODE", "false").lower() == "true",
        app_user_import_word_details_provider=os.getenv("APP__USER_IMPORT_WORD_DETAILS_PROVIDER", "openai"),
        app_user_import_word_audio_provider=os.getenv("APP__USER_IMPORT_WORD_AUDIO_PROVIDER", "google_tts"),
        app_user_import_google_tts_language_code=os.getenv("APP__USER_IMPORT_GOOGLE_TTS_LANGUAGE_CODE", "en-US"),
        app_user_import_google_tts_voice_name=os.getenv("APP__USER_IMPORT_GOOGLE_TTS_VOICE_NAME", "en-US-Neural2-F"),
        app_user_import_openai_refine_enabled=os.getenv("APP__USER_IMPORT_OPENAI_REFINE_ENABLED", "true").lower()
        == "true",
        app_user_import_openai_model=os.getenv("APP__USER_IMPORT_OPENAI_MODEL", DEFAULT_USER_IMPORT_OPENAI_MODEL),
        app_user_import_openai_api_url=os.getenv(
            "APP__USER_IMPORT_OPENAI_API_URL",
            DEFAULT_OPENAI_API_URL,
        ),
        app_user_import_embeddings_model=os.getenv(
            "APP__USER_IMPORT_EMBEDDINGS_MODEL",
            DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
        ),
        app_user_import_embeddings_device=os.getenv("APP__USER_IMPORT_EMBEDDINGS_DEVICE", "cpu"),
        app_google_oauth_client_id=os.getenv("APP__GOOGLE_OAUTH_CLIENT_ID", ""),
        google_oauth_client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        google_oauth_token_secret=os.getenv("GOOGLE_OAUTH_TOKEN_SECRET", ""),
        app_google_oauth_redirect_uri=os.getenv("APP__GOOGLE_OAUTH_REDIRECT_URI", ""),
        app_admin_dev_login_enabled=os.getenv("APP__ADMIN_DEV_LOGIN_ENABLED", "false").lower() == "true",
        app_admin_cookie_secure=os.getenv("APP__ADMIN_COOKIE_SECURE", "true").lower() == "true",
        app_admin_session_hours=int(os.getenv("APP__ADMIN_SESSION_HOURS", "12")),
        app_admin_otp_ttl_minutes=int(os.getenv("APP__ADMIN_OTP_TTL_MINUTES", "5")),
        app_admin_magic_link_ttl_minutes=int(
            os.getenv("APP__ADMIN_MAGIC_LINK_TTL_MINUTES", str(TELEGRAM_LONG_WAIT_MINUTES))
        ),
        app_internal_api_token=os.getenv("APP__INTERNAL_API_TOKEN", ""),
        monobank_token_test=os.getenv("MONOBANK_TOKEN_TEST", ""),
        monobank_token=os.getenv("MONOBANK_TOKEN", ""),
    )
