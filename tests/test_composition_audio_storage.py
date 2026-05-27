from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.composition.audio_storage as audio_storage_composition


@pytest.mark.parametrize("provider_name", ["filesystem", " FileSystem "])
def test_build_audio_storage_provider_delegates_to_filesystem_provider(
    monkeypatch,
    provider_name: str,
) -> None:
    provider = object()
    settings = SimpleNamespace(app_audio_storage_provider=provider_name)
    calls = []

    def fake_filesystem_audio_storage_provider() -> object:
        calls.append("called")
        return provider

    monkeypatch.setattr(
        audio_storage_composition,
        "filesystem_audio_storage_provider",
        fake_filesystem_audio_storage_provider,
    )

    result = audio_storage_composition.build_audio_storage_provider(settings)

    assert result is provider
    assert calls == ["called"]


@pytest.mark.parametrize(
    "settings",
    [
        None,
        SimpleNamespace(),
        SimpleNamespace(app_audio_storage_provider=""),
        SimpleNamespace(app_audio_storage_provider=None),
    ],
)
def test_build_audio_storage_provider_defaults_to_filesystem_provider(
    monkeypatch,
    settings: object | None,
) -> None:
    provider = object()
    calls = []

    def fake_filesystem_audio_storage_provider() -> object:
        calls.append("called")
        return provider

    monkeypatch.setattr(
        audio_storage_composition,
        "filesystem_audio_storage_provider",
        fake_filesystem_audio_storage_provider,
    )

    result = audio_storage_composition.build_audio_storage_provider(settings)

    assert result is provider
    assert calls == ["called"]


def test_build_audio_storage_provider_rejects_unsupported_provider() -> None:
    settings = SimpleNamespace(app_audio_storage_provider="s3")

    with pytest.raises(
        RuntimeError,
        match="^Unsupported audio storage provider: s3$",
    ):
        audio_storage_composition.build_audio_storage_provider(settings)
