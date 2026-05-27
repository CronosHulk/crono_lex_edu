from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


def build_database_url(settings: Settings) -> str:
    return (
        f"postgresql+psycopg://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


class SessionManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    def connect(self) -> None:
        if self._engine is not None:
            return
        self._engine = create_engine(
            build_database_url(self.settings),
            pool_pre_ping=True,
            pool_size=self.settings.app_db_pool_max_size,
            max_overflow=0,
            future=True,
        )
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False, future=True)

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

    def run_migrations(self) -> None:
        from app.data_access.schema_migrations import run_schema_migrations
        run_schema_migrations(self.engine, app_timezone=self.settings.app_timezone)

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            raise RuntimeError("Database engine is not initialized")
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        if self._session_factory is None:
            raise RuntimeError("Session factory is not initialized")
        return self._session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            session.execute(text("SELECT set_config('TimeZone', :tz, false)"), {"tz": self.settings.app_timezone})
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
