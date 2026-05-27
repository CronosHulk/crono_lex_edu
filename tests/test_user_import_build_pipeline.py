from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import app.composition.user_import_build_pipeline as user_import_build_pipeline


def test_configure_user_import_build_pipeline_runtime_injects_audio_storage_provider(
    monkeypatch,
) -> None:
    audio_storage_provider = object()
    artifact_storage_provider = object()
    db = SimpleNamespace(
        settings=SimpleNamespace(app_user_import_audio_dir="runtime/audio"),
        user_profiles=object(),
    )
    service = SimpleNamespace(
        reference=SimpleNamespace(language_levels=lambda: []),
        user_import_summary_service=object(),
    )
    captured = {}

    def fake_build_audio_storage_provider(settings: object) -> object:
        captured["audio_storage_settings"] = settings
        return audio_storage_provider

    def fake_build_user_import_artifact_storage_provider(settings: object) -> object:
        captured["artifact_storage_settings"] = settings
        return artifact_storage_provider

    class FakePreparationAccessPolicyAdapter:
        def __init__(self, db_arg: object) -> None:
            captured["preparation_policy_db"] = db_arg

    class FakePreparationService:
        def __init__(self, db_arg: object, access_policy: object) -> None:
            captured["preparation_db"] = db_arg
            captured["preparation_access_policy"] = access_policy

        def prepare_import_job_items(self) -> None:
            raise AssertionError("prepare_import_job_items should not run during composition")

    class FakeAudioBuilderService:
        def __init__(self, db_arg: object, *, build_audio_provider: object) -> None:
            captured["audio_builder"] = (db_arg, build_audio_provider)

        def build_audio(self) -> None:
            raise AssertionError("build_audio should not run during composition")

    class FakeUserDictionaryBuildService:
        def __init__(self, db_arg: object, **kwargs: object) -> None:
            captured["user_dictionary_build"] = (db_arg, kwargs)

    class FakeService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured[self.__class__.__name__] = (args, kwargs)
            captured.setdefault("FakeService_calls", []).append((args, kwargs))

    monkeypatch.setattr(
        user_import_build_pipeline,
        "build_audio_storage_provider",
        fake_build_audio_storage_provider,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "build_user_import_artifact_storage_provider",
        fake_build_user_import_artifact_storage_provider,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "UserImportPreparationService",
        FakePreparationService,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "UserImportPreparationAccessPolicyAdapter",
        FakePreparationAccessPolicyAdapter,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "UserImportCollectingResolver",
        FakeService,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "UserImportJobTaskResultService",
        FakeService,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "UserImportJobProcessingService",
        FakeService,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "UserImportNotificationService",
        FakeService,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "UserImportAudioBuilderService",
        FakeAudioBuilderService,
    )
    monkeypatch.setattr(
        user_import_build_pipeline,
        "UserDictionaryBuildService",
        FakeUserDictionaryBuildService,
    )

    user_import_build_pipeline.configure_user_import_build_pipeline_runtime(
        service,
        db,
        lambda name: f"helper:{name}",
    )

    user_dictionary_build_db, user_dictionary_build_kwargs = captured[
        "user_dictionary_build"
    ]
    assert captured["audio_storage_settings"] is db.settings
    assert captured["artifact_storage_settings"] is db.settings
    assert service.user_import_artifact_storage_provider is artifact_storage_provider
    assert captured["FakeService_calls"][0][1]["artifact_storage_provider"] is artifact_storage_provider
    assert captured["preparation_db"] is db
    assert captured["preparation_policy_db"] is db
    assert isinstance(captured["preparation_access_policy"], FakePreparationAccessPolicyAdapter)
    assert user_dictionary_build_db is db
    assert user_dictionary_build_kwargs["audio_storage_provider"] is audio_storage_provider
    assert user_dictionary_build_kwargs["user_audio_root"] == "runtime/audio"
    assert user_dictionary_build_kwargs["resolver"] is service.user_import_collecting_resolver
    audio_builder = user_dictionary_build_kwargs["audio_builder"]
    assert getattr(audio_builder, "__self__", None) is service.user_import_audio_builder_service
    assert getattr(audio_builder, "__func__", None) is FakeAudioBuilderService.build_audio


def test_preparation_access_policy_allows_new_entries_without_subscription() -> None:
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    db = SimpleNamespace(user_dictionary=object())
    policy = user_import_build_pipeline.UserImportPreparationAccessPolicyAdapter(db)
    policy.entitlement_resolver = SimpleNamespace(
        subscription_for_user_uuid=lambda user_uuid: None,
    )

    assert policy.can_create_new_user_dictionary_entry(
        user_uuid,
        current_time=datetime(2026, 5, 6, 10, 0, 0),
    )


def test_preparation_access_policy_counts_weekly_import_quota_from_monday() -> None:
    user_uuid = UUID("11111111-1111-4111-8111-111111111111")
    captured = {}

    class FakeEntitlements:
        new_import_words_per_week = 2

    class FakeUserDictionary:
        def count_entries_created_by_user_since(self, user_uuid_arg: UUID, *, since: datetime) -> int:
            captured["count"] = (user_uuid_arg, since)
            return 2

    db = SimpleNamespace(user_dictionary=FakeUserDictionary())
    policy = user_import_build_pipeline.UserImportPreparationAccessPolicyAdapter(db)
    policy.entitlement_resolver = SimpleNamespace(
        subscription_for_user_uuid=lambda user_uuid: {"plan_key": "premium"},
        resolve_subscription=lambda subscription, *, current_time: FakeEntitlements(),
    )

    assert not policy.can_create_new_user_dictionary_entry(
        user_uuid,
        current_time=datetime(2026, 5, 6, 10, 0, 0),
    )
    assert captured["count"] == (user_uuid, datetime(2026, 5, 4, 0, 0, 0))
