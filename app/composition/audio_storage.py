from __future__ import annotations

from app.storage.audio import AudioStorageProvider, filesystem_audio_storage_provider


def build_audio_storage_provider(settings: object | None = None) -> AudioStorageProvider:
    configured_provider = getattr(settings, "app_audio_storage_provider", None)
    provider_name = str(configured_provider).strip().lower() if configured_provider is not None else ""
    if provider_name == "":
        provider_name = "filesystem"

    if provider_name == "filesystem":
        return filesystem_audio_storage_provider()

    raise RuntimeError(f"Unsupported audio storage provider: {provider_name}")
