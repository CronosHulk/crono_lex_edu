from __future__ import annotations

from app.application.client_import.text_input_service import ClientImportTextInputService
from app.contracts import ScreenModel, TelegramUserContext


def build_user() -> TelegramUserContext:
    return TelegramUserContext(telegram_user_id=11, language_code="uk", raw_telegram_json="{}")


class CaptureHandlers:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def build_import_screen(self, telegram_user_id: int, locale: str, notice: str | None = None) -> ScreenModel:
        self.calls.append(("screen", (telegram_user_id, locale, notice)))
        return ScreenModel(screen_id="import", text=notice or "")

    def submit_import(self, user: TelegramUserContext, locale: str, source_url: str) -> ScreenModel:
        self.calls.append(("submit", (user.telegram_user_id, locale, source_url)))
        return ScreenModel(screen_id="submitted", text=source_url)


def build_service(capture: CaptureHandlers) -> ClientImportTextInputService:
    return ClientImportTextInputService(
        build_user_import_screen=capture.build_import_screen,
        submit_user_vocabulary_import=capture.submit_import,
    )


def test_import_text_input_routes_google_doc_url_to_submitter() -> None:
    capture = CaptureHandlers()

    screen = build_service(capture).handle_text_input(
        user=build_user(),
        locale="uk",
        normalized_text="https://docs.google.com/document/d/demo/edit",
    )

    assert screen is not None
    assert screen.screen_id == "submitted"
    assert capture.calls == [("submit", (11, "uk", "https://docs.google.com/document/d/demo/edit"))]


def test_import_text_input_rejects_plain_word_list_with_disabled_notice() -> None:
    capture = CaptureHandlers()

    screen = build_service(capture).handle_text_input(
        user=build_user(),
        locale="uk",
        normalized_text="take over\ncarry on",
    )

    assert screen is not None
    assert screen.screen_id == "import"
    assert "тимчасово вимкнений" in screen.text
    assert capture.calls[0][0] == "screen"


def test_import_text_input_rejects_non_google_url() -> None:
    capture = CaptureHandlers()

    screen = build_service(capture).handle_text_input(
        user=build_user(),
        locale="uk",
        normalized_text="https://example.com/words",
    )

    assert screen is not None
    assert screen.screen_id == "import"
    assert "Не вдалося прийняти посилання" in screen.text
    assert capture.calls[0][0] == "screen"


def test_import_text_input_ignores_unrelated_text() -> None:
    capture = CaptureHandlers()

    screen = build_service(capture).handle_text_input(
        user=build_user(),
        locale="uk",
        normalized_text="just hello",
    )

    assert screen is None
    assert capture.calls == []
