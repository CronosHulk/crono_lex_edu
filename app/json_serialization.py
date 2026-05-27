from __future__ import annotations

import json
from collections.abc import AsyncIterator

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.serialization.json_datetimes import normalize_json_datetimes


class ProjectDateTimeJSONMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, timezone_name: str) -> None:
        super().__init__(app)
        self.timezone_name = timezone_name

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b"".join([chunk async for chunk in _iterate_response_body(response)])
        if not body:
            return response

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=_response_headers_without_content_length(response),
                media_type=response.media_type,
            )

        normalized_payload = normalize_json_datetimes(payload, timezone_name=self.timezone_name)
        return Response(
            content=json.dumps(normalized_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            status_code=response.status_code,
            headers=_response_headers_without_content_length(response),
            media_type="application/json",
            background=response.background,
        )


async def _iterate_response_body(response) -> AsyncIterator[bytes]:
    async for chunk in response.body_iterator:
        yield chunk


def _response_headers_without_content_length(response) -> dict[str, str]:
    return {
        key: value
        for key, value in response.headers.items()
        if key.lower() != "content-length"
    }
