from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class WebRequestContext:
    api_origin: str | None = None
    api_path: str | None = None
    client_ip: str | None = None
    user_agent: str | None = None

    @property
    def device_fingerprint_hash(self) -> str:
        payload = "|".join(
            [
                self.api_origin or "",
                self.client_ip or "",
                self.user_agent or "",
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
