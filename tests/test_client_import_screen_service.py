from __future__ import annotations

from types import SimpleNamespace

from app.application.client_import.screen_service import ClientImportScreenService


class FakeImportScreenUserProfiles:
    def __init__(self) -> None:
        self.profile = {"import_google_doc_id": None}
        self.super_admin_ids = set()

    def get_profile(self, telegram_user_id: int):
        return self.profile

    def is_super_admin(self, telegram_user_id: int) -> bool:
        return telegram_user_id in self.super_admin_ids


def build_settings():
    return SimpleNamespace(
        app_user_import_max_words_per_bind=100,
        app_user_import_test_mode=False,
    )


def test_import_screen_service_builds_default_google_doc_screen() -> None:
    screen = ClientImportScreenService(FakeImportScreenUserProfiles(), build_settings()).build_user_import_screen(1, "uk")

    assert screen.screen_id == "menu:import_words"
    assert "Google Doc" in screen.text
    assert "кожні 3 дні о 00:00" in screen.text
    assert "до 100 нових слів" in screen.text
    assert [button.action for button in screen.buttons] == ["m:settings", "m:menu"]


def test_import_screen_service_shows_test_mode_run_now_only_for_super_admin() -> None:
    user_profiles = FakeImportScreenUserProfiles()
    settings = build_settings()
    settings.app_user_import_test_mode = True

    non_admin_screen = ClientImportScreenService(user_profiles, settings).build_user_import_screen(1, "uk")
    user_profiles.super_admin_ids.add(1)
    admin_screen = ClientImportScreenService(user_profiles, settings).build_user_import_screen(1, "uk")

    assert all(button.action != "m:i:run-now" for button in non_admin_screen.buttons)
    assert any(button.action == "m:i:run-now" for button in admin_screen.buttons)


def test_import_screen_service_shows_masked_bound_doc_and_unbind_action() -> None:
    user_profiles = FakeImportScreenUserProfiles()
    user_profiles.profile["import_google_doc_id"] = "demo"

    screen = ClientImportScreenService(user_profiles, build_settings()).build_user_import_screen(1, "uk", notice="Готово")

    assert "Готово" in screen.text
    assert "Привʼязаний Google Doc" in screen.text
    assert any(button.action == "m:i:unbind" for button in screen.buttons)
