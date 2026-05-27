from __future__ import annotations

import html
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from app.contracts import ScreenModel, TelegramUserContext
from app.i18n import translate
from app.screen_delivery_policy import with_screen_delivery_policy
from app.user_import.services.google_doc_progress import parse_google_doc_since_progress
from app.user_import.services.intake_manual_bind_job_submission_service import (
    UserImportManualBindJobSubmissionService,
)
from app.user_import.services.intake_manual_bind_progress_service import (
    UserImportManualBindProgressService,
)
from app.user_import.services.intake_manual_bind_validation_service import (
    UserImportManualBindValidationService,
)


class UserImportManualBindGoogleDocRepository(Protocol):
    def set_binding(self, telegram_user_id: int, doc_id: str, current_time: datetime) -> None: ...

    def get_progress(self, telegram_user_id: int, doc_id: str) -> dict[str, Any] | None: ...

    def mark_progress(
        self,
        telegram_user_id: int,
        doc_id: str,
        *,
        current_time: datetime,
        last_processed_line: int,
        last_processed_line_hash: str | None,
        last_processed_lookup_word: str | None,
    ) -> None: ...

    def mark_sync_success(self, telegram_user_id: int, *, current_time: datetime) -> None: ...


class UserImportManualBindUserProfileRepository(Protocol):
    def save_user_event(
        self,
        *,
        telegram_user_id: int,
        event_type: str,
        raw_update_json: dict[str, Any],
        message_text: str | None = None,
        callback_data: str | None = None,
    ) -> None: ...

    def get_profile(self, telegram_user_id: int) -> dict[str, Any] | None: ...


class UserImportManualBindJobsPort(Protocol):
    def get_existing_lookup_words(self, telegram_user_id: int, lookup_words: list[str]) -> set[str]: ...


class UserImportManualBindDatabasePort(Protocol):
    @property
    def user_import_jobs(self) -> UserImportManualBindJobsPort: ...


class UserImportManualBindIntakeJobPort(Protocol):
    def build_user_import_intake_snapshot(
        self,
        parsed_words: list[Any],
        existing_lookup_words: set[str],
        invalid_fragments: list[str],
        *,
        max_words_per_bind: int,
    ) -> dict[str, Any]: ...

    def create_user_import_job_from_words(
        self,
        *,
        telegram_user_id: int,
        source_identifier: str,
        parsed_words: list[Any],
        current_time: datetime,
        task_log_id: int | None = None,
        source_type: str = "google_doc",
        max_words_per_job: int | None = None,
    ) -> tuple[int, int, int | None]: ...


class UserImportManualBindCandidateFilterPort(Protocol):
    def list_assigned_lookup_words(self, user_uuid: str | None) -> set[str]: ...

    def filter_already_assigned_words(
        self,
        parsed_words: list[Any],
        *,
        user_uuid: str | None,
    ) -> Any: ...


class UserImportManualBindImportModeResolver(Protocol):
    def __call__(self, user_uuid: str, *, current_time: datetime) -> str | None: ...


class UserImportIntakeManualBindService:
    def __init__(
        self,
        db: UserImportManualBindDatabasePort,
        google_docs: UserImportManualBindGoogleDocRepository,
        user_profiles: UserImportManualBindUserProfileRepository,
        *,
        intake_job_service: UserImportManualBindIntakeJobPort,
        extract_google_doc_id: Callable[[str], str],
        build_google_doc_export_url: Callable[[str], str],
        fetch_google_doc_text: Callable[[str], str],
        parse_user_vocabulary_text_result: Callable[[str], Any],
        mask_google_doc_url: Callable[[str], str],
        build_invalid_import_notice: Callable[[str, list[str]], str | None],
        candidate_filter: UserImportManualBindCandidateFilterPort,
        import_mode_for_user: UserImportManualBindImportModeResolver,
        max_import_entries_per_submission: Callable[[], int],
        validation_service: Any | None = None,
        manual_bind_validation_service: UserImportManualBindValidationService | None = None,
        progress_service: UserImportManualBindProgressService | None = None,
        job_submission_service: UserImportManualBindJobSubmissionService | None = None,
    ) -> None:
        self.db = db
        self.google_docs = google_docs
        self.user_profiles = user_profiles
        self.intake_job_service = intake_job_service
        self.extract_google_doc_id = extract_google_doc_id
        self.build_google_doc_export_url = build_google_doc_export_url
        self.fetch_google_doc_text = fetch_google_doc_text
        self.parse_user_vocabulary_text_result = parse_user_vocabulary_text_result
        self.mask_google_doc_url = mask_google_doc_url
        self.build_invalid_import_notice = build_invalid_import_notice
        self.candidate_filter = candidate_filter
        self.max_import_entries_per_submission = max_import_entries_per_submission
        self.manual_bind_validation_service = manual_bind_validation_service or UserImportManualBindValidationService(
            validation_service=validation_service,
            import_mode_for_user=import_mode_for_user,
        )
        self.progress_service = progress_service or UserImportManualBindProgressService(google_docs)
        self.job_submission_service = job_submission_service or UserImportManualBindJobSubmissionService(
            db,
            intake_job_service=intake_job_service,
        )

    def submit_user_vocabulary_import(
        self,
        *,
        user: TelegramUserContext,
        locale: str,
        source_url: str,
        current_time: datetime,
        build_user_import_screen: Callable[..., ScreenModel],
        prepare_import_job_items: Callable[..., None],
        build_user_import_summary_screen_for_user: Callable[..., ScreenModel],
        process_queued_attribute_builds_after_import: Callable[[int, datetime], None] | None = None,
    ) -> ScreenModel:
        try:
            doc_id = self.extract_google_doc_id(source_url)
            export_url = self.build_google_doc_export_url(doc_id)
            raw_text = self.fetch_google_doc_text(export_url)
            progress = self.google_docs.get_progress(user.telegram_user_id, doc_id)
            actor_user_uuid = self._actor_user_uuid(user.telegram_user_id)
            assigned_lookup_words = self.candidate_filter.list_assigned_lookup_words(actor_user_uuid)
            scope = parse_google_doc_since_progress(
                raw_text,
                progress,
                self.parse_user_vocabulary_text_result,
                max_parsed_words=self._max_import_entries_per_submission(),
                skip_lookup_words=assigned_lookup_words,
            )
            parse_result = scope.parse_result
        except Exception as error:
            return build_user_import_screen(
                user.telegram_user_id,
                locale,
                notice=f"{translate(locale, 'import_words_invalid_url')}\n{html.escape(str(error))}",
            )

        self.google_docs.set_binding(user.telegram_user_id, doc_id, current_time)
        max_words_per_bind = self._max_import_entries_per_submission()
        if not parse_result.parsed_words:
            invalid_notice = self.build_invalid_import_notice(locale, parse_result.invalid_fragments)
            self.progress_service.mark_google_doc_progress(
                telegram_user_id=user.telegram_user_id,
                doc_id=doc_id,
                scope=scope,
                existing_lookup_words=set(getattr(scope, "skipped_lookup_words", [])),
                max_words_per_bind=max_words_per_bind,
                current_time=current_time,
            )
            self.google_docs.mark_sync_success(user.telegram_user_id, current_time=current_time)
            empty_notice = translate(locale, "import_words_empty_notice")
            notice = "\n\n".join(part for part in (invalid_notice, empty_notice) if part)
            screen = build_user_import_screen(
                user.telegram_user_id,
                locale,
                notice=notice,
            )
            return with_screen_delivery_policy(screen, force_resend=True)

        candidate_filter_result = self.candidate_filter.filter_already_assigned_words(
            parse_result.parsed_words,
            user_uuid=actor_user_uuid,
        )
        validation_outcome = self.manual_bind_validation_service.validate_parsed_words(
            candidate_filter_result.eligible_words,
            user_uuid=actor_user_uuid,
            current_time=current_time,
        )
        validated_words = validation_outcome.valid_words
        invalid_fragments = [
            *parse_result.invalid_fragments,
            *self.manual_bind_validation_service.rejected_fragments(validation_outcome.rejected_items),
        ]
        invalid_notice = self.build_invalid_import_notice(locale, invalid_fragments)
        if not validated_words:
            self.progress_service.mark_google_doc_progress(
                telegram_user_id=user.telegram_user_id,
                doc_id=doc_id,
                scope=scope,
                existing_lookup_words={
                    *(
                        str(getattr(item, "lookup_word", "") or "")
                        for item in candidate_filter_result.skipped_existing_words
                    ),
                    *getattr(scope, "skipped_lookup_words", []),
                },
                max_words_per_bind=max_words_per_bind,
                current_time=current_time,
            )
            self.google_docs.mark_sync_success(user.telegram_user_id, current_time=current_time)
            self.manual_bind_validation_service.record_usage(
                validation_outcome,
                task_scope="telegram",
                actor_user_uuid=actor_user_uuid,
                source_type="bound_google_doc",
                source_identifier=doc_id,
                import_job_id=None,
                task_log_id=None,
                batch_key=f"bound_google_doc:{user.telegram_user_id}:{doc_id}:word_validation",
                current_time=current_time,
            )
            empty_notice = translate(locale, "import_words_empty_notice")
            notice = "\n\n".join(part for part in (invalid_notice, empty_notice) if part)
            screen = build_user_import_screen(
                user.telegram_user_id,
                locale,
                notice=notice,
            )
            return with_screen_delivery_policy(screen, force_resend=True)

        already_seen_lookup_words = self.db.user_import_jobs.get_existing_lookup_words(
            user.telegram_user_id,
            [item.lookup_word for item in validated_words],
        )
        already_seen_lookup_words.update(getattr(scope, "skipped_lookup_words", []))
        already_seen_lookup_words.update(
            str(getattr(item, "lookup_word", "") or "")
            for item in candidate_filter_result.skipped_existing_words
        )
        intake_snapshot = self.intake_job_service.build_user_import_intake_snapshot(
            validated_words,
            already_seen_lookup_words,
            invalid_fragments,
            max_words_per_bind=max_words_per_bind,
        )
        job_submission_result = self.job_submission_service.create_validated_import_job(
            telegram_user_id=user.telegram_user_id,
            source_identifier=doc_id,
            parsed_words=validated_words,
            intake_snapshot=intake_snapshot,
            current_time=current_time,
            max_words_per_bind=max_words_per_bind,
        )
        self.manual_bind_validation_service.record_usage(
            validation_outcome,
            task_scope="telegram",
            actor_user_uuid=actor_user_uuid,
            source_type="bound_google_doc",
            source_identifier=doc_id,
            import_job_id=job_submission_result.job_id,
            task_log_id=job_submission_result.bind_task_log["id"]
            if job_submission_result.bind_task_log is not None
            else None,
            batch_key=f"bound_google_doc:{user.telegram_user_id}:{doc_id}:word_validation",
            current_time=current_time,
        )
        self.progress_service.mark_google_doc_progress(
            telegram_user_id=user.telegram_user_id,
            doc_id=doc_id,
            scope=scope,
            existing_lookup_words=already_seen_lookup_words,
            max_words_per_bind=max_words_per_bind,
            current_time=current_time,
        )
        self.google_docs.mark_sync_success(user.telegram_user_id, current_time=current_time)
        self.user_profiles.save_user_event(
            telegram_user_id=user.telegram_user_id,
            event_type="user_vocabulary_import_submitted",
            raw_update_json=user.model_dump(mode="json"),
            message_text=self.mask_google_doc_url(source_url),
        )

        if job_submission_result.created_count > 0 and job_submission_result.job_id is not None:
            self.job_submission_service.finalize_created_import_job(
                telegram_user_id=user.telegram_user_id,
                source_identifier=doc_id,
                result=job_submission_result,
                intake_snapshot=intake_snapshot,
                current_time=current_time,
                prepare_import_job_items=prepare_import_job_items,
                process_queued_attribute_builds_after_import=process_queued_attribute_builds_after_import,
            )
            staged_notice = translate(
                locale,
                "import_words_started_notice",
                count=job_submission_result.created_count,
            )
            duplicates_notice = (
                translate(
                    locale,
                    "import_words_skipped_duplicates_notice",
                    count=job_submission_result.skipped_count,
                )
                if job_submission_result.skipped_count > 0
                else None
            )
            notice = "\n\n".join(part for part in (invalid_notice, duplicates_notice, staged_notice) if part)
            return build_user_import_summary_screen_for_user(
                user.telegram_user_id,
                locale,
                job_submission_result.job_id,
                notice=notice,
            )

        if job_submission_result.skipped_count > 0:
            skipped_notice = translate(
                locale,
                "import_words_skipped_duplicates_notice",
                count=job_submission_result.skipped_count,
            )
            notice = "\n\n".join(part for part in (invalid_notice, skipped_notice) if part)
            screen = build_user_import_screen(
                user.telegram_user_id,
                locale,
                notice=notice,
            )
            return with_screen_delivery_policy(screen, force_resend=True)

        saved_notice = translate(locale, "import_words_saved_notice")
        notice = "\n\n".join(part for part in (invalid_notice, saved_notice) if part)
        screen = build_user_import_screen(
            user.telegram_user_id,
            locale,
            notice=notice,
        )
        return with_screen_delivery_policy(screen, force_resend=True)

    def _max_import_entries_per_submission(self) -> int:
        return max(int(self.max_import_entries_per_submission()), 1)

    def _actor_user_uuid(self, telegram_user_id: int) -> str:
        profile = self.user_profiles.get_profile(telegram_user_id)
        user_uuid = (profile or {}).get("user_uuid") or (profile or {}).get("user_id") or (profile or {}).get("id")
        if user_uuid is None:
            raise ValueError("user profile uuid is required for vocabulary import")
        return str(user_uuid)
