from __future__ import annotations

from typing import Any

from app.application.client_import.read_action_service import ClientImportReadActionService
from app.composition.user_import_artifact_storage import (
    build_user_import_artifact_storage_provider,
)
from app.user_import.services.summary_service import UserImportSummaryService


def configure_user_import_summary_read_runtime(service: Any, db: Any) -> None:
    if getattr(service, "user_import_artifact_storage_provider", None) is None:
        service.user_import_artifact_storage_provider = (
            build_user_import_artifact_storage_provider(db.settings)
        )
    service.user_import_summary_service = UserImportSummaryService(
        db,
        build_import_screen=lambda telegram_user_id,
        locale,
        notice=None: service.client_import_screen_service.build_user_import_screen(
            telegram_user_id,
            locale,
            notice,
        ),
        build_import_url=service.client_learning_web_link_service.build_import_url,
        get_intake_snapshot=service.user_import_intake_service.get_user_import_intake_snapshot,
        artifact_storage_provider=service.user_import_artifact_storage_provider,
    )
    service.client_import_read_action_service = ClientImportReadActionService(
        build_import_screen=lambda telegram_user_id,
        locale: service.client_import_screen_service.build_user_import_screen(
            telegram_user_id,
            locale,
        ),
        build_summary_screen_for_user=lambda telegram_user_id,
        locale,
        job_id: service.user_import_summary_service.build_user_import_summary_screen_for_user(
            telegram_user_id=telegram_user_id,
            locale=locale,
            job_id=job_id,
        ),
        build_document_screen_for_user=lambda telegram_user_id,
        locale,
        job_id,
        slice_name: service.user_import_summary_service.build_user_import_document_screen_for_user(
            telegram_user_id=telegram_user_id,
            locale=locale,
            job_id=job_id,
            slice_name=slice_name,
        ),
        build_intake_slice_screen=lambda telegram_user_id,
        locale,
        job_id,
        slice_name: service.user_import_intake_service.build_user_import_intake_slice_screen(
            telegram_user_id=telegram_user_id,
            locale=locale,
            job_id=job_id,
            slice_name=slice_name,
            build_user_import_screen=service.client_import_screen_service.build_user_import_screen,
        ),
        build_failed_items_screen=lambda telegram_user_id,
        locale,
        job_id: service.user_import_summary_service.build_user_import_failed_items_screen(
            telegram_user_id=telegram_user_id,
            locale=locale,
            job_id=job_id,
        ),
        build_close_to_menu_screen=service.client_learning_menu_screen_service.build_close_to_menu_screen,
    )
