from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlencode

from app.application.client_web.teacher_students_errors import (
    ClientWebTeacherStudentConfigurationError,
    ClientWebTeacherStudentConflictError,
    ClientWebTeacherStudentError,
    ClientWebTeacherStudentForbiddenError,
    ClientWebTeacherStudentNotFoundError,
    ClientWebTeacherStudentUpstreamError,
    ClientWebTeacherStudentValidationError,
)
from app.application.client_web.teacher_students_validators import (
    normalize_group_title,
    normalize_teacher_alias,
)
from app.security.token_cipher import TokenCipher

GOOGLE_MEET_ERROR_DETAIL = "google_meet_creation_failed"


class ClientWebTeacherStudentSettingsPort(Protocol):
    app_google_oauth_client_id: str
    google_oauth_client_secret: str
    app_google_oauth_redirect_uri: str
    app_internal_api_token: str
    app_web_base_url: str
    app_timezone: str
    bot_token: str


class ClientWebTeacherStudentLearningLevelsPort(Protocol):
    def list_levels(self) -> list[dict[str, Any]]: ...


class ClientWebTeacherStudentLinksPort(Protocol):
    def list_students_for_teacher(self, **kwargs: Any) -> dict[str, Any]: ...

    def list_groups_for_teacher(self, **kwargs: Any) -> list[dict[str, Any]]: ...

    def create_group_for_teacher(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def update_group_for_teacher(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def archive_group_for_teacher(self, **kwargs: Any) -> bool: ...

    def update_student_alias(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def update_student_level(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def update_student_group(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def save_google_connection(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def get_student_for_teacher(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def get_active_meet_session(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def get_google_connection(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def create_meet_session(self, **kwargs: Any) -> dict[str, Any] | None: ...

    def update_google_access_token(self, **kwargs: Any) -> Any: ...


class ClientWebTeacherStudentDatabasePort(Protocol):
    settings: ClientWebTeacherStudentSettingsPort
    learning_levels: ClientWebTeacherStudentLearningLevelsPort
    teacher_student_links: ClientWebTeacherStudentLinksPort


class ClientWebTeacherStudentTimeService(Protocol):
    def now(self) -> datetime: ...


class ClientWebTeacherStudentTelegramGateway(Protocol):
    def send_message(
        self,
        *,
        chat_id: int | str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        disable_notification: bool = False,
        ignore_errors: bool = False,
    ) -> int | None: ...


class ClientWebTeacherStudentOAuthTokenResult(Protocol):
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scope: str


class ClientWebTeacherStudentMeetSessionResult(Protocol):
    calendar_event_id: str
    join_url: str


class ClientWebTeacherStudentGoogleMeetProvider(Protocol):
    def authorization_url(self, *, state: str) -> str: ...

    def exchange_code(self, code: str) -> ClientWebTeacherStudentOAuthTokenResult: ...

    def refresh_access_token(self, refresh_token: str) -> ClientWebTeacherStudentOAuthTokenResult: ...

    def create_meet_session(
        self,
        *,
        access_token: str,
        summary: str,
        description: str,
        start: datetime,
        end: datetime,
        timezone: str,
    ) -> ClientWebTeacherStudentMeetSessionResult: ...


class ClientWebTeacherStudentService:
    def __init__(
        self,
        db: ClientWebTeacherStudentDatabasePort,
        time_service: ClientWebTeacherStudentTimeService,
        telegram_gateway: ClientWebTeacherStudentTelegramGateway,
        google_provider_factory: Callable[[], ClientWebTeacherStudentGoogleMeetProvider],
        token_cipher: TokenCipher | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.telegram_gateway = telegram_gateway
        self.google_provider_factory = google_provider_factory
        self._token_cipher = token_cipher

    def list_students(
        self,
        user: dict[str, Any],
        *,
        page: int,
        page_size: int,
        name: str = "",
        login: str = "",
        level: str = "",
        group_id: int | None = None,
    ) -> dict[str, Any]:
        self._require_teacher(user)
        self._validate_level(level)
        return {
            **self.db.teacher_student_links.list_students_for_teacher(
                teacher_telegram_user_id=int(user["telegram_user_id"]),
                page=page,
                page_size=page_size,
                name=name,
                login=login,
                level=level,
                group_id=group_id,
            ),
            "filters": self.filter_metadata(user),
        }

    def filter_metadata(self, user: dict[str, Any]) -> dict[str, Any]:
        self._require_teacher(user)
        return {
            "levels": [{"value": row["title"], "label": row["title"]} for row in self.db.learning_levels.list_levels()],
            "groups": self.list_groups(user)["items"],
        }

    def list_groups(self, user: dict[str, Any]) -> dict[str, Any]:
        self._require_teacher(user)
        return {
            "items": self.db.teacher_student_links.list_groups_for_teacher(
                teacher_telegram_user_id=int(user["telegram_user_id"])
            )
        }

    def create_group(self, user: dict[str, Any], *, title: str) -> dict[str, Any]:
        self._require_teacher(user)
        row = self.db.teacher_student_links.create_group_for_teacher(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            title=normalize_group_title(title),
            current_time=self.time_service.now(),
        )
        if row is None:
            raise ClientWebTeacherStudentNotFoundError("Teacher profile not found")
        return {"group": row}

    def update_group(self, user: dict[str, Any], *, group_id: int, title: str) -> dict[str, Any]:
        self._require_teacher(user)
        row = self.db.teacher_student_links.update_group_for_teacher(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            group_id=group_id,
            title=normalize_group_title(title),
            current_time=self.time_service.now(),
        )
        if row == {"error": "group_title_exists"}:
            raise ClientWebTeacherStudentConflictError("group_title_exists")
        if row is None:
            raise ClientWebTeacherStudentNotFoundError("Student group not found")
        return {"group": row}

    def delete_group(self, user: dict[str, Any], *, group_id: int) -> dict[str, str]:
        self._require_teacher(user)
        ok = self.db.teacher_student_links.archive_group_for_teacher(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            group_id=group_id,
            current_time=self.time_service.now(),
        )
        if not ok:
            raise ClientWebTeacherStudentNotFoundError("Student group not found")
        return {"status": "ok"}

    def update_student_alias(self, user: dict[str, Any], *, student_user_id: str, teacher_alias: str | None) -> dict[str, Any]:
        self._require_teacher(user)
        row = self.db.teacher_student_links.update_student_alias(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            student_user_id=student_user_id,
            teacher_alias=normalize_teacher_alias(teacher_alias),
            current_time=self.time_service.now(),
        )
        if row is None:
            raise ClientWebTeacherStudentNotFoundError("Student not found")
        return row

    def update_student_level(self, user: dict[str, Any], *, student_user_id: str, language_level: str) -> dict[str, Any]:
        self._require_teacher(user)
        self._validate_level(language_level)
        row = self.db.teacher_student_links.update_student_level(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            student_user_id=student_user_id,
            level_title=language_level,
            current_time=self.time_service.now(),
        )
        if row is None:
            raise ClientWebTeacherStudentNotFoundError("Student not found")
        return row

    def update_student_group(self, user: dict[str, Any], *, student_user_id: str, group_id: int | None) -> dict[str, Any]:
        self._require_teacher(user)
        row = self.db.teacher_student_links.update_student_group(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            student_user_id=student_user_id,
            group_id=group_id,
            current_time=self.time_service.now(),
        )
        if row is None:
            raise ClientWebTeacherStudentNotFoundError("Student or group not found")
        return row

    def create_google_oauth_redirect(
        self,
        user: dict[str, Any],
        *,
        return_to: str,
        pending_action: str | None,
        student_user_id: str | None,
    ) -> str:
        self._require_teacher(user)
        provider = self._google_provider()
        state = self._encode_state(
            {
                "teacher_telegram_user_id": int(user["telegram_user_id"]),
                "return_to": _safe_return_path(return_to),
                "pending_action": pending_action,
                "student_user_id": student_user_id,
            }
        )
        return provider.authorization_url(state=state)

    def complete_google_oauth(
        self,
        user: dict[str, Any],
        *,
        code: str | None,
        state: str,
        oauth_error: str | None = None,
    ) -> str:
        self._require_teacher(user)
        state_payload = self._decode_state(state)
        if int(state_payload.get("teacher_telegram_user_id") or 0) != int(user["telegram_user_id"]):
            raise ClientWebTeacherStudentValidationError("Invalid Google OAuth state")
        if oauth_error or not code:
            return _oauth_return_url(self.db.settings.app_web_base_url, state_payload, status="error")
        try:
            provider = self._google_provider()
            token_result = provider.exchange_code(code)
        except ClientWebTeacherStudentConfigurationError:
            raise
        except Exception:
            return _oauth_return_url(self.db.settings.app_web_base_url, state_payload, status="error")
        if not token_result.refresh_token:
            return _oauth_return_url(self.db.settings.app_web_base_url, state_payload, status="error")
        cipher = self._get_token_cipher()
        saved = self.db.teacher_student_links.save_google_connection(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            refresh_token_ciphertext=cipher.encrypt(token_result.refresh_token),
            access_token_ciphertext=cipher.encrypt(token_result.access_token),
            access_token_expires_at=token_result.expires_at,
            scope=token_result.scope,
            current_time=self.time_service.now(),
        )
        if saved is None:
            raise ClientWebTeacherStudentNotFoundError("Teacher profile not found")
        return _oauth_return_url(self.db.settings.app_web_base_url, state_payload, status="success")

    def create_meet_session(self, user: dict[str, Any], *, student_user_id: str) -> dict[str, Any]:
        self._require_teacher(user)
        student = self.db.teacher_student_links.get_student_for_teacher(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            student_user_id=student_user_id,
        )
        if student is None:
            raise ClientWebTeacherStudentNotFoundError("Student not found")
        active_session = self.db.teacher_student_links.get_active_meet_session(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            student_user_id=student_user_id,
        )
        if active_session is not None:
            return {"meet_session": active_session}
        connection = self.db.teacher_student_links.get_google_connection(teacher_telegram_user_id=int(user["telegram_user_id"]))
        if connection is None:
            raise ClientWebTeacherStudentConflictError("google_auth_required")
        try:
            access_token = self._resolve_access_token(user, connection)
            current_time = self.time_service.now()
            end_time = current_time + timedelta(hours=1)
            provider_result = self._google_provider().create_meet_session(
                access_token=access_token,
                summary=f"CronoLex lesson: {_student_display_name(student)}",
                description="CronoLex teacher-student lesson.",
                start=current_time,
                end=end_time,
                timezone=self.db.settings.app_timezone,
            )
            self._send_meet_link_to_student(student, provider_result.join_url)
            session = self.db.teacher_student_links.create_meet_session(
                teacher_telegram_user_id=int(user["telegram_user_id"]),
                student_user_id=student_user_id,
                calendar_event_id=provider_result.calendar_event_id,
                join_url=provider_result.join_url,
                current_time=current_time,
            )
            if session is None:
                raise ClientWebTeacherStudentNotFoundError("Student not found")
            return {"meet_session": session}
        except ClientWebTeacherStudentError:
            raise
        except Exception:
            raise ClientWebTeacherStudentUpstreamError(GOOGLE_MEET_ERROR_DETAIL) from None

    def _resolve_access_token(self, user: dict[str, Any], connection: dict[str, Any]) -> str:
        cipher = self._get_token_cipher()
        expires_at = connection.get("access_token_expires_at")
        access_token = cipher.decrypt(connection.get("access_token_ciphertext"))
        now = self.time_service.now()
        if access_token and expires_at is not None and expires_at > now + timedelta(minutes=2):
            return str(access_token)
        refresh_token = cipher.decrypt(connection.get("refresh_token_ciphertext"))
        if not refresh_token:
            raise ClientWebTeacherStudentConflictError("google_auth_required")
        token_result = self._google_provider().refresh_access_token(refresh_token)
        self.db.teacher_student_links.update_google_access_token(
            teacher_telegram_user_id=int(user["telegram_user_id"]),
            access_token_ciphertext=cipher.encrypt(token_result.access_token),
            access_token_expires_at=token_result.expires_at,
            current_time=now,
        )
        return token_result.access_token

    def _send_meet_link_to_student(self, student: dict[str, Any], join_url: str) -> None:
        chat_id = student.get("chat_id")
        if chat_id is None:
            raise ClientWebTeacherStudentValidationError("Student does not have Telegram chat_id")
        text = f"Ваш викладач створив Google Meet для заняття:\n{join_url}"
        self.telegram_gateway.send_message(chat_id=int(chat_id), text=text)

    def _google_provider(self) -> ClientWebTeacherStudentGoogleMeetProvider:
        return self.google_provider_factory()

    def _get_token_cipher(self) -> TokenCipher:
        if self._token_cipher is not None:
            return self._token_cipher
        try:
            self._token_cipher = TokenCipher(getattr(self.db.settings, "google_oauth_token_secret", ""))
        except ValueError as exc:
            raise ClientWebTeacherStudentConfigurationError("Google OAuth token encryption is not configured") from exc
        return self._token_cipher

    def _require_teacher(self, user: dict[str, Any]) -> None:
        if user.get("learning_role") != "teacher":
            raise ClientWebTeacherStudentForbiddenError("Teacher access is required")

    def _validate_level(self, level: str) -> None:
        if level and level not in {row["title"] for row in self.db.learning_levels.list_levels()}:
            raise ClientWebTeacherStudentValidationError("Unsupported language level")

    def _encode_state(self, payload: dict[str, Any]) -> str:
        raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        signature = hmac.new(_state_secret(self.db.settings), raw_payload, hashlib.sha256).digest()
        payload_part = base64.urlsafe_b64encode(raw_payload).decode().rstrip("=")
        signature_part = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        return f"{payload_part}.{signature_part}"

    def _decode_state(self, state: str) -> dict[str, Any]:
        try:
            payload_part, signature_part = state.split(".", 1)
            raw_payload = base64.urlsafe_b64decode((payload_part + "=" * (-len(payload_part) % 4)).encode())
            signature = base64.urlsafe_b64decode((signature_part + "=" * (-len(signature_part) % 4)).encode())
        except Exception:
            raise ClientWebTeacherStudentValidationError("Invalid Google OAuth state") from None
        expected = hmac.new(_state_secret(self.db.settings), raw_payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ClientWebTeacherStudentValidationError("Invalid Google OAuth state")
        return json.loads(raw_payload.decode())


def _state_secret(settings: Any) -> bytes:
    value = settings.app_internal_api_token or settings.google_oauth_client_secret or settings.bot_token
    return str(value).encode()


def _safe_return_path(value: str) -> str:
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/students"
    return value[:512]


def _oauth_return_url(base_url: str, state_payload: dict[str, Any], *, status: str) -> str:
    return_to = _safe_return_path(str(state_payload.get("return_to") or "/students"))
    query = {
        "google_auth": status,
    }
    if state_payload.get("pending_action"):
        query["pending_action"] = str(state_payload["pending_action"])
    if state_payload.get("student_user_id"):
        query["student_id"] = str(state_payload["student_user_id"])
    separator = "&" if "?" in return_to else "?"
    return f"{base_url.rstrip('/')}{return_to}{separator}{urlencode(query)}"


def _student_display_name(student: dict[str, Any]) -> str:
    alias = str(student.get("teacher_alias") or "").strip()
    if alias:
        return alias
    name = " ".join(str(student.get(field) or "").strip() for field in ("first_name", "last_name")).strip()
    if name:
        return name
    username = str(student.get("username") or "").strip()
    return f"@{username}" if username else f"student {student['telegram_user_id']}"
