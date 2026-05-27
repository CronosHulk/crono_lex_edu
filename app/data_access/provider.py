from __future__ import annotations

import importlib
from typing import Any

from app.config import Settings
from app.orm import SessionManager


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._session_manager = SessionManager(settings)

    def connect(self) -> None:
        self._session_manager.connect()

    def close(self) -> None:
        self._session_manager.close()

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def engine(self) -> Any:
        return self._session_manager.engine

    @property
    def session_factory(self) -> Any:
        return self._session_manager.session_factory

    def session(self) -> Any:
        return self._session_manager.session()

    def run_migrations(self) -> None:
        self._session_manager.run_migrations()

    def __getattr__(self, name: str) -> Any:
        repo_mappings = {
            "acl_permissions": ("app.data_access.acl_permissions", "AclPermissionRepository"),
            "admin_auth": ("app.data_access.admin_auth", "AdminAuthRepository"),
            "admin_dashboard": ("app.data_access.admin_dashboard", "AdminDashboardRepository"),
            "admin_dictionary": ("app.data_access.admin_dictionary", "AdminDictionaryRepository"),
            "admin_users": ("app.data_access.admin_users", "AdminUserRepository"),
            "ai_provider_pricing_snapshots": ("app.data_access.ai_provider_pricing_snapshots", "AIProviderPricingSnapshotRepository"),
            "ai_usage_sessions": ("app.data_access.ai_usage_sessions", "AIUsageSessionRepository"),
            "app_runtime_state": ("app.data_access.app_runtime_state", "AppRuntimeStateRepository"),
            "app_settings": ("app.data_access.app_settings", "AppSettingRepository"),
            "billing": ("app.data_access.billing", "BillingRepository"),
            "bot_message_logs": ("app.data_access.bot_message_logs", "BotMessageLogRepository"),
            "client_web_auth": ("app.data_access.client_web_auth", "ClientWebAuthRepository"),
            "dictionary_audio": ("app.data_access.dictionary_audio", "DictionaryAudioRepository"),
            "dictionary_lookup": ("app.data_access.dictionary_lookup", "DictionaryLookupRepository"),
            "dictionary_search": ("app.data_access.dictionary_search", "DictionarySearchRepository"),
            "error_logs": ("app.data_access.error_logs", "ErrorLogRepository"),
            "exercise_texts": ("app.data_access.exercise_texts", "ExerciseTextRepository"),
            "tts_voices": ("app.data_access.exercise_texts", "TTSVoiceRepository"),
            "external_provider_settings": ("app.data_access.external_provider_settings", "ExternalProviderSettingsRepository"),
            "grammar_topics": ("app.data_access.grammar_topics", "GrammarTopicRepository"),
            "learning_levels": ("app.data_access.learning_levels", "LearningLevelRepository"),
            "learning_progress": ("app.data_access.learning_progress", "LearningProgressRepository"),
            "learning_sessions": ("app.data_access.learning_sessions", "LearningSessionRepository"),
            "learning_word_priority": ("app.data_access.learning_word_priority", "LearningWordPriorityRepository"),
            "lesson_word_selection": ("app.data_access.lesson_word_selection", "LessonWordSelectionRepository"),
            "similar_words": ("app.data_access.similar_words", "SimilarWordRepository"),
            "subscriptions": ("app.data_access.subscriptions", "SubscriptionRepository"),
            "task_logs": ("app.data_access.task_logs", "TaskLogRepository"),
            "teacher_student_links": ("app.data_access.teacher_student_links", "TeacherStudentLinkRepository"),
            "training_schedules": ("app.data_access.training_schedules", "TrainingScheduleRepository"),
            "user_dictionary": ("app.data_access.user_dictionary", "UserDictionaryRepository"),
            "user_dictionaries": ("app.data_access.user_dictionary", "UserDictionaryRepository"),
            "user_import_google_docs": ("app.data_access.user_import_google_docs", "UserImportGoogleDocRepository"),
            "user_import_items": ("app.data_access.user_import_items", "UserImportItemRepository"),
            "user_import_jobs": ("app.data_access.user_import_jobs", "UserImportJobRepository"),
            "user_learning_settings": ("app.data_access.user_learning_settings", "UserLearningSettingsRepository"),
            "user_profiles": ("app.data_access.user_profiles", "UserProfileRepository"),
            "web_login_history": ("app.data_access.web_login_history", "WebLoginHistoryRepository"),
        }

        if name in repo_mappings:
            module_path, class_name = repo_mappings[name]
            module = importlib.import_module(module_path)
            repo_class = getattr(module, class_name)
            if class_name == "LessonWordSelectionRepository":
                instance = repo_class(self._session_manager, self.settings)
            else:
                instance = repo_class(self._session_manager)
            setattr(self, name, instance)
            return instance

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
