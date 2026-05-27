from __future__ import annotations

from typing import Any

import httpx


class BackendBotApiTransport:
    def __init__(self, base_url: str, *, internal_api_token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.internal_api_token = internal_api_token.strip()

    async def post(self, path: str, *, json: dict[str, Any] | None = None, timeout: float = 30.0) -> Any:
        headers = {}
        if self.internal_api_token:
            headers["X-CronoLex-Internal-Token"] = self.internal_api_token
        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
            response = await client.post(path, json=json, headers=headers or None)
            response.raise_for_status()
            return response.json()
