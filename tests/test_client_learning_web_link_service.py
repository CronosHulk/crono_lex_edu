from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from app.application.client_learning.web_link_service import ClientLearningWebLinkService


class FakeClientWebAuthRepository:
    def __init__(self) -> None:
        self.users = {
            1: {
                "id": "00000000-0000-4000-8000-000000000001",
                "telegram_user_id": 1,
                "chat_id": 1001,
            }
        }
        self.magic_links: list[dict[str, object]] = []

    def get_user_by_id(self, telegram_user_id: int) -> dict[str, object] | None:
        return self.users.get(telegram_user_id)

    def create_magic_link(self, **kwargs: object) -> dict[str, object]:
        row = {"id": len(self.magic_links) + 1, "consumed": None, **kwargs}
        self.magic_links.append(row)
        return row


class FixedTimeService:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


def make_settings() -> SimpleNamespace:
    return SimpleNamespace(
        app_web_base_url="https://client.test",
        app_admin_magic_link_ttl_minutes=5,
        bot_token="bot-token",
    )


def test_build_settings_link_screen_uses_client_web_magic_link(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.client_web.auth_service.secrets.token_urlsafe",
        lambda size: "settings-token",
    )
    db = SimpleNamespace(
        settings=make_settings(),
        client_web_auth=FakeClientWebAuthRepository(),
    )
    service = ClientLearningWebLinkService(
        db,
        FixedTimeService(datetime(2026, 5, 19, 12, 0, 0)),
        build_telegram_gateway=lambda settings: SimpleNamespace(),
    )

    screen = service.build_settings_link_screen(1, "uk")

    assert screen.screen_id == "menu:settings:web"
    assert [button.action for button in screen.buttons] == ["web:settings", "m:menu"]
    assert screen.buttons[0].url == "https://client.test/auth/magic?token=settings-token&next=%2Fsettings"
    assert screen.metadata["auto_advance_after_ms"] == 5 * 60 * 1000
    assert db.client_web_auth.magic_links[-1]["target_path"] == "/settings"


def test_build_import_url_uses_client_web_magic_link(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.application.client_web.auth_service.secrets.token_urlsafe",
        lambda size: "import-token",
    )
    db = SimpleNamespace(
        settings=make_settings(),
        client_web_auth=FakeClientWebAuthRepository(),
    )
    service = ClientLearningWebLinkService(
        db,
        FixedTimeService(datetime(2026, 5, 19, 12, 0, 0)),
        build_telegram_gateway=lambda settings: SimpleNamespace(),
    )

    url = service.build_import_url(1)

    assert url == "https://client.test/auth/magic?token=import-token&next=%2Fimport-words"
    assert db.client_web_auth.magic_links[-1]["target_path"] == "/import-words"


def test_web_links_fall_back_to_direct_client_paths_without_auth_repository() -> None:
    db = SimpleNamespace(settings=make_settings())
    service = ClientLearningWebLinkService(
        db,
        FixedTimeService(datetime(2026, 5, 19, 12, 0, 0)),
        build_telegram_gateway=lambda settings: SimpleNamespace(),
    )

    screen = service.build_settings_link_screen(1, "uk")

    assert screen.buttons[0].url == "https://client.test/settings"
    assert service.build_import_url(1) == "https://client.test/import-words"
