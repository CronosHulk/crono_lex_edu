from __future__ import annotations

import json

from app.bot_runtime.telegram_payload import serialize_telegram_payload


class DummyEntity:
    def __init__(self, payload):
        self.payload = payload

    def to_dict(self):
        return self.payload


def test_serialize_telegram_payload_combines_user_and_chat() -> None:
    result = serialize_telegram_payload(DummyEntity({"id": 1}), DummyEntity({"id": 2}))

    assert json.loads(result) == {"user": {"id": 1}, "chat": {"id": 2}}


def test_serialize_telegram_payload_keeps_unicode_readable() -> None:
    result = serialize_telegram_payload(DummyEntity({"first_name": "Олена"}), DummyEntity({"title": "Київ"}))

    assert "Олена" in result
    assert "Київ" in result


def test_serialize_telegram_payload_accepts_missing_user_or_chat() -> None:
    result = serialize_telegram_payload(None, None)

    assert json.loads(result) == {"user": None, "chat": None}

