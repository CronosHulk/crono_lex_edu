from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_, select

from app.data_access.user_identity import get_user_by_telegram_id, get_user_uuid_by_telegram_id
from app.models import User, UserImportGoogleDocProgress, UserLearningSettings, UserSubscription
from app.orm import SessionManager


class UserImportGoogleDocRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def _get_or_create_settings(self, session, telegram_user_id: int) -> UserLearningSettings:
        user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
        if user_uuid is None:
            raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
        settings = session.get(UserLearningSettings, user_uuid)
        if settings is None:
            settings = UserLearningSettings(user_uuid=user_uuid)
            session.add(settings)
        return settings

    def _get_or_create_progress(self, session, telegram_user_id: int, doc_id: str) -> UserImportGoogleDocProgress:
        user_uuid = get_user_uuid_by_telegram_id(session, telegram_user_id)
        if user_uuid is None:
            raise ValueError(f"Unknown user for telegram_user_id={telegram_user_id}")
        progress = session.get(UserImportGoogleDocProgress, (user_uuid, doc_id))
        if progress is None:
            progress = UserImportGoogleDocProgress(user_uuid=user_uuid, google_doc_id=doc_id)
            session.add(progress)
        return progress

    def set_binding(self, telegram_user_id: int, doc_id: str, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            settings.import_google_doc_id = doc_id
            settings.is_import_google_doc_auto_sync_enabled = True
            settings.import_google_doc_last_synced = None
            settings.import_google_doc_last_error = None
            settings.import_google_doc_retry_count = 0
            settings.import_google_doc_next_retry_at = None
            settings.import_google_doc_claimed_until = None
            settings.updated = current_time
            self._get_or_create_progress(session, telegram_user_id, doc_id)

    def clear_binding(self, telegram_user_id: int, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            settings.import_google_doc_id = None
            settings.is_import_google_doc_auto_sync_enabled = False
            settings.import_google_doc_last_synced = None
            settings.import_google_doc_last_error = None
            settings.import_google_doc_retry_count = 0
            settings.import_google_doc_next_retry_at = None
            settings.import_google_doc_claimed_until = None
            settings.updated = current_time

    def claim_due_syncs(
        self,
        current_time: datetime,
        sync_hour: int,
        sync_interval_days: int,
        claimed_until: datetime,
        sync_weekdays: list[int] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            stmt = (
                select(User.uuid, User.telegram_user_id, User.chat_id, User.language_code, UserLearningSettings)
                .join(UserLearningSettings, UserLearningSettings.user_uuid == User.uuid)
                .where(
                    User.status == "active",
                    UserLearningSettings.is_import_google_doc_auto_sync_enabled.is_(True),
                    UserLearningSettings.import_google_doc_id.is_not(None),
                    or_(
                        UserLearningSettings.import_google_doc_claimed_until.is_(None),
                        UserLearningSettings.import_google_doc_claimed_until <= current_time,
                    ),
                )
                .order_by(User.telegram_user_id.asc())
                .with_for_update(skip_locked=True)
            )
            rows = session.execute(stmt).all()
            payload: list[dict[str, Any]] = []
            for user_uuid, telegram_user_id, chat_id, language_code, settings in rows:
                if limit is not None and len(payload) >= max(int(limit), 1):
                    break
                last_synced = settings.import_google_doc_last_synced
                next_retry_at = settings.import_google_doc_next_retry_at
                retry_count = int(settings.import_google_doc_retry_count or 0)
                is_retry_due = (
                    retry_count > 0
                    and retry_count <= 3
                    and next_retry_at is not None
                    and next_retry_at <= current_time
                )
                normalized_interval_days = max(int(sync_interval_days), 1)
                is_weekday_due = False
                if sync_weekdays is not None:
                    is_weekday_due = current_time.hour == sync_hour and current_time.weekday() in set(sync_weekdays) and (
                        last_synced is None or last_synced.date() < current_time.date()
                    )
                is_interval_due = sync_weekdays is None and current_time.hour == sync_hour and (
                    last_synced is None
                    or last_synced <= current_time - timedelta(days=normalized_interval_days)
                )
                if not is_retry_due and not is_interval_due and not is_weekday_due:
                    continue
                settings.import_google_doc_claimed_until = claimed_until
                settings.updated = current_time
                payload.append(
                    {
                        "telegram_user_id": telegram_user_id,
                        "user_id": str(user_uuid),
                        "user_uuid": str(user_uuid),
                        "chat_id": chat_id,
                        "language_code": language_code,
                        "source_identifier": settings.import_google_doc_id,
                        "last_synced": last_synced,
                        "last_error": settings.import_google_doc_last_error,
                        "retry_count": retry_count,
                        "next_retry_at": next_retry_at,
                    }
                )
            return payload

    def list_post_upgrade_rescan_candidates(
        self,
        *,
        current_time: datetime,
        paid_plan_keys: set[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        normalized_plan_keys = {str(plan_key) for plan_key in paid_plan_keys}
        if not normalized_plan_keys:
            return []
        with self.session_manager.session() as session:
            rows = session.execute(
                select(User.uuid, User.telegram_user_id, User.chat_id, User.language_code, UserLearningSettings)
                .join(UserLearningSettings, UserLearningSettings.user_uuid == User.uuid)
                .join(UserSubscription, UserSubscription.user_uuid == User.uuid)
                .where(
                    User.status == "active",
                    UserLearningSettings.is_import_google_doc_auto_sync_enabled.is_(True),
                    UserLearningSettings.import_google_doc_id.is_not(None),
                    UserSubscription.status == "active",
                    UserSubscription.plan_key.in_(normalized_plan_keys),
                    UserSubscription.start <= current_time,
                    or_(UserSubscription.end.is_(None), UserSubscription.end > current_time),
                    or_(
                        UserLearningSettings.import_google_doc_last_synced.is_(None),
                        UserLearningSettings.import_google_doc_last_synced < UserSubscription.start,
                    ),
                )
                .order_by(UserSubscription.start.asc(), User.telegram_user_id.asc())
                .limit(max(int(limit), 1))
            ).all()
            return [
                {
                    "telegram_user_id": telegram_user_id,
                    "user_id": str(user_uuid),
                    "user_uuid": str(user_uuid),
                    "chat_id": chat_id,
                    "language_code": language_code,
                    "source_identifier": settings.import_google_doc_id,
                    "last_synced": settings.import_google_doc_last_synced,
                    "last_error": settings.import_google_doc_last_error,
                    "retry_count": int(settings.import_google_doc_retry_count or 0),
                    "next_retry_at": settings.import_google_doc_next_retry_at,
                }
                for user_uuid, telegram_user_id, chat_id, language_code, settings in rows
            ]

    def mark_sync_success(
        self,
        telegram_user_id: int,
        *,
        current_time: datetime,
    ) -> None:
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            settings.import_google_doc_last_synced = current_time
            settings.import_google_doc_last_error = None
            settings.import_google_doc_retry_count = 0
            settings.import_google_doc_next_retry_at = None
            settings.import_google_doc_claimed_until = None
            settings.updated = current_time

    def get_progress(self, telegram_user_id: int, doc_id: str) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user = get_user_by_telegram_id(session, telegram_user_id)
            if user is None:
                return None
            progress = session.get(UserImportGoogleDocProgress, (user.uuid, doc_id))
            if progress is None:
                return None
            return {
                "user_id": str(progress.user_uuid),
                "user_uuid": str(progress.user_uuid),
                "google_doc_id": progress.google_doc_id,
                "last_processed_line": progress.last_processed_line,
                "last_processed_line_hash": progress.last_processed_line_hash,
                "last_processed_lookup_word": progress.last_processed_lookup_word,
                "last_synced": progress.last_synced,
            }

    def get_bound_doc_for_telegram_user(self, telegram_user_id: int) -> dict[str, Any] | None:
        with self.session_manager.session() as session:
            user = get_user_by_telegram_id(session, telegram_user_id)
            if user is None:
                return None
            settings = session.get(UserLearningSettings, user.uuid)
            if settings is None or not settings.is_import_google_doc_auto_sync_enabled:
                return None
            if not settings.import_google_doc_id:
                return None
            return {
                "telegram_user_id": user.telegram_user_id,
                "user_id": str(user.uuid),
                "user_uuid": str(user.uuid),
                "chat_id": user.chat_id,
                "language_code": user.language_code,
                "source_identifier": settings.import_google_doc_id,
                "last_synced": settings.import_google_doc_last_synced,
                "last_error": settings.import_google_doc_last_error,
                "retry_count": int(settings.import_google_doc_retry_count or 0),
                "next_retry_at": settings.import_google_doc_next_retry_at,
            }

    def mark_progress(
        self,
        telegram_user_id: int,
        doc_id: str,
        *,
        current_time: datetime,
        last_processed_line: int,
        last_processed_line_hash: str | None,
        last_processed_lookup_word: str | None,
    ) -> None:
        with self.session_manager.session() as session:
            progress = self._get_or_create_progress(session, telegram_user_id, doc_id)
            progress.last_processed_line = max(int(last_processed_line), 0)
            progress.last_processed_line_hash = last_processed_line_hash
            progress.last_processed_lookup_word = last_processed_lookup_word
            progress.last_synced = current_time
            progress.updated = current_time

    def clear_progress(self, telegram_user_id: int, doc_id: str, *, current_time: datetime) -> None:
        with self.session_manager.session() as session:
            user = get_user_by_telegram_id(session, telegram_user_id)
            if user is None:
                return
            progress = session.get(UserImportGoogleDocProgress, (user.uuid, doc_id))
            if progress is None:
                return
            session.delete(progress)
            settings = session.get(UserLearningSettings, user.uuid)
            if settings is not None:
                settings.updated = current_time

    def mark_sync_failure(
        self,
        telegram_user_id: int,
        *,
        current_time: datetime,
        error_text: str,
        retry_count: int,
        next_retry_at: datetime | None,
    ) -> None:
        with self.session_manager.session() as session:
            settings = self._get_or_create_settings(session, telegram_user_id)
            settings.import_google_doc_last_error = error_text
            settings.import_google_doc_retry_count = retry_count
            settings.import_google_doc_next_retry_at = next_retry_at
            settings.import_google_doc_claimed_until = None
            if next_retry_at is None:
                settings.import_google_doc_last_synced = current_time
            settings.updated = current_time
