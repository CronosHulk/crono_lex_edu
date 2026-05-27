from __future__ import annotations

import re
import traceback
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

MAX_ERROR_TEXT_CHARS = 8000
MAX_CONTEXT_VALUE_CHARS = 1000


async def api_http_exception_handler(request: Request, error: StarletteHTTPException) -> JSONResponse:
    if int(error.status_code) >= 500:
        log_api_error(
            request,
            error,
            status_code=int(error.status_code),
            detail=safe_string(error.detail),
        )
    return JSONResponse(status_code=int(error.status_code), content=jsonable_encoder({"detail": error.detail}))


async def api_unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
    log_api_error(request, error, status_code=500, detail=safe_string(error))
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


def log_api_error(
    request: Request,
    error: Exception,
    *,
    status_code: int,
    detail: str,
) -> None:
    db = getattr(request.app.state, "db", None)
    if db is None or not hasattr(db, "error_logs"):
        return
    error_type = type(error).__name__
    safe_detail = sanitize_error_text(detail)[:MAX_CONTEXT_VALUE_CHARS]
    safe_traceback = sanitize_error_text("".join(traceback.format_exception(type(error), error, error.__traceback__)))
    try:
        db.error_logs.create(
            "fatal",
            [
                f"route={request.url.path}",
                f"method={request.method}",
                f"status_code={status_code}",
                f"error_type={error_type}",
                f"detail={safe_detail}",
                safe_traceback[:MAX_ERROR_TEXT_CHARS],
            ],
            context_json={
                "route": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "error_type": error_type,
                "detail": safe_detail,
            },
        )
    except Exception:
        return


def safe_string(value: Any) -> str:
    return str(value or "")


def sanitize_error_text(value: str) -> str:
    sanitized = value
    sanitized = re.sub(r"([?&](?:api_key|key|token|access_token|refresh_token)=)[^&\s]+", r"\1[redacted]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(DeepL-Auth-Key\s+)[^\s,;]+", r"\1[redacted]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(Authorization['\"]?:\s*['\"]?(?:Bearer\s+)?)[^'\",\s]+", r"\1[redacted]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[redacted]", sanitized, flags=re.IGNORECASE)
    return sanitized
