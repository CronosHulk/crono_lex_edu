from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Header, HTTPException

from app.security.internal_api_tokens import (
    InternalApiTokenError,
    read_internal_api_token,
    validate_internal_api_token,
)

INTERNAL_API_TOKEN_HEADER = "X-CronoLex-Internal-Token"


def build_internal_api_guard(service: Any) -> Callable[[str | None], None]:
    def require_internal_api_token(
        token: Annotated[str | None, Header(alias=INTERNAL_API_TOKEN_HEADER)] = None,
    ) -> None:
        try:
            validate_internal_api_token(expected=read_internal_api_token(service), token=token)
        except InternalApiTokenError as error:
            raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    return require_internal_api_token
