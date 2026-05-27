from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.contracts import ButtonModel, ImportDispatchNotificationModel, ScreenModel
from app.helpers.locale import resolve_user_locale
from app.i18n import translate
from app.screen_delivery_policy import with_delete_after_hours
from app.user_import.services.helpers import format_import_count_text

ADMIN_DETAILS_REPORT_RUNTIME_KEY = "user_import:admin_details_report"


class UserImportNotificationProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def list_super_admin_profiles(self) -> list[dict[str, Any]]: ...


class UserImportNotificationJobsPort(Protocol):
    def list_completed_pending_summary(self) -> list[dict[str, Any]]: ...

    def list_completed_pending_publish_summary(self) -> list[dict[str, Any]]: ...

    def list_items(self, job_id: int) -> list[dict[str, Any]]: ...

    def mark_summary_sent(self, job_id: int, current_time: datetime) -> None: ...

    def mark_publish_summary_sent(self, job_id: int, current_time: datetime) -> None: ...


class UserImportNotificationRuntimeStatePort(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...

    def set(self, key: str, value_json: dict[str, Any], current_time: datetime) -> None: ...


class UserImportNotificationItemsPort(Protocol):
    def count_import_report_sources(self, *, since: datetime, until: datetime) -> dict[str, int]: ...


class UserImportNotificationDatabasePort(Protocol):
    @property
    def user_import_jobs(self) -> UserImportNotificationJobsPort: ...

    @property
    def app_runtime_state(self) -> UserImportNotificationRuntimeStatePort: ...

    @property
    def user_import_items(self) -> UserImportNotificationItemsPort: ...


class UserImportNotificationService:
    def __init__(
        self,
        db: UserImportNotificationDatabasePort,
        user_profiles: UserImportNotificationProfileReader,
        build_user_import_publish_summary_screen: Callable[[int, str, int, int], ScreenModel] | None = None,
        build_user_import_summary_screen: Callable[..., ScreenModel] | None = None,
    ) -> None:
        self.db = db
        self.user_profiles = user_profiles
        self.build_user_import_publish_summary_screen = build_user_import_publish_summary_screen
        self.build_user_import_summary_screen = build_user_import_summary_screen

    def dispatch_due_user_import_summary_notifications(self, current_time: datetime) -> list[ImportDispatchNotificationModel]:
        if self.build_user_import_summary_screen is None:
            return []
        notifications: list[ImportDispatchNotificationModel] = []
        for job in self.db.user_import_jobs.list_completed_pending_summary():
            telegram_user_id = _job_telegram_user_id(job)
            if telegram_user_id is None:
                self.db.user_import_jobs.mark_summary_sent(job["id"], current_time)
                continue
            profile = self.user_profiles.get_profile(telegram_user_id)
            locale = resolve_user_locale(profile)
            if profile is not None and profile.get("chat_id") is not None:
                notifications.append(
                    ImportDispatchNotificationModel(
                        telegram_user_id=telegram_user_id,
                        chat_id=int(profile["chat_id"]),
                        screen=self.build_user_import_summary_screen(
                            telegram_user_id=telegram_user_id,
                            locale=locale,
                            job_id=int(job["id"]),
                            items=self.db.user_import_jobs.list_items(job["id"]),
                            job_status=str(job["status"]),
                            last_error=job.get("last_error"),
                        ),
                    )
                )
            self.db.user_import_jobs.mark_summary_sent(job["id"], current_time)
        return notifications

    def dispatch_due_user_import_publish_notifications(self, current_time: datetime) -> list[ImportDispatchNotificationModel]:
        if self.build_user_import_publish_summary_screen is None:
            return []
        notifications: list[ImportDispatchNotificationModel] = []
        for job in self.db.user_import_jobs.list_completed_pending_publish_summary():
            telegram_user_id = _job_telegram_user_id(job)
            if telegram_user_id is None:
                self.db.user_import_jobs.mark_publish_summary_sent(job["id"], current_time)
                continue
            profile = self.user_profiles.get_profile(telegram_user_id)
            if profile is None or profile.get("chat_id") is None:
                self.db.user_import_jobs.mark_publish_summary_sent(job["id"], current_time)
                continue
            locale = resolve_user_locale(profile)
            items = self.db.user_import_jobs.list_items(job["id"])
            priority_count = len([item for item in items if item["status"] == "imported"])
            notifications.append(
                ImportDispatchNotificationModel(
                    telegram_user_id=telegram_user_id,
                    chat_id=int(profile["chat_id"]),
                    screen=self.build_user_import_publish_summary_screen(
                        telegram_user_id,
                        locale,
                        int(job["id"]),
                        priority_count,
                    ),
                )
            )
            self.db.user_import_jobs.mark_publish_summary_sent(job["id"], current_time)
        return notifications

    def dispatch_admin_details_completion_notifications(
        self,
        details_summary: dict[str, Any],
        current_time: datetime,
    ) -> list[ImportDispatchNotificationModel]:
        if not bool(details_summary.get("phase_ran")):
            return []
        state_row = self.db.app_runtime_state.get(ADMIN_DETAILS_REPORT_RUNTIME_KEY)
        state = dict(state_row.get("value_json") or {}) if state_row is not None else {}
        since = _parse_datetime(state.get("last_report_at")) or current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        source_counts = self.db.user_import_items.count_import_report_sources(since=since, until=current_time)
        new_details_count = int(details_summary.get("queued_for_audio_count") or 0)
        total_count = int(source_counts.get("total_count") or 0)
        dictionary_count = int(source_counts.get("dictionary_count") or 0)
        if total_count <= 0 and dictionary_count <= 0 and new_details_count <= 0:
            self.db.app_runtime_state.set(
                ADMIN_DETAILS_REPORT_RUNTIME_KEY,
                value_json={"last_report_at": current_time.isoformat()},
                current_time=current_time,
            )
            return []

        notifications: list[ImportDispatchNotificationModel] = []
        for admin_profile in self.user_profiles.list_super_admin_profiles():
            chat_id = admin_profile.get("chat_id")
            if chat_id is None:
                continue
            locale = resolve_user_locale(admin_profile)
            notifications.append(
                ImportDispatchNotificationModel(
                    telegram_user_id=int(admin_profile["telegram_user_id"]),
                    chat_id=int(chat_id),
                    screen=with_delete_after_hours(
                        ScreenModel(
                            screen_id="admin:details-summary",
                            text="\n".join(
                                [
                                    "Звіт наповнення слів деталями",
                                    "",
                                    f"Усього юзерами за період додано: {format_import_count_text(locale, total_count)}.",
                                    f"Слів зі словників: {format_import_count_text(locale, dictionary_count)}.",
                                    f"Нових слів з новими деталями: {format_import_count_text(locale, new_details_count)}.",
                                ]
                            ),
                            buttons=[
                                ButtonModel(action="m:menu", text=translate(locale, "import_words_report_close_button")),
                            ],
                            keyboard_type="inline",
                            metadata={"buttons_per_row": 1},
                        ),
                        24,
                    ),
                    disable_notification=True,
                )
            )
        self.db.app_runtime_state.set(
            ADMIN_DETAILS_REPORT_RUNTIME_KEY,
            value_json={"last_report_at": current_time.isoformat()},
            current_time=current_time,
        )
        return notifications

    def dispatch_admin_audio_completion_notifications(
        self,
        audio_summary: dict[str, Any],
    ) -> list[ImportDispatchNotificationModel]:
        return []


def _job_telegram_user_id(job: dict[str, Any]) -> int | None:
    value = job.get("telegram_user_id")
    return int(value) if value is not None else None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
