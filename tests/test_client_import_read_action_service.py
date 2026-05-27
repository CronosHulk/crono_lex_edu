from __future__ import annotations

import pytest

from app.application.client_import.action_payload import parse_import_job_id
from app.application.client_import.read_action_service import ClientImportReadActionService
from app.contracts import ScreenModel


class CaptureBuilders:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def import_screen(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("import", (telegram_user_id, locale)))
        return ScreenModel(screen_id="import", text="import")

    def summary_screen(self, telegram_user_id: int, locale: str, job_id: int) -> ScreenModel:
        self.calls.append(("summary", (telegram_user_id, locale, job_id)))
        return ScreenModel(screen_id="summary", text="summary")

    def document_screen(self, telegram_user_id: int, locale: str, job_id: int, slice_name: str) -> ScreenModel:
        self.calls.append(("document", (telegram_user_id, locale, job_id, slice_name)))
        return ScreenModel(screen_id=f"document:{slice_name}", text="document")

    def intake_slice_screen(self, telegram_user_id: int, locale: str, job_id: int, slice_name: str) -> ScreenModel:
        self.calls.append(("intake", (telegram_user_id, locale, job_id, slice_name)))
        return ScreenModel(screen_id=f"intake:{slice_name}", text="intake")

    def failed_items_screen(self, telegram_user_id: int, locale: str, job_id: int) -> ScreenModel:
        self.calls.append(("failed", (telegram_user_id, locale, job_id)))
        return ScreenModel(screen_id="failed", text="failed")

    def close_to_menu_screen(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append(("close_to_menu", (telegram_user_id, locale)))
        return ScreenModel(
            screen_id="menu",
            text="menu",
            clear_chat=True,
            metadata={"force_resend": True, "delete_cached_active_screen": True},
        )


def build_service(capture: CaptureBuilders) -> ClientImportReadActionService:
    return ClientImportReadActionService(
        build_import_screen=capture.import_screen,
        build_summary_screen_for_user=capture.summary_screen,
        build_document_screen_for_user=capture.document_screen,
        build_intake_slice_screen=capture.intake_slice_screen,
        build_failed_items_screen=capture.failed_items_screen,
        build_close_to_menu_screen=capture.close_to_menu_screen,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (None, None),
        ("bad", None),
        ("0", None),
        ("-1", None),
        ("7", 7),
    ),
)
def test_parse_import_job_id_returns_positive_int_only(
    value: str | None,
    expected: int | None,
) -> None:
    assert parse_import_job_id(value) == expected


def test_import_read_action_routes_summary_screen() -> None:
    capture = CaptureBuilders()

    screen = build_service(capture).handle_action(11, "uk", "m:i:summary:7")

    assert screen is not None
    assert screen.screen_id == "summary"
    assert capture.calls == [("summary", (11, "uk", 7))]


def test_import_read_action_routes_document_slices() -> None:
    capture = CaptureBuilders()
    service = build_service(capture)

    existing_screen = service.handle_action(11, "uk", "m:i:existing:7")
    queued_screen = service.handle_action(11, "uk", "m:i:queued:8")

    assert existing_screen is not None
    assert queued_screen is not None
    assert existing_screen.screen_id == "document:existing"
    assert queued_screen.screen_id == "document:queued"
    assert capture.calls == [
        ("document", (11, "uk", 7, "existing")),
        ("document", (11, "uk", 8, "queued")),
    ]


def test_import_read_action_routes_intake_and_failed_screens() -> None:
    capture = CaptureBuilders()
    service = build_service(capture)

    invalid_screen = service.handle_action(11, "uk", "m:i:invalid:7")
    failed_screen = service.handle_action(11, "uk", "m:i:failed:8")

    assert invalid_screen is not None
    assert failed_screen is not None
    assert invalid_screen.screen_id == "intake:invalid"
    assert failed_screen.screen_id == "failed"
    assert capture.calls == [
        ("intake", (11, "uk", 7, "invalid")),
        ("failed", (11, "uk", 8)),
    ]


def test_import_read_action_falls_back_to_import_screen_for_bad_job_id() -> None:
    capture = CaptureBuilders()

    screen = build_service(capture).handle_action(11, "uk", "m:i:summary:bad")

    assert screen is not None
    assert screen.screen_id == "import"
    assert capture.calls == [("import", (11, "uk"))]


def test_import_read_action_routes_delete_to_close_to_menu_screen() -> None:
    capture = CaptureBuilders()

    screen = build_service(capture).handle_action(11, "uk", "m:i:delete:7")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert screen.clear_chat is True
    assert screen.metadata == {"force_resend": True, "delete_cached_active_screen": True}
    assert capture.calls == [("close_to_menu", (11, "uk"))]


def test_import_read_action_ignores_mutation_and_unrelated_actions() -> None:
    capture = CaptureBuilders()
    service = build_service(capture)

    assert service.handle_action(11, "uk", "m:i:run-now") is None
    assert service.handle_action(11, "uk", "m:i:unbind") is None
    assert service.handle_action(11, "uk", "m:n") is None
    assert capture.calls == []
