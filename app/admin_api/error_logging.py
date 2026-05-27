from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ADMIN_API_PREFIX = "/api/v1/admin"


async def admin_request_validation_exception_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    log_admin_validation_error(request, error)
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": error.errors()}))


def log_admin_validation_error(request: Request, error: RequestValidationError) -> None:
    if not request.url.path.startswith(ADMIN_API_PREFIX):
        return
    db = getattr(request.app.state, "db", None)
    if db is None or not hasattr(db, "error_logs"):
        return
    try:
        db.error_logs.create(
            "warn",
            [
                f"route={request.url.path}",
                f"method={request.method}",
                "status_code=422",
                "error_type=RequestValidationError",
            ],
            context_json={
                "route": request.url.path,
                "method": request.method,
                "status_code": 422,
                "validation_errors": sanitize_validation_errors(error.errors()),
            },
        )
    except Exception:
        return


def sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    safe_errors: list[dict[str, str]] = []
    for item in errors[:20]:
        location = ".".join(str(part) for part in item.get("loc", []))
        safe_errors.append(
            {
                "loc": location[:200],
                "msg": str(item.get("msg", ""))[:300],
                "type": str(item.get("type", ""))[:100],
            }
        )
    return safe_errors
