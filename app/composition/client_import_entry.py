from __future__ import annotations

from typing import Any

from app.application.client_import.mutation_action_service import (
    ClientImportMutationActionService,
)
from app.application.client_import.screen_service import ClientImportScreenService
from app.application.client_import.text_input_service import ClientImportTextInputService
from app.data_access.user_import_google_docs import UserImportGoogleDocRepository
from app.data_access.user_profiles import UserProfileRepository
from app.user_import.runtime_settings import read_user_import_runtime_settings


def configure_client_import_entry_runtime(service: Any, db: Any) -> None:
    user_profiles_repo = getattr(db, "user_profiles", None) or UserProfileRepository(db)
    user_import_google_docs_repo = getattr(db, "user_import_google_docs", None) or UserImportGoogleDocRepository(db)

    service.client_import_screen_service = ClientImportScreenService(
        user_profiles_repo,
        db.settings,
        import_settings_reader=lambda: read_user_import_runtime_settings(db),
    )

    def submit_user_vocabulary_import(user: Any, locale: str, source_url: str) -> Any:
        def process_immediate_user_import_attribute_builds(
            telegram_user_id: int,
            current_time: Any,
        ) -> None:
            runtime_settings = read_user_import_runtime_settings(db)
            if not bool(runtime_settings["enrich_after_google_doc_import_enabled"]):
                return
            service.user_import_scheduled_runtime_service.process_user_import_attribute_queue_now(
                telegram_user_id,
                current_time,
            )

        def build_summary_screen(
            telegram_user_id: int,
            locale: str,
            job_id: int,
            notice: str | None = None,
        ) -> Any:
            return service.user_import_summary_service.build_user_import_summary_screen_for_user(
                telegram_user_id=telegram_user_id,
                locale=locale,
                job_id=job_id,
                notice=notice,
            )

        return service.user_import_intake_service.submit_user_vocabulary_import(
            user=user,
            locale=locale,
            source_url=source_url,
            current_time=service.time_service.now(),
            build_user_import_screen=service.client_import_screen_service.build_user_import_screen,
            prepare_import_job_items=service.user_import_preparation_service.prepare_import_job_items,
            build_user_import_summary_screen_for_user=build_summary_screen,
            process_queued_attribute_builds_after_import=process_immediate_user_import_attribute_builds,
        )

    service.client_import_text_input_service = ClientImportTextInputService(
        build_user_import_screen=lambda telegram_user_id,
        locale,
        notice=None: service.client_import_screen_service.build_user_import_screen(
            telegram_user_id,
            locale,
            notice,
        ),
        submit_user_vocabulary_import=submit_user_vocabulary_import,
    )
    service.client_import_mutation_action_service = ClientImportMutationActionService(
        user_profiles=user_profiles_repo,
        is_test_mode_enabled=lambda: bool(
            getattr(service.db.settings, "app_user_import_test_mode", False)
        ),
        current_time=lambda: service.time_service.now(),
        process_due_user_vocabulary_imports=lambda **kwargs: service.user_import_runtime_service.process_due_user_vocabulary_imports_at(
            **kwargs
        ),
        clear_import_google_doc_binding=lambda telegram_user_id,
        current_time: user_import_google_docs_repo.clear_binding(
            telegram_user_id,
            current_time,
        ),
        build_import_screen=lambda telegram_user_id,
        locale,
        notice=None: service.client_import_screen_service.build_user_import_screen(
            telegram_user_id,
            locale,
            notice,
        ),
        build_menu_screen=lambda telegram_user_id,
        locale,
        notice=None,
        clear_chat=False,
        force_resend=False: service.client_learning_menu_screen_service.build_menu_screen(
            telegram_user_id,
            locale,
            notice=notice,
            clear_chat=clear_chat,
            force_resend=force_resend,
        ),
    )
