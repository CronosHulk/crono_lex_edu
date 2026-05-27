from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

MIGRATIONS_ADVISORY_LOCK_KEY = 2_025_041_100


def default_migrations_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "migrations"


def run_schema_migrations(
    engine,
    *,
    app_timezone: str,
    migrations_dir: Path | None = None,
) -> None:
    resolved_migrations_dir = migrations_dir or default_migrations_dir()
    migration_files = sorted(resolved_migrations_dir.glob("*.sql"))

    with engine.begin() as conn:
        conn.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": MIGRATIONS_ADVISORY_LOCK_KEY},
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        applied = set(conn.execute(text("SELECT version FROM schema_migrations")).scalars().all())
        conn.execute(text("SELECT set_config('TimeZone', :tz, false)"), {"tz": app_timezone})

        for migration_path in migration_files:
            if migration_path.name in applied:
                continue
            content = migration_path.read_text(encoding="utf-8")
            # Filter out backslash-prefixed system annotations (e.g., \restrict)
            clean_lines = [
                line for line in content.splitlines()
                if not line.strip().startswith("\\")
            ]
            conn.execute(text("\n".join(clean_lines)))
            conn.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": migration_path.name},
            )

