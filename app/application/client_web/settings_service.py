from __future__ import annotations

from typing import Any, Protocol

from app.helpers.locale import SUPPORTED_INTERFACE_LOCALES
from app.reference.reminder_schedules import enabled_reminder_rows, normalize_reminder_schedule
from app.reference.service import AppReference
from app.reference.teacher_referrals import build_teacher_referral_url
from app.subscriptions.learning_caps import (
    filter_level_rows,
    filter_words_per_session_options,
    is_level_title_allowed,
    is_words_per_session_allowed,
)
from app.subscriptions.paywall import CAPABILITY_REMINDERS_PER_DAY, PaywallService
from app.support.runtime_settings import SupportSettingsValidationError, read_support_settings
from app.time_utils import TimeService
from app.user_import.runtime_settings import (
    UserImportRuntimeSettingsValidationError,
    read_user_import_runtime_settings,
)
from app.user_import.services.bound_google_doc_sync_service import (
    POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE,
)


class ClientWebSettingsError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ClientWebSettingsValidationError(ClientWebSettingsError):
    pass


class ClientWebSettingsAppSettingsPort(Protocol):
    def get_value(self, key: str) -> Any | None: ...


class ClientWebSettingsUserProfilesPort(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def set_interface_locale(self, telegram_user_id: int, locale: str) -> Any: ...


class ClientWebSettingsUserLearningSettingsPort(Protocol):
    def get_current_app_version(self) -> str | None: ...

    def set_words_per_session(self, telegram_user_id: int, words_per_session: int) -> Any: ...

    def replace_reminder_schedule(self, telegram_user_id: int, reminder_schedule: list[dict[str, int | str]]) -> Any: ...

    def set_daily_reminder_hour(self, telegram_user_id: int, daily_reminder_hour: int) -> Any: ...

    def set_reminder_weekdays(self, telegram_user_id: int, reminder_weekdays: list[int]) -> Any: ...


class ClientWebSettingsLearningLevelsPort(Protocol):
    def save_language_level(self, telegram_user_id: int, language_level: str) -> Any: ...


class ClientWebSettingsTaskLogsPort(Protocol):
    def has_active_for_user(self, *, task_type: str, user_uuid: str, statuses: set[str]) -> bool: ...


class ClientWebSettingsDatabasePort(Protocol):
    settings: Any
    app_settings: ClientWebSettingsAppSettingsPort
    user_profiles: ClientWebSettingsUserProfilesPort
    user_learning_settings: ClientWebSettingsUserLearningSettingsPort
    learning_levels: ClientWebSettingsLearningLevelsPort
    task_logs: ClientWebSettingsTaskLogsPort | None


class ClientWebSettingsEntitlementProvider(Protocol):
    def resolve_for_profile(self, profile: dict[str, Any] | None, *, current_time: Any) -> Any: ...

    def user_uuid_from_profile(self, profile: dict[str, Any] | None) -> str | None: ...


class ClientWebSettingsService:
    def __init__(
        self,
        db: ClientWebSettingsDatabasePort,
        reference: AppReference,
        time_service: TimeService | None = None,
        *,
        entitlement_provider: ClientWebSettingsEntitlementProvider,
    ) -> None:
        self.db = db
        self.reference = reference
        self.time_service = time_service or TimeService("Europe/Kyiv")
        self.entitlement_provider = entitlement_provider
        self.paywall = PaywallService()

    def get_settings(self, user: dict[str, Any]) -> dict[str, Any]:
        profile = self.db.user_profiles.get_profile(int(user["telegram_user_id"]))
        entitlements = self._resolve_entitlements(profile)
        levels = [row["title"] for row in filter_level_rows(self.reference.language_levels(), entitlements)]
        try:
            support_settings = read_support_settings(self.db)
        except SupportSettingsValidationError as error:
            raise ClientWebSettingsValidationError(str(error)) from error

        return {
            "app_version": self.db.user_learning_settings.get_current_app_version() or "0.0.5",
            "profile": profile,
            "subscription": {
                "import_mode": entitlements.import_mode,
                "reminders_per_day": entitlements.reminders_per_day,
            },
            "levels": levels,
            "interface_locale_options": [
                {"value": "uk", "label": "UK"},
                {"value": "ru", "label": "RU"},
                {"value": "pl", "label": "PL"},
            ],
            "words_per_session_options": list(
                filter_words_per_session_options(self.reference.words_per_session_options(), entitlements)
            ),
            "support_settings": support_settings,
            "google_doc_rescan_schedule": self._google_doc_rescan_schedule(),
            "google_doc_post_upgrade_rescan_pending": self._google_doc_post_upgrade_rescan_pending(profile),
        }

    def update_settings(
        self,
        user: dict[str, Any],
        *,
        interface_locale: str | None,
        language_level: str | None,
        words_per_session: int | None,
        daily_reminder_hour: int | None,
        reminder_weekdays: list[int] | None,
        reminder_schedule: list[dict[str, object]] | None,
    ) -> dict[str, Any]:
        telegram_user_id = int(user["telegram_user_id"])
        if interface_locale is not None:
            if interface_locale not in SUPPORTED_INTERFACE_LOCALES:
                raise ClientWebSettingsValidationError("Unsupported interface locale")
            self.db.user_profiles.set_interface_locale(telegram_user_id, interface_locale)
        if language_level is not None:
            if self.reference.get_level_by_title(language_level) is None:
                raise ClientWebSettingsValidationError("Unknown language level")
            if not is_level_title_allowed(language_level, self._resolve_entitlements_for_user(user)):
                raise ClientWebSettingsValidationError("Language level is not available for current subscription")
            self.db.learning_levels.save_language_level(telegram_user_id, language_level)
        if words_per_session is not None:
            if words_per_session not in self.reference.words_per_session_options():
                raise ClientWebSettingsValidationError("Unsupported words_per_session value")
            if not is_words_per_session_allowed(words_per_session, self._resolve_entitlements_for_user(user)):
                raise ClientWebSettingsValidationError("Words per session value is not available for current subscription")
            self.db.user_learning_settings.set_words_per_session(telegram_user_id, words_per_session)
        if reminder_schedule is not None:
            normalized_schedule = self._normalize_reminder_schedule(reminder_schedule)
            self._ensure_reminder_schedule_allowed(normalized_schedule, self._resolve_entitlements_for_user(user))
            self.db.user_learning_settings.replace_reminder_schedule(telegram_user_id, normalized_schedule)
        elif daily_reminder_hour is not None:
            self.db.user_learning_settings.set_daily_reminder_hour(telegram_user_id, daily_reminder_hour)
        if reminder_schedule is None and reminder_weekdays is not None:
            self.db.user_learning_settings.set_reminder_weekdays(telegram_user_id, reminder_weekdays)
        settings = self.get_settings({**user, "interface_locale": interface_locale or user.get("interface_locale")})
        return {
            **settings,
            "user": {
                **user,
                **(settings.get("profile") or {}),
                "teacher_referral_url": self._build_teacher_referral_url({
                    **user,
                    **(settings.get("profile") or {}),
                }),
            },
        }

    def _build_teacher_referral_url(self, user: dict[str, Any]) -> str | None:
        if user.get("learning_role") != "teacher":
            return None
        return build_teacher_referral_url(
            getattr(self.db.settings, "app_bot_username", ""),
            user.get("user_uuid") or user.get("user_id"),
        )

    def _resolve_entitlements_for_user(self, user: dict[str, Any]):
        profile = self.db.user_profiles.get_profile(int(user["telegram_user_id"]))
        return self._resolve_entitlements(profile)

    def _resolve_entitlements(self, profile: dict[str, Any] | None):
        return self.entitlement_provider.resolve_for_profile(
            profile,
            current_time=self.time_service.now(),
        )

    def _google_doc_rescan_schedule(self) -> dict[str, Any]:
        try:
            runtime_settings = read_user_import_runtime_settings(self.db)
        except UserImportRuntimeSettingsValidationError as error:
            raise ClientWebSettingsValidationError(str(error)) from error
        return {
            "hour": runtime_settings["google_doc_sync_hour"],
            "weekdays": runtime_settings.get("google_doc_sync_weekdays"),
            "interval_days": runtime_settings["google_doc_sync_interval_days"],
        }

    def _google_doc_post_upgrade_rescan_pending(self, profile: dict[str, Any] | None) -> bool:
        user_uuid = self.entitlement_provider.user_uuid_from_profile(profile)
        if not user_uuid:
            return False
        task_logs: ClientWebSettingsTaskLogsPort | None = getattr(self.db, "task_logs", None)
        if task_logs is None or not hasattr(task_logs, "has_active_for_user"):
            return False
        return bool(
            task_logs.has_active_for_user(
                task_type=POST_UPGRADE_GOOGLE_DOC_RESCAN_SCOPE,
                user_uuid=user_uuid,
                statuses={"queued", "processing"},
            )
        )

    def _normalize_reminder_schedule(self, reminder_schedule: list[dict[str, object]]) -> list[dict[str, int | str]]:
        try:
            return normalize_reminder_schedule(reminder_schedule)
        except ValueError as error:
            raise ClientWebSettingsValidationError(str(error)) from error

    def _ensure_reminder_schedule_allowed(self, reminder_schedule: list[dict[str, int | str]], entitlements) -> None:
        per_weekday: dict[int, int] = {}
        for row in enabled_reminder_rows(reminder_schedule):
            weekday = int(row["weekday"])
            per_weekday[weekday] = per_weekday.get(weekday, 0) + 1
            if not self.paywall.can_use(entitlements, CAPABILITY_REMINDERS_PER_DAY, per_weekday[weekday]):
                raise ClientWebSettingsValidationError(
                    "Reminder schedule exceeds reminders_per_day for current subscription"
                )
