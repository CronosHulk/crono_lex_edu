from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from app.user_import.providers import DEFAULT_OPENAI_API_URL, DEFAULT_USER_IMPORT_OPENAI_MODEL
from app.user_import.services.collecting_resolver import UserImportCollectingResolver


class ProviderFactorySpy:
    def __init__(self, provider: object) -> None:
        self.provider = provider
        self.calls: list[Any] = []

    def __call__(self, settings: Any) -> object:
        self.calls.append(settings)
        return self.provider


class ResolverSpy:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return self.result


def test_collecting_resolver_builds_provider_backed_resolve_request() -> None:
    settings = SimpleNamespace(
        app_user_import_openai_refine_enabled=False,
        app_user_import_openai_model="gpt-test",
        app_user_import_openai_api_url="https://api.example.test/responses",
    )
    details_provider = object()
    artifact_storage_provider = object()
    details_factory = ProviderFactorySpy(details_provider)
    expected_result = object()
    resolver = ResolverSpy(expected_result)
    service = UserImportCollectingResolver(
        settings,
        resolve_pending_import_word=resolver,
        artifact_storage_provider=artifact_storage_provider,
        build_word_details_provider=details_factory,
    )
    current_time = datetime(2026, 4, 26, 12, 0, 0)

    result = service.resolve(
        lookup_word="take over",
        telegram_user_id=42,
        current_time=current_time,
    )

    assert result is expected_result
    assert details_factory.calls == [settings]
    assert resolver.calls == [
        {
            "lookup_word": "take over",
            "telegram_user_id": 42,
            "artifact_storage_provider": artifact_storage_provider,
            "current_time": current_time,
            "openai_refine_enabled": False,
            "openai_model": "gpt-test",
            "openai_api_url": "https://api.example.test/responses",
            "language_level_id_by_title": {},
            "word_details_provider": details_provider,
            "part_of_speech": None,
            "translation_uk": None,
            "translation_ru": None,
            "translation_pl": None,
            "details_retry_feedback": None,
        }
    ]


def test_collecting_resolver_uses_default_openai_settings() -> None:
    settings = SimpleNamespace()
    resolver = ResolverSpy(object())
    service = UserImportCollectingResolver(
        settings,
        resolve_pending_import_word=resolver,
        artifact_storage_provider=object(),
        build_word_details_provider=ProviderFactorySpy(None),
    )

    service.resolve(
        lookup_word="write",
        telegram_user_id=7,
        current_time=datetime(2026, 4, 26, 12, 0, 0),
    )

    assert resolver.calls[0]["openai_refine_enabled"] is True
    assert resolver.calls[0]["openai_model"] == DEFAULT_USER_IMPORT_OPENAI_MODEL
    assert resolver.calls[0]["openai_api_url"] == DEFAULT_OPENAI_API_URL
    assert resolver.calls[0]["word_details_provider"] is None


def test_collecting_resolver_forwards_details_retry_feedback() -> None:
    settings = SimpleNamespace()
    resolver = ResolverSpy(object())
    service = UserImportCollectingResolver(
        settings,
        resolve_pending_import_word=resolver,
        artifact_storage_provider=object(),
        build_word_details_provider=ProviderFactorySpy(None),
    )

    service.resolve(
        lookup_word="take pains",
        telegram_user_id=7,
        current_time=datetime(2026, 4, 26, 12, 0, 0),
        details_retry_feedback="Previous examples did not contain exact lookup_word.",
    )

    assert resolver.calls[0]["details_retry_feedback"] == "Previous examples did not contain exact lookup_word."
