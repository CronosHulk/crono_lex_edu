from __future__ import annotations

from app.user_import.services.task_error_context import build_user_import_task_error_context


def test_build_user_import_task_error_context_includes_base_fields() -> None:
    assert build_user_import_task_error_context(
        task_log_id=10,
        telegram_user_id=20,
        source_type="google_doc",
        source_identifier="doc-1",
    ) == {
        "task_log_id": 10,
        "telegram_user_id": 20,
        "source_type": "google_doc",
        "source_identifier": "doc-1",
    }


def test_build_user_import_task_error_context_adds_optional_fields() -> None:
    assert build_user_import_task_error_context(
        task_log_id=10,
        telegram_user_id=None,
        source_type=None,
        source_identifier=None,
        import_job_id=30,
        import_item_id=40,
        lookup_word="abandon",
    ) == {
        "task_log_id": 10,
        "telegram_user_id": None,
        "source_type": None,
        "source_identifier": None,
        "import_job_id": 30,
        "import_item_id": 40,
        "lookup_word": "abandon",
    }
