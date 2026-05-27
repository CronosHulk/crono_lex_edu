from __future__ import annotations

import base64
import hashlib

from ecdsa import BadSignatureError, VerifyingKey
from ecdsa.util import sigdecode_der


def verify_monobank_webhook_signature(*, public_key_base64: str, signature_base64: str, raw_body: bytes) -> bool:
    try:
        public_key_bytes = base64.b64decode(public_key_base64)
        signature = base64.b64decode(signature_base64)
        verifying_key = VerifyingKey.from_pem(public_key_bytes)
        body_hash = hashlib.sha256(raw_body).digest()
        return verifying_key.verify_digest(signature, body_hash, sigdecode=sigdecode_der)
    except (BadSignatureError, ValueError, TypeError):
        return False
