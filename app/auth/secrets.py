from __future__ import annotations

import hashlib
import hmac
import secrets

PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000


def hash_secret(value: str, *, salt: str | None = None) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        value.encode("utf-8"),
        resolved_salt.encode("ascii"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${resolved_salt}${digest}"


def verify_secret(value: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        scheme, iterations_raw, salt, digest = stored_hash.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            value.encode("utf-8"),
            salt.encode("ascii"),
            int(iterations_raw),
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculated, digest)


def hash_token_for_lookup(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
