from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.application.admin.user_dictionary.bulk import AdminUserDictionaryBulkAction
from app.application.admin.user_dictionary.errors import (
    AdminUserDictionaryActionAccessDeniedError,
    AdminUserDictionaryActionNotFoundError,
    AdminUserDictionaryActionValidationError,
)
from app.application.admin.user_dictionary.promote import AdminUserDictionaryPromoteAction


class FakeAclPermissionRepository:
    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        if group_title == "admin" and action == "dictionary/update_word" and environment == "web_admin":
            return "enabled"
        return "disabled"

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        return []


class FakeSettings:
    app_dictionary_audio_dir = "word_base/base"
    app_user_import_audio_dir = "word_base/user"


class FakeUserDictionaryRepository:
    def __init__(self, entry: dict | None, *, entries: list[dict] | None = None, fail_promote: bool = False) -> None:
        self.entries = entries or ([entry] if entry else [])
        self.fail_promote = fail_promote
        self.promoted_args = None
        self.promoted_ids = []
        self.marked_args = None
        self.requeued_details: list[dict] = []
        self.requeued_embeddings: list[dict] = []
        self.updated_statuses: list[dict] = []
        self.archived_assignment_entries: list[dict] = []

    def get_entry(self, entry_id: int) -> dict | None:
        for entry in self.entries:
            if entry["id"] == entry_id:
                return dict(entry)
        return None

    def promote_entry_to_core(self, entry_id: int, **kwargs) -> dict:
        if self.fail_promote:
            raise RuntimeError("db failed")
        self.promoted_args = {"entry_id": entry_id, **kwargs}
        self.promoted_ids.append(entry_id)
        entry = self.get_entry(entry_id) or {}
        return {"id": 70 + entry_id, "word": entry.get("word"), "audio_path": kwargs["audio_path"]}

    def mark_entry_promoted(self, entry_id: int, **kwargs) -> dict:
        self.marked_args = {"entry_id": entry_id, **kwargs}
        return {**self.entry, "promoted_dictionary_entry_id": kwargs["dictionary_entry_id"]}

    def requeue_entry_details_build(self, entry_id: int, **kwargs) -> dict:
        self.requeued_details.append({"entry_id": entry_id, **kwargs})
        entry = self.get_entry(entry_id) or {}
        return {**entry, "status": "queued_for_details"}

    def requeue_entry_embedding_build(self, entry_id: int, **kwargs) -> dict:
        self.requeued_embeddings.append({"entry_id": entry_id, **kwargs})
        entry = self.get_entry(entry_id) or {}
        return {**entry, "status": "queued_for_embedding", "is_embedding_ready": False}

    def update_entry_status(self, entry_id: int, **kwargs) -> dict:
        self.updated_statuses.append({"entry_id": entry_id, **kwargs})
        entry = self.get_entry(entry_id) or {}
        return {**entry, "status": kwargs["status"], "source_provider_status_json": kwargs.get("source_provider_status_json")}

    def archive_assignments_for_entry(self, entry_id: int, **kwargs) -> int:
        self.archived_assignment_entries.append({"entry_id": entry_id, **kwargs})
        return 1


class FakeImportItemsRepository:
    def __init__(self) -> None:
        self.synced: list[dict] = []

    def sync_for_user_dictionary_entry(self, entry_id: int, **kwargs) -> None:
        self.synced.append({"entry_id": entry_id, **kwargs})


class FakeAdminDictionaryRepository:
    def get_entry(self, entry_id: int) -> dict | None:
        if entry_id == 77:
            return {"id": 77, "word": "cord"}
        return None


class FakeDb:
    def __init__(self, entry: dict | None = None, *, entries: list[dict] | None = None, fail_promote: bool = False) -> None:
        self.acl_permissions = FakeAclPermissionRepository()
        self.admin_dictionary = FakeAdminDictionaryRepository()
        self.settings = FakeSettings()
        self.user_dictionary = FakeUserDictionaryRepository(entry, entries=entries, fail_promote=fail_promote)
        self.user_import_items = FakeImportItemsRepository()


class FakeTimeService:
    def now(self) -> datetime:
        return datetime(2026, 5, 3, 12, 0, 0)


class FakeAudioStorageProvider:
    def __init__(self, existing_paths: set[str] | None = None) -> None:
        self.existing_paths = set(existing_paths or set())
        self.exists_calls: list[str] = []
        self.copy_calls: list[tuple[str, str]] = []
        self.delete_calls: list[tuple[str, list[str]]] = []

    def resolve_local_path(self, audio_path):
        return Path(str(audio_path))

    def exists(self, audio_path) -> bool:
        path = str(audio_path)
        self.exists_calls.append(path)
        return path in self.existing_paths

    def write_bytes_atomic(self, audio_path, payload: bytes) -> str:
        raise AssertionError("write_bytes_atomic should not be called")

    def copy(self, source_audio_path, target_audio_path) -> str:
        source = str(source_audio_path)
        target = str(target_audio_path)
        self.copy_calls.append((source, target))
        self.existing_paths.add(target)
        return target

    def delete_if_under_roots(self, audio_path, audio_roots) -> bool:
        path = str(audio_path)
        roots = [str(root) for root in audio_roots]
        self.delete_calls.append((path, roots))
        self.existing_paths.discard(path)
        return True


def test_promote_user_dictionary_entry_copies_audio_and_marks_promoted() -> None:
    source_audio_path = "word_base/user/noun/cord.mp3"
    target_audio_path = "word_base/base/noun/cord.mp3"
    db = FakeDb(
        {
            "id": 5,
            "word": "cord",
            "part_of_speech": "noun",
            "audio_path": source_audio_path,
            "status": "ready_for_rotation",
        }
    )
    storage_provider = FakeAudioStorageProvider({source_audio_path})
    action = AdminUserDictionaryPromoteAction(
        db,
        FakeTimeService(),
        audio_storage_provider=storage_provider,
    )

    result = action.promote_entry(actor={"acl_group_title": "admin"}, entry_id=5)

    assert result["dictionary_entry"]["id"] == 75
    assert source_audio_path not in storage_provider.existing_paths
    assert target_audio_path in storage_provider.existing_paths
    assert storage_provider.copy_calls == [(source_audio_path, target_audio_path)]
    assert storage_provider.delete_calls == [(source_audio_path, ["word_base/user"])]
    assert db.user_dictionary.promoted_args["audio_path"] == target_audio_path


def test_promote_user_dictionary_entry_uses_injected_audio_storage_provider() -> None:
    source_audio_path = "word_base/user/noun/cord.mp3"
    target_audio_path = "word_base/base/noun/cord.mp3"
    db = FakeDb(
        {
            "id": 5,
            "word": "cord",
            "part_of_speech": "noun",
            "audio_path": source_audio_path,
            "status": "ready_for_rotation",
        }
    )
    storage_provider = FakeAudioStorageProvider({source_audio_path})
    action = AdminUserDictionaryPromoteAction(
        db,
        FakeTimeService(),
        audio_storage_provider=storage_provider,
    )

    result = action.promote_entry(actor={"acl_group_title": "admin"}, entry_id=5)

    assert result["dictionary_entry"]["audio_path"] == target_audio_path
    assert result["entry"]["audio_path"] == target_audio_path
    assert db.user_dictionary.promoted_args["audio_path"] == target_audio_path
    assert storage_provider.exists_calls == [
        target_audio_path,
        source_audio_path,
        target_audio_path,
        source_audio_path,
    ]
    assert storage_provider.copy_calls == [(source_audio_path, target_audio_path)]
    assert storage_provider.delete_calls == [(source_audio_path, ["word_base/user"])]


def test_promote_user_dictionary_entry_raises_application_error_for_denied_access() -> None:
    action = AdminUserDictionaryPromoteAction(
        FakeDb(
            {
                "id": 5,
                "word": "cord",
                "part_of_speech": "noun",
                "audio_path": "word_base/user/noun/cord.mp3",
                "status": "ready_for_rotation",
            }
        ),
        FakeTimeService(),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    with pytest.raises(AdminUserDictionaryActionAccessDeniedError) as error_info:
        action.promote_entry(actor={"acl_group_title": "student"}, entry_id=5)

    assert error_info.value.detail == "User dictionary promotion is not allowed"


def test_bulk_promote_user_dictionary_entries_validates_all_before_promoting() -> None:
    source_audio_path = "word_base/user/noun/cord.mp3"
    db = FakeDb(
        entries=[
            {
                "id": 5,
                "word": "cord",
                "part_of_speech": "noun",
                "audio_path": source_audio_path,
                "status": "ready_for_rotation",
            },
            {
                "id": 6,
                "word": "spark",
                "part_of_speech": "noun",
                "audio_path": "word_base/user/noun/spark.mp3",
                "status": "queued_for_audio",
            },
        ],
    )
    storage_provider = FakeAudioStorageProvider({source_audio_path})
    action = AdminUserDictionaryPromoteAction(
        db,
        FakeTimeService(),
        audio_storage_provider=storage_provider,
    )

    with pytest.raises(AdminUserDictionaryActionValidationError) as error_info:
        action.promote_entries(actor={"acl_group_title": "admin"}, entry_ids=[5, 6])

    assert "Only ready" in error_info.value.detail

    assert db.user_dictionary.promoted_ids == []
    assert storage_provider.existing_paths == {source_audio_path}
    assert storage_provider.copy_calls == []
    assert storage_provider.delete_calls == []


def test_promote_user_dictionary_entry_keeps_user_audio_when_db_promotion_fails() -> None:
    source_audio_path = "word_base/user/noun/cord.mp3"
    target_audio_path = "word_base/base/noun/cord.mp3"
    storage_provider = FakeAudioStorageProvider({source_audio_path})
    action = AdminUserDictionaryPromoteAction(
        FakeDb(
            {
                "id": 5,
                "word": "cord",
                "part_of_speech": "noun",
                "audio_path": source_audio_path,
                "status": "ready_for_rotation",
            },
            fail_promote=True,
        ),
        FakeTimeService(),
        audio_storage_provider=storage_provider,
    )

    try:
        action.promote_entry(actor={"acl_group_title": "admin"}, entry_id=5)
    except RuntimeError as error:
        assert "db failed" in str(error)
    else:  # pragma: no cover
        raise AssertionError("RuntimeError was expected")

    assert storage_provider.existing_paths == {source_audio_path, target_audio_path}
    assert storage_provider.copy_calls == [(source_audio_path, target_audio_path)]
    assert storage_provider.delete_calls == []


def test_promote_user_dictionary_entry_rejects_not_ready_entry() -> None:
    storage_provider = FakeAudioStorageProvider()
    action = AdminUserDictionaryPromoteAction(
        FakeDb({"id": 5, "word": "cord", "audio_path": "word_base/user/noun/cord.mp3", "status": "queued_for_audio"}),
        FakeTimeService(),
        audio_storage_provider=storage_provider,
    )

    with pytest.raises(AdminUserDictionaryActionValidationError) as error_info:
        action.promote_entry(actor={"acl_group_title": "admin"}, entry_id=5)

    assert "Only ready" in error_info.value.detail
    assert storage_provider.exists_calls == []


def test_promote_user_dictionary_entry_rejects_missing_entry() -> None:
    action = AdminUserDictionaryPromoteAction(
        FakeDb(),
        FakeTimeService(),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    with pytest.raises(AdminUserDictionaryActionNotFoundError) as error_info:
        action.promote_entry(actor={"acl_group_title": "admin"}, entry_id=404)

    assert error_info.value.detail == "User dictionary entry not found"


def test_bulk_action_requeues_failed_details() -> None:
    db = FakeDb({"id": 5, "word": "cord", "status": "details_failed"})
    promote_action = AdminUserDictionaryPromoteAction(
        db,
        FakeTimeService(),
        audio_storage_provider=FakeAudioStorageProvider(),
    )
    action = AdminUserDictionaryBulkAction(db, FakeTimeService(), promote_action)

    result = action.execute(actor={"acl_group_title": "admin", "telegram_user_id": 1}, action="rebuild_details", entry_ids=[5])

    assert result["updated_count"] == 1
    assert db.user_dictionary.requeued_details[0]["entry_id"] == 5
    assert db.user_import_items.synced[0]["status"] == "queued_for_details"


def test_bulk_action_requeues_embedding_when_details_exist() -> None:
    db = FakeDb(
        {
            "id": 5,
            "word": "cord",
            "status": "embedding_failed",
            "translation_uk": "шнур",
            "part_of_speech": "noun",
            "examples_json": ["Pull the cord."],
            "is_embedding_ready": False,
        }
    )
    promote_action = AdminUserDictionaryPromoteAction(
        db,
        FakeTimeService(),
        audio_storage_provider=FakeAudioStorageProvider(),
    )
    action = AdminUserDictionaryBulkAction(db, FakeTimeService(), promote_action)

    result = action.execute(actor={"acl_group_title": "admin", "telegram_user_id": 1}, action="rebuild_embedding", entry_ids=[5])

    assert result["updated_count"] == 1
    assert db.user_dictionary.requeued_embeddings[0]["entry_id"] == 5
    assert db.user_import_items.synced[0]["status"] == "queued_for_embedding"


def test_bulk_action_rejects_user_dictionary_entry_and_archives_assignments() -> None:
    db = FakeDb({"id": 5, "word": "cord", "status": "ready_for_rotation"})
    promote_action = AdminUserDictionaryPromoteAction(
        db,
        FakeTimeService(),
        audio_storage_provider=FakeAudioStorageProvider(),
    )
    action = AdminUserDictionaryBulkAction(db, FakeTimeService(), promote_action)

    result = action.execute(actor={"acl_group_title": "admin", "telegram_user_id": 1}, action="reject", entry_ids=[5])

    assert result["updated_count"] == 1
    assert db.user_dictionary.updated_statuses[0]["status"] == "rejected"
    assert db.user_dictionary.updated_statuses[0]["source_provider_status_json"]["admin_reject"]["actor"] == "1"
    assert db.user_dictionary.archived_assignment_entries[0]["entry_id"] == 5
    assert db.user_import_items.synced[0]["status"] == "rejected"


def test_bulk_action_rejects_unsupported_action() -> None:
    db = FakeDb({"id": 5, "word": "cord", "status": "ready_for_rotation"})
    promote_action = AdminUserDictionaryPromoteAction(
        db,
        FakeTimeService(),
        audio_storage_provider=FakeAudioStorageProvider(),
    )
    action = AdminUserDictionaryBulkAction(db, FakeTimeService(), promote_action)

    with pytest.raises(AdminUserDictionaryActionValidationError) as error_info:
        action.execute(actor={"acl_group_title": "admin", "telegram_user_id": 1}, action="bad_action", entry_ids=[5])

    assert error_info.value.detail == "Unsupported user dictionary bulk action"
