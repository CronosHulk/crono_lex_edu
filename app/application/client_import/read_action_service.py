from __future__ import annotations

from collections.abc import Callable

from app.application.client_import.action_payload import parse_import_job_id
from app.contracts import ScreenModel

ImportScreenBuilder = Callable[[int, str], ScreenModel]
SummaryScreenBuilder = Callable[[int, str, int], ScreenModel]
DocumentScreenBuilder = Callable[[int, str, int, str], ScreenModel]
IntakeSliceScreenBuilder = Callable[[int, str, int, str], ScreenModel]
FailedItemsScreenBuilder = Callable[[int, str, int], ScreenModel]
CloseToMenuScreenBuilder = Callable[[int, str], ScreenModel]


class ClientImportReadActionService:
    def __init__(
        self,
        *,
        build_import_screen: ImportScreenBuilder,
        build_summary_screen_for_user: SummaryScreenBuilder,
        build_document_screen_for_user: DocumentScreenBuilder,
        build_intake_slice_screen: IntakeSliceScreenBuilder,
        build_failed_items_screen: FailedItemsScreenBuilder,
        build_close_to_menu_screen: CloseToMenuScreenBuilder,
    ) -> None:
        self.build_import_screen = build_import_screen
        self.build_summary_screen_for_user = build_summary_screen_for_user
        self.build_document_screen_for_user = build_document_screen_for_user
        self.build_intake_slice_screen = build_intake_slice_screen
        self.build_failed_items_screen = build_failed_items_screen
        self.build_close_to_menu_screen = build_close_to_menu_screen

    def handle_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel | None:
        if action.startswith("m:i:summary:"):
            job_id = self._parse_job_id_or_none(action)
            if job_id is None:
                return self.build_import_screen(telegram_user_id, locale)
            return self.build_summary_screen_for_user(telegram_user_id, locale, job_id)

        if action.startswith("m:i:existing:"):
            job_id = self._parse_job_id_or_none(action)
            if job_id is None:
                return self.build_import_screen(telegram_user_id, locale)
            return self.build_document_screen_for_user(telegram_user_id, locale, job_id, "existing")

        if action.startswith("m:i:queued:"):
            job_id = self._parse_job_id_or_none(action)
            if job_id is None:
                return self.build_import_screen(telegram_user_id, locale)
            return self.build_document_screen_for_user(telegram_user_id, locale, job_id, "queued")

        if action.startswith("m:i:invalid:"):
            job_id = self._parse_job_id_or_none(action)
            if job_id is None:
                return self.build_import_screen(telegram_user_id, locale)
            return self.build_intake_slice_screen(telegram_user_id, locale, job_id, "invalid")

        if action.startswith("m:i:failed:"):
            job_id = self._parse_job_id_or_none(action)
            if job_id is None:
                return self.build_import_screen(telegram_user_id, locale)
            return self.build_failed_items_screen(telegram_user_id, locale, job_id)

        if action.startswith("m:i:delete:"):
            return self.build_close_to_menu_screen(telegram_user_id, locale)

        return None

    def _parse_job_id_or_none(self, action: str) -> int | None:
        return parse_import_job_id(action.split(":")[-1])
