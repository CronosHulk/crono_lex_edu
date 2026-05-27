from __future__ import annotations

import json
from typing import Any


def serialize_telegram_payload(user: Any, chat: Any) -> str:
    payload = {
        "user": user.to_dict() if user is not None else None,
        "chat": chat.to_dict() if chat is not None else None,
    }
    return json.dumps(payload, ensure_ascii=False)
