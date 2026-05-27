from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.application.client_reminders.action_payload import parse_int_or_none
from app.application.client_reminders.settings_ui import (
    build_button_row_widths,
    build_single_choice_label,
)
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.reference.reminder_schedules import enabled_reminder_rows
from app.reference.scheduling import (
    HOURS_BY_PERIOD,
    WEEKDAY_CODES,
    format_hour_label,
    format_weekday_labels,
    weekday_name,
)

DEFAULT_REMINDERS_PER_DAY = 1


class UserProfileReader(Protocol):
    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None:
        ...


class UserLearningSettingsWriter(Protocol):
    def set_daily_reminder_hour(self, telegram_user_id: int, daily_reminder_hour: int | None) -> None:
        ...

    def list_reminder_schedule(self, telegram_user_id: int) -> list[dict[str, object]]:
        ...

    def replace_reminder_schedule(self, telegram_user_id: int, schedule_rows: list[dict[str, object]]) -> list[dict[str, object]]:
        ...

    def get_reminder_weekdays(self, telegram_user_id: int) -> list[int]:
        ...

    def set_reminder_weekdays(self, telegram_user_id: int, weekdays: list[int]) -> None:
        ...

    def clear_daily_reminder_settings(self, telegram_user_id: int) -> None:
        ...


class ClientReminderSettingsService:
    def __init__(
        self,
        user_profiles: UserProfileReader,
        user_learning_settings: UserLearningSettingsWriter,
        resolve_reminders_per_day: Callable[[int], int] | None = None,
    ) -> None:
        self.user_profiles = user_profiles
        self.user_learning_settings = user_learning_settings
        self.resolve_reminders_per_day = resolve_reminders_per_day or (lambda _telegram_user_id: DEFAULT_REMINDERS_PER_DAY)

    def handle_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel | None:
        if action == "m:n":
            return self.build_notification_menu_screen(telegram_user_id, locale)
        if action == "m:n:pick":
            return self.build_period_screen(telegram_user_id, locale)
        if action == "m:n:days":
            return self.build_weekdays_screen(telegram_user_id, locale)
        if action == "m:n:disable":
            self.user_learning_settings.clear_daily_reminder_settings(telegram_user_id)
            return self.build_notification_menu_screen(
                telegram_user_id,
                locale,
                notice=translate(locale, "reminder_disabled_notice"),
            )
        if action.startswith("m:n:period:"):
            period_code = action.split(":")[-1]
            if period_code not in HOURS_BY_PERIOD:
                return self.build_notification_menu_screen(telegram_user_id, locale)
            return self.build_hour_screen(telegram_user_id, locale, period_code)
        if action.startswith("m:n:hour:"):
            hour = parse_int_or_none(action.split(":")[-1])
            allowed_hours = {item for hours in HOURS_BY_PERIOD.values() for item in hours}
            if hour is None or hour not in allowed_hours:
                return self.build_notification_menu_screen(telegram_user_id, locale)
            return self._handle_hour_action(telegram_user_id, locale, hour)
        if action.startswith("m:n:d:"):
            return self._handle_weekday_action(telegram_user_id, locale, action)
        return None

    def build_notification_menu_screen(
        self,
        telegram_user_id: int,
        locale: str,
        notice: str | None = None,
    ) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        schedule = self._current_schedule(telegram_user_id, profile)
        reminder_hours = self._enabled_hours(schedule)
        reminder_weekdays = self._enabled_weekdays(schedule, profile)
        lines = [translate(locale, "reminder_menu_title")]
        if notice:
            lines.append(notice)
        lines.append(
            translate(
                locale,
                "reminder_menu_current",
                time=", ".join(format_hour_label(hour) for hour in reminder_hours) if reminder_hours else translate(locale, "reminder_not_set"),
            )
        )
        lines.append(
            translate(
                locale,
                "reminder_menu_days",
                days=format_weekday_labels(locale, reminder_weekdays),
            )
        )
        buttons = [
            ButtonModel(action="m:n:pick", text=translate(locale, "reminder_menu_set_button")),
            ButtonModel(action="m:n:days", text=translate(locale, "reminder_menu_days_button")),
            ButtonModel(action="m:n:disable", text=translate(locale, "reminder_menu_disable_button")),
            ButtonModel(action="m:settings", text=translate(locale, "menu_back")),
            ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
        ]
        return ScreenModel(
            screen_id="menu:notifications",
            text="\n\n".join(lines),
            buttons=buttons,
            keyboard_type="inline",
            metadata={"buttons_per_row": 1},
        )

    def build_period_screen(self, telegram_user_id: int, locale: str) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        selected_hours = set(self._enabled_hours(self._current_schedule(telegram_user_id, profile)))
        buttons = [
            ButtonModel(
                action=f"m:n:period:{period}",
                text=build_single_choice_label(
                    translate(locale, f"period_{period}"),
                    bool(selected_hours.intersection(HOURS_BY_PERIOD[period])),
                ),
            )
            for period in ("morning", "day", "evening")
        ]
        buttons.append(ButtonModel(action="m:n", text=translate(locale, "menu_back")))
        buttons.append(ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")))
        return ScreenModel(
            screen_id="menu:notifications:period",
            text=translate(locale, "reminder_period_prompt"),
            buttons=buttons,
            keyboard_type="inline",
            metadata={"buttons_per_row": 1},
        )

    def build_hour_screen(
        self,
        telegram_user_id: int,
        locale: str,
        period_code: str,
        notice: str | None = None,
    ) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        selected_hours = set(self._enabled_hours(self._current_schedule(telegram_user_id, profile)))
        buttons = [
            ButtonModel(
                action=f"m:n:hour:{hour}",
                text=build_single_choice_label(format_hour_label(hour), hour in selected_hours),
            )
            for hour in HOURS_BY_PERIOD[period_code]
        ]
        buttons.append(ButtonModel(action="m:n:pick", text=translate(locale, "menu_back")))
        buttons.append(ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")))
        return ScreenModel(
            screen_id=f"menu:notifications:hours:{period_code}",
            text="\n\n".join(
                item
                for item in [
                    translate(locale, "reminder_hour_prompt", period=translate(locale, f"period_{period_code}")),
                    notice,
                ]
                if item
            ),
            buttons=buttons,
            keyboard_type="inline",
            metadata={"button_row_widths": build_button_row_widths(len(HOURS_BY_PERIOD[period_code]), trailing_full_width_buttons=2)},
        )

    def build_weekdays_screen(
        self,
        telegram_user_id: int,
        locale: str,
        notice: str | None = None,
    ) -> ScreenModel:
        selected = set(self.user_learning_settings.get_reminder_weekdays(telegram_user_id))
        buttons = [
            ButtonModel(
                action=f"m:n:d:toggle:{weekday}",
                text=translate(
                    locale,
                    "reminder_day_selected" if weekday in selected else f"reminder_day_{weekday_name(weekday)}",
                    day=translate(locale, f"reminder_day_{weekday_name(weekday)}"),
                ),
            )
            for weekday in WEEKDAY_CODES
        ]
        buttons.append(ButtonModel(action="m:n:d:save", text=translate(locale, "menu_back")))
        buttons.append(ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")))
        lines = [translate(locale, "reminder_weekdays_prompt")]
        if notice:
            lines.append(notice)
        lines.append(
            translate(
                locale,
                "reminder_menu_days",
                days=format_weekday_labels(locale, list(selected)),
            )
        )
        return ScreenModel(
            screen_id="menu:notifications:days",
            text="\n\n".join(lines),
            buttons=buttons,
            keyboard_type="inline",
            metadata={"button_row_widths": build_button_row_widths(len(WEEKDAY_CODES), trailing_full_width_buttons=2)},
        )

    def _handle_weekday_action(self, telegram_user_id: int, locale: str, action: str) -> ScreenModel:
        parts = action.split(":")
        if len(parts) < 4:
            return self.build_notification_menu_screen(telegram_user_id, locale)
        weekday_action = parts[3]
        weekdays = self.user_learning_settings.get_reminder_weekdays(telegram_user_id)
        if weekday_action == "toggle":
            weekday = parse_int_or_none(parts[4] if len(parts) > 4 else None)
            if weekday not in WEEKDAY_CODES:
                return self.build_weekdays_screen(telegram_user_id, locale)
            updated = [item for item in weekdays if item != weekday] if weekday in weekdays else [*weekdays, weekday]
            self.user_learning_settings.set_reminder_weekdays(telegram_user_id, updated)
            return self.build_weekdays_screen(telegram_user_id, locale)
        if weekday_action == "save":
            if not weekdays:
                return self.build_weekdays_screen(
                    telegram_user_id,
                    locale,
                    notice=translate(locale, "reminder_days_required_notice"),
                )
            return self.build_notification_menu_screen(
                telegram_user_id,
                locale,
                notice=translate(
                    locale,
                    "reminder_weekdays_saved_notice",
                    days=format_weekday_labels(locale, weekdays),
                ),
            )
        return self.build_notification_menu_screen(telegram_user_id, locale)

    def _handle_hour_action(self, telegram_user_id: int, locale: str, hour: int) -> ScreenModel:
        profile = self.user_profiles.get_profile(telegram_user_id)
        schedule = self._current_schedule(telegram_user_id, profile)
        weekdays = self._enabled_weekdays(schedule, profile)
        if not weekdays:
            self.user_learning_settings.set_daily_reminder_hour(telegram_user_id, hour)
            return self.build_weekdays_screen(
                telegram_user_id,
                locale,
                notice=translate(locale, "reminder_saved_notice", time=format_hour_label(hour)),
            )

        selected_hours = self._enabled_hours(schedule)
        if hour in selected_hours:
            updated_hours = [item for item in selected_hours if item != hour]
        else:
            max_hours = max(int(self.resolve_reminders_per_day(telegram_user_id)), 1)
            if len(selected_hours) >= max_hours:
                return self.build_hour_screen(telegram_user_id, locale, self._period_for_hour(hour))
            updated_hours = sorted([*selected_hours, hour])

        self.user_learning_settings.replace_reminder_schedule(
            telegram_user_id,
            [
                {"weekday": weekday, "hour": selected_hour, "status": "enabled"}
                for weekday in weekdays
                for selected_hour in updated_hours
            ],
        )
        return self.build_hour_screen(telegram_user_id, locale, self._period_for_hour(hour))

    def _current_schedule(self, telegram_user_id: int, profile: dict[str, Any] | None) -> list[dict[str, object]]:
        schedule = self.user_learning_settings.list_reminder_schedule(telegram_user_id)
        if schedule:
            return schedule
        reminder_hour = profile.get("daily_reminder_hour") if profile else None
        if reminder_hour is None:
            return []
        return [
            {"weekday": weekday, "hour": reminder_hour, "status": "enabled"}
            for weekday in (profile.get("reminder_weekdays", []) if profile else [])
        ]

    def _enabled_hours(self, schedule: list[dict[str, object]]) -> list[int]:
        return sorted({int(row["hour"]) for row in enabled_reminder_rows(schedule)})

    def _enabled_weekdays(self, schedule: list[dict[str, object]], profile: dict[str, Any] | None) -> list[int]:
        weekdays = sorted({int(row["weekday"]) for row in enabled_reminder_rows(schedule)})
        if weekdays:
            return weekdays
        return sorted({int(weekday) for weekday in (profile.get("reminder_weekdays", []) if profile else [])})

    def _period_for_hour(self, hour: int) -> str:
        for period_code, hours in HOURS_BY_PERIOD.items():
            if hour in hours:
                return period_code
        return "day"
