from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.encoders import ENCODERS_BY_TYPE
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.admin_api.error_logging import admin_request_validation_exception_handler
from app.api import build_api_router
from app.api_error_logging import api_http_exception_handler, api_unhandled_exception_handler
from app.composition.root import build_database, build_learning_runtime
from app.config import Settings, load_settings
from app.json_serialization import ProjectDateTimeJSONMiddleware
from app.time_utils import TimeService, format_project_datetime


def configure_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    app_settings = settings or load_settings()
    ENCODERS_BY_TYPE[datetime] = lambda value: format_project_datetime(value, app_settings.app_timezone)
    db = build_database(app_settings)
    time_service = TimeService(app_settings.app_timezone)
    service = build_learning_runtime(db, time_service)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        db.connect()
        db.run_migrations()
        try:
            yield
        finally:
            db.close()

    app = FastAPI(title="CronoLex API", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.db = db
    app.state.time_service = time_service
    app.state.learning_service = service
    app.add_exception_handler(RequestValidationError, admin_request_validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, api_http_exception_handler)
    app.add_exception_handler(Exception, api_unhandled_exception_handler)
    app.add_middleware(ProjectDateTimeJSONMiddleware, timezone_name=app_settings.app_timezone)
    app.include_router(build_api_router(service))
    return app
