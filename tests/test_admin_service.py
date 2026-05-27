from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.application.admin.ai_usage.action_otp import AdminAIUsageActionOtpVerifier
from app.application.admin.ai_usage.errors import (
    AdminAIUsageReadAccessDeniedError,
    AdminAIUsageReadTooManyAttemptsError,
    AdminAIUsageReadUnauthorizedError,
    AdminAIUsageReadValidationError,
)
from app.application.admin.ai_usage.read_service import AdminAIUsageReadService
from app.application.admin.auth.auth_service import AdminAuthService
from app.application.admin.auth.errors import (
    AdminAuthAccessDeniedError,
    AdminAuthTooManyAttemptsError,
    AdminAuthUnauthorizedError,
    AdminAuthValidationError,
)
from app.application.admin.dictionary.dictionary_service import AdminDictionaryService
from app.application.admin.dictionary.errors import AdminDictionaryServiceAccessDeniedError
from app.application.admin.read.read_service import AdminReadService
from app.application.admin.settings.action_otp import AdminSettingsActionOtpVerifier
from app.application.admin.settings.errors import (
    AdminSettingsAccessDeniedError,
    AdminSettingsTooManyAttemptsError,
    AdminSettingsUnauthorizedError,
    AdminSettingsValidationError,
)
from app.application.admin.settings.settings_service import AdminSettingsService
from app.application.admin.user_dictionary.errors import AdminUserDictionaryReadAccessDeniedError
from app.application.admin.users.action_service import AdminUserActionService
from app.application.admin.users.errors import (
    AdminUserActionAccessDeniedError,
    AdminUserActionNotFoundError,
)
from app.auth.secrets import hash_token_for_lookup
from app.billing.runtime_settings import (
    BILLING_MONOBANK_MODE_SETTINGS_KEY,
    BILLING_RUNTIME_SETTINGS_KEY,
)
from app.composition.admin import build_admin_service_dependencies
from app.time_utils import TimeService


class FakeAudioStorageProvider:
    def delete_if_under_roots(self, audio_path, audio_roots) -> bool:
        return False


class FakeTaskLogRepository:
    def __init__(self, db: FakeAdminDb) -> None:
        self.db = db

    def get(self, task_log_id):
        if self.db.task_log and self.db.task_log["id"] == task_log_id:
            return dict(self.db.task_log)
        return None

    def list_admin(self, **kwargs):
        items = self.db.user_task_logs
        user_id = kwargs.get("telegram_user_id")
        if user_id is not None:
            items = [item for item in items if item.get("telegram_user_id") == user_id]
        return {
            "items": [dict(item) for item in items],
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 50),
            "total": len(items),
            "pages": 1 if items else 0,
        }

    def get_filter_metadata(self, **kwargs):
        return {"entity": "task_logs", "page_sizes": [50, 100], "filters": []}

    def get_latest_for_import_job(self, import_job_id, *, task_type=None):
        if self.db.processing_task_log and self.db.processing_task_log["import_job_id"] == import_job_id:
            if task_type is None or self.db.processing_task_log["task_type"] == task_type:
                return dict(self.db.processing_task_log)
        return None

    def has_active_for_user(self, **kwargs):
        return False


class FakePendingWordRepository:
    def __init__(self, db: FakeAdminDb) -> None:
        self.db = db

    def list_admin(self, **kwargs):
        return {
            "items": [self.db.pending_row] if self.db.pending_row is not None else [],
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 50),
            "total": 1 if self.db.pending_row is not None else 0,
            "pages": 1 if self.db.pending_row is not None else 0,
        }

    def get_admin_filter_metadata(self):
        return {"entity": "import_review", "page_sizes": [50, 100], "filters": []}

    def get_by_ids(self, pending_word_ids):
        if self.db.pending_row is None:
            return []
        return [self.db.pending_row]

    def update_admin(self, pending_word_id, **kwargs):
        self.db.updated_payload = {"pending_word_id": pending_word_id, **kwargs}
        return {
            **self.db.pending_row,
            "word": kwargs.get("word") or self.db.pending_row["word"],
            "translation_uk": kwargs.get("translation_uk") or self.db.pending_row["translation_uk"],
            "translation_ru": kwargs.get("translation_ru"),
            "translation_pl": kwargs.get("translation_pl"),
            "examples_json": kwargs.get("examples_json") or self.db.pending_row.get("examples_json", []),
            "audio_path": None,
            "updated": kwargs.get("current_time") or datetime(2026, 5, 6, 11, 0, 0),
        }

    def get_audio(self, pending_word_id):
        if self.db.pending_word_audio and self.db.pending_word_audio["id"] == pending_word_id:
            return dict(self.db.pending_word_audio)
        return None

    def delete_all(self):
        deleted = 1 if self.db.pending_row is not None else 0
        self.db.pending_row = None
        return deleted


class FakeAIUsageSessionRepository:
    def __init__(self, db: FakeAdminDb) -> None:
        self.db = db

    def delete_all(self):
        deleted = len(self.db._ai_usage_session_rows)
        self.db._ai_usage_session_rows = []
        return {"deleted_ai_usage_sessions": deleted}

    def summarize_admin(self, *, created_from=None):
        _ = created_from
        return {"items": list(self.db._ai_usage_session_rows)}

    def list_admin(self, **kwargs):
        _ = kwargs
        return {"items": list(self.db._ai_usage_session_rows), "total": len(self.db._ai_usage_session_rows)}

    def summarize_totals(self, *, created_from=None):
        _ = created_from
        user_ids = {row.get("actor_user_uuid") for row in self.db._ai_usage_session_rows if row.get("actor_user_uuid")}
        return {
            "session_count": len(self.db._ai_usage_session_rows),
            "request_count": sum(int(row.get("request_count") or 0) for row in self.db._ai_usage_session_rows),
            "total_tokens": sum(int(row.get("total_tokens") or 0) for row in self.db._ai_usage_session_rows),
            "estimated_cost_usd": str(sum(float(row.get("estimated_cost_usd") or 0) for row in self.db._ai_usage_session_rows)),
            "ai_active_user_count": len(user_ids),
        }

    def summarize_by_actor_user_ids(self, user_ids, *, created_from=None):
        _ = created_from
        result = {}
        for user_id in user_ids:
            rows = [row for row in self.db._ai_usage_session_rows if str(row.get("actor_user_uuid") or "") == str(user_id)]
            result[str(user_id)] = {
                "session_count": len(rows),
                "request_count": sum(int(row.get("request_count") or 0) for row in rows),
                "total_tokens": sum(int(row.get("total_tokens") or 0) for row in rows),
                "estimated_cost_usd": str(sum(float(row.get("estimated_cost_usd") or 0) for row in rows)),
            }
        return result


class FakeAclPermissionRepository:
    def __init__(self, db: FakeAdminDb) -> None:
        self.db = db

    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        capabilities = set(self.list_group_capabilities(group_title=group_title, environment=environment))
        return "enabled" if action in capabilities else "disabled"

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        if environment == "telegram_user":
            if group_title == "super_admin":
                return [
                    "import_review/approve",
                    "import_review/delete",
                    "import_review/open_menu",
                    "import_review/open",
                    "import_review/regenerate",
                    "import_review/reject",
                    "learning/open_menu",
                ]
            return ["learning/open_menu"]
        if environment != "web_admin":
            return []
        admin_capabilities = [
            "auth/login",
            "auth/set_password",
            "auth/use_session",
            "bootstrap/view",
            "dictionary/archive_word",
            "dictionary/verify_word",
            "dictionary/list_filters",
            "dictionary/play_audio",
            "dictionary/update_word",
            "dictionary/list_words",
            "dictionary/view_word",
            "imports/list_items",
            "imports/list_jobs",
            "imports/list_job_filters",
            "imports/view_job",
            "logs/list_error_log",
            "logs/list_error_log_filters",
            "logs/list_login_history",
            "logs/list_task_log_filters",
            "logs/list_task_logs",
            "logs/view_task_log",
            "imports/list_item_filters",
            "settings/view",
            "users/archive",
            "users/list",
            "users/list_filters",
            "users/view_login_history",
            "users/update_learning_role",
            "users/view",
        ]
        if group_title == "super_admin":
            return sorted(
                {
                    *admin_capabilities,
                    "acl/manage",
                    "dictionary/delete_word",
                    "import_review/approve",
                    "import_review/play_audio",
                    "import_review/delete",
                    "import_review/update_word",
                    "import_review/list_words",
                    "import_review/regenerate",
                    "import_review/reject",
                    "import_review/view_word",
                    "users/delete",
                    "users/reset_password",
                    "users/update_role_to_admin",
                    "users/update_role_to_admin_editor",
                    "users/update_role_to_student",
                    "users/update_subscription",
                }
            )
        if group_title == "admin":
            return admin_capabilities
        if group_title == "admin_editor":
            return [
                "auth/login",
                "auth/set_password",
                "auth/use_session",
                "bootstrap/view",
                "dictionary/archive_word",
                "dictionary/list_filters",
                "dictionary/list_words",
                "dictionary/play_audio",
                "dictionary/update_word",
                "dictionary/verify_word",
                "dictionary/view_word",
                "imports/list_item_filters",
                "imports/list_items",
                "imports/list_job_filters",
                "imports/list_jobs",
                "imports/view_job",
            ]
        return []


class FakeWebLoginHistoryRepository:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = list(rows or [])

    def create(self, **kwargs):
        row = {"id": len(self.rows) + 1, **kwargs}
        self.rows.append(row)
        return dict(row)

    def list_admin(self, **kwargs):
        items = self.rows
        user_id = kwargs.get("telegram_user_id")
        if user_id is None:
            user_id = kwargs.get("user_id")
        if user_id is not None:
            items = [
                item
                for item in items
                if item.get("telegram_user_id") == user_id
                or str(item.get("user_id") or item.get("user_uuid")) == str(user_id)
            ]
        interface_context = kwargs.get("interface_context")
        if interface_context:
            context_values = interface_context if isinstance(interface_context, list) else [interface_context]
            items = [item for item in items if item.get("interface_context") in context_values]
        result = kwargs.get("result")
        if result:
            result_values = result if isinstance(result, list) else [result]
            items = [item for item in items if item.get("result") in result_values]
        api_origin = str(kwargs.get("api_origin") or "").lower()
        if api_origin:
            items = [item for item in items if api_origin in str(item.get("api_origin") or "").lower()]
        return {
            "items": [dict(item) for item in items],
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 50),
            "total": len(items),
            "pages": 1 if items else 0,
        }

    def list_latest_for_user(self, user_id, *, limit):
        return [
            dict(item)
            for item in self.rows
            if item.get("telegram_user_id") == user_id
            or str(item.get("user_id") or item.get("user_uuid")) == str(user_id)
        ][:limit]

    def append(self, row):
        self.rows.append(row)

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, index):
        return self.rows[index]

    def __eq__(self, other):
        return self.rows == other


class FakeErrorLogRepository:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = list(rows or [])

    def create(self, level, text, *, context_json=None) -> None:
        self.rows.append({"level": level, "text": text, "context_json": context_json})

    def list_admin(self, **kwargs):
        items = self.rows
        level = kwargs.get("level")
        if level:
            level_values = level if isinstance(level, list) else [level]
            items = [item for item in items if item.get("level") in level_values]
        search = str(kwargs.get("search") or "").lower()
        if search:
            items = [item for item in items if search in str(item.get("text") or "").lower()]
        return {
            "items": [dict(item) for item in items],
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 50),
            "total": len(items),
            "pages": 1 if items else 0,
        }

    def get_filter_metadata(self):
        return {"entity": "error_log", "page_sizes": [50, 100], "filters": []}


class FakeBotMessageLogRepository:
    def __init__(self, db) -> None:
        self.db = db

    def get_latest_active_screen(self, telegram_user_id):
        return None

    def create(self, telegram_user_id, chat_id, message_id, screen_id, delete_after, current_time):
        row = {
            "telegram_user_id": telegram_user_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "screen_id": screen_id,
            "delete_after": delete_after,
            "current_time": current_time,
        }
        self.db.created_bot_messages.append(row)
        return {"id": len(self.db.created_bot_messages), **row}


class FakeAdminAuthRepository:
    def __init__(self, db) -> None:
        self.db = db

    def ensure_dev_admin_user(self, *, current_time):
        self.db.admin_user["updated"] = current_time
        return dict(self.db.admin_user)

    def get_credential(self, telegram_user_id):
        return self.db.admin_credential

    def set_password_hash(self, telegram_user_id, password_hash, *, current_time):
        self.db.admin_credential = {"telegram_user_id": telegram_user_id, "password_hash": password_hash}

    def mark_password_prompted(self, telegram_user_id, *, current_time):
        if telegram_user_id == self.db.admin_user["telegram_user_id"]:
            self.db.admin_user["admin_web_password_prompted"] = True

    def create_otp_challenge(self, **kwargs):
        row = {
            "id": len(self.db.otp_challenges) + 1,
            "attempts_count": 0,
            "consumed": None,
            **kwargs,
        }
        self.db.otp_challenges.append(row)
        return dict(row)

    def save_otp_message_id(self, challenge_id, message_id, *, current_time):
        for row in self.db.otp_challenges:
            if row["id"] == challenge_id:
                row["sent_message_id"] = message_id
                row["updated"] = current_time

    def get_otp_challenge(self, challenge_id):
        for row in self.db.otp_challenges:
            if row["id"] == challenge_id:
                return dict(row)
        return None

    def increment_otp_attempts(self, challenge_id, *, current_time):
        for row in self.db.otp_challenges:
            if row["id"] == challenge_id:
                row["attempts_count"] += 1
                row["updated"] = current_time

    def consume_otp_challenge(self, challenge_id, *, current_time):
        for row in self.db.otp_challenges:
            if row["id"] == challenge_id:
                row["consumed"] = current_time
                row["updated"] = current_time

    def create_magic_link(self, **kwargs):
        row = {"id": len(self.db.magic_links) + 1, **kwargs}
        self.db.magic_links.append(row)
        return dict(row)

    def get_active_magic_link_by_token_hash(self, token_hash, *, current_time):
        for row in self.db.magic_links:
            if (
                row["token_hash"] == token_hash
                and row["expires"] > current_time
                and row["id"] not in self.db.consumed_magic_link_ids
            ):
                return dict(row)
        return None

    def consume_magic_link(self, magic_link_id, *, current_time):
        self.db.consumed_magic_link_ids.append(magic_link_id)

    def create_session(self, **kwargs):
        row = {"id": len(self.db.sessions) + 1, **kwargs}
        self.db.sessions.append(row)
        return dict(row)

    def schedule_bot_restore(self, **kwargs):
        self.db.restores.append(kwargs)
        return {"id": len(self.db.restores), **kwargs}

    def get_active_session_by_token_hash(self, *, token_hash_matcher, current_time):
        for row in self.db.sessions:
            if row.get("revoked") is None and row.get("expires") > current_time and token_hash_matcher(row["session_token_hash"]):
                return dict(row)
        return None

    def touch_session(self, session_id, *, current_time):
        for row in self.db.sessions:
            if row["id"] == session_id:
                row["last_seen"] = current_time
                row["updated"] = current_time

    def revoke_session(self, session_id, *, current_time):
        for row in self.db.sessions:
            if row["id"] == session_id and row.get("revoked") is None:
                row["revoked"] = current_time
                row["updated"] = current_time

    def revoke_session_by_token_match(self, *, token_hash_matcher, current_time):
        for row in self.db.sessions:
            if row.get("revoked") is None and token_hash_matcher(row["session_token_hash"]):
                row["revoked"] = current_time
                row["updated"] = current_time
                return


class FakeAdminDb:
    def __init__(self, pending_row: dict | None = None) -> None:
        self.pending_row = pending_row
        self.updated_payload = None
        self.settings = SimpleNamespace(
            app_web_base_url="https://cronolex.local",
            app_admin_magic_link_ttl_minutes=5,
            app_admin_otp_ttl_minutes=5,
            app_admin_session_hours=12,
            app_admin_dev_login_enabled=False,
            app_env="test",
            app_bot_message_retention_days=30,
        )
        self.admin_user = {
            "user_id": "11111111-1111-4111-8111-111111111111",
            "user_uuid": "11111111-1111-4111-8111-111111111111",
            "telegram_user_id": 1,
            "username": "admin",
            "chat_id": 55,
            "acl_group_title": "super_admin",
            "status": "active",
            "learning_role": "student",
            "interface_locale": "uk",
            "admin_web_password_prompted": False,
        }
        self.admin_credential = None
        self.client_web_credentials = {}
        self.client_web_sessions = []
        self._admin_users = []
        self.magic_links = []
        self.sessions = []
        self.otp_challenges = []
        self.consumed_magic_link_ids = []
        self._web_login_history = FakeWebLoginHistoryRepository()
        self.created_bot_messages = []
        self.restores = []
        self.import_job = None
        self.import_jobs = []
        self.import_items = []
        self.google_doc_progress = []
        self.import_data_user_audio_roots = None
        self.import_data_audio_storage_provider = None
        self._ai_usage_session_rows = []
        self.task_log = None
        self.user_task_logs = []
        self._error_logs = FakeErrorLogRepository()
        self.processing_task_log = None
        self.dictionary_entry = None
        self.dictionary_entries = []
        self.dictionary_update_audio_storage_provider = None
        self.dictionary_audio = None
        self.pending_word_audio = None
        self.user_status_updates = []
        self.deleted_user_ids = []
        self.archived_dictionary_entry_ids = []
        self.deleted_dictionary_entry_ids = []
        self.assigned_dictionary_entry_count = 0
        self.current_app_version = "0.0.7"
        self._admin_auth_repository = FakeAdminAuthRepository(self)
        self.bot_message_logs = FakeBotMessageLogRepository(self)
        self.task_logs = FakeTaskLogRepository(self)
        self._ai_usage_sessions_repository = FakeAIUsageSessionRepository(self)
        self._pending_words_repository = FakePendingWordRepository(self)
        self._acl_permissions_repository = FakeAclPermissionRepository(self)
        self.subscription_updates = []
        self.app_setting_values = {}

    @property
    def user_learning_settings(self):
        return self

    @property
    def user_profiles(self):
        return self

    @property
    def admin_auth(self):
        return self._admin_auth_repository

    @property
    def client_web_auth(self):
        return self

    @property
    def admin_dictionary(self):
        return self

    @property
    def user_dictionary(self):
        return self

    @property
    def admin_users(self):
        return self

    @admin_users.setter
    def admin_users(self, users):
        self._admin_users = users

    @property
    def pending_words(self):
        return self._pending_words_repository

    @property
    def ai_usage_sessions(self):
        return self._ai_usage_sessions_repository

    @ai_usage_sessions.setter
    def ai_usage_sessions(self, value):
        self._ai_usage_session_rows = value

    @property
    def acl_permissions(self):
        return self._acl_permissions_repository

    @property
    def subscriptions(self):
        return self

    @property
    def app_settings(self):
        return self

    @property
    def web_login_history(self):
        return self._web_login_history

    @web_login_history.setter
    def web_login_history(self, rows):
        self._web_login_history = rows if isinstance(rows, FakeWebLoginHistoryRepository) else FakeWebLoginHistoryRepository(rows)

    @property
    def error_logs(self):
        return self._error_logs

    @error_logs.setter
    def error_logs(self, rows):
        self._error_logs = rows if isinstance(rows, FakeErrorLogRepository) else FakeErrorLogRepository(rows)

    def get_value(self, key):
        return self.app_setting_values.get(key)

    def upsert_value(self, key, value_json, current_time):
        self.app_setting_values[key] = dict(value_json)
        return {"key": key, "value_json": dict(value_json), "created": current_time, "updated": current_time}

    def get_current_app_version(self):
        return self.current_app_version

    def set_current_app_version(self, version, *, current_time):
        self.current_app_version = version
        return self.current_app_version

    def set_interface_locale(self, telegram_user_id, interface_locale):
        if telegram_user_id == self.admin_user["telegram_user_id"]:
            self.admin_user["interface_locale"] = interface_locale

    def get_by_id(self, user_id):
        for user in self._admin_users:
            if str(user.get("user_id") or user.get("user_uuid") or user.get("telegram_user_id")) == str(user_id):
                return dict(user)
        if str(self.admin_user.get("user_id") or self.admin_user.get("user_uuid")) == str(user_id):
            return dict(self.admin_user)
        if str(self.admin_user["telegram_user_id"]) == str(user_id):
            return dict(self.admin_user)
        return None

    def get_login_by_username(self, normalized_username):
        candidates = [
            user
            for user in [*self._admin_users, self.admin_user]
            if str(user.get("username") or "").lower() == normalized_username and user.get("status") == "active"
        ]
        if len(candidates) != 1:
            return None
        return dict(candidates[0])

    def list_admin(self, **kwargs):
        items = self._admin_users or [self.admin_user]
        archived = bool(kwargs.get("archived"))
        items = [item for item in items if (item.get("status") == "archived") is archived]
        search = str(kwargs.get("search") or "").lower()
        if search:
            items = [
                item
                for item in items
                if search in str(item.get("username") or "").lower()
                or search in str(item.get("telegram_user_id") or "").lower()
            ]
        user_id = kwargs.get("user_id")
        if user_id:
            items = [item for item in items if str(item.get("user_id") or item.get("user_uuid")) == str(user_id)]
        role = kwargs.get("role")
        if role:
            role_values = role if isinstance(role, list) else [role]
            items = [item for item in items if item.get("acl_group_title") in role_values]
        user_type = kwargs.get("user_type")
        if user_type == "admin":
            items = [
                item
                for item in items
                if item.get("acl_group_title") in {"admin", "admin_editor", "super_admin"}
            ]
        elif user_type in {"student", "teacher"}:
            items = [
                item
                for item in items
                if item.get("learning_role", "student") == user_type
                and item.get("acl_group_title") not in {"admin", "admin_editor", "super_admin"}
            ]
        status = kwargs.get("status")
        if status:
            status_values = status if isinstance(status, list) else [status]
            items = [item for item in items if item.get("status") in status_values]
        return {
            "items": [dict(item) for item in items],
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 50),
            "total": len(items),
            "pages": 1 if items else 0,
        }

    def get_filter_metadata(self):
        return {
            "entity": "users",
            "page_sizes": [50, 100],
            "filters": [
                {
                    "name": "user_type",
                    "options": [
                        {"value": "admin", "label": "Admin"},
                        {"value": "student", "label": "Student"},
                        {"value": "teacher", "label": "Teacher"},
                    ],
                },
                {
                    "name": "role",
                    "options": [
                        {"value": "student", "label": "user"},
                        {"value": "admin", "label": "admin"},
                        {"value": "admin_editor", "label": "admin editor"},
                        {"value": "super_admin", "label": "super admin"},
                    ],
                },
                {
                    "name": "status",
                    "options": [
                        {"value": "active", "label": "active"},
                        {"value": "inactive", "label": "inactive"},
                        {"value": "blocked", "label": "blocked"},
                        {"value": "archived", "label": "archived"},
                    ],
                },
            ],
        }

    def clear_password_hash(self, telegram_user_id, *, current_time):
        credential = self.client_web_credentials.get(telegram_user_id)
        if credential is not None:
            credential["password_hash"] = None
            credential["updated"] = current_time
        for user in [*self._admin_users, self.admin_user]:
            if user["telegram_user_id"] == telegram_user_id:
                user["client_web_password_prompted"] = False
                user["updated"] = current_time

    def revoke_sessions_for_user(self, telegram_user_id, *, current_time):
        revoked_count = 0
        for session in self.client_web_sessions:
            if session["telegram_user_id"] == telegram_user_id and session.get("revoked") is None:
                session["revoked"] = current_time
                session["updated"] = current_time
                revoked_count += 1
        return revoked_count

    @property
    def user_import_jobs(self):
        return self

    @property
    def user_import_items(self):
        return self

    def list_by_pending_word(self, pending_word_id):
        return [dict(item) for item in self.import_items if item.get("pending_word_id") == pending_word_id]

    def get_job(self, job_id):
        if self.import_job and self.import_job["id"] == job_id:
            return dict(self.import_job)
        for job in self.import_jobs:
            if job["id"] == job_id:
                return dict(job)
        return None

    def list_admin_jobs(self, **kwargs):
        items = self.import_jobs
        status = kwargs.get("status")
        if status:
            status_values = status if isinstance(status, list) else [status]
            items = [item for item in items if item.get("status") in status_values]
        source_type = kwargs.get("source_type")
        if source_type:
            source_values = source_type if isinstance(source_type, list) else [source_type]
            items = [item for item in items if item.get("source_type") in source_values]
        user_id = kwargs.get("telegram_user_id")
        if user_id is not None:
            items = [item for item in items if item.get("telegram_user_id") == user_id]
        search = str(kwargs.get("search") or "").lower()
        if search:
            items = [
                item
                for item in items
                if search in str(item.get("source_identifier") or "").lower()
                or search in str(item.get("last_error") or "").lower()
            ]
        return {
            "items": [dict(item) for item in items],
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 50),
            "total": len(items),
            "pages": 1 if items else 0,
        }

    def get_admin_job_filter_metadata(self):
        return {"entity": "import_jobs", "page_sizes": [50, 100], "filters": []}

    def list_admin_items(self, **kwargs):
        items = self.import_items
        status = kwargs.get("status")
        if status:
            status_values = status if isinstance(status, list) else [status]
            items = [item for item in items if item.get("status") in status_values]
        import_job_id = kwargs.get("import_job_id")
        if import_job_id is not None:
            items = [item for item in items if item.get("import_job_id") == import_job_id]
        user_id = kwargs.get("telegram_user_id")
        if user_id is not None:
            items = [item for item in items if item.get("telegram_user_id") == user_id]
        search = str(kwargs.get("search") or "").lower()
        if search:
            items = [
                item
                for item in items
                if search in str(item.get("lookup_word") or "").lower()
                or search in str(item.get("raw_value") or "").lower()
                or search in str(item.get("error_text") or "").lower()
            ]
        return {
            "items": [dict(item) for item in items],
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 50),
            "total": len(items),
            "pages": 1 if items else 0,
        }

    def get_admin_item_filter_metadata(self):
        return {"entity": "import_items", "page_sizes": [50, 100], "filters": []}

    def list_items(self, job_id):
        return [dict(item) for item in self.import_items if item.get("import_job_id") == job_id]

    def delete_all_import_data(self, *, audio_storage_provider, user_audio_roots=None):
        self.import_data_audio_storage_provider = audio_storage_provider
        self.import_data_user_audio_roots = list(user_audio_roots or [])
        result = {
            "deleted_import_items": len(self.import_items),
            "deleted_import_jobs": len(self.import_jobs),
            "deleted_google_doc_progress": len(self.google_doc_progress),
            "cleared_google_doc_bindings": 0,
            "deleted_user_dictionary_entries": 0,
            "deleted_user_dictionary_embeddings": 0,
            "deleted_user_word_assignments": 0,
            "deleted_user_learning_session_words": 0,
            "deleted_user_audio_files": 0,
        }
        self.import_items = []
        self.import_jobs = []
        self.google_doc_progress = []
        return result

    def list_item_status_counts(self, job_id):
        counts = {}
        for item in self.import_items:
            if item.get("import_job_id") != job_id:
                continue
            status = str(item.get("status") or "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def update_entry(self, entry_id, **kwargs):
        if self.dictionary_entry is None or self.dictionary_entry["id"] != entry_id:
            return None
        self.dictionary_update_audio_storage_provider = kwargs["audio_storage_provider"]
        self.dictionary_entry = {
            **self.dictionary_entry,
            **{
                key: value
                for key, value in kwargs.items()
                if key not in {"audio_storage_provider", "current_time"} and value is not None
            },
            "updated": kwargs["current_time"],
        }
        return dict(self.dictionary_entry)

    def list_entries(self, **kwargs):
        items = self.dictionary_entries or ([self.dictionary_entry] if self.dictionary_entry else [])
        search = str(kwargs.get("search") or "").lower()
        if search:
            items = [item for item in items if search in str(item.get("word") or "").lower()]
        archived = bool(kwargs.get("archived"))
        items = [item for item in items if bool(item.get("archived")) is archived]
        if kwargs.get("verified") == "verified":
            items = [item for item in items if bool(item.get("is_teacher_verified"))]
        elif kwargs.get("verified") == "unverified":
            items = [item for item in items if not bool(item.get("is_teacher_verified"))]
        return {
            "items": [dict(item) for item in items],
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 50),
            "total": len(items),
            "pages": 1 if items else 0,
        }

    def get_entry(self, entry_id):
        if self.dictionary_entry and self.dictionary_entry["id"] == entry_id:
            return dict(self.dictionary_entry)
        for entry in self.dictionary_entries:
            if entry["id"] == entry_id:
                return dict(entry)
        return None

    def get_filter_metadata(self):
        return {"entity": "dictionary", "page_sizes": [50, 100], "filters": []}

    def get_entry_audio(self, entry_id):
        if self.dictionary_audio and self.dictionary_audio["id"] == entry_id:
            return dict(self.dictionary_audio)
        return None

    def set_acl_group_by_title(self, telegram_user_id, role, *, current_time):
        if telegram_user_id != self.admin_user["telegram_user_id"]:
            return None
        self.admin_user = {**self.admin_user, "acl_group_title": role, "updated": current_time}
        return dict(self.admin_user)

    def set_learning_role(self, telegram_user_id, learning_role, *, current_time):
        if telegram_user_id != self.admin_user["telegram_user_id"]:
            return None
        self.admin_user = {**self.admin_user, "learning_role": learning_role, "updated": current_time}
        return dict(self.admin_user)

    def set_plan_for_user(self, user_uuid, *, plan_key, current_time):
        if str(user_uuid) != str(self.admin_user["user_id"]):
            return None
        subscription = {
            "user_uuid": str(user_uuid),
            "plan_key": plan_key,
            "start": current_time,
            "end": None,
            "trial_start": None,
            "trial_end": None,
            "status": "active",
            "created": current_time,
            "updated": current_time,
        }
        self.subscription_updates.append(subscription)
        self.admin_user = {**self.admin_user, "subscription": subscription, "subscription_plan_key": plan_key}
        return dict(subscription)

    def set_trial_for_user(self, user_uuid, *, trial_duration_days, current_time):
        if str(user_uuid) != str(self.admin_user["user_id"]):
            return None
        if self.admin_user.get("subscription_plan_key") not in {None, "free"}:
            return None
        subscription = {
            "user_uuid": str(user_uuid),
            "plan_key": self.admin_user.get("subscription_plan_key") or "free",
            "start": current_time,
            "end": None,
            "trial_start": current_time,
            "trial_end": current_time + timedelta(days=trial_duration_days),
            "status": "active",
            "created": current_time,
            "updated": current_time,
        }
        self.subscription_updates.append(subscription)
        self.admin_user = {
            **self.admin_user,
            "subscription": subscription,
            "subscription_plan_key": subscription["plan_key"],
            "trial_end": subscription["trial_end"],
        }
        return dict(subscription)

    def clear_trial_for_user(self, user_uuid, *, current_time):
        if str(user_uuid) != str(self.admin_user["user_id"]):
            return None
        subscription = {
            **(self.admin_user.get("subscription") or {}),
            "user_uuid": str(user_uuid),
            "plan_key": self.admin_user.get("subscription_plan_key") or "free",
            "trial_start": None,
            "trial_end": None,
            "updated": current_time,
        }
        self.subscription_updates.append(subscription)
        self.admin_user = {
            **self.admin_user,
            "subscription": subscription,
            "subscription_plan_key": subscription["plan_key"],
            "trial_end": None,
        }
        return dict(subscription)

    def set_status(self, telegram_user_id, status, *, current_time):
        if telegram_user_id != self.admin_user["telegram_user_id"]:
            return False
        self.user_status_updates.append({"telegram_user_id": telegram_user_id, "status": status, "updated": current_time})
        return True

    def delete(self, telegram_user_id):
        if telegram_user_id != self.admin_user["telegram_user_id"]:
            return False
        self.deleted_user_ids.append(telegram_user_id)
        return True

    def set_entry_archived(self, entry_id, *, is_archived, current_time):
        if self.dictionary_entry is None or self.dictionary_entry["id"] != entry_id:
            return False
        self.archived_dictionary_entry_ids.append(entry_id)
        self.dictionary_entry = {**self.dictionary_entry, "archived": is_archived, "updated": current_time}
        return True

    def delete_entry(self, entry_id):
        if self.dictionary_entry is None or self.dictionary_entry["id"] != entry_id:
            return False
        self.deleted_dictionary_entry_ids.append(entry_id)
        return True

    def count_assignments_for_word(self, *, word_source, word_id):
        if word_source == "core" and self.dictionary_entry and self.dictionary_entry["id"] == word_id:
            return self.assigned_dictionary_entry_count
        return 0

    def mark_entries_teacher_verified(self, entry_ids, *, verified_by_user_uuid=None, verified_by_telegram_user_id=None, current_time):
        ids = set(entry_ids)
        updated = 0
        verifier_id = verified_by_user_uuid or verified_by_telegram_user_id
        next_entries = []
        for entry in self.dictionary_entries:
            if entry["id"] in ids and not entry.get("archived"):
                updated += 1
                next_entries.append({
                    **entry,
                    "is_teacher_verified": True,
                    "teacher_verified_by_user_uuid": verifier_id,
                    "teacher_verified_at": current_time,
                    "updated": current_time,
                })
            else:
                next_entries.append(entry)
        self.dictionary_entries = next_entries
        if self.dictionary_entry and self.dictionary_entry["id"] in ids:
            updated += 1
            self.dictionary_entry = {
                **self.dictionary_entry,
                "is_teacher_verified": True,
                "teacher_verified_by_user_uuid": verifier_id,
                "teacher_verified_at": current_time,
                "updated": current_time,
            }
        return updated


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.sent_messages = []
        self.deleted_messages = []

    def send_message(self, *, chat_id, text, reply_markup=None, disable_notification=False, ignore_errors=False):
        self.sent_messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup,
                "disable_notification": disable_notification,
                "ignore_errors": ignore_errors,
            }
        )
        return 123

    def delete_message(self, *, chat_id, message_id, ignore_errors=False):
        self.deleted_messages.append({"chat_id": chat_id, "message_id": message_id, "ignore_errors": ignore_errors})
        return True


class FakeActionOtpVerifier:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls = []
        self.error = error

    def verify_action_otp(self, *, user, action_key, challenge_id, otp) -> None:
        self.calls.append(
            {
                "user": user,
                "action_key": action_key,
                "challenge_id": challenge_id,
                "otp": otp,
            }
        )
        if self.error is not None:
            raise self.error


def build_pending_row(status: str = "ready_for_review") -> dict:
    return {
        "id": 77,
        "word": "harbor",
        "status": status,
        "translation_uk": "гавань",
        "translation_ru": None,
        "translation_pl": None,
        "examples_json": ["The harbor was quiet."],
        "audio_path": "runtime/user_import_audio/harbor.mp3",
    }


def test_admin_service_dependencies_preserve_public_dependency_wiring() -> None:
    db = FakeAdminDb(build_pending_row())
    dependencies = build_admin_service_dependencies(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())

    assert isinstance(dependencies.admin_settings_service.action_otp_verifier, AdminSettingsActionOtpVerifier)
    assert dependencies.admin_settings_service.action_otp_verifier.verifier is dependencies.admin_auth_service
    assert isinstance(dependencies.admin_ai_usage_read_service.action_otp_verifier, AdminAIUsageActionOtpVerifier)
    assert dependencies.admin_ai_usage_read_service.action_otp_verifier.verifier is dependencies.admin_auth_service
    assert dependencies.admin_entity_service.user_action_service is dependencies.admin_user_action_service
    assert dependencies.admin_entity_service.dictionary_action_service is dependencies.admin_dictionary_action_service
    assert dependencies.admin_user_dictionary_bulk_action.promote_action is dependencies.admin_user_dictionary_promote_action


def test_get_import_job_detail_returns_counts_and_task_context_without_items() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_job = {
        "id": 91,
        "user_id": "11111111-1111-4111-8111-111111111111",
        "telegram_user_id": 1,
        "task_log_id": 13,
        "status": "completed",
        "source_type": "bound_google_doc",
        "source_identifier": "doc",
    }
    db.import_items = [
        {"id": 5, "import_job_id": 91, "pending_word_id": 77, "lookup_word": "harbor", "status": "imported"},
        {"id": 6, "import_job_id": 91, "pending_word_id": None, "lookup_word": "dock", "status": "failed"},
    ]
    db.task_log = {"id": 13, "task_type": "bound_google_doc_sync", "status": "success"}
    db.processing_task_log = {
        "id": 14,
        "import_job_id": 91,
        "task_type": "user_vocabulary_import_job_process",
        "status": "success",
    }
    service = AdminReadService(db)

    result = service.get_import_job_detail(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        import_job_id=91,
    )

    assert result["job"]["id"] == 91
    assert result["status_counts"] == {"imported": 1, "failed": 1}
    assert "items" not in result
    assert result["origin_task_log"]["id"] == 13
    assert result["processing_task_log"]["id"] == 14
    assert result["user"]["telegram_user_id"] == 1


def test_get_task_log_detail_returns_related_user_and_import_job() -> None:
    db = FakeAdminDb(build_pending_row())
    db.task_log = {
        "id": 14,
        "user_id": "11111111-1111-4111-8111-111111111111",
        "telegram_user_id": 1,
        "import_job_id": 91,
        "task_type": "user_vocabulary_import_job_process",
        "status": "success",
    }
    db.import_job = {
        "id": 91,
        "user_id": "11111111-1111-4111-8111-111111111111",
        "telegram_user_id": 1,
        "status": "completed",
    }
    service = AdminReadService(db)

    result = service.get_task_log_detail(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        task_log_id=14,
    )

    assert result["task_log"]["id"] == 14
    assert result["user"]["telegram_user_id"] == 1
    assert result["import_job"]["id"] == 91


def test_list_import_jobs_filters_and_requires_admin() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_jobs = [
        {"id": 91, "telegram_user_id": 1, "status": "completed", "source_type": "bound_google_doc", "source_identifier": "doc-a"},
        {"id": 92, "telegram_user_id": 2, "status": "failed", "source_type": "manual", "source_identifier": "doc-b"},
    ]
    service = AdminReadService(db)

    result = service.list_import_jobs(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        params={"page": 1, "page_size": 50, "status": ["completed"], "search": "doc"},
    )

    assert [item["id"] for item in result["items"]] == [91]


def test_list_import_items_filters_by_job_user_status_and_search() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_items = [
        {"id": 5, "import_job_id": 91, "telegram_user_id": 1, "lookup_word": "harbor", "raw_value": "Harbor", "status": "imported"},
        {"id": 6, "import_job_id": 92, "telegram_user_id": 2, "lookup_word": "dock", "raw_value": "Dock", "status": "failed"},
    ]
    service = AdminReadService(db)

    result = service.list_import_items(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        params={"page": 1, "page_size": 50, "status": ["imported"], "import_job_id": 91, "telegram_user_id": 1, "search": "har"},
    )

    assert [item["id"] for item in result["items"]] == [5]


def test_get_user_detail_returns_recent_context() -> None:
    db = FakeAdminDb(build_pending_row())
    db.web_login_history = [{"id": 1, "telegram_user_id": 1, "result": "success"}]
    db.user_task_logs = [{"id": 14, "telegram_user_id": 1, "task_type": "bound_google_doc_sync"}]
    service = AdminReadService(db)

    result = service.get_user_detail(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        user_id=1,
    )

    assert result["user"]["telegram_user_id"] == 1
    assert result["latest_login_history"][0]["id"] == 1
    assert result["recent_task_logs"][0]["id"] == 14


def test_admin_read_service_returns_user_dictionary_audio_path() -> None:
    db = FakeAdminDb(build_pending_row())
    db.dictionary_audio = {"id": 10, "audio_path": "runtime/user_audio/harbor.mp3"}
    service = AdminReadService(db)

    audio_path = service.get_user_dictionary_audio_path(
        entry_id=10,
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
    )

    assert audio_path == "runtime/user_audio/harbor.mp3"


def test_admin_read_service_preserves_user_dictionary_audio_denied_acl_detail() -> None:
    service = AdminReadService(FakeAdminDb(build_pending_row()))

    try:
        service.get_user_dictionary_audio_path(
            entry_id=10,
            actor={"telegram_user_id": 1, "acl_group_title": "student"},
        )
    except AdminUserDictionaryReadAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminUserDictionaryReadAccessDeniedError was expected")


def test_admin_dictionary_service_preserves_audio_denied_acl_detail() -> None:
    service = AdminDictionaryService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.get_audio_path(
            entry_id=10,
            actor={"telegram_user_id": 1, "acl_group_title": "student"},
        )
    except AdminDictionaryServiceAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminDictionaryServiceAccessDeniedError was expected")


def test_list_login_history_accepts_client_web_context() -> None:
    db = FakeAdminDb(build_pending_row())
    db.web_login_history = [
        {"id": 1, "telegram_user_id": 1, "interface_context": "client_web", "result": "success"},
        {"id": 2, "telegram_user_id": 1, "interface_context": "admin", "result": "success"},
    ]
    service = AdminReadService(db)

    result = service.list_login_history(
        actor={"telegram_user_id": 1, "acl_group_title": "admin"},
        params={"page": 1, "page_size": 50, "interface_context": ["client_web"]},
    )

    assert [item["id"] for item in result["items"]] == [1]


def test_reset_user_password_clears_client_password_and_revokes_sessions() -> None:
    db = FakeAdminDb(build_pending_row())
    db.admin_users = [
        {
            "telegram_user_id": 2,
            "username": "student",
            "chat_id": 56,
            "acl_group_title": "student",
            "status": "active",
            "interface_locale": "uk",
            "client_web_password_prompted": True,
        }
    ]
    db.client_web_credentials[2] = {"telegram_user_id": 2, "password_hash": "stored-hash"}
    db.client_web_sessions = [
        {"id": 1, "telegram_user_id": 2, "revoked": None},
        {"id": 2, "telegram_user_id": 2, "revoked": datetime(2026, 1, 1, 10, 0, 0)},
        {"id": 3, "telegram_user_id": 3, "revoked": None},
    ]
    service = AdminUserActionService(db, TimeService("Europe/Kyiv"))

    result = service.reset_password(
        actor={"telegram_user_id": 1, "acl_group_title": "super_admin"},
        user_id=2,
    )

    assert result == {"status": "ok", "revoked_sessions": 1}
    assert db.client_web_credentials[2]["password_hash"] is None
    assert db._admin_users[0]["client_web_password_prompted"] is False
    assert db.client_web_sessions[0]["revoked"] is not None
    assert db.client_web_sessions[1]["revoked"] == datetime(2026, 1, 1, 10, 0, 0)
    assert db.client_web_sessions[2]["revoked"] is None


def test_reset_user_password_requires_super_admin_capability() -> None:
    service = AdminUserActionService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    try:
        service.reset_password(actor={"telegram_user_id": 1, "acl_group_title": "admin"}, user_id=1)
    except AdminUserActionAccessDeniedError as error:
        assert error.detail == "Password reset is not allowed"
    else:  # pragma: no cover
        raise AssertionError("AdminUserActionAccessDeniedError was expected")


def test_set_user_subscription_requires_super_admin_capability() -> None:
    service = AdminUserActionService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    try:
        service.set_subscription(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            target_user_id="11111111-1111-4111-8111-111111111111",
            plan_key="premium",
        )
    except AdminUserActionAccessDeniedError as error:
        assert error.detail == "Subscription change is not allowed"
    else:  # pragma: no cover
        raise AssertionError("AdminUserActionAccessDeniedError was expected")


def test_reset_user_password_raises_local_error_for_missing_user() -> None:
    service = AdminUserActionService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    try:
        service.reset_password(actor={"telegram_user_id": 1, "acl_group_title": "super_admin"}, user_id=404)
    except AdminUserActionNotFoundError as error:
        assert error.detail == "User not found"
    else:  # pragma: no cover
        raise AssertionError("AdminUserActionNotFoundError was expected")


def test_admin_auth_service_sends_otp_through_telegram_gateway() -> None:
    gateway = FakeTelegramGateway()
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), gateway)

    message_id = service.send_otp_message({"telegram_user_id": 1, "chat_id": 55}, "123456")

    assert message_id == 123
    assert gateway.sent_messages == [
        {
            "chat_id": 55,
            "text": "Код входу CronoLex Admin: 123 456",
            "reply_markup": None,
            "disable_notification": False,
            "ignore_errors": False,
        }
    ]
    assert db.created_bot_messages[-1]["screen_id"] == "auth:otp"


def test_admin_auth_service_cleans_otp_message_through_telegram_gateway() -> None:
    gateway = FakeTelegramGateway()
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), gateway)

    service.cleanup_otp_message(
        {"sent_chat_id": 55, "sent_message_id": 12},
        {"telegram_user_id": 1, "chat_id": 99},
    )

    assert gateway.deleted_messages == [{"chat_id": 55, "message_id": 12, "ignore_errors": True}]
    assert gateway.sent_messages == [
        {
            "chat_id": 55,
            "text": "Вхід виконано успішно",
            "reply_markup": None,
            "disable_notification": False,
            "ignore_errors": True,
        }
    ]
    assert db.created_bot_messages[-1]["screen_id"] == "auth:login_success"
    assert db.restores == []


def test_admin_auth_service_create_magic_link_url_stores_short_lived_token(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())

    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.token_urlsafe", lambda size: "magic-token")

    url = service.create_admin_magic_link_url(telegram_user_id=1, target_path="/admin/user-dictionary")

    assert url == "https://cronolex.local/admin/auth/magic?token=magic-token&next=%2Fadmin%2Fuser-dictionary"
    assert db.magic_links[0]["telegram_user_id"] == 1
    assert db.magic_links[0]["token_hash"] == hash_token_for_lookup("magic-token")
    assert db.magic_links[0]["target_path"] == "/admin/user-dictionary"
    assert db.magic_links[0]["expires"] > datetime.now().astimezone()


def test_admin_auth_service_consume_magic_link_creates_admin_session(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    gateway = FakeTelegramGateway()
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), gateway)
    current_time = service.time_service.now()
    db.magic_links.append(
        {
            "id": 11,
            "telegram_user_id": 1,
            "token_hash": hash_token_for_lookup("magic-token"),
            "target_path": "/admin/user-dictionary",
            "expires": current_time + timedelta(minutes=5),
            "created": current_time,
            "updated": current_time,
        }
    )
    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.token_urlsafe", lambda size: "session-token")

    result = service.consume_magic_link(token="magic-token")

    assert result.session_token == "session-token"
    assert result.target_path == "/admin/user-dictionary"
    assert result.user["telegram_user_id"] == 1
    assert db.consumed_magic_link_ids == [11]
    assert db.sessions[0]["telegram_user_id"] == 1
    assert db.web_login_history[-1]["event_type"] == "magic_login"
    assert db.web_login_history[-1]["result"] == "success"
    assert db.created_bot_messages[-1]["screen_id"] == "auth:login_success"
    assert db.restores == []


def test_admin_settings_service_updates_locale_and_version() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    result = service.update_settings(
        user={"telegram_user_id": 1, "acl_group_title": "super_admin", "interface_locale": "uk"},
        payload={"interface_locale": "pl", "app_version": "0.0.5-beta"},
    )

    assert result["user"]["interface_locale"] == "pl"
    assert result["settings"]["interface_locale"] == "pl"
    assert result["settings"]["app_version"] == "0.0.5-beta"


def test_admin_settings_service_rejects_invalid_locale() -> None:
    service = AdminSettingsService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_settings(
            user={"telegram_user_id": 1, "acl_group_title": "super_admin", "interface_locale": "uk"},
            payload={"interface_locale": "en"},
        )
    except AdminSettingsValidationError as error:
        assert "interface_locale" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_admin_settings_service_update_requires_acl_before_payload_validation() -> None:
    service = AdminSettingsService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_settings(
            user={"telegram_user_id": 1, "acl_group_title": "student", "interface_locale": "uk"},
            payload={"billing_settings": {"monobank_mode": "test"}},
        )
    except AdminSettingsAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsAccessDeniedError was expected")


def test_admin_settings_service_app_version_update_requires_acl_manage() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_settings(
            user={"telegram_user_id": 1, "acl_group_title": "admin", "interface_locale": "uk"},
            payload={"app_version": "0.0.8"},
        )
    except AdminSettingsAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsAccessDeniedError was expected")

    assert db.current_app_version == "0.0.7"


def test_admin_settings_service_rejects_direct_monobank_mode_update() -> None:
    service = AdminSettingsService(
        FakeAdminDb(build_pending_row()),
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
    )

    try:
        service.update_settings(
            user={"telegram_user_id": 1, "acl_group_title": "super_admin", "interface_locale": "uk"},
            payload={"billing_settings": {"monobank_mode": "test"}},
        )
    except AdminSettingsValidationError as error:
        assert "OTP-protected" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")


def test_composed_admin_services_delete_import_data_with_action_otp(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_jobs = [{"id": 1}, {"id": 2}]
    db.import_items = [{"id": 10}, {"id": 11}, {"id": 12}]
    db.google_doc_progress = [{"telegram_user_id": 1, "google_doc_id": "doc"}]
    gateway = FakeTelegramGateway()
    dependencies = build_admin_service_dependencies(db, TimeService("Europe/Kyiv"), gateway)
    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.randbelow", lambda size: 123456)

    challenge = dependencies.admin_auth_service.start_action_otp(user=db.admin_user, action_key="delete_import_data")
    result = dependencies.admin_settings_service.delete_all_import_data_with_otp(
        user=db.admin_user,
        challenge_id=challenge["challenge_id"],
        otp="123456",
    )

    assert result == {
        "status": "ok",
        "deleted_import_items": 3,
        "deleted_import_jobs": 2,
        "deleted_google_doc_progress": 1,
        "cleared_google_doc_bindings": 0,
        "deleted_user_dictionary_entries": 0,
        "deleted_user_dictionary_embeddings": 0,
        "deleted_user_word_assignments": 0,
        "deleted_user_learning_session_words": 0,
        "deleted_user_audio_files": 0,
    }
    assert [str(path) for path in db.import_data_user_audio_roots] == ["word_base/user"]
    assert db.import_jobs == []
    assert db.import_items == []
    assert db.google_doc_progress == []
    assert db.import_data_audio_storage_provider is dependencies.audio_storage_provider
    assert db.otp_challenges[0]["consumed"] is not None
    assert gateway.sent_messages[0]["text"] == "CronoLex OTP (delete_import_data): 123 456"
    assert gateway.deleted_messages == [{"chat_id": 55, "message_id": 123, "ignore_errors": True}]


def test_composed_admin_settings_service_invalid_action_otp_raises_application_unauthorized_error(
    monkeypatch,
) -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_jobs = [{"id": 1}, {"id": 2}]
    db.import_items = [{"id": 10}, {"id": 11}, {"id": 12}]
    db.google_doc_progress = [{"telegram_user_id": 1, "google_doc_id": "doc"}]
    dependencies = build_admin_service_dependencies(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())
    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.randbelow", lambda size: 123456)
    challenge = dependencies.admin_auth_service.start_action_otp(user=db.admin_user, action_key="delete_import_data")

    try:
        dependencies.admin_settings_service.delete_all_import_data_with_otp(
            user=db.admin_user,
            challenge_id=challenge["challenge_id"],
            otp="000000",
        )
    except AdminSettingsUnauthorizedError as error:
        assert error.detail == "Invalid OTP"
        assert not isinstance(error, AdminAuthUnauthorizedError)
        assert isinstance(error.__cause__, AdminAuthUnauthorizedError)
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsUnauthorizedError was expected")

    assert db.import_jobs == [{"id": 1}, {"id": 2}]
    assert db.import_items == [{"id": 10}, {"id": 11}, {"id": 12}]
    assert db.google_doc_progress == [{"telegram_user_id": 1, "google_doc_id": "doc"}]


def test_admin_settings_service_import_data_delete_checks_acl_before_otp() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_jobs = [{"id": 1}]
    verifier = FakeActionOtpVerifier()
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
        action_otp_verifier=verifier,
    )

    try:
        service.delete_all_import_data_with_otp(
            user={"telegram_user_id": 1, "acl_group_title": "admin", "interface_locale": "uk"},
            challenge_id=999,
            otp="000000",
        )
    except AdminSettingsAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsAccessDeniedError was expected")

    assert db.import_jobs == [{"id": 1}]
    assert verifier.calls == []


def test_settings_service_owns_import_data_delete_otp_orchestration() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_jobs = [{"id": 1}]
    verifier = FakeActionOtpVerifier()
    audio_storage_provider = FakeAudioStorageProvider()
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=audio_storage_provider,
        action_otp_verifier=verifier,
    )

    result = service.delete_all_import_data_with_otp(user=db.admin_user, challenge_id=7, otp="123456")

    assert result["status"] == "ok"
    assert verifier.calls == [
        {
            "user": db.admin_user,
            "action_key": "delete_import_data",
            "challenge_id": 7,
            "otp": "123456",
        }
    ]
    assert db.import_jobs == []
    assert db.import_data_audio_storage_provider is audio_storage_provider


def test_settings_service_does_not_delete_import_data_when_action_otp_fails() -> None:
    db = FakeAdminDb(build_pending_row())
    db.import_jobs = [{"id": 1}]
    verifier = FakeActionOtpVerifier(error=AdminSettingsUnauthorizedError("Invalid OTP"))
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
        action_otp_verifier=verifier,
    )

    try:
        service.delete_all_import_data_with_otp(user=db.admin_user, challenge_id=7, otp="000000")
    except AdminSettingsUnauthorizedError as error:
        assert error.detail == "Invalid OTP"
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsUnauthorizedError was expected")

    assert db.import_jobs == [{"id": 1}]


def test_composed_admin_services_switch_monobank_test_mode_with_action_otp(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    db.settings.monobank_token_test = "test-token"
    gateway = FakeTelegramGateway()
    dependencies = build_admin_service_dependencies(db, TimeService("Europe/Kyiv"), gateway)
    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.randbelow", lambda size: 123456)

    challenge = dependencies.admin_auth_service.start_action_otp(
        user=db.admin_user,
        action_key="billing_monobank_mode",
    )
    result = dependencies.admin_settings_service.update_billing_monobank_mode_with_otp(
        user=db.admin_user,
        monobank_mode="test",
        challenge_id=challenge["challenge_id"],
        otp="123456",
    )

    settings = db.app_setting_values[BILLING_MONOBANK_MODE_SETTINGS_KEY]
    assert settings["monobank_mode"] == "test"
    assert result["settings"]["billing_settings"]["monobank_mode"] == "test"
    assert BILLING_RUNTIME_SETTINGS_KEY not in db.app_setting_values
    assert db.otp_challenges[0]["consumed"] is not None
    assert gateway.sent_messages[0]["text"] == "CronoLex OTP (billing_monobank_mode): 123 456"


def test_admin_settings_service_monobank_mode_switch_checks_acl_before_token_validation() -> None:
    db = FakeAdminDb(build_pending_row())
    verifier = FakeActionOtpVerifier()
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
        action_otp_verifier=verifier,
    )

    try:
        service.update_billing_monobank_mode_with_otp(
            user={"telegram_user_id": 1, "acl_group_title": "admin", "interface_locale": "uk"},
            monobank_mode="test",
            challenge_id=999,
            otp="000000",
        )
    except AdminSettingsAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsAccessDeniedError was expected")

    assert BILLING_MONOBANK_MODE_SETTINGS_KEY not in db.app_setting_values
    assert verifier.calls == []


def test_admin_settings_service_monobank_mode_switch_rejects_missing_token_before_otp() -> None:
    db = FakeAdminDb(build_pending_row())
    verifier = FakeActionOtpVerifier()
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
        action_otp_verifier=verifier,
    )

    try:
        service.update_billing_monobank_mode_with_otp(
            user=db.admin_user,
            monobank_mode="test",
            challenge_id=999,
            otp="123456",
        )
    except AdminSettingsValidationError as error:
        assert error.detail == "MONOBANK_TOKEN_TEST is not configured"
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsValidationError was expected")

    assert BILLING_RUNTIME_SETTINGS_KEY not in db.app_setting_values
    assert verifier.calls == []


def test_settings_service_owns_monobank_mode_otp_orchestration() -> None:
    db = FakeAdminDb(build_pending_row())
    db.settings.monobank_token_test = "test-token"
    verifier = FakeActionOtpVerifier()
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
        action_otp_verifier=verifier,
    )

    result = service.update_billing_monobank_mode_with_otp(
        user=db.admin_user,
        monobank_mode="test",
        challenge_id=7,
        otp="123456",
    )

    assert db.app_setting_values[BILLING_MONOBANK_MODE_SETTINGS_KEY]["monobank_mode"] == "test"
    assert result["settings"]["billing_settings"]["monobank_mode"] == "test"
    assert verifier.calls == [
        {
            "user": db.admin_user,
            "action_key": "billing_monobank_mode",
            "challenge_id": 7,
            "otp": "123456",
        }
    ]


def test_settings_service_does_not_update_monobank_mode_when_action_otp_fails() -> None:
    db = FakeAdminDb(build_pending_row())
    db.settings.monobank_token_test = "test-token"
    verifier = FakeActionOtpVerifier(error=AdminSettingsUnauthorizedError("Invalid OTP"))
    service = AdminSettingsService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeAudioStorageProvider(),
        action_otp_verifier=verifier,
    )

    try:
        service.update_billing_monobank_mode_with_otp(
            user=db.admin_user,
            monobank_mode="test",
            challenge_id=7,
            otp="000000",
        )
    except AdminSettingsUnauthorizedError as error:
        assert error.detail == "Invalid OTP"
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsUnauthorizedError was expected")

    assert BILLING_MONOBANK_MODE_SETTINGS_KEY not in db.app_setting_values


def test_admin_settings_action_otp_verifier_maps_auth_access_denied_to_application_error() -> None:
    wrapped_error = AdminAuthAccessDeniedError("Action is allowed only for super_admin")
    verifier = AdminSettingsActionOtpVerifier(FakeActionOtpVerifier(error=wrapped_error))

    try:
        verifier.verify_action_otp(
            user={"telegram_user_id": 1, "acl_group_title": "admin"},
            action_key="delete_import_data",
            challenge_id=7,
            otp="123456",
        )
    except AdminSettingsAccessDeniedError as error:
        assert error.detail == "Action is allowed only for super_admin"
        assert error.__cause__ is wrapped_error
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsAccessDeniedError was expected")


def test_admin_settings_action_otp_verifier_maps_auth_too_many_attempts_to_application_error() -> None:
    wrapped_error = AdminAuthTooManyAttemptsError("Too many attempts")
    verifier = AdminSettingsActionOtpVerifier(FakeActionOtpVerifier(error=wrapped_error))

    try:
        verifier.verify_action_otp(
            user={"telegram_user_id": 1, "acl_group_title": "super_admin"},
            action_key="delete_import_data",
            challenge_id=7,
            otp="123456",
        )
    except AdminSettingsTooManyAttemptsError as error:
        assert error.detail == "Too many attempts"
        assert error.__cause__ is wrapped_error
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsTooManyAttemptsError was expected")


def test_admin_settings_action_otp_verifier_maps_auth_unauthorized_to_application_error() -> None:
    wrapped_error = AdminAuthUnauthorizedError("Invalid OTP")
    verifier = AdminSettingsActionOtpVerifier(FakeActionOtpVerifier(error=wrapped_error))

    try:
        verifier.verify_action_otp(
            user={"telegram_user_id": 1, "acl_group_title": "super_admin"},
            action_key="delete_import_data",
            challenge_id=7,
            otp="000000",
        )
    except AdminSettingsUnauthorizedError as error:
        assert error.detail == "Invalid OTP"
        assert error.__cause__ is wrapped_error
    else:  # pragma: no cover
        raise AssertionError("AdminSettingsUnauthorizedError was expected")


def test_admin_auth_service_action_otp_cannot_be_used_as_login_otp(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())
    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.randbelow", lambda size: 123456)

    challenge = service.start_action_otp(user=db.admin_user, action_key="delete_import_data")

    try:
        service.verify_otp(challenge_id=challenge["challenge_id"], otp="123456")
    except AdminAuthUnauthorizedError as error:
        assert error.detail == "Invalid OTP"
    else:  # pragma: no cover
        raise AssertionError("AdminAuthUnauthorizedError was expected")


def test_admin_auth_service_admin_cannot_start_destructive_action_otp() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())

    try:
        service.start_action_otp(
            user={"telegram_user_id": 2, "acl_group_title": "admin", "username": "admin2"},
            action_key="delete_import_data",
        )
    except AdminAuthAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminAuthAccessDeniedError was expected")


def test_admin_auth_service_action_otp_checks_acl_before_action_key_validation() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())

    try:
        service.start_action_otp(
            user={"telegram_user_id": 2, "acl_group_title": "admin", "username": "admin2"},
            action_key="not_allowed",
        )
    except AdminAuthAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminAuthAccessDeniedError was expected")


def test_admin_auth_service_super_admin_action_otp_validates_action_key_before_challenge() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())

    try:
        service.start_action_otp(user=db.admin_user, action_key="not_allowed")
    except AdminAuthValidationError as error:
        assert "action_key" in str(error.detail)
    else:  # pragma: no cover
        raise AssertionError("AdminAuthValidationError was expected")

    assert db.otp_challenges == []


def test_composed_admin_services_delete_ai_usage_log_with_action_otp(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    db._ai_usage_session_rows = [{"id": 1}, {"id": 2}]
    gateway = FakeTelegramGateway()
    dependencies = build_admin_service_dependencies(db, TimeService("Europe/Kyiv"), gateway)
    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.randbelow", lambda size: 654321)

    challenge = dependencies.admin_auth_service.start_action_otp(user=db.admin_user, action_key="delete_ai_usage_log")
    result = dependencies.admin_ai_usage_read_service.delete_all_sessions_with_otp(
        actor=db.admin_user,
        challenge_id=challenge["challenge_id"],
        otp="654321",
    )

    assert result == {"status": "ok", "deleted_ai_usage_sessions": 2}
    assert db._ai_usage_session_rows == []
    assert db.otp_challenges[0]["consumed"] is not None


def test_ai_usage_service_delete_checks_acl_before_otp() -> None:
    db = FakeAdminDb(build_pending_row())
    db._ai_usage_session_rows = [{"id": 1}]
    verifier = FakeActionOtpVerifier()
    service = AdminAIUsageReadService(db, TimeService("Europe/Kyiv"), action_otp_verifier=verifier)

    try:
        service.delete_all_sessions_with_otp(
            actor={"telegram_user_id": 1, "acl_group_title": "admin", "interface_locale": "uk"},
            challenge_id=999,
            otp="000000",
        )
    except AdminAIUsageReadAccessDeniedError as error:
        assert error.detail == "Access denied"
    else:  # pragma: no cover
        raise AssertionError("AdminAIUsageReadAccessDeniedError was expected")

    assert db._ai_usage_session_rows == [{"id": 1}]
    assert verifier.calls == []


def test_ai_usage_service_rejects_unknown_summary_period() -> None:
    service = AdminAIUsageReadService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    try:
        service.summarize(actor={"telegram_user_id": 1, "acl_group_title": "admin"}, period="decade")
    except AdminAIUsageReadValidationError as error:
        assert "period must be one of" in error.detail
    else:  # pragma: no cover
        raise AssertionError("AdminAIUsageReadValidationError was expected")


def test_ai_usage_service_rejects_invalid_session_filter_value() -> None:
    service = AdminAIUsageReadService(FakeAdminDb(build_pending_row()), TimeService("Europe/Kyiv"))

    try:
        service.list_sessions(
            actor={"telegram_user_id": 1, "acl_group_title": "admin"},
            params={"provider_key": ["bad value"]},
        )
    except AdminAIUsageReadValidationError as error:
        assert "provider_key values must match pattern" in error.detail
    else:  # pragma: no cover
        raise AssertionError("AdminAIUsageReadValidationError was expected")


def test_ai_usage_service_owns_delete_otp_orchestration() -> None:
    db = FakeAdminDb(build_pending_row())
    db._ai_usage_session_rows = [{"id": 1}]
    verifier = FakeActionOtpVerifier()
    service = AdminAIUsageReadService(db, TimeService("Europe/Kyiv"), action_otp_verifier=verifier)

    result = service.delete_all_sessions_with_otp(actor=db.admin_user, challenge_id=7, otp="654321")

    assert result == {"status": "ok", "deleted_ai_usage_sessions": 1}
    assert verifier.calls == [
        {
            "user": db.admin_user,
            "action_key": "delete_ai_usage_log",
            "challenge_id": 7,
            "otp": "654321",
        }
    ]
    assert db._ai_usage_session_rows == []


def test_ai_usage_service_does_not_delete_when_action_otp_fails() -> None:
    db = FakeAdminDb(build_pending_row())
    db._ai_usage_session_rows = [{"id": 1}]
    verifier = FakeActionOtpVerifier(error=AdminAIUsageReadUnauthorizedError("Invalid OTP"))
    service = AdminAIUsageReadService(db, TimeService("Europe/Kyiv"), action_otp_verifier=verifier)

    try:
        service.delete_all_sessions_with_otp(actor=db.admin_user, challenge_id=7, otp="000000")
    except AdminAIUsageReadUnauthorizedError as error:
        assert error.detail == "Invalid OTP"
    else:  # pragma: no cover
        raise AssertionError("AdminAIUsageReadUnauthorizedError was expected")

    assert db._ai_usage_session_rows == [{"id": 1}]


def test_admin_ai_usage_action_otp_verifier_maps_auth_access_denied_to_application_error() -> None:
    wrapped_error = AdminAuthAccessDeniedError("Action is allowed only for super_admin")
    verifier = AdminAIUsageActionOtpVerifier(FakeActionOtpVerifier(error=wrapped_error))

    try:
        verifier.verify_action_otp(
            user={"telegram_user_id": 1, "acl_group_title": "admin"},
            action_key="delete_ai_usage_log",
            challenge_id=7,
            otp="123456",
        )
    except AdminAIUsageReadAccessDeniedError as error:
        assert error.detail == "Action is allowed only for super_admin"
        assert error.__cause__ is wrapped_error
    else:  # pragma: no cover
        raise AssertionError("AdminAIUsageReadAccessDeniedError was expected")


def test_admin_ai_usage_action_otp_verifier_maps_auth_too_many_attempts_to_application_error() -> None:
    wrapped_error = AdminAuthTooManyAttemptsError("Too many attempts")
    verifier = AdminAIUsageActionOtpVerifier(FakeActionOtpVerifier(error=wrapped_error))

    try:
        verifier.verify_action_otp(
            user={"telegram_user_id": 1, "acl_group_title": "super_admin"},
            action_key="delete_ai_usage_log",
            challenge_id=7,
            otp="123456",
        )
    except AdminAIUsageReadTooManyAttemptsError as error:
        assert error.detail == "Too many attempts"
        assert error.__cause__ is wrapped_error
    else:  # pragma: no cover
        raise AssertionError("AdminAIUsageReadTooManyAttemptsError was expected")


def test_composed_admin_ai_usage_service_invalid_action_otp_raises_application_unauthorized_error(
    monkeypatch,
) -> None:
    db = FakeAdminDb(build_pending_row())
    db._ai_usage_session_rows = [{"id": 1}, {"id": 2}]
    dependencies = build_admin_service_dependencies(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())
    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.randbelow", lambda size: 654321)
    challenge = dependencies.admin_auth_service.start_action_otp(user=db.admin_user, action_key="delete_ai_usage_log")

    try:
        dependencies.admin_ai_usage_read_service.delete_all_sessions_with_otp(
            actor=db.admin_user,
            challenge_id=challenge["challenge_id"],
            otp="000000",
        )
    except AdminAIUsageReadUnauthorizedError as error:
        assert error.detail == "Invalid OTP"
        assert not isinstance(error, AdminAuthUnauthorizedError)
        assert isinstance(error.__cause__, AdminAuthUnauthorizedError)
    else:  # pragma: no cover
        raise AssertionError("AdminAIUsageReadUnauthorizedError was expected")

    assert db._ai_usage_session_rows == [{"id": 1}, {"id": 2}]


def test_admin_auth_service_password_prompt_can_be_dismissed_once_without_password() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())

    first_payload = service._with_auth_flags(db.admin_user)
    marked_payload = service.mark_password_prompted(user=first_payload)

    assert first_payload["requires_password_setup"] is True
    assert marked_payload["requires_password_setup"] is False
    assert db.admin_user["admin_web_password_prompted"] is True


def test_admin_auth_service_password_update_requires_current_password_when_password_exists() -> None:
    db = FakeAdminDb(build_pending_row())
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), FakeTelegramGateway())
    user = {"telegram_user_id": 1, "acl_group_title": "super_admin", "username": "admin"}
    service.update_password(user=user, current_password=None, password="Pass1234")

    try:
        service.update_password(user=user, current_password="bad", password="Next1234")
    except AdminAuthUnauthorizedError as error:
        assert error.detail == "Invalid current password"
    else:  # pragma: no cover
        raise AssertionError("AdminAuthUnauthorizedError was expected")


def test_admin_auth_service_password_login_still_requires_otp(monkeypatch) -> None:
    db = FakeAdminDb(build_pending_row())
    gateway = FakeTelegramGateway()
    service = AdminAuthService(db, TimeService("Europe/Kyiv"), gateway)
    service.update_password(user=db.admin_user, current_password=None, password="Pass1234")
    monkeypatch.setattr("app.application.admin.auth.auth_service.secrets.randbelow", lambda size: 123456)

    password_required = service.start_login(username="admin")
    result = service.start_login(username="admin", password="Pass1234")

    assert password_required.requires_password is True
    assert password_required.requires_otp is False
    assert result.requires_password is False
    assert result.requires_otp is True
    assert result.challenge_id == 1
    assert result.requires_password_setup is False
    assert db.sessions == []
    assert gateway.sent_messages == [
        {
            "chat_id": 55,
            "text": "Код входу CronoLex Admin: 123 456",
            "reply_markup": None,
            "disable_notification": False,
            "ignore_errors": False,
        }
    ]
