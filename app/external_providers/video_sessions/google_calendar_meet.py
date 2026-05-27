from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import httpx

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


@dataclass(frozen=True)
class GoogleOAuthTokenResult:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scope: str | None


@dataclass(frozen=True)
class GoogleMeetSessionResult:
    calendar_event_id: str | None
    join_url: str


class GoogleCalendarMeetProvider:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def authorization_url(self, *, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_CALENDAR_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> GoogleOAuthTokenResult:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        data = self._post_token(payload)
        return _token_result(data)

    def refresh_access_token(self, refresh_token: str) -> GoogleOAuthTokenResult:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        data = self._post_token(payload)
        return _token_result(data)

    def create_meet_session(
        self,
        *,
        access_token: str,
        summary: str,
        description: str,
        start: datetime,
        end: datetime,
        timezone: str,
    ) -> GoogleMeetSessionResult:
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end.isoformat(), "timeZone": timezone},
            "conferenceData": {
                "createRequest": {
                    "requestId": uuid4().hex,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(timeout=15) as client:
            response = client.post(
                GOOGLE_CALENDAR_EVENTS_URL,
                params={"conferenceDataVersion": "1"},
                headers=headers,
                json=event,
            )
            response.raise_for_status()
            data = response.json()
        join_url = _meet_join_url(data)
        if not join_url:
            raise ValueError("Google Calendar did not return a Meet link")
        return GoogleMeetSessionResult(calendar_event_id=data.get("id"), join_url=join_url)

    def _post_token(self, payload: dict[str, str]) -> dict[str, Any]:
        with httpx.Client(timeout=15) as client:
            response = client.post(GOOGLE_TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()


def _token_result(data: dict[str, Any]) -> GoogleOAuthTokenResult:
    expires_in = int(data.get("expires_in") or 0)
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in) if expires_in > 0 else None
    return GoogleOAuthTokenResult(
        access_token=str(data["access_token"]),
        refresh_token=data.get("refresh_token"),
        expires_at=expires_at,
        scope=data.get("scope"),
    )


def _meet_join_url(data: dict[str, Any]) -> str | None:
    hangout_link = data.get("hangoutLink")
    if isinstance(hangout_link, str) and hangout_link.startswith("https://"):
        return hangout_link
    conference_data = data.get("conferenceData")
    if not isinstance(conference_data, dict):
        return None
    for entry in conference_data.get("entryPoints") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("entryPointType") == "video" and isinstance(entry.get("uri"), str):
            return entry["uri"]
    return None
