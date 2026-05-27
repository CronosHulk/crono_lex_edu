from __future__ import annotations

from pathlib import Path

from app.data_access.schema_migrations import MIGRATIONS_ADVISORY_LOCK_KEY, run_schema_migrations


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalars(self):
        return self


class FakeMigrationConnection:
    def __init__(self, *, applied_versions=None) -> None:
        self.applied_versions = list(applied_versions or [])
        self.calls: list[tuple[str, dict | None]] = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params))
        if "SELECT version FROM schema_migrations" in sql:
            return FakeScalarsResult(self.applied_versions)
        return FakeScalarsResult([])


class FakeMigrationBeginContext:
    def __init__(self, connection: FakeMigrationConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeMigrationConnection:
        return self.connection

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FakeMigrationEngine:
    def __init__(self, connection: FakeMigrationConnection) -> None:
        self.connection = connection

    def begin(self) -> FakeMigrationBeginContext:
        return FakeMigrationBeginContext(self.connection)


def test_run_schema_migrations_acquires_lock_and_applies_unseen_files(tmp_path: Path) -> None:
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    (migration_dir / "001_done.sql").write_text("SELECT 1;", encoding="utf-8")
    (migration_dir / "002_new.sql").write_text("SELECT 2;", encoding="utf-8")
    connection = FakeMigrationConnection(applied_versions=["001_done.sql"])

    run_schema_migrations(
        FakeMigrationEngine(connection),
        app_timezone="Europe/Kyiv",
        migrations_dir=migration_dir,
    )

    assert "pg_advisory_xact_lock" in connection.calls[0][0]
    assert connection.calls[0][1] == {"lock_key": MIGRATIONS_ADVISORY_LOCK_KEY}
    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in connection.calls[1][0]
    assert "SELECT version FROM schema_migrations" in connection.calls[2][0]
    assert connection.calls[3][1] == {"tz": "Europe/Kyiv"}
    assert any("SELECT 2" in sql for sql, _ in connection.calls)
    assert not any("SELECT 1" in sql for sql, _ in connection.calls)
    assert connection.calls[-1][1] == {"version": "002_new.sql"}
