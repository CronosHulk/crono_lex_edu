from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from httpx import HTTPError as GoogleMeetProviderTransportError

from app.application.client_web.auth_gateways import ClientWebAuthTelegramGateway
from app.application.client_web.learning_service import ClientWebLearningTelegramGateway
from app.application.client_web.teacher_students_service import (
    ClientWebTeacherStudentGoogleMeetProvider,
    ClientWebTeacherStudentTelegramGateway,
)
from app.external_providers.video_sessions.google_calendar_meet import (
    GoogleCalendarMeetProvider,
)
from app.telegram_gateway import TelegramGateway


class GoogleMeetProviderConfigurationError(Exception):
    pass


class GoogleMeetProviderError(Exception):
    pass


def build_client_web_auth_telegram_gateway(settings: Any) -> ClientWebAuthTelegramGateway:
    return TelegramGateway(getattr(settings, "bot_token", ""))


def build_web_learning_telegram_gateway(settings: Any) -> ClientWebLearningTelegramGateway:
    return TelegramGateway(getattr(settings, "bot_token", ""))


def build_teacher_student_telegram_gateway(
    settings: Any,
) -> ClientWebTeacherStudentTelegramGateway:
    return TelegramGateway(getattr(settings, "bot_token", ""))


def build_google_calendar_meet_provider(settings: Any) -> ClientWebTeacherStudentGoogleMeetProvider:
    if not (
        settings.app_google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.app_google_oauth_redirect_uri
    ):
        raise GoogleMeetProviderConfigurationError("Google OAuth is not configured")
    return GoogleCalendarMeetProviderAdapter(
        GoogleCalendarMeetProvider(
            client_id=settings.app_google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            redirect_uri=settings.app_google_oauth_redirect_uri,
        )
    )


class GoogleCalendarMeetProviderAdapter:
    def __init__(self, provider: GoogleCalendarMeetProvider) -> None:
        self.provider = provider

    def authorization_url(self, *, state: str) -> str:
        return self.provider.authorization_url(state=state)

    def exchange_code(self, code: str) -> Any:
        return _call_google_provider(lambda: self.provider.exchange_code(code))

    def refresh_access_token(self, refresh_token: str) -> Any:
        return _call_google_provider(lambda: self.provider.refresh_access_token(refresh_token))

    def create_meet_session(
        self,
        *,
        access_token: str,
        summary: str,
        description: str,
        start: datetime,
        end: datetime,
        timezone: str,
    ) -> Any:
        return _call_google_provider(
            lambda: self.provider.create_meet_session(
                access_token=access_token,
                summary=summary,
                description=description,
                start=start,
                end=end,
                timezone=timezone,
            )
        )


def _call_google_provider(action: Callable[[], Any]) -> Any:
    try:
        return action()
    except (GoogleMeetProviderTransportError, KeyError, ValueError) as error:
        raise GoogleMeetProviderError(str(error)) from error
