from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import UUID

from app.data_access.user_import_google_docs import UserImportGoogleDocRepository
from app.models import User, UserImportGoogleDocProgress, UserLearningSettings

USER_UUID = UUID("00000000-0000-0000-0000-000000000042")


def fake_user() -> User:
    return User(uuid=USER_UUID, telegram_user_id=42, chat_id=1001, language_code="uk", status="active")


class FakeExecuteResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, row_by_id=None, execute_rows=None) -> None:
        self.row_by_id = row_by_id or {}
        self.execute_rows = list(execute_rows or [])
        self.added = []
        self.deleted = []

    def get(self, model, primary_key):
        return self.row_by_id.get((model, primary_key), self.row_by_id.get(primary_key))

    def add(self, row) -> None:
        self.added.append(row)
        if isinstance(row, UserImportGoogleDocProgress):
            self.row_by_id[(row.user_uuid, row.google_doc_id)] = row
        elif isinstance(row, UserLearningSettings):
            self.row_by_id[row.user_uuid] = row

    def delete(self, row) -> None:
        self.deleted.append(row)
        if isinstance(row, UserImportGoogleDocProgress):
            self.row_by_id.pop((row.user_uuid, row.google_doc_id), None)

    def execute(self, statement):
        return FakeExecuteResult(self.execute_rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_set_binding_creates_settings_and_resets_sync_state() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    session = FakeSession(row_by_id={(User, 42): fake_user()})
    repository = UserImportGoogleDocRepository(FakeSessionManager(session))

    repository.set_binding(telegram_user_id=42, doc_id="doc-1", current_time=current_time)

    settings = session.added[0]
    assert settings.user_uuid == USER_UUID
    assert settings.import_google_doc_id == "doc-1"
    assert settings.is_import_google_doc_auto_sync_enabled is True
    assert settings.import_google_doc_last_error is None
    assert settings.import_google_doc_retry_count == 0
    assert settings.updated == current_time
    assert session.row_by_id[(USER_UUID, "doc-1")].google_doc_id == "doc-1"


def test_clear_binding_disables_sync_and_resets_state() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    settings = UserLearningSettings(
        user_uuid=USER_UUID,
        import_google_doc_id="doc-1",
        is_import_google_doc_auto_sync_enabled=True,
        import_google_doc_last_error="old",
        import_google_doc_retry_count=2,
        import_google_doc_next_retry_at=current_time,
    )
    repository = UserImportGoogleDocRepository(
        FakeSessionManager(FakeSession(row_by_id={(User, 42): fake_user(), USER_UUID: settings}))
    )

    repository.clear_binding(telegram_user_id=42, current_time=current_time)

    assert settings.import_google_doc_id is None
    assert settings.is_import_google_doc_auto_sync_enabled is False
    assert settings.import_google_doc_last_error is None
    assert settings.import_google_doc_retry_count == 0
    assert settings.updated == current_time


def test_clear_binding_keeps_google_doc_progress() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    settings = UserLearningSettings(
        user_uuid=USER_UUID,
        import_google_doc_id="doc-1",
        is_import_google_doc_auto_sync_enabled=True,
    )
    progress = UserImportGoogleDocProgress(
        user_uuid=USER_UUID,
        google_doc_id="doc-1",
        last_processed_line=15,
        last_processed_line_hash="hash",
    )
    session = FakeSession(row_by_id={(User, 42): fake_user(), USER_UUID: settings, (USER_UUID, "doc-1"): progress})
    repository = UserImportGoogleDocRepository(FakeSessionManager(session))

    repository.clear_binding(telegram_user_id=42, current_time=current_time)

    assert session.row_by_id[(USER_UUID, "doc-1")].last_processed_line == 15


def test_get_and_mark_google_doc_progress() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    session = FakeSession(row_by_id={(User, 42): fake_user()})
    repository = UserImportGoogleDocRepository(FakeSessionManager(session))

    assert repository.get_progress(telegram_user_id=42, doc_id="doc-1") is None

    repository.mark_progress(
        telegram_user_id=42,
        doc_id="doc-1",
        current_time=current_time,
        last_processed_line=7,
        last_processed_line_hash="hash",
        last_processed_lookup_word="speak",
    )

    assert repository.get_progress(telegram_user_id=42, doc_id="doc-1") == {
        "user_id": str(USER_UUID),
        "user_uuid": str(USER_UUID),
        "google_doc_id": "doc-1",
        "last_processed_line": 7,
        "last_processed_line_hash": "hash",
        "last_processed_lookup_word": "speak",
        "last_synced": current_time,
    }


def test_clear_progress_deletes_google_doc_checkpoint() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    settings = UserLearningSettings(user_uuid=USER_UUID)
    progress = UserImportGoogleDocProgress(
        user_uuid=USER_UUID,
        google_doc_id="doc-1",
        last_processed_line=7,
    )
    session = FakeSession(row_by_id={(User, 42): fake_user(), USER_UUID: settings, (USER_UUID, "doc-1"): progress})
    repository = UserImportGoogleDocRepository(FakeSessionManager(session))

    repository.clear_progress(telegram_user_id=42, doc_id="doc-1", current_time=current_time)

    assert session.deleted == [progress]
    assert repository.get_progress(telegram_user_id=42, doc_id="doc-1") is None
    assert settings.updated == current_time


def test_claim_due_syncs_claims_retry_due_and_interval_due_rows() -> None:
    current_time = datetime(2026, 4, 26, 22, 0, 0)
    claimed_until = current_time + timedelta(minutes=30)
    retry_settings = UserLearningSettings(
        user_uuid=USER_UUID,
        import_google_doc_id="retry-doc",
        import_google_doc_retry_count=1,
        import_google_doc_next_retry_at=current_time - timedelta(minutes=1),
        import_google_doc_last_error="temporary",
    )
    interval_settings = UserLearningSettings(
        user_uuid=UUID("00000000-0000-0000-0000-000000000043"),
        import_google_doc_id="interval-doc",
        import_google_doc_last_synced=current_time - timedelta(days=4),
        import_google_doc_retry_count=0,
    )
    skipped_settings = UserLearningSettings(
        user_uuid=UUID("00000000-0000-0000-0000-000000000044"),
        import_google_doc_id="fresh-doc",
        import_google_doc_last_synced=current_time,
        import_google_doc_retry_count=0,
    )
    session = FakeSession(
        execute_rows=[
            (USER_UUID, 42, 1001, "uk", retry_settings),
            (UUID("00000000-0000-0000-0000-000000000043"), 43, 1002, "en", interval_settings),
            (UUID("00000000-0000-0000-0000-000000000044"), 44, 1003, "pl", skipped_settings),
        ]
    )
    repository = UserImportGoogleDocRepository(FakeSessionManager(session))

    payload = repository.claim_due_syncs(
        current_time=current_time,
        sync_hour=22,
        sync_interval_days=3,
        claimed_until=claimed_until,
        limit=10,
    )

    assert [row["telegram_user_id"] for row in payload] == [42, 43]
    assert payload[0]["source_identifier"] == "retry-doc"
    assert payload[0]["last_error"] == "temporary"
    assert retry_settings.import_google_doc_claimed_until == claimed_until
    assert interval_settings.import_google_doc_claimed_until == claimed_until
    assert skipped_settings.import_google_doc_claimed_until is None


def test_claim_due_syncs_applies_limit_after_due_filtering() -> None:
    current_time = datetime(2026, 4, 26, 22, 0, 0)
    claimed_until = current_time + timedelta(minutes=30)
    fresh_settings = UserLearningSettings(
        user_uuid=USER_UUID,
        import_google_doc_id="fresh-doc",
        import_google_doc_last_synced=current_time,
        import_google_doc_retry_count=0,
    )
    due_settings = UserLearningSettings(
        user_uuid=UUID("00000000-0000-0000-0000-000000000043"),
        import_google_doc_id="due-doc",
        import_google_doc_last_synced=current_time - timedelta(days=4),
        import_google_doc_retry_count=0,
    )
    session = FakeSession(
        execute_rows=[
            (USER_UUID, 42, 1001, "uk", fresh_settings),
            (UUID("00000000-0000-0000-0000-000000000043"), 43, 1002, "en", due_settings),
        ]
    )
    repository = UserImportGoogleDocRepository(FakeSessionManager(session))

    payload = repository.claim_due_syncs(
        current_time=current_time,
        sync_hour=22,
        sync_interval_days=3,
        claimed_until=claimed_until,
        limit=1,
    )

    assert [row["telegram_user_id"] for row in payload] == [43]
    assert fresh_settings.import_google_doc_claimed_until is None
    assert due_settings.import_google_doc_claimed_until == claimed_until


def test_claim_due_syncs_uses_minimum_one_day_interval() -> None:
    current_time = datetime(2026, 4, 26, 22, 0, 0)
    settings = UserLearningSettings(
        user_uuid=USER_UUID,
        import_google_doc_id="doc-1",
        import_google_doc_last_synced=current_time - timedelta(days=1, minutes=1),
    )
    repository = UserImportGoogleDocRepository(
        FakeSessionManager(FakeSession(execute_rows=[(USER_UUID, 42, 1001, "uk", settings)]))
    )

    payload = repository.claim_due_syncs(
        current_time=current_time,
        sync_hour=22,
        sync_interval_days=0,
        claimed_until=current_time + timedelta(minutes=30),
    )

    assert payload[0]["telegram_user_id"] == 42


def test_list_post_upgrade_rescan_candidates_returns_bound_paid_docs() -> None:
    current_time = datetime(2026, 5, 8, 13, 0, 0)
    settings = UserLearningSettings(
        user_uuid=USER_UUID,
        import_google_doc_id="doc-1",
        is_import_google_doc_auto_sync_enabled=True,
        import_google_doc_last_synced=datetime(2026, 5, 8, 12, 48, 0),
    )
    repository = UserImportGoogleDocRepository(
        FakeSessionManager(FakeSession(execute_rows=[(USER_UUID, 42, 1001, "uk", settings)]))
    )

    payload = repository.list_post_upgrade_rescan_candidates(
        current_time=current_time,
        paid_plan_keys={"premium", "premium_plus"},
        limit=25,
    )

    assert payload == [
        {
            "telegram_user_id": 42,
            "user_id": str(USER_UUID),
            "user_uuid": str(USER_UUID),
            "chat_id": 1001,
            "language_code": "uk",
            "source_identifier": "doc-1",
            "last_synced": datetime(2026, 5, 8, 12, 48, 0),
            "last_error": None,
            "retry_count": 0,
            "next_retry_at": None,
        }
    ]


def test_mark_sync_success_resets_error_and_retry_state() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    settings = UserLearningSettings(
        user_uuid=USER_UUID,
        import_google_doc_last_error="old",
        import_google_doc_retry_count=2,
        import_google_doc_next_retry_at=current_time,
        import_google_doc_claimed_until=current_time,
    )
    repository = UserImportGoogleDocRepository(
        FakeSessionManager(FakeSession(row_by_id={(User, 42): fake_user(), USER_UUID: settings}))
    )

    repository.mark_sync_success(telegram_user_id=42, current_time=current_time)

    assert settings.import_google_doc_last_synced == current_time
    assert settings.import_google_doc_last_error is None
    assert settings.import_google_doc_retry_count == 0
    assert settings.import_google_doc_next_retry_at is None
    assert settings.import_google_doc_claimed_until is None


def test_mark_sync_failure_schedules_retry_or_finishes_when_no_retry() -> None:
    current_time = datetime(2026, 4, 26, 10, 0, 0)
    next_retry_at = current_time + timedelta(hours=1)
    settings = UserLearningSettings(user_uuid=USER_UUID, import_google_doc_claimed_until=current_time)
    repository = UserImportGoogleDocRepository(
        FakeSessionManager(FakeSession(row_by_id={(User, 42): fake_user(), USER_UUID: settings}))
    )

    repository.mark_sync_failure(
        telegram_user_id=42,
        current_time=current_time,
        error_text="provider down",
        retry_count=1,
        next_retry_at=next_retry_at,
    )

    assert settings.import_google_doc_last_error == "provider down"
    assert settings.import_google_doc_retry_count == 1
    assert settings.import_google_doc_next_retry_at == next_retry_at
    assert settings.import_google_doc_claimed_until is None
    assert settings.import_google_doc_last_synced is None

    repository.mark_sync_failure(
        telegram_user_id=42,
        current_time=current_time,
        error_text="final failure",
        retry_count=4,
        next_retry_at=None,
    )

    assert settings.import_google_doc_last_synced == current_time
