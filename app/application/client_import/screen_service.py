from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any, Protocol

from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.reference.scheduling import format_hour_label
from app.user_import.runtime_settings import DEFAULT_IMPORT_RUNTIME_SETTINGS
from app.validators.google_docs import mask_google_doc_url


class ImportScreenUserReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...

    def is_super_admin(self, telegram_user_id: int) -> bool:
        ...

    def can_access(self, telegram_user_id: int, *, action: str, environment: str) -> bool:
        ...


class ClientImportScreenService:
    def __init__(
        self,
        user_profiles: ImportScreenUserReader,
        settings: Any,
        import_settings_reader: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.user_profiles = user_profiles
        self.settings = settings
        self.import_settings_reader = import_settings_reader

    def build_user_import_screen(self, telegram_user_id: int, locale: str, notice: str | None = None) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        runtime_settings = (
            self.import_settings_reader() if self.import_settings_reader is not None else DEFAULT_IMPORT_RUNTIME_SETTINGS
        )
        max_words = max(int(runtime_settings["max_import_entries_per_submission"]), 1)
        sync_interval_days = int(runtime_settings["google_doc_sync_interval_days"])
        sync_hour = int(runtime_settings["google_doc_sync_hour"])
        is_test_mode = bool(getattr(self.settings, "app_user_import_test_mode", False))
        lines = [translate(locale, "import_words_title")]
        if notice:
            lines.append(notice)
        lines.extend(
            [
                translate(
                    locale,
                    "import_words_description",
                    max_words=max_words,
                    sync_interval_days=sync_interval_days,
                    sync_time=format_hour_label(sync_hour),
                ),
                translate(locale, "import_words_link_hint", max_words=max_words),
                translate(locale, "import_words_test_mode_notice") if is_test_mode else "",
                translate(
                    locale,
                    "import_words_bound_doc_notice" if profile and profile.get("import_google_doc_id") else "import_words_bound_doc_missing",
                    source=html.escape(mask_google_doc_url(str(profile.get("import_google_doc_id"))))
                    if profile and profile.get("import_google_doc_id")
                    else "",
                ),
            ]
        )
        buttons = [ButtonModel(action="m:settings", text=translate(locale, "menu_back"))]
        has_run_now_access = (
            self.user_profiles.can_access(
                telegram_user_id,
                action="imports/run_now",
                environment="telegram_user",
            )
            if hasattr(self.user_profiles, "can_access")
            else self.user_profiles.is_super_admin(telegram_user_id)
        )
        if is_test_mode and has_run_now_access:
            buttons.append(ButtonModel(action="m:i:run-now", text=translate(locale, "import_words_run_now_button")))
        if profile and profile.get("import_google_doc_id"):
            buttons.append(ButtonModel(action="m:i:unbind", text=translate(locale, "import_words_unbind_button")))
        buttons.append(ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")))
        return ScreenModel(
            screen_id="menu:import_words",
            text="\n\n".join(line for line in lines if line),
            buttons=buttons,
            keyboard_type="inline",
            metadata={"buttons_per_row": 1},
        )
