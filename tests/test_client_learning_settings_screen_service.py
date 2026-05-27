from __future__ import annotations

from app.application.client_learning.settings_screen_service import (
    ClientLearningSettingsScreenService,
)
from app.subscriptions.plans import FREE_ENTITLEMENTS


class FakeSettingsProfileReader:
    def __init__(self, profile: dict[str, object] | None) -> None:
        self.profile = profile
        self.profile_requests: list[int] = []

    def get_profile(self, telegram_user_id: int) -> dict[str, object] | None:
        self.profile_requests.append(telegram_user_id)
        return self.profile


class FakeReference:
    def language_levels(self) -> list[dict[str, object]]:
        return [{"title": "A1"}, {"title": "A2"}, {"title": "B1"}]

    def words_per_session_options(self) -> tuple[int, ...]:
        return (10, 20, 30)


def build_service(user_profiles: FakeSettingsProfileReader) -> ClientLearningSettingsScreenService:
    return ClientLearningSettingsScreenService(
        user_profiles,
        FakeReference(),
        build_days_suffix=lambda locale, hour, weekdays: f" days:{hour}:{','.join(map(str, weekdays))}",
    )


def test_build_settings_screen_uses_profile_and_days_suffix() -> None:
    user_profiles = FakeSettingsProfileReader(
        {
            "language_level_title": "A2",
            "words_per_session": 20,
            "daily_reminder_hour": 9,
            "reminder_weekdays": [0, 2],
            "import_google_doc_id": "doc-secret",
        }
    )
    service = build_service(user_profiles)

    screen = service.build_settings_screen(telegram_user_id=42, locale="uk", notice="Saved")

    assert user_profiles.profile_requests == [42]
    assert screen.screen_id == "menu:settings"
    assert "Saved" in screen.text
    assert "Поточний рівень: A2" in screen.text
    assert "20 слів" in screen.text
    assert "09:00 days:9:0,2" in screen.text
    assert [button.action for button in screen.buttons] == ["m:levels", "m:modes", "m:n", "m:i", "m:menu"]
    assert screen.metadata == {"buttons_per_row": 1}


def test_build_settings_screen_handles_missing_profile() -> None:
    screen = build_service(FakeSettingsProfileReader(None)).build_settings_screen(telegram_user_id=42, locale="uk")

    assert "Поточний рівень: —" in screen.text
    assert "10 слів" in screen.text
    assert "не налаштовано days:None:" in screen.text


def test_build_level_menu_screen_uses_profile_and_reference_levels() -> None:
    user_profiles = FakeSettingsProfileReader({"language_level_title": "A2"})
    service = build_service(user_profiles)

    screen = service.build_level_menu_screen(telegram_user_id=42, locale="uk", notice="Saved")

    assert user_profiles.profile_requests == [42]
    assert screen.screen_id == "menu:levels"
    assert "Saved" in screen.text
    assert "Поточний рівень: A2" in screen.text
    assert [button.action for button in screen.buttons] == ["m:l:A1", "m:l:A2", "m:l:B1", "m:settings", "m:menu"]
    assert "✓" in screen.buttons[1].text


def test_build_level_menu_screen_handles_missing_profile() -> None:
    service = build_service(FakeSettingsProfileReader(None))

    screen = service.build_level_menu_screen(telegram_user_id=42, locale="uk")

    assert "Поточний рівень: —" in screen.text
    assert [button.action for button in screen.buttons] == ["m:l:A1", "m:l:A2", "m:l:B1", "m:settings", "m:menu"]


def test_build_mode_menu_screen_uses_profile_and_reference_options() -> None:
    user_profiles = FakeSettingsProfileReader({"words_per_session": 20})
    service = build_service(user_profiles)

    screen = service.build_mode_menu_screen(telegram_user_id=77, locale="uk", notice="Saved")

    assert user_profiles.profile_requests == [77]
    assert screen.screen_id == "menu:modes"
    assert "Saved" in screen.text
    assert "20 слів" in screen.text
    assert [button.action for button in screen.buttons] == ["m:w:10", "m:w:20", "m:w:30", "m:settings", "m:menu"]
    assert "✓" in screen.buttons[1].text


def test_build_mode_menu_screen_uses_default_count_without_profile() -> None:
    service = build_service(FakeSettingsProfileReader(None))

    screen = service.build_mode_menu_screen(telegram_user_id=77, locale="uk")

    assert "10 слів" in screen.text
    assert "✓" in screen.buttons[0].text


def test_build_level_menu_screen_filters_levels_by_entitlements() -> None:
    service = ClientLearningSettingsScreenService(
        FakeSettingsProfileReader({"language_level_title": "A2"}),
        FakeReference(),
        build_days_suffix=lambda locale, hour, weekdays: "",
        resolve_entitlements=lambda telegram_user_id: FREE_ENTITLEMENTS,
    )

    screen = service.build_level_menu_screen(telegram_user_id=42, locale="uk")

    assert [button.action for button in screen.buttons] == ["m:l:A1", "m:l:A2", "m:settings", "m:menu"]


def test_build_mode_menu_screen_filters_word_counts_by_entitlements() -> None:
    service = ClientLearningSettingsScreenService(
        FakeSettingsProfileReader({"words_per_session": 20}),
        FakeReference(),
        build_days_suffix=lambda locale, hour, weekdays: "",
        resolve_entitlements=lambda telegram_user_id: FREE_ENTITLEMENTS,
    )

    screen = service.build_mode_menu_screen(telegram_user_id=77, locale="uk")

    assert [button.action for button in screen.buttons] == ["m:w:10", "m:settings", "m:menu"]
