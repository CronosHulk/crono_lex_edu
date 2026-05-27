from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.contracts import ButtonModel, ScreenModel, TelegramUserContext
from app.i18n import translate
from app.screen_delivery_policy import with_delete_after_hours
from app.user_import.services.helpers import format_numbered_import_item_list


class UserImportIntakeJobsPort(Protocol):
    def get_job_for_user(self, telegram_user_id: int, job_id: int) -> dict[str, Any] | None: ...


class UserImportIntakeDatabasePort(Protocol):
    @property
    def user_import_jobs(self) -> UserImportIntakeJobsPort: ...


class UserImportIntakeJobServicePort(Protocol):
    def build_user_import_intake_snapshot(
        self,
        parsed_words: list[Any],
        existing_lookup_words: set[str],
        invalid_fragments: list[str],
        *,
        max_words_per_bind: int,
    ) -> dict[str, Any]: ...

    def get_user_import_intake_snapshot(self, job: dict[str, Any]) -> dict[str, Any]: ...

    def create_user_import_job_from_words(
        self,
        *,
        telegram_user_id: int,
        source_identifier: str,
        parsed_words: list[Any],
        current_time: datetime,
        task_log_id: int | None = None,
        source_type: str = "google_doc",
        max_words_per_job: int | None = None,
    ) -> tuple[int, int, int | None]: ...


class UserImportIntakeManualBindServicePort(Protocol):
    def submit_user_vocabulary_import(
        self,
        *,
        user: TelegramUserContext,
        locale: str,
        source_url: str,
        current_time: datetime,
        build_user_import_screen: Callable[..., ScreenModel],
        prepare_import_job_items: Callable[..., None],
        build_user_import_summary_screen_for_user: Callable[..., ScreenModel],
        process_queued_attribute_builds_after_import: Callable[[int, datetime], None] | None = None,
    ) -> ScreenModel: ...


class UserImportIntakeService:
    def __init__(
        self,
        db: UserImportIntakeDatabasePort,
        *,
        intake_job_service: UserImportIntakeJobServicePort,
        manual_bind_service: UserImportIntakeManualBindServicePort,
    ) -> None:
        self.db = db
        self.intake_job_service = intake_job_service
        self.manual_bind_service = manual_bind_service

    def submit_user_vocabulary_import(
        self,
        *,
        user: TelegramUserContext,
        locale: str,
        source_url: str,
        current_time: datetime,
        build_user_import_screen: Callable[..., ScreenModel],
        prepare_import_job_items: Callable[..., None],
        build_user_import_summary_screen_for_user: Callable[..., ScreenModel],
        process_queued_attribute_builds_after_import: Callable[[int, datetime], None] | None = None,
    ) -> ScreenModel:
        return self.manual_bind_service.submit_user_vocabulary_import(
            user=user,
            locale=locale,
            source_url=source_url,
            current_time=current_time,
            build_user_import_screen=build_user_import_screen,
            prepare_import_job_items=prepare_import_job_items,
            build_user_import_summary_screen_for_user=build_user_import_summary_screen_for_user,
            process_queued_attribute_builds_after_import=process_queued_attribute_builds_after_import,
        )

    def build_user_import_intake_snapshot(
        self,
        parsed_words: list[Any],
        existing_lookup_words: set[str],
        invalid_fragments: list[str],
        *,
        max_words_per_bind: int,
    ) -> dict[str, Any]:
        return self.intake_job_service.build_user_import_intake_snapshot(
            parsed_words,
            existing_lookup_words,
            invalid_fragments,
            max_words_per_bind=max_words_per_bind,
        )

    def get_user_import_intake_snapshot(self, job: dict[str, Any]) -> dict[str, Any]:
        return self.intake_job_service.get_user_import_intake_snapshot(job)

    def build_user_import_intake_slice_screen(
        self,
        *,
        telegram_user_id: int,
        locale: str,
        job_id: int,
        slice_name: str,
        build_user_import_screen: Callable[..., ScreenModel],
    ) -> ScreenModel:
        job = self.db.user_import_jobs.get_job_for_user(telegram_user_id, job_id)
        if job is None:
            return build_user_import_screen(
                telegram_user_id,
                locale,
                notice=translate(locale, "import_words_invalid_url"),
            )
        intake_snapshot = self.get_user_import_intake_snapshot(job)
        if slice_name == "existing":
            title_key = "import_words_existing_list_title"
            values = intake_snapshot["existing_lookup_words"]
            screen_suffix = "existing"
        elif slice_name == "queued":
            title_key = "import_words_queued_list_title"
            values = intake_snapshot["queued_lookup_words"]
            screen_suffix = "queued"
        else:
            title_key = "import_words_invalid_list_title"
            values = intake_snapshot["invalid_fragments"]
            screen_suffix = "invalid"
        lines = [translate(locale, title_key)]
        formatted = format_numbered_import_item_list(locale, values)
        if formatted:
            lines.append(formatted)
        else:
            lines.append(translate(locale, "import_words_intake_list_empty"))
        screen = ScreenModel(
            screen_id=f"import_words:{screen_suffix}:{job_id}",
            text="\n\n".join(lines),
            buttons=[
                ButtonModel(action=f"m:i:summary:{job_id}", text=translate(locale, "menu_back")),
                ButtonModel(action=f"m:i:delete:{job_id}", text=translate(locale, "import_words_delete_button")),
                ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
            ],
            keyboard_type="inline",
            metadata={"buttons_per_row": 1, "sticky_import_report": True},
        )
        return with_delete_after_hours(screen, 24)

    def create_user_import_job_from_words(
        self,
        *,
        telegram_user_id: int,
        source_identifier: str,
        parsed_words: list[Any],
        current_time: datetime,
        task_log_id: int | None = None,
        source_type: str = "google_doc",
        max_words_per_job: int | None = None,
    ) -> tuple[int, int, int | None]:
        return self.intake_job_service.create_user_import_job_from_words(
            telegram_user_id=telegram_user_id,
            source_identifier=source_identifier,
            parsed_words=parsed_words,
            current_time=current_time,
            task_log_id=task_log_id,
            source_type=source_type,
            max_words_per_job=max_words_per_job,
        )
