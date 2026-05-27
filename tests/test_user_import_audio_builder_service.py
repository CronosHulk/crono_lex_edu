from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.user_import.providers import WORD_AUDIO_TASK_KEY
from app.user_import.services.audio_builder import UserImportAudioBuilderService


class FakeProviderSettingsRepository:
    def __init__(self, values: dict[str, dict[str, Any]]) -> None:
        self.values = values

    def get_map(self) -> dict[str, dict[str, Any]]:
        return self.values


class ProviderFactorySpy:
    def __init__(self, provider: object) -> None:
        self.provider = provider
        self.calls: list[tuple[Any, dict[str, Any] | None]] = []

    def __call__(self, settings: Any, task_settings: dict[str, Any] | None) -> Any:
        self.calls.append((settings, task_settings))
        return self.provider


class AudioProviderSpy:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def build_audio(
        self,
        *,
        lookup_word: str,
        audio_dir: Path,
    ) -> tuple[str | None, dict[str, Any], str | None]:
        self.calls.append({"lookup_word": lookup_word, "audio_dir": audio_dir})
        return "word_base/user/take-over.mp3", {"status": "ok"}, None


def test_user_import_audio_builder_uses_configured_provider_task_settings() -> None:
    settings = SimpleNamespace()
    task_settings = {"provider_key": "google_tts", "config": {"voice_name": "en-GB-Neural2-A"}}
    db = SimpleNamespace(
        settings=settings,
        external_provider_settings=FakeProviderSettingsRepository(
            {WORD_AUDIO_TASK_KEY: task_settings}
        ),
    )
    provider = AudioProviderSpy()
    factory = ProviderFactorySpy(provider)
    service = UserImportAudioBuilderService(db, build_audio_provider=factory)

    result = service.build_audio(
        lookup_word="take over",
        audio_dir=Path("runtime/audio"),
    )

    assert result == ("word_base/user/take-over.mp3", {"status": "ok"}, None)
    assert factory.calls == [(settings, task_settings)]
    assert provider.calls == [
        {"lookup_word": "take over", "audio_dir": Path("runtime/audio")}
    ]


def test_user_import_audio_builder_handles_missing_provider_settings_repository() -> None:
    settings = SimpleNamespace()
    db = SimpleNamespace(settings=settings)
    provider = AudioProviderSpy()
    factory = ProviderFactorySpy(provider)
    service = UserImportAudioBuilderService(db, build_audio_provider=factory)

    service.build_audio(
        lookup_word="take over",
        audio_dir=Path("runtime/audio"),
    )

    assert factory.calls == [(settings, None)]
