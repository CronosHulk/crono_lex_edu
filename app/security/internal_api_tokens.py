from __future__ import annotations

import hmac
from typing import Any


class InternalApiTokenError(Exception):
    status_code = 500
    detail = "Internal API token validation failed"


class InternalApiTokenNotConfiguredError(InternalApiTokenError):
    status_code = 503
    detail = "Internal API token is not configured"


class InvalidInternalApiTokenError(InternalApiTokenError):
    status_code = 401
    detail = "Invalid internal API token"


def read_internal_api_token(service: Any) -> str:
    settings = getattr(getattr(service, "db", None), "settings", None)
    return str(getattr(settings, "app_internal_api_token", "") or "").strip()


def validate_internal_api_token(*, expected: str, token: str | None) -> None:
    if not expected:
        raise InternalApiTokenNotConfiguredError
    if not token or not hmac.compare_digest(token, expected):
        raise InvalidInternalApiTokenError
