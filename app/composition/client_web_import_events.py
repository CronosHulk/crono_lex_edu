from __future__ import annotations

import json
import queue
from collections.abc import Iterator
from threading import Lock
from typing import Any

from app.application.client_web.import_events import ClientWebImportEvent

IMPORT_EVENTS_HEARTBEAT_SECONDS = 15
IMPORT_EVENTS_QUEUE_SIZE = 100


class LocalImportEventBroker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._subscribers: dict[tuple[int, int], set[queue.Queue[ClientWebImportEvent]]] = {}

    def publish(self, event: ClientWebImportEvent) -> None:
        key = (event.telegram_user_id, event.job_id)
        with self._lock:
            subscribers = list(self._subscribers.get(key, set()))
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(event)
            except queue.Full:
                try:
                    subscriber.get_nowait()
                    subscriber.put_nowait(event)
                except queue.Empty:
                    pass

    def subscribe(self, telegram_user_id: int, job_id: int) -> Iterator[ClientWebImportEvent | None]:
        subscriber: queue.Queue[ClientWebImportEvent] = queue.Queue(maxsize=IMPORT_EVENTS_QUEUE_SIZE)
        key = (telegram_user_id, job_id)
        with self._lock:
            self._subscribers.setdefault(key, set()).add(subscriber)
        try:
            while True:
                try:
                    yield subscriber.get(timeout=IMPORT_EVENTS_HEARTBEAT_SECONDS)
                except queue.Empty:
                    yield None
        finally:
            with self._lock:
                subscribers = self._subscribers.get(key)
                if subscribers is not None:
                    subscribers.discard(subscriber)
                    if not subscribers:
                        self._subscribers.pop(key, None)


LOCAL_IMPORT_EVENT_BROKER = LocalImportEventBroker()


def publish_import_event(learning_service: Any, event: ClientWebImportEvent) -> None:
    LOCAL_IMPORT_EVENT_BROKER.publish(event)


def stream_import_events(learning_service: Any, *, telegram_user_id: int, job_id: int) -> Iterator[str]:
    yield _format_sse("connected", {"job_id": job_id})
    yield from _stream_local_events(telegram_user_id, job_id)


def _stream_local_events(telegram_user_id: int, job_id: int) -> Iterator[str]:
    for event in LOCAL_IMPORT_EVENT_BROKER.subscribe(telegram_user_id, job_id):
        if event is None:
            yield ": heartbeat\n\n"
            continue
        yield _format_sse(event.event, event.payload())


def _format_sse(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"
