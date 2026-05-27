from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.application.client_web.teacher_students_errors import (
    ClientWebTeacherStudentConfigurationError,
    ClientWebTeacherStudentConflictError,
    ClientWebTeacherStudentForbiddenError,
    ClientWebTeacherStudentUpstreamError,
    ClientWebTeacherStudentValidationError,
)
from app.application.client_web.teacher_students_service import (
    ClientWebTeacherStudentService,
)
from app.application.client_web.teacher_students_validators import (
    normalize_group_title,
    normalize_teacher_alias,
)
from app.external_providers.video_sessions.google_calendar_meet import (
    GoogleMeetSessionResult,
    GoogleOAuthTokenResult,
)


class FakeTeacherStudentLinks:
    def __init__(self) -> None:
        self.students = {
            "student-1": {
                "teacher_user_id": "teacher-1",
                "student_user_id": "student-1",
                "telegram_user_id": 22,
                "first_name": "Ada",
                "last_name": "Lovelace",
                "username": "ada",
                "chat_id": 2200,
                "teacher_alias": "Ada L.",
            }
        }
        self.connection = None
        self.active_meet_session = None
        self.meet_sessions = []
        self.updated_tokens = []
        self.saved_connections = []
        self.group_update_result = {"id": 1, "title": "Group"}

    def list_students_for_teacher(self, **kwargs):
        return {"items": list(self.students.values()), "page": kwargs["page"], "page_size": kwargs["page_size"], "total": 1, "pages": 1}

    def list_groups_for_teacher(self, **kwargs):
        return []

    def update_student_alias(self, **kwargs):
        student = self.students.get(kwargs["student_user_id"])
        if student is None:
            return None
        student["teacher_alias"] = kwargs["teacher_alias"]
        return {"student_user_id": kwargs["student_user_id"], "teacher_alias": kwargs["teacher_alias"]}

    def update_group_for_teacher(self, **kwargs):
        return self.group_update_result

    def save_google_connection(self, **kwargs):
        self.saved_connections.append(kwargs)
        return {"id": 1}

    def get_student_for_teacher(self, **kwargs):
        return self.students.get(kwargs["student_user_id"])

    def get_google_connection(self, **kwargs):
        return self.connection

    def get_active_meet_session(self, **kwargs):
        return self.active_meet_session

    def update_google_access_token(self, **kwargs):
        self.updated_tokens.append(kwargs)

    def create_meet_session(self, **kwargs):
        self.meet_sessions.append(kwargs)
        return {"id": 1, "join_url": kwargs["join_url"], "calendar_event_id": kwargs["calendar_event_id"]}


class FakeDb:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            app_google_oauth_client_id="client-id",
            google_oauth_client_secret="client-secret",
            app_google_oauth_redirect_uri="https://app.test/api/v1/client-web/google/oauth/callback",
            app_internal_api_token="internal",
            app_web_base_url="https://app.test",
            app_timezone="Europe/Kyiv",
            bot_token="bot",
        )
        self.teacher_student_links = FakeTeacherStudentLinks()
        self.learning_levels = SimpleNamespace(list_levels=lambda: [{"title": "A1"}, {"title": "A2"}])


class FakeTime:
    def __init__(self) -> None:
        self.value = datetime(2026, 5, 11, 9, 0, tzinfo=UTC)

    def now(self):
        return self.value


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.messages = []

    def send_message(self, **kwargs):
        self.messages.append(kwargs)
        return 100


class FailingTelegramGateway(FakeTelegramGateway):
    def send_message(self, **kwargs):
        raise RuntimeError("telegram down")


class FakeGoogleProvider:
    def __init__(self) -> None:
        self.created = []
        self.authorization_states = []

    def authorization_url(self, *, state):
        self.authorization_states.append(state)
        return f"https://accounts.google.test/auth?state={state}"

    def refresh_access_token(self, refresh_token):
        return GoogleOAuthTokenResult(
            access_token="new-access",
            refresh_token=None,
            expires_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
            scope=None,
        )

    def create_meet_session(self, **kwargs):
        self.created.append(kwargs)
        return GoogleMeetSessionResult(calendar_event_id="event-1", join_url="https://meet.google.com/aaa-bbbb-ccc")

    def exchange_code(self, code):
        return GoogleOAuthTokenResult(
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
            scope="calendar",
        )


class FakeTokenCipher:
    def encrypt(self, value):
        return f"encrypted:{value}" if value is not None else None

    def decrypt(self, value):
        return str(value).removeprefix("encrypted:") if value is not None else None


def teacher_user():
    return {"telegram_user_id": 11, "learning_role": "teacher"}


def failing_google_provider_factory():
    raise AssertionError("Google provider should not be used")


def configuration_error_google_provider_factory():
    raise ClientWebTeacherStudentConfigurationError("Google OAuth is not configured")


def test_teacher_student_service_requires_teacher_access() -> None:
    service = ClientWebTeacherStudentService(
        FakeDb(),
        FakeTime(),
        FakeTelegramGateway(),
        failing_google_provider_factory,
    )

    with pytest.raises(ClientWebTeacherStudentForbiddenError) as error:
        service.list_students({"telegram_user_id": 11, "learning_role": "student"}, page=1, page_size=50)

    assert error.value.detail == "Teacher access is required"


def test_update_student_alias_uses_teacher_scoped_link() -> None:
    service = ClientWebTeacherStudentService(
        FakeDb(),
        FakeTime(),
        FakeTelegramGateway(),
        failing_google_provider_factory,
    )

    result = service.update_student_alias(teacher_user(), student_user_id="student-1", teacher_alias="  Ada Teacher  ")

    assert result == {"student_user_id": "student-1", "teacher_alias": "Ada Teacher"}


def test_teacher_student_validators_raise_service_validation_error() -> None:
    with pytest.raises(ClientWebTeacherStudentValidationError) as alias_error:
        normalize_teacher_alias("a" * 81)
    with pytest.raises(ClientWebTeacherStudentValidationError) as blank_group_error:
        normalize_group_title("   ")
    with pytest.raises(ClientWebTeacherStudentValidationError) as long_group_error:
        normalize_group_title("a" * 81)

    assert alias_error.value.detail == "teacher_alias must be at most 80 characters"
    assert blank_group_error.value.detail == "group title is required"
    assert long_group_error.value.detail == "group title must be at most 80 characters"


def test_update_group_returns_conflict_for_duplicate_title() -> None:
    db = FakeDb()
    db.teacher_student_links.group_update_result = {"error": "group_title_exists"}
    service = ClientWebTeacherStudentService(
        db,
        FakeTime(),
        FakeTelegramGateway(),
        failing_google_provider_factory,
    )

    with pytest.raises(ClientWebTeacherStudentConflictError) as error:
        service.update_group(teacher_user(), group_id=1, title="Existing")

    assert error.value.detail == "group_title_exists"


def test_create_meet_session_requires_google_auth() -> None:
    service = ClientWebTeacherStudentService(
        FakeDb(),
        FakeTime(),
        FakeTelegramGateway(),
        failing_google_provider_factory,
    )

    with pytest.raises(ClientWebTeacherStudentConflictError) as error:
        service.create_meet_session(teacher_user(), student_user_id="student-1")

    assert error.value.detail == "google_auth_required"


def test_create_meet_session_refreshes_token_saves_session_and_sends_telegram() -> None:
    db = FakeDb()
    db.teacher_student_links.connection = {
        "refresh_token_ciphertext": "encrypted:refresh",
        "access_token_ciphertext": "encrypted:old",
        "access_token_expires_at": datetime(2026, 5, 11, 8, 0, tzinfo=UTC),
    }
    gateway = FakeTelegramGateway()
    provider = FakeGoogleProvider()
    service = ClientWebTeacherStudentService(
        db,
        FakeTime(),
        gateway,
        lambda: provider,
        token_cipher=FakeTokenCipher(),
    )

    result = service.create_meet_session(teacher_user(), student_user_id="student-1")

    assert result["meet_session"]["join_url"] == "https://meet.google.com/aaa-bbbb-ccc"
    assert db.teacher_student_links.updated_tokens[0]["access_token_ciphertext"] == "encrypted:new-access"
    assert db.teacher_student_links.meet_sessions[0]["calendar_event_id"] == "event-1"
    assert gateway.messages[0]["chat_id"] == 2200
    assert "https://meet.google.com/aaa-bbbb-ccc" in gateway.messages[0]["text"]


def test_create_meet_session_returns_existing_active_session_without_provider_or_telegram() -> None:
    db = FakeDb()
    db.teacher_student_links.active_meet_session = {"id": 7, "join_url": "https://meet.google.com/existing"}
    gateway = FakeTelegramGateway()
    service = ClientWebTeacherStudentService(
        db,
        FakeTime(),
        gateway,
        failing_google_provider_factory,
        token_cipher=FakeTokenCipher(),
    )

    result = service.create_meet_session(teacher_user(), student_user_id="student-1")

    assert result == {"meet_session": {"id": 7, "join_url": "https://meet.google.com/existing"}}
    assert gateway.messages == []
    assert db.teacher_student_links.meet_sessions == []


def test_create_meet_session_does_not_save_active_session_when_telegram_send_fails() -> None:
    db = FakeDb()
    db.teacher_student_links.connection = {
        "refresh_token_ciphertext": "encrypted:refresh",
        "access_token_ciphertext": "encrypted:access",
        "access_token_expires_at": datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
    }
    provider = FakeGoogleProvider()
    service = ClientWebTeacherStudentService(
        db,
        FakeTime(),
        FailingTelegramGateway(),
        lambda: provider,
        token_cipher=FakeTokenCipher(),
    )

    with pytest.raises(ClientWebTeacherStudentUpstreamError) as error:
        service.create_meet_session(teacher_user(), student_user_id="student-1")

    assert error.value.detail == "google_meet_creation_failed"
    assert db.teacher_student_links.meet_sessions == []


def test_google_oauth_state_is_bound_to_current_teacher() -> None:
    db = FakeDb()
    service = ClientWebTeacherStudentService(
        db,
        FakeTime(),
        FakeTelegramGateway(),
        failing_google_provider_factory,
        token_cipher=FakeTokenCipher(),
    )
    state = service._encode_state({"teacher_telegram_user_id": 99, "return_to": "/students"})

    with pytest.raises(ClientWebTeacherStudentValidationError) as error:
        service.complete_google_oauth(teacher_user(), code="code", state=state)

    assert error.value.detail == "Invalid Google OAuth state"
    assert db.teacher_student_links.saved_connections == []


def test_google_oauth_start_uses_injected_provider_factory_configuration_error() -> None:
    service = ClientWebTeacherStudentService(
        FakeDb(),
        FakeTime(),
        FakeTelegramGateway(),
        configuration_error_google_provider_factory,
        token_cipher=FakeTokenCipher(),
    )

    with pytest.raises(ClientWebTeacherStudentConfigurationError) as error:
        service.create_google_oauth_redirect(
            teacher_user(),
            return_to="/students",
            pending_action=None,
            student_user_id=None,
        )

    assert error.value.detail == "Google OAuth is not configured"


def test_google_oauth_callback_saves_connection_for_matching_teacher() -> None:
    db = FakeDb()
    provider = FakeGoogleProvider()
    service = ClientWebTeacherStudentService(
        db,
        FakeTime(),
        FakeTelegramGateway(),
        lambda: provider,
        token_cipher=FakeTokenCipher(),
    )
    state = service._encode_state({"teacher_telegram_user_id": 11, "return_to": "/students"})

    redirect_url = service.complete_google_oauth(teacher_user(), code="code", state=state)

    assert redirect_url == "https://app.test/students?google_auth=success"
    assert db.teacher_student_links.saved_connections[0]["refresh_token_ciphertext"] == "encrypted:refresh"


def test_google_oauth_callback_redirects_error_without_saving_connection() -> None:
    db = FakeDb()
    service = ClientWebTeacherStudentService(
        db,
        FakeTime(),
        FakeTelegramGateway(),
        failing_google_provider_factory,
        token_cipher=FakeTokenCipher(),
    )
    state = service._encode_state(
        {
            "teacher_telegram_user_id": 11,
            "return_to": "/students",
            "pending_action": "create_meet",
            "student_user_id": "student-1",
        }
    )

    redirect_url = service.complete_google_oauth(
        teacher_user(),
        code=None,
        state=state,
        oauth_error="access_denied",
    )

    assert redirect_url == "https://app.test/students?google_auth=error&pending_action=create_meet&student_id=student-1"
    assert db.teacher_student_links.saved_connections == []
