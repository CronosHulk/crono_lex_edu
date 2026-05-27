from __future__ import annotations

from datetime import datetime

from app.application.client_import.mutation_action_service import (
    ClientImportMutationActionService,
)
from app.contracts import ScreenModel


class CaptureMutationHandlers:
    def __init__(self) -> None:
        self.current_time = datetime(2026, 4, 20, 10, 0, 0)
        self.is_test_mode = False
        self.is_access_denied = False
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def can_access(self, telegram_user_id: int, *, action: str, environment: str) -> bool:
        self.calls.append(
            (
                "can_access",
                (telegram_user_id,),
                {"action": action, "environment": environment},
            )
        )
        return not self.is_access_denied

    def is_test_mode_enabled(self) -> bool:
        self.calls.append(("test_mode", (), {}))
        return self.is_test_mode

    def now(self) -> datetime:
        self.calls.append(("now", (), {}))
        return self.current_time

    def process_imports(self, **kwargs) -> list:
        self.calls.append(("process", (), kwargs))
        return []

    def clear_binding(self, telegram_user_id: int, current_time: datetime) -> None:
        self.calls.append(("clear", (telegram_user_id, current_time), {}))

    def build_import_screen(self, telegram_user_id: int, locale: str, notice: str | None = None) -> ScreenModel:
        self.calls.append(("screen", (telegram_user_id, locale, notice), {}))
        return ScreenModel(screen_id="import", text=notice or "")

    def build_menu_screen(self, telegram_user_id: int, locale: str, **kwargs) -> ScreenModel:
        self.calls.append(("menu", (telegram_user_id, locale), kwargs))
        return ScreenModel(screen_id="menu", text=str(kwargs.get("notice") or ""))


def build_service(capture: CaptureMutationHandlers) -> ClientImportMutationActionService:
    return ClientImportMutationActionService(
        user_profiles=capture,
        is_test_mode_enabled=capture.is_test_mode_enabled,
        current_time=capture.now,
        process_due_user_vocabulary_imports=capture.process_imports,
        clear_import_google_doc_binding=capture.clear_binding,
        build_import_screen=capture.build_import_screen,
        build_menu_screen=capture.build_menu_screen,
    )


def test_import_mutation_run_now_rejects_non_admin_before_test_mode_check() -> None:
    capture = CaptureMutationHandlers()
    capture.is_access_denied = True

    screen = build_service(capture).handle_action(11, "uk", "m:i:run-now")

    assert screen is not None
    assert screen.screen_id == "menu"
    assert "Ручний запуск доступний лише" in screen.text
    assert [call[0] for call in capture.calls] == ["can_access", "menu"]


def test_import_mutation_run_now_rejects_when_test_mode_disabled() -> None:
    capture = CaptureMutationHandlers()

    screen = build_service(capture).handle_action(11, "uk", "m:i:run-now")

    assert screen is not None
    assert screen.screen_id == "import"
    assert "Ручний запуск доступний лише" in screen.text
    assert [call[0] for call in capture.calls] == ["can_access", "test_mode", "screen"]


def test_import_mutation_run_now_processes_imports_in_test_mode() -> None:
    capture = CaptureMutationHandlers()
    capture.is_test_mode = True

    screen = build_service(capture).handle_action(11, "uk", "m:i:run-now")

    assert screen is not None
    assert screen.screen_id == "import"
    assert screen.metadata == {"force_resend": True}
    process_call = next(call for call in capture.calls if call[0] == "process")
    assert process_call[2] == {
        "current_time": capture.current_time,
        "emit_notifications": False,
        "include_bound_sync": True,
    }


def test_import_mutation_unbind_clears_binding_with_current_time() -> None:
    capture = CaptureMutationHandlers()

    screen = build_service(capture).handle_action(11, "uk", "m:i:unbind")

    assert screen is not None
    assert screen.screen_id == "import"
    assert "Google Doc відвʼязано" in screen.text
    assert capture.calls[0] == ("now", (), {})
    assert capture.calls[1] == ("clear", (11, capture.current_time), {})


def test_import_mutation_ignores_unrelated_actions() -> None:
    capture = CaptureMutationHandlers()

    assert build_service(capture).handle_action(11, "uk", "m:i:summary:1") is None
    assert capture.calls == []
