from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.contracts import ScreenModel, TelegramUserContext
from app.helpers.locale import resolve_user_locale
from app.i18n import translate
from app.reference.teacher_referrals import extract_teacher_referral_from_start_text
from app.screen_delivery_policy import with_screen_delivery_policy

StartScreenBuilder = Callable[[int, str], ScreenModel]
CurrentTimeProvider = Callable[[], datetime]


class ClientBootstrapUserProfileRepository(Protocol):
    def upsert_user(self, payload: dict[str, Any]) -> None: ...

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...

    def get_profile_by_user_uuid(self, user_uuid: str) -> dict[str, Any] | None: ...

    def save_user_event(
        self,
        *,
        telegram_user_id: int,
        event_type: str,
        raw_update_json: dict[str, Any],
        message_text: str | None = None,
        callback_data: str | None = None,
    ) -> None: ...


class ClientBootstrapErrorLogRepository(Protocol):
    def create(
        self,
        level: str,
        text: str | list[str],
        *,
        context_json: dict[str, Any] | None = None,
    ) -> None: ...


class ClientBootstrapTeacherStudentLinkRepository(Protocol):
    def assign_student_to_teacher(
        self,
        *,
        teacher_user_id: str,
        student_user_id: str,
        current_time: datetime,
    ) -> dict[str, Any] | None: ...


class ClientBootstrapService:
    def __init__(
        self,
        user_profiles: ClientBootstrapUserProfileRepository,
        error_logs: ClientBootstrapErrorLogRepository,
        *,
        build_start_screen: StartScreenBuilder,
        teacher_student_links: ClientBootstrapTeacherStudentLinkRepository | None = None,
        current_time: CurrentTimeProvider | None = None,
    ) -> None:
        self.user_profiles = user_profiles
        self.error_logs = error_logs
        self.build_start_screen = build_start_screen
        self.teacher_student_links = teacher_student_links
        self.current_time = current_time

    def bootstrap(self, user: TelegramUserContext, message_text: str | None = None) -> ScreenModel:
        self.user_profiles.upsert_user(self.build_user_payload(user))
        profile_reader = getattr(self.user_profiles, "get_profile", None)
        profile = profile_reader(user.telegram_user_id) if profile_reader is not None else None
        locale = resolve_user_locale(profile or user)
        self.user_profiles.save_user_event(
            telegram_user_id=user.telegram_user_id,
            event_type="command_start",
            raw_update_json=user.model_dump(mode="json"),
            message_text=message_text,
        )
        self._apply_teacher_referral(message_text, profile)
        if not self._has_telegram_username(user):
            self.log_missing_username(user)
            return self.build_missing_username_screen(locale)
        return self.build_start_screen(user.telegram_user_id, locale)

    def log_missing_username(self, user: TelegramUserContext) -> None:
        self.error_logs.create(
            "warn",
            "Telegram /start received from user without username.",
            context_json={
                "route": "bootstrap",
                "screen_id": "start:missing_username",
                "telegram_user_id": user.telegram_user_id,
                "chat_id": user.chat_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code,
            },
        )

    def build_missing_username_screen(self, locale: str) -> ScreenModel:
        return with_screen_delivery_policy(
            ScreenModel(
                screen_id="start:missing_username",
                text=translate(locale, "start_missing_username"),
                keyboard_type="inline",
            ),
            force_resend=True,
        )

    def build_unexpected_error_screen(self, user: TelegramUserContext) -> ScreenModel:
        locale = resolve_user_locale(user)
        return with_screen_delivery_policy(
            ScreenModel(
                screen_id="transient:error",
                text=translate(locale, "transient_unexpected_error"),
                keyboard_type="inline",
            ),
            force_resend=True,
            auto_advance_after_ms=5000,
            next_action="m:menu",
        )

    def log_unexpected_error(
        self,
        *,
        route: str,
        user: TelegramUserContext | None,
        error: Exception,
        details: str,
    ) -> None:
        telegram_user_id = getattr(user, "telegram_user_id", None)
        self.error_logs.create(
            "fatal",
            [
                f"route={route}",
                f"telegram_user_id={telegram_user_id}",
                f"error_type={type(error).__name__}",
                f"error_text={error}",
                details,
            ],
        )

    def build_user_payload(self, user: TelegramUserContext) -> dict:
        payload = user.model_dump(mode="json")
        payload["acl_group_id"] = None
        return payload

    def _has_telegram_username(self, user: TelegramUserContext) -> bool:
        return bool(str(user.username or "").strip())

    def _apply_teacher_referral(self, message_text: str | None, student_profile: dict[str, Any] | None) -> None:
        teacher_user_id = extract_teacher_referral_from_start_text(message_text)
        if teacher_user_id is None or student_profile is None:
            return
        if self.teacher_student_links is None or self.current_time is None:
            return
        student_user_id = student_profile.get("user_id") or student_profile.get("user_uuid")
        if not student_user_id or str(student_user_id) == teacher_user_id:
            return
        teacher_profile = self.user_profiles.get_profile_by_user_uuid(teacher_user_id)
        if teacher_profile is None or teacher_profile.get("learning_role") != "teacher":
            return
        if student_profile.get("learning_role") != "student":
            return
        current_time = self.current_time()
        link = self.teacher_student_links.assign_student_to_teacher(
            teacher_user_id=teacher_user_id,
            student_user_id=str(student_user_id),
            current_time=current_time,
        )
        if link is None:
            return
