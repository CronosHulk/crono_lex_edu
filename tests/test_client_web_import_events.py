from __future__ import annotations

import time
from threading import Thread

import app.composition.client_web_import_events as import_events_module
from app.application.client_web.import_events import ClientWebImportEvent
from app.composition.client_web_import_events import (
    LocalImportEventBroker,
    publish_import_event,
    stream_import_events,
)


def test_client_web_import_event_payload_omits_empty_optional_fields() -> None:
    event = ClientWebImportEvent(telegram_user_id=42, job_id=9, event="completed", status="completed")

    assert event.payload() == {
        "telegram_user_id": 42,
        "job_id": 9,
        "event": "completed",
        "status": "completed",
    }


def test_local_import_event_broker_delivers_events_by_user_and_job() -> None:
    broker = LocalImportEventBroker()
    subscriber = broker.subscribe(telegram_user_id=42, job_id=9)
    received: list[ClientWebImportEvent | None] = []
    reader = Thread(target=lambda: received.append(next(subscriber)))
    reader.daemon = True
    reader.start()
    for _ in range(20):
        if broker._subscribers:
            break
        time.sleep(0.01)

    event = ClientWebImportEvent(telegram_user_id=42, job_id=9, event="items_changed", item_count=3)
    broker.publish(event)

    reader.join(timeout=1)
    assert received == [event]
    subscriber.close()


def test_publish_import_event_uses_local_broker(monkeypatch) -> None:
    class FakeBroker:
        def __init__(self) -> None:
            self.published: list[ClientWebImportEvent] = []

        def publish(self, event: ClientWebImportEvent) -> None:
            self.published.append(event)

    broker = FakeBroker()
    event = ClientWebImportEvent(telegram_user_id=42, job_id=9, event="completed")
    monkeypatch.setattr(import_events_module, "LOCAL_IMPORT_EVENT_BROKER", broker)

    publish_import_event(object(), event)

    assert broker.published == [event]


def test_stream_import_events_uses_local_broker(monkeypatch) -> None:
    event = ClientWebImportEvent(telegram_user_id=42, job_id=9, event="items_changed", item_count=3)

    class FakeBroker:
        def subscribe(self, telegram_user_id: int, job_id: int):
            assert telegram_user_id == 42
            assert job_id == 9
            yield event

    monkeypatch.setattr(import_events_module, "LOCAL_IMPORT_EVENT_BROKER", FakeBroker())

    stream = stream_import_events(object(), telegram_user_id=42, job_id=9)

    assert next(stream) == 'event: connected\ndata: {"job_id":9}\n\n'
    assert next(stream) == (
        'event: items_changed\ndata: {"telegram_user_id":42,"job_id":9,'
        '"event":"items_changed","item_count":3}\n\n'
    )
