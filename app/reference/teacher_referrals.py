from __future__ import annotations

import base64
from uuid import UUID

TEACHER_REFERRAL_PREFIX = "t_"


def encode_teacher_referral_payload(teacher_user_uuid: str | UUID) -> str:
    normalized_uuid = str(UUID(str(teacher_user_uuid)))
    encoded = base64.urlsafe_b64encode(normalized_uuid.encode("ascii")).decode("ascii")
    return f"{TEACHER_REFERRAL_PREFIX}{encoded.rstrip('=')}"


def decode_teacher_referral_payload(payload: str | None) -> str | None:
    normalized_payload = str(payload or "").strip()
    if not normalized_payload.startswith(TEACHER_REFERRAL_PREFIX):
        return None
    encoded = normalized_payload[len(TEACHER_REFERRAL_PREFIX) :]
    if not encoded:
        return None
    try:
        padding = "=" * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(f"{encoded}{padding}".encode("ascii")).decode("ascii")
        return str(UUID(decoded))
    except (ValueError, UnicodeDecodeError):
        return None


def extract_teacher_referral_from_start_text(message_text: str | None) -> str | None:
    parts = str(message_text or "").strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0] != "/start":
        return None
    return decode_teacher_referral_payload(parts[1])


def build_teacher_referral_url(bot_username: str | None, teacher_user_uuid: str | UUID | None) -> str | None:
    normalized_username = str(bot_username or "").strip().lstrip("@")
    if not normalized_username or teacher_user_uuid is None:
        return None
    payload = encode_teacher_referral_payload(teacher_user_uuid)
    return f"https://t.me/{normalized_username}?start={payload}"
