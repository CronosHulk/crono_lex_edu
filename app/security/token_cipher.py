from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


class TokenCipher:
    def __init__(self, secret: str) -> None:
        normalized = str(secret or "").strip()
        if len(normalized) < 32:
            raise ValueError("Token encryption secret must be at least 32 characters")
        key = base64.urlsafe_b64encode(hashlib.sha256(normalized.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
