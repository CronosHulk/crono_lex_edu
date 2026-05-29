from __future__ import annotations

from pathlib import Path


def test_production_compose_runs_billing_workers() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "  app-billing-reconciliation:" in compose
    assert 'command: ["python", "-m", "app.billing_reconciliation_worker_main"]' in compose
    assert "  app-subscription-maintenance:" in compose
    assert 'command: ["python", "-m", "app.subscription_maintenance_worker_main"]' in compose


def test_production_routes_telegram_webhook_to_bot_service() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    caddyfile = Path("Caddyfile").read_text(encoding="utf-8")
    app_env = Path("app.env").read_text(encoding="utf-8")
    app_bot_start = compose.index("\n  app-bot:") + 1
    app_import_scheduler_start = compose.index("\n  app-import-scheduler:")
    app_bot_block = compose[app_bot_start:app_import_scheduler_start]
    webhook_env_names = (
        "APP__BOT_WEBHOOK_LISTEN_HOST",
        "APP__BOT_WEBHOOK_PORT",
        "APP__BOT_WEBHOOK_PATH",
        "APP__BOT_WEBHOOK_URL",
    )

    assert "handle /telegram/webhook" in caddyfile
    assert "reverse_proxy app-bot:8080" in caddyfile
    assert 'expose:\n      - "8080"' in app_bot_block
    assert "env_file:\n      - app.env\n      - project.env" in app_bot_block
    assert "APP__BOT_ENABLED=true" in app_env
    assert "APP__BOT_ENABLED:" not in app_bot_block
    for env_name in webhook_env_names:
        assert f"{env_name}=" in app_env
        assert f"{env_name}:" not in app_bot_block


def test_telegram_webhook_secret_stays_in_project_env_example_only() -> None:
    secret_assignment = "APP__BOT_WEBHOOK_SECRET_TOKEN=replace_me"

    assert secret_assignment in Path("project.env.example").read_text(encoding="utf-8")
    assert "APP__BOT_WEBHOOK_SECRET_TOKEN" not in Path("app.env").read_text(encoding="utf-8")
    assert "APP__BOT_WEBHOOK_SECRET_TOKEN" not in Path("app.env.example").read_text(encoding="utf-8")


def test_local_compose_disabled_bot_does_not_inherit_restart_policy() -> None:
    compose = Path("docker-compose.local.yml").read_text(encoding="utf-8")
    app_api_block = compose[compose.index("  app-api:") : compose.index("  app-bot:")]
    app_bot_block = compose[compose.index("  app-bot:") : compose.index("  app-import-scheduler:")]
    app_import_scheduler_block = compose[compose.index("  app-import-scheduler:") :]

    assert "APP__BOT_ENABLED: \"false\"" in app_bot_block
    assert 'restart: "no"' in app_bot_block
    assert "restart:" not in app_api_block
    assert "restart:" not in app_import_scheduler_block


def test_gitlab_deploy_builds_default_compose_app_services_before_no_build_up() -> None:
    pipeline = Path(".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "gcloud run deploy" in pipeline
    assert "gcloud run jobs deploy" in pipeline
    assert "app-video-worker" not in pipeline
    assert "app-video-publishing-worker" not in pipeline
    assert "app-video-publishing-scheduler" not in pipeline


def test_gitlab_deploy_keeps_freshly_built_images_before_no_build_up() -> None:
    pipeline = Path(".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "docker build" in pipeline
    assert "docker push" in pipeline
    assert "docker build -f Dockerfile.embeddings" in pipeline


def test_production_compose_does_not_connect_video_pipeline_workers() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "app-video-worker" not in compose
    assert "app-video-publishing-worker" not in compose
    assert "app-video-publishing-scheduler" not in compose
    assert "APP__VIDEO_PIPELINE" not in compose
    assert "video_pipeline." not in compose


def test_user_dictionary_rejected_status_is_allowed_by_schema() -> None:
    init_schema = Path("migrations/001_init.sql").read_text(encoding="utf-8")
    model = Path("app/models/dictionary.py").read_text(encoding="utf-8")

    assert "'rejected'" in init_schema
    assert "'rejected'" in model


def test_production_compose_runs_database_backup_worker() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    script = Path("scripts/database_backup.sh").read_text(encoding="utf-8")

    assert "  app-database-backup:" in compose
    assert "image: pgvector/pgvector:pg16" in compose
    assert "./database_backup:/backup" in compose
    assert "./scripts/database_backup.sh:/usr/local/bin/cronolex-database-backup:ro" in compose
    assert 'command: ["cronolex-database-backup"]' in compose
    assert "database_backup/" in ignore
    assert "pg_dump" in script
    assert "openssl enc -aes-256-cbc" in script
