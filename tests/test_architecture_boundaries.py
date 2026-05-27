from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
README_PATH = APP_ROOT.parent / "README.md"
REQUIRED_README_BACKEND_MODULE_MAP_REFERENCES = (
    "`app/application/`",
    "`app/domain/`",
    "`app/reference/`",
    "`app/external_providers/`",
    "`app/billing/`",
    "`app/subscriptions/`",
    "`app/acl/`",
    "`app/marketing/`",
    "`app/helpers/`",
    "`app/security/`",
    "`app/serialization/`",
    "`app/support/`",
    "`app/api_helpers/`",
    "`app/validation/`",
    "`app/validators/`",
    "`app/models/`",
)
SCRIPTS_ROOT = APP_ROOT.parent / "scripts"
WORD_BASE_ROOT = APP_ROOT.parent / "word_base"
TESTS_ROOT = APP_ROOT.parent / "tests"
APP_PACKAGE_MARKER_MODULE = APP_ROOT / "__init__.py"
MODELS_PACKAGE_ENTRYPOINT_MODULE = APP_ROOT / "models" / "__init__.py"
STORAGE_PACKAGE_ENTRYPOINT_MODULE = APP_ROOT / "storage" / "__init__.py"
AUDIO_STORAGE_MODULE = APP_ROOT / "storage" / "audio.py"
AUDIO_STORAGE_COMPOSITION_FACTORY_MODULE = APP_ROOT / "composition" / "audio_storage.py"
USER_IMPORT_ARTIFACT_STORAGE_MODULE = APP_ROOT / "storage" / "user_import_artifacts.py"
USER_IMPORT_ARTIFACT_STORAGE_COMPOSITION_FACTORY_MODULE = (
    APP_ROOT / "composition" / "user_import_artifact_storage.py"
)
PENDING_IMPORT_ENRICHMENT_MODULE = (
    APP_ROOT / "user_import" / "services" / "pending_import_enrichment.py"
)
USER_IMPORT_COLLECTING_RESOLVER_MODULE = (
    APP_ROOT / "user_import" / "services" / "collecting_resolver.py"
)
AUDIO_STORAGE_BOUNDARY_MODULES = (
    APP_ROOT / "external_providers" / "user_import_google_tts.py",
    APP_ROOT / "application" / "admin" / "exercise_texts" / "tts_service.py",
    APP_ROOT / "application" / "admin" / "user_dictionary" / "promote.py",
    APP_ROOT / "api_helpers" / "audio_response.py",
    APP_ROOT / "helpers" / "audio_files.py",
)
USER_IMPORT_GOOGLE_TTS_PROVIDER_MODULE = (
    APP_ROOT / "external_providers" / "user_import_google_tts.py"
)
BOT_RUNTIME_AUDIO_STORAGE_MODULES = tuple(sorted((APP_ROOT / "bot_runtime").glob("*.py")))
HTTP_AUDIO_RESPONSE_ROUTE_MODULES = (
    APP_ROOT / "admin_api" / "dictionary" / "router.py",
    APP_ROOT / "admin_api" / "user_dictionary" / "router.py",
    APP_ROOT / "admin_api" / "exercise_texts" / "router.py",
    APP_ROOT / "client_api" / "client_web" / "router.py",
)
AUDIO_STORAGE_PROVIDER_IMPORT_NAMES = {
    "AudioStorageProvider",
    "FileSystemAudioStorageProvider",
    "filesystem_audio_storage_provider",
}
FILESYSTEM_AUDIO_STORAGE_PROVIDER_NAME = "filesystem_audio_storage_provider"
FILESYSTEM_AUDIO_STORAGE_PROVIDER_NAMES = frozenset(
    {
        FILESYSTEM_AUDIO_STORAGE_PROVIDER_NAME,
        "FileSystemAudioStorageProvider",
    }
)
FILESYSTEM_AUDIO_STORAGE_PROVIDER_MODULE_NAMES = frozenset(
    {
        "app.storage",
        "app.storage.audio",
    }
)
FILESYSTEM_AUDIO_STORAGE_PROVIDER_REFERENCES = frozenset(
    f"{module_name}.{provider_name}"
    for module_name in FILESYSTEM_AUDIO_STORAGE_PROVIDER_MODULE_NAMES
    for provider_name in FILESYSTEM_AUDIO_STORAGE_PROVIDER_NAMES
)
CENTRAL_AUDIO_STORAGE_FACTORY_CLIENT_MODULES = (
    APP_ROOT / "bot_main.py",
    APP_ROOT / "composition" / "admin.py",
    APP_ROOT / "composition" / "client_web.py",
    APP_ROOT / "composition" / "user_import_build_pipeline.py",
    APP_ROOT / "composition" / "user_import_provider_adapters.py",
)
AUDIO_STORAGE_DIRECT_MUTATION_CALL_NAMES = {
    "app.helpers.audio_files.delete_audio_file_if_under_roots",
    "app.helpers.user_import_storage.write_bytes_atomic",
    "os.remove",
    "os.unlink",
    "remove",
    "shutil.copy2",
    "shutil.copyfile",
    "unlink",
    "write_bytes_atomic",
}
AUDIO_STORAGE_DIRECT_MUTATION_ATTR_NAMES = {
    "unlink",
    "write_bytes",
}
AUTH_PACKAGE_FACADE_MODULE = APP_ROOT / "auth" / "__init__.py"
DOMAIN_PACKAGE_FACADE_MODULE = APP_ROOT / "domain" / "__init__.py"
DOMAIN_USER_DICTIONARY_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "domain" / "user_dictionary" / "__init__.py"
)
DOMAIN_USER_IMPORT_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "domain" / "user_import" / "__init__.py"
)
MARKETING_PACKAGE_FACADE_MODULE = APP_ROOT / "marketing" / "__init__.py"
BOT_RUNTIME_PACKAGE_FACADE_MODULE = APP_ROOT / "bot_runtime" / "__init__.py"
ADMIN_API_PACKAGE_FACADE_MODULE = APP_ROOT / "admin_api" / "__init__.py"
CLIENT_API_PACKAGE_FACADE_MODULE = APP_ROOT / "client_api" / "__init__.py"
ADMIN_API_ROOT = APP_ROOT / "admin_api"
ADMIN_API_FORBIDDEN_BUSINESS_DIR_NAMES = frozenset(
    {
        "actions",
        "helpers",
        "services",
        "validators",
    }
)
USER_IMPORT_SERVICES_ROOT = APP_ROOT / "user_import" / "services"
USER_IMPORT_ROOT = APP_ROOT / "user_import"
USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "bound_google_doc_sync_service.py"
)
USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_PROCESSOR_PATH = (
    USER_IMPORT_SERVICES_ROOT / "bound_google_doc_sync_processor.py"
)
USER_IMPORT_POST_UPGRADE_GOOGLE_DOC_RESCAN_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "post_upgrade_google_doc_rescan_service.py"
)
USER_IMPORT_POST_UPGRADE_GOOGLE_DOC_RESCAN_QUEUE_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "post_upgrade_google_doc_rescan_queue_service.py"
)
USER_IMPORT_DOCUMENT_SERVICE_PATH = USER_IMPORT_SERVICES_ROOT / "document_service.py"
USER_IMPORT_INTAKE_COMPOSITION_PATH = APP_ROOT / "composition" / "user_import_intake.py"
USER_IMPORT_INTAKE_JOB_SERVICE_PATH = USER_IMPORT_SERVICES_ROOT / "intake_job_service.py"
USER_IMPORT_INTAKE_MANUAL_BIND_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "intake_manual_bind_service.py"
)
USER_IMPORT_INTAKE_MANUAL_BIND_VALIDATION_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "intake_manual_bind_validation_service.py"
)
USER_IMPORT_INTAKE_MANUAL_BIND_PROGRESS_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "intake_manual_bind_progress_service.py"
)
USER_IMPORT_INTAKE_MANUAL_BIND_JOB_SUBMISSION_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "intake_manual_bind_job_submission_service.py"
)
USER_IMPORT_INTAKE_SERVICE_PATH = USER_IMPORT_SERVICES_ROOT / "intake_service.py"
USER_IMPORT_JOB_PROCESSING_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "job_processing_service.py"
)
USER_IMPORT_JOB_TASK_RESULT_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "job_task_result_service.py"
)
USER_IMPORT_NOTIFICATION_SERVICE_PATH = USER_IMPORT_SERVICES_ROOT / "notification_service.py"
USER_IMPORT_PREPARATION_SERVICE_PATH = USER_IMPORT_SERVICES_ROOT / "preparation_service.py"
USER_IMPORT_RUNTIME_SERVICE_PATH = USER_IMPORT_SERVICES_ROOT / "runtime_service.py"
USER_IMPORT_SUMMARY_SERVICE_PATH = USER_IMPORT_SERVICES_ROOT / "summary_service.py"
USER_IMPORT_SUMMARY_SCREEN_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "summary_screen_service.py"
)
USER_IMPORT_TECHNICAL_DETAILS_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "technical_details_service.py"
)
USER_IMPORT_USER_DICTIONARY_BUILD_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "user_dictionary_build_service.py"
)
USER_IMPORT_USER_DICTIONARY_DETAILS_BUILD_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "user_dictionary_details_build_service.py"
)
USER_IMPORT_USER_DICTIONARY_AUDIO_BUILD_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "user_dictionary_audio_build_service.py"
)
USER_IMPORT_USER_DICTIONARY_EMBEDDING_BUILD_SERVICE_PATH = (
    USER_IMPORT_SERVICES_ROOT / "user_dictionary_embedding_build_service.py"
)
USER_IMPORT_USER_DICTIONARY_BUILD_LOGGING_PATH = (
    USER_IMPORT_SERVICES_ROOT / "user_dictionary_build_logging.py"
)
USER_IMPORT_USER_DICTIONARY_BUILD_PHASE_MODULE_PATHS = (
    USER_IMPORT_USER_DICTIONARY_DETAILS_BUILD_SERVICE_PATH,
    USER_IMPORT_USER_DICTIONARY_AUDIO_BUILD_SERVICE_PATH,
    USER_IMPORT_USER_DICTIONARY_EMBEDDING_BUILD_SERVICE_PATH,
    USER_IMPORT_USER_DICTIONARY_BUILD_LOGGING_PATH,
)
USER_IMPORT_USER_DICTIONARY_BUILD_PHASE_MODULE_CLASSES = (
    (
        USER_IMPORT_USER_DICTIONARY_DETAILS_BUILD_SERVICE_PATH,
        "UserDictionaryDetailsBuildService",
    ),
    (
        USER_IMPORT_USER_DICTIONARY_AUDIO_BUILD_SERVICE_PATH,
        "UserDictionaryAudioBuildService",
    ),
    (
        USER_IMPORT_USER_DICTIONARY_EMBEDDING_BUILD_SERVICE_PATH,
        "UserDictionaryEmbeddingBuildService",
    ),
    (
        USER_IMPORT_USER_DICTIONARY_BUILD_LOGGING_PATH,
        "UserDictionaryBuildLogger",
    ),
)
DATA_ACCESS_ROOT = APP_ROOT / "data_access"
DATA_ACCESS_PACKAGE_FACADE_MODULE = DATA_ACCESS_ROOT / "__init__.py"
DATA_ACCESS_PROVIDER_MODULE = APP_ROOT / "data_access" / "provider.py"
DATA_ACCESS_BILLING_MODULE = DATA_ACCESS_ROOT / "billing.py"
DATA_ACCESS_SUBSCRIPTIONS_MODULE = DATA_ACCESS_ROOT / "subscriptions.py"
DATA_ACCESS_EXERCISE_TEXTS_MODULE = DATA_ACCESS_ROOT / "exercise_texts.py"
DATA_ACCESS_USER_DICTIONARY_MODULE = DATA_ACCESS_ROOT / "user_dictionary.py"
DATA_ACCESS_USER_DICTIONARY_ASSIGNMENTS_MODULE = (
    DATA_ACCESS_ROOT / "user_dictionary_assignments.py"
)
DATA_ACCESS_USER_DICTIONARY_CONSTANTS_MODULE = (
    DATA_ACCESS_ROOT / "user_dictionary_constants.py"
)
DOMAIN_BILLING_CONSTANTS_MODULE = "app.domain.billing.constants"
DOMAIN_BILLING_CONSTANTS_MODULE_PATH = APP_ROOT / "domain" / "billing" / "constants.py"
BILLING_ADMIN_READ_VOCABULARY_CONSTANT_NAMES = {
    "BILLING_PAYMENT_STATUSES",
    "BILLING_PROVIDER_MODES",
    "MONOBANK_AUDIT_DIRECTIONS",
    "MONOBANK_AUDIT_PROVIDER_MODES",
}
BILLING_VOCABULARY_CONSTANT_NAMES = {
    "BILLING_TERMINAL_STATUSES",
    *BILLING_ADMIN_READ_VOCABULARY_CONSTANT_NAMES,
}
BILLING_VOCABULARY_LITERAL_VALUES = {
    frozenset({"success", "failure", "reversed", "expired"}): "BILLING_TERMINAL_STATUSES",
    frozenset(
        {
            "created",
            "invoice_created",
            "processing",
            "success",
            "failure",
            "reversed",
            "expired",
        }
    ): "BILLING_PAYMENT_STATUSES",
    frozenset({"test", "production"}): "BILLING_PROVIDER_MODES",
    frozenset({"outgoing", "incoming"}): "MONOBANK_AUDIT_DIRECTIONS",
    frozenset({"test", "production", "unknown"}): "MONOBANK_AUDIT_PROVIDER_MODES",
}
BILLING_VOCABULARY_LITERAL_SCAN_ROOTS = (
    APP_ROOT / "admin_api" / "billing",
    APP_ROOT / "application" / "admin" / "billing",
    APP_ROOT / "billing",
    APP_ROOT / "domain" / "billing",
)
BILLING_VOCABULARY_LITERAL_SCAN_FILES = (DATA_ACCESS_BILLING_MODULE,)
DOMAIN_EXERCISE_TEXT_ERRORS_MODULE = "app.domain.exercise_texts.errors"
EXERCISE_TEXT_VERSION_CONFLICT_ERROR_NAME = "ExerciseTextVersionConflictError"
USER_DICTIONARY_STATUS_CONSTANT_NAMES = {
    "USER_DICTIONARY_AUDIO_FAILED",
    "USER_DICTIONARY_DETAILS_FAILED",
    "USER_DICTIONARY_EMBEDDING_FAILED",
    "USER_DICTIONARY_QUEUED_AUDIO",
    "USER_DICTIONARY_QUEUED_DETAILS",
    "USER_DICTIONARY_QUEUED_EMBEDDING",
    "USER_DICTIONARY_READY",
    "USER_DICTIONARY_REJECTED",
    "USER_DICTIONARY_STATUSES",
}
USER_WORD_SOURCE_CONSTANT_NAMES = {
    "USER_WORD_SOURCE_CORE",
    "USER_WORD_SOURCE_USER",
}
USER_WORD_ASSIGNMENT_CONSTANT_NAMES = {
    "USER_WORD_ASSIGNMENT_ARCHIVED",
    "USER_WORD_ASSIGNMENT_AVAILABLE",
    "USER_WORD_ASSIGNMENT_HIDDEN",
    "USER_WORD_ASSIGNMENT_WAITING",
}
USER_DICTIONARY_ASSIGNMENT_SOURCE_CONSTANT_NAMES = (
    USER_WORD_SOURCE_CONSTANT_NAMES | USER_WORD_ASSIGNMENT_CONSTANT_NAMES
)
DATA_ACCESS_USER_DICTIONARY_STATUS_MODULE_NAMES = frozenset(
    {"app.data_access.user_dictionary"}
)
DATA_ACCESS_USER_DICTIONARY_ASSIGNMENT_SOURCE_MODULE_NAMES = frozenset(
    {
        "app.data_access.user_dictionary",
        "app.data_access.user_dictionary_assignments",
        "app.data_access.user_dictionary_constants",
    }
)
DATA_ACCESS_USER_DICTIONARY_ASSIGNMENT_SOURCE_REEXPORTS = {
    DATA_ACCESS_USER_DICTIONARY_MODULE: {
        "USER_WORD_ASSIGNMENT_AVAILABLE",
        "USER_WORD_ASSIGNMENT_WAITING",
        "USER_WORD_SOURCE_CORE",
        "USER_WORD_SOURCE_USER",
    },
    DATA_ACCESS_USER_DICTIONARY_ASSIGNMENTS_MODULE: (
        USER_DICTIONARY_ASSIGNMENT_SOURCE_CONSTANT_NAMES
    ),
    DATA_ACCESS_USER_DICTIONARY_CONSTANTS_MODULE: (
        USER_DICTIONARY_ASSIGNMENT_SOURCE_CONSTANT_NAMES
    ),
}
EMPTY_MARKER_PACKAGE_FACADES = (
    (AUTH_PACKAGE_FACADE_MODULE, "app.auth"),
    (DOMAIN_PACKAGE_FACADE_MODULE, "app.domain"),
    (DOMAIN_USER_DICTIONARY_PACKAGE_FACADE_MODULE, "app.domain.user_dictionary"),
    (DOMAIN_USER_IMPORT_PACKAGE_FACADE_MODULE, "app.domain.user_import"),
    (MARKETING_PACKAGE_FACADE_MODULE, "app.marketing"),
    (DATA_ACCESS_PACKAGE_FACADE_MODULE, "app.data_access"),
)
RAW_SQL_ALLOWED_ROOTS = (DATA_ACCESS_ROOT, APP_ROOT / "models")
RAW_SQL_ALLOWED_FILES = (APP_ROOT / "orm.py",)
RAW_SQL_TEXT_IMPORT_MODULES = {
    "sqlalchemy",
    "sqlalchemy.sql",
    "sqlalchemy.sql.expression",
}
RAW_SQL_FORBIDDEN_CALLABLE_NAMES = {
    f"{module}.text" for module in RAW_SQL_TEXT_IMPORT_MODULES
}
GENERIC_HELPERS_ROOT = APP_ROOT / "helpers"
HELPERS_PACKAGE_FACADE_MODULE = GENERIC_HELPERS_ROOT / "__init__.py"
VALIDATION_ROOT = APP_ROOT / "validation"
VALIDATION_PACKAGE_FACADE_MODULE = VALIDATION_ROOT / "__init__.py"
VALIDATORS_ROOT = APP_ROOT / "validators"
VALIDATORS_PACKAGE_FACADE_MODULE = VALIDATORS_ROOT / "__init__.py"
LEGACY_REQUEST_VALIDATOR_SHIM_MODULE = VALIDATORS_ROOT / "request.py"
REQUEST_VALUE_VALIDATORS_MODULE = VALIDATION_ROOT / "request_values.py"
COMPOSITION_CLIENT_WEB_IMPORT_EVENTS_MODULE = (
    APP_ROOT / "composition" / "client_web_import_events.py"
)
CLIENT_WEB_SCHEMAS_MODULE = APP_ROOT / "client_api" / "client_web" / "schemas.py"
CLIENT_API_INTERNAL_AUTH_MODULE = APP_ROOT / "client_api" / "internal_auth.py"
SECURITY_INTERNAL_API_TOKENS_MODULE = APP_ROOT / "security" / "internal_api_tokens.py"
ADMIN_BOOTSTRAP_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "admin_api" / "bootstrap" / "__init__.py"
)
ADMIN_BOOTSTRAP_ACTIONS_ROOT = APP_ROOT / "admin_api" / "bootstrap" / "actions"
ADMIN_BOOTSTRAP_HELPERS_ROOT = APP_ROOT / "admin_api" / "bootstrap" / "helpers"
ADMIN_BOOTSTRAP_SERVICES_ROOT = APP_ROOT / "admin_api" / "bootstrap" / "services"
ADMIN_BOOTSTRAP_VALIDATORS_ROOT = APP_ROOT / "admin_api" / "bootstrap" / "validators"
ADMIN_DASHBOARD_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "admin_api" / "dashboard" / "__init__.py"
)
ADMIN_VALIDATORS_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "admin_api" / "validators" / "__init__.py"
)
RETIRED_ADMIN_HELPERS_ROOT = APP_ROOT / "admin_api" / "helpers"
RETIRED_ADMIN_HELPERS_PACKAGE_FACADE_MODULE = RETIRED_ADMIN_HELPERS_ROOT / "__init__.py"
RETIRED_ADMIN_HELPERS_PACKAGE_NAME = "app.admin_api.helpers"
RETIRED_ADMIN_TOP_LEVEL_PACKAGE_FACADES = (
    (
        RETIRED_ADMIN_HELPERS_PACKAGE_FACADE_MODULE,
        RETIRED_ADMIN_HELPERS_PACKAGE_NAME,
        ("admin_api", "helpers"),
        "permissions",
        "ensure_admin_actor",
    ),
)
ADMIN_BOOTSTRAP_SERVICES_PACKAGE_FACADE_MODULE = ADMIN_BOOTSTRAP_SERVICES_ROOT / "__init__.py"
ADMIN_BOOTSTRAP_SERVICE_MODULE = ADMIN_BOOTSTRAP_SERVICES_ROOT / "bootstrap_service.py"
APPLICATION_PACKAGE_FACADE_MODULE = APP_ROOT / "application" / "__init__.py"
APPLICATION_ADMIN_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "application" / "admin" / "__init__.py"
)
APPLICATION_CLIENT_RUNTIME_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "application" / "client_runtime" / "__init__.py"
)
APPLICATION_CLIENT_PACKAGE_FACADE_MODULE = APP_ROOT / "application" / "client" / "__init__.py"
APPLICATION_CLIENT_LEARNING_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "__init__.py"
)
APPLICATION_CLIENT_REMINDERS_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "application" / "client_reminders" / "__init__.py"
)
APPLICATION_CLIENT_UI_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "application" / "client_ui" / "__init__.py"
)
APPLICATION_CLIENT_WEB_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "application" / "client_web" / "__init__.py"
)
AUTH_PRIMITIVES_ROOT = APP_ROOT / "auth"
AUTH_PRIMITIVES_MODULES = (
    AUTH_PRIMITIVES_ROOT / "identity.py",
    AUTH_PRIMITIVES_ROOT / "otp.py",
    AUTH_PRIMITIVES_ROOT / "password.py",
    AUTH_PRIMITIVES_ROOT / "request_context.py",
    AUTH_PRIMITIVES_ROOT / "secrets.py",
)
APPLICATION_CLIENT_BOT_MESSAGE_SERVICE_MODULE = (
    APP_ROOT / "application" / "client" / "bot_message_service.py"
)
APPLICATION_CLIENT_ADMIN_RESTORE_SERVICE_MODULE = (
    APP_ROOT / "application" / "client" / "admin_restore_service.py"
)
APPLICATION_CLIENT_BOOTSTRAP_SERVICE_MODULE = (
    APP_ROOT / "application" / "client" / "bootstrap_service.py"
)
APPLICATION_CLIENT_LEARNING_WEB_LINK_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "web_link_service.py"
)
APPLICATION_CLIENT_LEARNING_DISPLAY_MODULE = (
    APP_ROOT / "application" / "client_learning" / "display.py"
)
APPLICATION_CLIENT_LEARNING_CONTENT_MODULE = (
    APP_ROOT / "application" / "client_learning" / "content.py"
)
APPLICATION_CLIENT_LEARNING_NAVIGATION_MODULE = (
    APP_ROOT / "application" / "client_learning" / "navigation.py"
)
APPLICATION_CLIENT_LEARNING_CARD_SCREENS_MODULE = (
    APP_ROOT / "application" / "client_learning" / "card_screens.py"
)
APPLICATION_CLIENT_LEARNING_READY_SCREENS_MODULE = (
    APP_ROOT / "application" / "client_learning" / "ready_screens.py"
)
APPLICATION_CLIENT_LEARNING_PROGRESS_MODULE = (
    APP_ROOT / "application" / "client_learning" / "progress.py"
)
APPLICATION_CLIENT_LEARNING_QUIZ_SCREENS_MODULE = (
    APP_ROOT / "application" / "client_learning" / "quiz_screens.py"
)
APPLICATION_CLIENT_LEARNING_SESSION_SCREEN_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "session_screen_service.py"
)
APPLICATION_CLIENT_LEARNING_SESSION_COMPLETION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "session_completion_service.py"
)
APPLICATION_CLIENT_LEARNING_QUIZ_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "quiz_action_service.py"
)
APPLICATION_CLIENT_LEARNING_RESUME_MODULE = (
    APP_ROOT / "application" / "client_learning" / "resume.py"
)
APPLICATION_CLIENT_LEARNING_MENU_SCREENS_MODULE = (
    APP_ROOT / "application" / "client_learning" / "menu_screens.py"
)
APPLICATION_CLIENT_LEARNING_MENU_SCREEN_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "menu_screen_service.py"
)
APPLICATION_CLIENT_LEARNING_SETTINGS_SCREENS_MODULE = (
    APP_ROOT / "application" / "client_learning" / "settings_screens.py"
)
APPLICATION_CLIENT_LEARNING_SETTINGS_SCREEN_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "settings_screen_service.py"
)
APPLICATION_CLIENT_LEARNING_COMPLETION_SCREENS_MODULE = (
    APP_ROOT / "application" / "client_learning" / "completion_screens.py"
)
APPLICATION_CLIENT_LEARNING_COMPLETION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "completion_service.py"
)
APPLICATION_CLIENT_LEARNING_PLANNING_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "planning_service.py"
)
APPLICATION_CLIENT_LEARNING_PLANNING_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "planning_action_service.py"
)
APPLICATION_CLIENT_LEARNING_SESSION_IDENTITY_MODULE = (
    APP_ROOT / "application" / "client_learning" / "session_identity.py"
)
APPLICATION_CLIENT_LEARNING_ACTION_PAYLOAD_MODULE = (
    APP_ROOT / "application" / "client_learning" / "action_payload.py"
)
APPLICATION_CLIENT_LEARNING_CARD_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "card_action_service.py"
)
APPLICATION_CLIENT_LEARNING_READY_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "ready_action_service.py"
)
APPLICATION_CLIENT_LEARNING_RESUME_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "resume_service.py"
)
APPLICATION_CLIENT_LEARNING_SESSION_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "session_action_service.py"
)
APPLICATION_CLIENT_LEARNING_START_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "start_service.py"
)
APPLICATION_CLIENT_LEARNING_SETTINGS_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "settings_action_service.py"
)
APPLICATION_CLIENT_LEARNING_LEVEL_RUN_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "level_run_service.py"
)
APPLICATION_CLIENT_LEARNING_SUMMARY_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_learning" / "summary_service.py"
)
APPLICATION_CLIENT_REMINDER_ACTION_PAYLOAD_MODULE = (
    APP_ROOT / "application" / "client_reminders" / "action_payload.py"
)
APPLICATION_CLIENT_REMINDER_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_reminders" / "action_service.py"
)
APPLICATION_CLIENT_REMINDER_DISPATCH_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_reminders" / "dispatch_service.py"
)
APPLICATION_CLIENT_REMINDER_DISPLAY_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_reminders" / "display_service.py"
)
APPLICATION_CLIENT_REMINDER_SETTINGS_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_reminders" / "settings_service.py"
)
APPLICATION_CLIENT_REMINDER_SETTINGS_UI_MODULE = (
    APP_ROOT / "application" / "client_reminders" / "settings_ui.py"
)
APPLICATION_CLIENT_REMINDER_UPCOMING_MODULE = (
    APP_ROOT / "application" / "client_reminders" / "upcoming.py"
)
APPLICATION_CLIENT_REMINDER_MODULES = (
    APPLICATION_CLIENT_REMINDER_ACTION_PAYLOAD_MODULE,
    APPLICATION_CLIENT_REMINDER_ACTION_SERVICE_MODULE,
    APPLICATION_CLIENT_REMINDER_DISPATCH_SERVICE_MODULE,
    APPLICATION_CLIENT_REMINDER_DISPLAY_SERVICE_MODULE,
    APPLICATION_CLIENT_REMINDER_SETTINGS_SERVICE_MODULE,
    APPLICATION_CLIENT_REMINDER_SETTINGS_UI_MODULE,
    APPLICATION_CLIENT_REMINDER_UPCOMING_MODULE,
)
APPLICATION_CLIENT_LEARNING_PRESENTATION_MODULES = (
    APPLICATION_CLIENT_LEARNING_DISPLAY_MODULE,
    APPLICATION_CLIENT_LEARNING_CONTENT_MODULE,
    APPLICATION_CLIENT_LEARNING_NAVIGATION_MODULE,
    APPLICATION_CLIENT_LEARNING_CARD_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_READY_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_QUIZ_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_SESSION_SCREEN_SERVICE_MODULE,
)
APPLICATION_CLIENT_LEARNING_MENU_MODULES = (
    APPLICATION_CLIENT_LEARNING_DISPLAY_MODULE,
    APPLICATION_CLIENT_LEARNING_CONTENT_MODULE,
    APPLICATION_CLIENT_LEARNING_NAVIGATION_MODULE,
    APPLICATION_CLIENT_LEARNING_CARD_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_READY_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_PROGRESS_MODULE,
    APPLICATION_CLIENT_LEARNING_QUIZ_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_SESSION_SCREEN_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_SESSION_COMPLETION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_QUIZ_ACTION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_RESUME_MODULE,
    APPLICATION_CLIENT_LEARNING_MENU_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_MENU_SCREEN_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_SETTINGS_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_SETTINGS_SCREEN_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_COMPLETION_SCREENS_MODULE,
    APPLICATION_CLIENT_LEARNING_COMPLETION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_PLANNING_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_PLANNING_ACTION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_SESSION_IDENTITY_MODULE,
    APPLICATION_CLIENT_LEARNING_ACTION_PAYLOAD_MODULE,
    APPLICATION_CLIENT_LEARNING_CARD_ACTION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_READY_ACTION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_RESUME_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_SESSION_ACTION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_START_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_SETTINGS_ACTION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_LEVEL_RUN_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_SUMMARY_SERVICE_MODULE,
)
APPLICATION_CLIENT_LEARNING_PLANNING_MODULES = (
    APPLICATION_CLIENT_LEARNING_PLANNING_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_PLANNING_ACTION_SERVICE_MODULE,
    APPLICATION_CLIENT_LEARNING_SESSION_IDENTITY_MODULE,
    APPLICATION_CLIENT_LEARNING_ACTION_PAYLOAD_MODULE,
)
APPLICATION_CLIENT_UI_CHOICE_CONTROLS_MODULE = (
    APP_ROOT / "application" / "client_ui" / "choice_controls.py"
)
APPLICATION_CLIENT_WEB_PLAN_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "plan_service.py"
)
APPLICATION_CLIENT_WEB_SETTINGS_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "settings_service.py"
)
APPLICATION_CLIENT_WEB_AUTH_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "auth_service.py"
)
APPLICATION_CLIENT_WEB_AUTH_SESSION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "auth_session_service.py"
)
APPLICATION_CLIENT_WEB_AUTH_ERRORS_MODULE = (
    APP_ROOT / "application" / "client_web" / "auth_errors.py"
)
APPLICATION_CLIENT_WEB_AUTH_GATEWAYS_MODULE = (
    APP_ROOT / "application" / "client_web" / "auth_gateways.py"
)
APPLICATION_CLIENT_WEB_AUTH_MODULES = (
    APPLICATION_CLIENT_WEB_AUTH_SERVICE_MODULE,
    APPLICATION_CLIENT_WEB_AUTH_SESSION_SERVICE_MODULE,
    APPLICATION_CLIENT_WEB_AUTH_ERRORS_MODULE,
    APPLICATION_CLIENT_WEB_AUTH_GATEWAYS_MODULE,
)
APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "import_service.py"
)
APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "import_processing_service.py"
)
APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "import_results_service.py"
)
APPLICATION_CLIENT_WEB_IMPORT_ERRORS_MODULE = (
    APP_ROOT / "application" / "client_web" / "import_errors.py"
)
APPLICATION_CLIENT_WEB_IMPORT_STATUSES_MODULE = (
    APP_ROOT / "application" / "client_web" / "import_statuses.py"
)
APPLICATION_CLIENT_WEB_IMPORT_SOURCES_MODULE = (
    APP_ROOT / "application" / "client_web" / "import_sources.py"
)
APPLICATION_CLIENT_WEB_IMPORT_EVENTS_MODULE = (
    APP_ROOT / "application" / "client_web" / "import_events.py"
)
APPLICATION_CLIENT_WEB_LEARNING_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "learning_service.py"
)
APPLICATION_CLIENT_WEB_LEARNING_SESSION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "learning_session_service.py"
)
APPLICATION_CLIENT_WEB_LEARNING_WORDS_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "learning_words_service.py"
)
APPLICATION_CLIENT_WEB_LEARNING_ERRORS_MODULE = (
    APP_ROOT / "application" / "client_web" / "learning_errors.py"
)
APPLICATION_CLIENT_WEB_LEARNING_MARKUP_MODULE = (
    APP_ROOT / "application" / "client_web" / "learning_markup.py"
)
APPLICATION_CLIENT_WEB_LEARNING_MODULES = (
    APPLICATION_CLIENT_WEB_LEARNING_SERVICE_MODULE,
    APPLICATION_CLIENT_WEB_LEARNING_SESSION_SERVICE_MODULE,
    APPLICATION_CLIENT_WEB_LEARNING_WORDS_SERVICE_MODULE,
    APPLICATION_CLIENT_WEB_LEARNING_ERRORS_MODULE,
    APPLICATION_CLIENT_WEB_LEARNING_MARKUP_MODULE,
)
CLIENT_WEB_LEARNING_SESSION_DATABASE_DEPENDENCIES = frozenset(
    {
        "learning_sessions",
        "similar_words",
        "teacher_student_links",
        "admin_auth",
        "bot_message_logs",
    }
)
CLIENT_WEB_LEARNING_WORDS_DATABASE_DEPENDENCIES = frozenset(
    {
        "dictionary_lookup",
        "dictionary_search",
        "learning_levels",
        "learning_progress",
        "learning_word_priority",
        "user_import_items",
    }
)
CLIENT_WEB_IMPORT_RESULT_QUERY_JOB_METHODS = frozenset(
    {
        "list_items_for_user_by_category_paginated",
        "list_item_category_counts",
        "get_latest_job_for_user",
        "list_all_items_for_user_by_category_paginated",
        "list_user_item_category_counts",
        "list_items",
        "list_unfinished_items",
    }
)
CLIENT_WEB_IMPORT_RESULTS_SERVICE_METHODS = frozenset(
    {
        "list_results",
        "ensure_job_for_user",
        "list_user_results",
        "serialize_job",
        "_repair_lookup_only_pending_job",
        "_list_unfinished_items",
        "_serialize_item",
    }
)
APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_web" / "teacher_students_service.py"
)
APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_ERRORS_MODULE = (
    APP_ROOT / "application" / "client_web" / "teacher_students_errors.py"
)
APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_VALIDATORS_MODULE = (
    APP_ROOT / "application" / "client_web" / "teacher_students_validators.py"
)
APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_MODULES = (
    APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_SERVICE_MODULE,
    APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_ERRORS_MODULE,
    APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_VALIDATORS_MODULE,
)
APPLICATION_CLIENT_IMPORT_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "application" / "client_import" / "__init__.py"
)
APPLICATION_CLIENT_IMPORT_ACTION_PAYLOAD_MODULE = (
    APP_ROOT / "application" / "client_import" / "action_payload.py"
)
APPLICATION_CLIENT_IMPORT_TEXT_INPUT_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_import" / "text_input_service.py"
)
APPLICATION_CLIENT_IMPORT_SCREEN_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_import" / "screen_service.py"
)
APPLICATION_CLIENT_IMPORT_READ_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_import" / "read_action_service.py"
)
APPLICATION_CLIENT_IMPORT_MUTATION_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_import" / "mutation_action_service.py"
)
APPLICATION_CLIENT_RUNTIME_TEXT_ACTION_SERVICE_MODULE = (
    APP_ROOT / "application" / "client_runtime" / "text_action_service.py"
)
APPLICATION_SCHEDULED_RUNTIME_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "application" / "scheduled_runtime" / "__init__.py"
)
APPLICATION_PACKAGE_FACADES = (
    (APPLICATION_PACKAGE_FACADE_MODULE, "app.application"),
    (APPLICATION_ADMIN_PACKAGE_FACADE_MODULE, "app.application.admin"),
    (APPLICATION_CLIENT_PACKAGE_FACADE_MODULE, "app.application.client"),
    (
        APPLICATION_CLIENT_IMPORT_PACKAGE_FACADE_MODULE,
        "app.application.client_import",
    ),
    (
        APPLICATION_CLIENT_LEARNING_PACKAGE_FACADE_MODULE,
        "app.application.client_learning",
    ),
    (
        APPLICATION_CLIENT_REMINDERS_PACKAGE_FACADE_MODULE,
        "app.application.client_reminders",
    ),
    (APPLICATION_CLIENT_RUNTIME_PACKAGE_FACADE_MODULE, "app.application.client_runtime"),
    (APPLICATION_CLIENT_UI_PACKAGE_FACADE_MODULE, "app.application.client_ui"),
    (APPLICATION_CLIENT_WEB_PACKAGE_FACADE_MODULE, "app.application.client_web"),
    (
        APPLICATION_SCHEDULED_RUNTIME_PACKAGE_FACADE_MODULE,
        "app.application.scheduled_runtime",
    ),
)
APPLICATION_SCHEDULED_RUNTIME_IMPORT_NOTIFICATION_SERVICE_MODULE = (
    APP_ROOT / "application" / "scheduled_runtime" / "import_notification_service.py"
)
SERIALIZATION_PACKAGE_FACADE_MODULE = APP_ROOT / "serialization" / "__init__.py"
REFERENCE_PACKAGE_FACADE_MODULE = APP_ROOT / "reference" / "__init__.py"
JSON_DATETIME_SERIALIZATION_MODULE = APP_ROOT / "serialization" / "json_datetimes.py"
ACL_PACKAGE_FACADE_MODULE = APP_ROOT / "acl" / "__init__.py"
EXTERNAL_PROVIDERS_PACKAGE_FACADE_MODULE = APP_ROOT / "external_providers" / "__init__.py"
EXTERNAL_PROVIDERS_EMBEDDINGS_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "external_providers" / "embeddings" / "__init__.py"
)
EXTERNAL_PROVIDERS_VIDEO_SESSIONS_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "external_providers" / "video_sessions" / "__init__.py"
)
SUBSCRIPTIONS_PACKAGE_FACADE_MODULE = APP_ROOT / "subscriptions" / "__init__.py"
SUPPORT_PACKAGE_FACADE_MODULE = APP_ROOT / "support" / "__init__.py"
BILLING_PACKAGE_FACADE_MODULE = APP_ROOT / "billing" / "__init__.py"
BILLING_API_ROUTER_MODULE = APP_ROOT / "billing_api.py"
BILLING_ROOT = APP_ROOT / "billing"
BILLING_HELPERS_PACKAGE_FACADE_MODULE = BILLING_ROOT / "helpers" / "__init__.py"
BILLING_PROVIDERS_PACKAGE_FACADE_MODULE = BILLING_ROOT / "providers" / "__init__.py"
BILLING_RETIRED_ROUTER_MODULE = BILLING_ROOT / "router.py"
SECURITY_PACKAGE_FACADE_MODULE = APP_ROOT / "security" / "__init__.py"
ADMIN_AUTH_ROOT = APP_ROOT / "admin_api" / "auth"
RETIRED_ADMIN_AUTH_SERVICES_ROOT = ADMIN_AUTH_ROOT / "services"
RETIRED_ADMIN_AUTH_HELPERS_ROOT = ADMIN_AUTH_ROOT / "helpers"
RETIRED_ADMIN_AUTH_VALIDATORS_ROOT = ADMIN_AUTH_ROOT / "validators"
RETIRED_ADMIN_AUTH_ERRORS_MODULE = ADMIN_AUTH_ROOT / "errors.py"
RETIRED_ADMIN_AUTH_GATEWAYS_MODULE = ADMIN_AUTH_ROOT / "gateways.py"
APPLICATION_ADMIN_AUTH_ROOT = APP_ROOT / "application" / "admin" / "auth"
APPLICATION_ADMIN_AUTH_SERVICE_MODULE = APPLICATION_ADMIN_AUTH_ROOT / "auth_service.py"
APPLICATION_ADMIN_AUTH_PORTS_MODULE = APPLICATION_ADMIN_AUTH_ROOT / "admin_auth_ports.py"
APPLICATION_ADMIN_AUTH_LOGIN_HISTORY_MODULE = (
    APPLICATION_ADMIN_AUTH_ROOT / "admin_auth_login_history.py"
)
APPLICATION_ADMIN_AUTH_MESSAGES_MODULE = APPLICATION_ADMIN_AUTH_ROOT / "admin_auth_messages.py"
APPLICATION_ADMIN_AUTH_SESSIONS_MODULE = APPLICATION_ADMIN_AUTH_ROOT / "admin_auth_sessions.py"
APPLICATION_ADMIN_AUTH_PASSWORDS_MODULE = APPLICATION_ADMIN_AUTH_ROOT / "admin_auth_passwords.py"
APPLICATION_ADMIN_AUTH_MAGIC_LINKS_MODULE = (
    APPLICATION_ADMIN_AUTH_ROOT / "admin_auth_magic_links.py"
)
APPLICATION_ADMIN_AUTH_COLLABORATOR_MODULES = (
    APPLICATION_ADMIN_AUTH_PORTS_MODULE,
    APPLICATION_ADMIN_AUTH_LOGIN_HISTORY_MODULE,
    APPLICATION_ADMIN_AUTH_MESSAGES_MODULE,
    APPLICATION_ADMIN_AUTH_SESSIONS_MODULE,
    APPLICATION_ADMIN_AUTH_PASSWORDS_MODULE,
    APPLICATION_ADMIN_AUTH_MAGIC_LINKS_MODULE,
)
APPLICATION_ADMIN_AI_USAGE_ROOT = APP_ROOT / "application" / "admin" / "ai_usage"
APPLICATION_ADMIN_AI_USAGE_READ_SERVICE_PATH = APPLICATION_ADMIN_AI_USAGE_ROOT / "read_service.py"
APPLICATION_ADMIN_AI_USAGE_ACTION_OTP_PATH = APPLICATION_ADMIN_AI_USAGE_ROOT / "action_otp.py"
ADMIN_API_AI_USAGE_ROOT = APP_ROOT / "admin_api" / "ai_usage"
ADMIN_API_AI_USAGE_PACKAGE_NAME = "app.admin_api.ai_usage"
ADMIN_API_AI_USAGE_ALLOWED_PACKAGE_IMPORT_NAMES = frozenset({"http_errors", "router"})
RETIRED_ADMIN_AI_USAGE_PACKAGE_FACADE_MODULE = ADMIN_API_AI_USAGE_ROOT / "__init__.py"
RETIRED_ADMIN_AI_USAGE_SERVICES_ROOT = ADMIN_API_AI_USAGE_ROOT / "services"
RETIRED_ADMIN_AI_USAGE_ACTION_OTP_MODULE = ADMIN_API_AI_USAGE_ROOT / "action_otp.py"
ADMIN_API_AI_USAGE_ROUTER_MODULE = ADMIN_API_AI_USAGE_ROOT / "router.py"
ADMIN_API_AI_USAGE_HTTP_ERRORS_MODULE = ADMIN_API_AI_USAGE_ROOT / "http_errors.py"
APPLICATION_ADMIN_BILLING_ROOT = APP_ROOT / "application" / "admin" / "billing"
APPLICATION_ADMIN_BILLING_READ_SERVICE_PATH = APPLICATION_ADMIN_BILLING_ROOT / "read_service.py"
ADMIN_API_BILLING_ROOT = APP_ROOT / "admin_api" / "billing"
ADMIN_API_BILLING_PACKAGE_NAME = "app.admin_api.billing"
ADMIN_API_BILLING_ALLOWED_PACKAGE_IMPORT_NAMES = frozenset({"http_errors", "router"})
RETIRED_ADMIN_BILLING_PACKAGE_FACADE_MODULE = ADMIN_API_BILLING_ROOT / "__init__.py"
RETIRED_ADMIN_BILLING_SERVICES_ROOT = ADMIN_API_BILLING_ROOT / "services"
ADMIN_API_BILLING_ROUTER_MODULE = ADMIN_API_BILLING_ROOT / "router.py"
ADMIN_API_BILLING_HTTP_ERRORS_MODULE = ADMIN_API_BILLING_ROOT / "http_errors.py"
APPLICATION_ADMIN_IMPORTS_ROOT = APP_ROOT / "application" / "admin" / "imports"
APPLICATION_ADMIN_IMPORTS_READ_SERVICE_PATH = APPLICATION_ADMIN_IMPORTS_ROOT / "read_service.py"
ADMIN_API_IMPORTS_ROOT = APP_ROOT / "admin_api" / "imports"
ADMIN_API_IMPORTS_PACKAGE_NAME = "app.admin_api.imports"
ADMIN_API_IMPORTS_ALLOWED_PACKAGE_IMPORT_NAMES = frozenset({"http_errors", "router"})
RETIRED_ADMIN_IMPORT_PACKAGE_FACADE_MODULE = ADMIN_API_IMPORTS_ROOT / "__init__.py"
RETIRED_ADMIN_IMPORT_HELPERS_ROOT = ADMIN_API_IMPORTS_ROOT / "helpers"
RETIRED_ADMIN_IMPORT_HELPERS_PACKAGE_NAME = f"{ADMIN_API_IMPORTS_PACKAGE_NAME}.helpers"
RETIRED_ADMIN_IMPORT_VALIDATORS_ROOT = ADMIN_API_IMPORTS_ROOT / "validators"
RETIRED_ADMIN_IMPORT_VALIDATORS_PACKAGE_NAME = f"{ADMIN_API_IMPORTS_PACKAGE_NAME}.validators"
RETIRED_ADMIN_IMPORT_SERVICES_ROOT = ADMIN_API_IMPORTS_ROOT / "services"
RETIRED_ADMIN_IMPORT_FACADE_HELPER_VALIDATOR_PATHS = (
    RETIRED_ADMIN_IMPORT_PACKAGE_FACADE_MODULE,
    RETIRED_ADMIN_IMPORT_HELPERS_ROOT,
    RETIRED_ADMIN_IMPORT_VALIDATORS_ROOT,
)
ADMIN_API_IMPORTS_ROUTER_MODULE = ADMIN_API_IMPORTS_ROOT / "router.py"
ADMIN_API_IMPORTS_HTTP_ERRORS_MODULE = ADMIN_API_IMPORTS_ROOT / "http_errors.py"
APPLICATION_ADMIN_LOGS_ROOT = APP_ROOT / "application" / "admin" / "logs"
APPLICATION_ADMIN_LOGS_READ_SERVICE_PATH = APPLICATION_ADMIN_LOGS_ROOT / "read_service.py"
RETIRED_ADMIN_LOG_SERVICES_ROOT = APP_ROOT / "admin_api" / "logs" / "services"
ADMIN_API_LOGS_ROUTER_MODULE = APP_ROOT / "admin_api" / "logs" / "router.py"
ADMIN_API_LOGS_HTTP_ERRORS_MODULE = APP_ROOT / "admin_api" / "logs" / "http_errors.py"
APPLICATION_ADMIN_DASHBOARD_ROOT = APP_ROOT / "application" / "admin" / "dashboard"
APPLICATION_ADMIN_DASHBOARD_SERVICE_PATH = APPLICATION_ADMIN_DASHBOARD_ROOT / "dashboard_service.py"
RETIRED_ADMIN_DASHBOARD_SERVICES_ROOT = APP_ROOT / "admin_api" / "dashboard" / "services"
ADMIN_API_DASHBOARD_ROUTER_MODULE = APP_ROOT / "admin_api" / "dashboard" / "router.py"
ADMIN_API_DASHBOARD_HTTP_ERRORS_MODULE = APP_ROOT / "admin_api" / "dashboard" / "http_errors.py"
APPLICATION_ADMIN_SETTINGS_ROOT = APP_ROOT / "application" / "admin" / "settings"
APPLICATION_ADMIN_SETTINGS_SERVICE_PATH = APPLICATION_ADMIN_SETTINGS_ROOT / "settings_service.py"
APPLICATION_ADMIN_SETTINGS_ACTION_OTP_PATH = APPLICATION_ADMIN_SETTINGS_ROOT / "action_otp.py"
APPLICATION_ADMIN_SETTINGS_VALIDATORS_PATH = APPLICATION_ADMIN_SETTINGS_ROOT / "validators.py"
APPLICATION_ADMIN_SETTINGS_PROVIDER_REFERENCE_PATH = (
    APPLICATION_ADMIN_SETTINGS_ROOT / "provider_reference.py"
)
DOMAIN_PROVIDER_SETTINGS_MODULE = "app.domain.provider_settings"
DOMAIN_PROVIDER_SETTINGS_MODULE_PATH = APP_ROOT / "domain" / "provider_settings.py"
DOMAIN_PROVIDER_SETTING_LITERAL_NAMES = (
    "DEFAULT_OPENAI_API_URL",
    "DEFAULT_USER_IMPORT_OPENAI_MODEL",
    "DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL",
    "WORD_VALIDATION_TASK_KEY",
    "WORD_DETAILS_TASK_KEY",
    "WORD_AUDIO_TASK_KEY",
    "WORD_EMBEDDINGS_TASK_KEY",
    "EXERCISE_TEXT_GENERATION_TASK_KEY",
    "EXERCISE_TEXT_TTS_TASK_KEY",
)
DOMAIN_PROVIDER_PRICING_MODULE = "app.domain.provider_pricing"
ADMIN_API_SETTINGS_ROOT = APP_ROOT / "admin_api" / "settings"
ADMIN_API_SETTINGS_PACKAGE_NAME = "app.admin_api.settings"
ADMIN_API_SETTINGS_ALLOWED_PACKAGE_IMPORT_NAMES = frozenset({"http_errors", "router"})
RETIRED_ADMIN_SETTINGS_PACKAGE_FACADE_MODULE = ADMIN_API_SETTINGS_ROOT / "__init__.py"
RETIRED_ADMIN_SETTINGS_SERVICES_ROOT = ADMIN_API_SETTINGS_ROOT / "services"
RETIRED_ADMIN_SETTINGS_VALIDATORS_ROOT = ADMIN_API_SETTINGS_ROOT / "validators"
RETIRED_ADMIN_SETTINGS_ACTION_OTP_MODULE = ADMIN_API_SETTINGS_ROOT / "action_otp.py"
ADMIN_API_SETTINGS_ROUTER_MODULE = ADMIN_API_SETTINGS_ROOT / "router.py"
ADMIN_API_SETTINGS_HTTP_ERRORS_MODULE = ADMIN_API_SETTINGS_ROOT / "http_errors.py"
APPLICATION_ADMIN_DICTIONARY_ROOT = APP_ROOT / "application" / "admin" / "dictionary"
APPLICATION_ADMIN_DICTIONARY_READ_SERVICE_PATH = APPLICATION_ADMIN_DICTIONARY_ROOT / "read_service.py"
APPLICATION_ADMIN_DICTIONARY_SERVICE_PATH = APPLICATION_ADMIN_DICTIONARY_ROOT / "dictionary_service.py"
APPLICATION_ADMIN_DICTIONARY_ACTION_SERVICE_PATH = APPLICATION_ADMIN_DICTIONARY_ROOT / "action_service.py"
APPLICATION_ADMIN_DICTIONARY_VALIDATORS_PATH = APPLICATION_ADMIN_DICTIONARY_ROOT / "validators.py"
ADMIN_COMPOSITION_MODULE = APP_ROOT / "composition" / "admin.py"
RETIRED_ADMIN_API_COMPOSITION_MODULE = APP_ROOT / "admin_api" / "composition.py"
RETIRED_ADMIN_PAGINATION_HELPER_MODULE = RETIRED_ADMIN_HELPERS_ROOT / "pagination.py"
RETIRED_ADMIN_PERMISSION_CHECKS_MODULE = RETIRED_ADMIN_HELPERS_ROOT / "permission_checks.py"
RETIRED_ADMIN_PERMISSIONS_HELPER_MODULE = RETIRED_ADMIN_HELPERS_ROOT / "permissions.py"
ADMIN_HTTP_PERMISSIONS_MODULE = APP_ROOT / "admin_api" / "http_permissions.py"
APPLICATION_ADMIN_PERMISSIONS_MODULE = APP_ROOT / "application" / "admin" / "permissions.py"
ADMIN_API_DICTIONARY_ROOT = APP_ROOT / "admin_api" / "dictionary"
ADMIN_API_DICTIONARY_ROUTER_MODULE = ADMIN_API_DICTIONARY_ROOT / "router.py"
ADMIN_API_DICTIONARY_HTTP_ERRORS_MODULE = ADMIN_API_DICTIONARY_ROOT / "http_errors.py"
RETIRED_ADMIN_DICTIONARY_PACKAGE_FACADE_MODULE = ADMIN_API_DICTIONARY_ROOT / "__init__.py"
RETIRED_ADMIN_DICTIONARY_ACTIONS_ROOT = ADMIN_API_DICTIONARY_ROOT / "actions"
RETIRED_ADMIN_DICTIONARY_SERVICES_ROOT = ADMIN_API_DICTIONARY_ROOT / "services"
RETIRED_ADMIN_DICTIONARY_HELPERS_ROOT = ADMIN_API_DICTIONARY_ROOT / "helpers"
RETIRED_ADMIN_DICTIONARY_VALIDATORS_ROOT = ADMIN_API_DICTIONARY_ROOT / "validators"
RETIRED_ADMIN_VALIDATORS_ROOT = APP_ROOT / "admin_api" / "validators"
RETIRED_ADMIN_ENTITY_SERVICES_ROOT = APP_ROOT / "admin_api" / "entity" / "services"
APPLICATION_ADMIN_ENTITY_ROOT = APP_ROOT / "application" / "admin" / "entity"
ADMIN_SETTINGS_PACKAGE_FACADE_MODULE = RETIRED_ADMIN_SETTINGS_PACKAGE_FACADE_MODULE
ADMIN_API_USERS_ROOT = APP_ROOT / "admin_api" / "users"
ADMIN_API_USERS_ROUTER_MODULE = ADMIN_API_USERS_ROOT / "router.py"
ADMIN_API_USERS_HTTP_ERRORS_MODULE = ADMIN_API_USERS_ROOT / "http_errors.py"
RETIRED_ADMIN_USERS_PACKAGE_FACADE_MODULE = ADMIN_API_USERS_ROOT / "__init__.py"
RETIRED_ADMIN_USER_ACTIONS_ROOT = ADMIN_API_USERS_ROOT / "actions"
RETIRED_ADMIN_USER_SERVICES_ROOT = ADMIN_API_USERS_ROOT / "services"
RETIRED_ADMIN_USER_HELPERS_ROOT = ADMIN_API_USERS_ROOT / "helpers"
RETIRED_ADMIN_USER_VALIDATORS_ROOT = ADMIN_API_USERS_ROOT / "validators"
ADMIN_API_USER_DICTIONARY_ROOT = APP_ROOT / "admin_api" / "user_dictionary"
RETIRED_ADMIN_USER_DICTIONARY_ACTIONS_ROOT = ADMIN_API_USER_DICTIONARY_ROOT / "actions"
RETIRED_ADMIN_USER_DICTIONARY_SERVICES_ROOT = ADMIN_API_USER_DICTIONARY_ROOT / "services"
APPLICATION_ADMIN_USER_DICTIONARY_ROOT = APP_ROOT / "application" / "admin" / "user_dictionary"
APPLICATION_ADMIN_USER_DICTIONARY_READ_SERVICE_PATH = APPLICATION_ADMIN_USER_DICTIONARY_ROOT / "read_service.py"
APPLICATION_ADMIN_USER_DICTIONARY_PROMOTE_ACTION_PATH = (
    APPLICATION_ADMIN_USER_DICTIONARY_ROOT / "promote.py"
)
REMOVED_API_PACKAGE_FACADES = (
    (ADMIN_BOOTSTRAP_PACKAGE_FACADE_MODULE, "app.admin_api.bootstrap"),
    (ADMIN_SETTINGS_PACKAGE_FACADE_MODULE, ADMIN_API_SETTINGS_PACKAGE_NAME),
    (ADMIN_VALIDATORS_PACKAGE_FACADE_MODULE, "app.admin_api.validators"),
    (RETIRED_ADMIN_DICTIONARY_PACKAGE_FACADE_MODULE, "app.admin_api.dictionary"),
    (RETIRED_ADMIN_USERS_PACKAGE_FACADE_MODULE, "app.admin_api.users"),
    (RETIRED_ADMIN_USER_ACTIONS_ROOT / "__init__.py", "app.admin_api.users.actions"),
    (RETIRED_ADMIN_USER_SERVICES_ROOT / "__init__.py", "app.admin_api.users.services"),
    (RETIRED_ADMIN_USER_HELPERS_ROOT / "__init__.py", "app.admin_api.users.helpers"),
    (RETIRED_ADMIN_USER_VALIDATORS_ROOT / "__init__.py", "app.admin_api.users.validators"),
    (
        RETIRED_ADMIN_USER_DICTIONARY_ACTIONS_ROOT / "__init__.py",
        "app.admin_api.user_dictionary.actions",
    ),
    (
        RETIRED_ADMIN_USER_DICTIONARY_SERVICES_ROOT / "__init__.py",
        "app.admin_api.user_dictionary.services",
    ),
)
ADMIN_API_READ_ROOT = APP_ROOT / "admin_api" / "read"
RETIRED_ADMIN_READ_SERVICES_ROOT = ADMIN_API_READ_ROOT / "services"
RETIRED_ADMIN_READ_MARKER_ONLY_PATHS = (
    ADMIN_API_READ_ROOT / "__init__.py",
    ADMIN_API_READ_ROOT / "helpers.py",
    ADMIN_API_READ_ROOT / "validators.py",
    ADMIN_API_READ_ROOT / "helpers" / "__init__.py",
    ADMIN_API_READ_ROOT / "validators" / "__init__.py",
)
APPLICATION_ADMIN_READ_ROOT = APP_ROOT / "application" / "admin" / "read"
APPLICATION_ADMIN_READ_SERVICE_PATH = APPLICATION_ADMIN_READ_ROOT / "read_service.py"
APPLICATION_ADMIN_USERS_ROOT = APP_ROOT / "application" / "admin" / "users"
APPLICATION_ADMIN_USERS_READ_SERVICE_PATH = APPLICATION_ADMIN_USERS_ROOT / "read_service.py"
ADMIN_API_SCHEMAS_MODULE = APP_ROOT / "admin_api" / "schemas.py"
ADMIN_SCHEMA_VALIDATORS_MODULE = APP_ROOT / "admin_api" / "schema_validators.py"
ADMIN_API_EXERCISE_TEXT_ROOT = APP_ROOT / "admin_api" / "exercise_texts"
ADMIN_EXERCISE_TEXT_SCHEMAS_MODULE = ADMIN_API_EXERCISE_TEXT_ROOT / "schemas.py"
RETIRED_ADMIN_EXERCISE_TEXT_SERVICES_ROOT = ADMIN_API_EXERCISE_TEXT_ROOT / "services"
RETIRED_ADMIN_EXERCISE_TEXT_VALIDATORS_ROOT = (
    ADMIN_API_EXERCISE_TEXT_ROOT / "validators"
)
RETIRED_ADMIN_EXERCISE_TEXT_PATHS = (
    ADMIN_API_EXERCISE_TEXT_ROOT / "__init__.py",
    ADMIN_API_EXERCISE_TEXT_ROOT / "errors.py",
    ADMIN_API_EXERCISE_TEXT_ROOT / "generation_service.py",
    ADMIN_API_EXERCISE_TEXT_ROOT / "providers.py",
    ADMIN_API_EXERCISE_TEXT_ROOT / "prompts.py",
    ADMIN_API_EXERCISE_TEXT_ROOT / "tts_service.py",
    RETIRED_ADMIN_EXERCISE_TEXT_SERVICES_ROOT,
    RETIRED_ADMIN_EXERCISE_TEXT_VALIDATORS_ROOT,
)
APPLICATION_ADMIN_EXERCISE_TEXT_ROOT = (
    APP_ROOT / "application" / "admin" / "exercise_texts"
)
ADMIN_EXERCISE_TEXT_SERVICE_PATH = (
    APPLICATION_ADMIN_EXERCISE_TEXT_ROOT / "exercise_text_service.py"
)
ADMIN_EXERCISE_TEXT_GENERATION_SERVICE = (
    APPLICATION_ADMIN_EXERCISE_TEXT_ROOT / "generation_service.py"
)
ADMIN_EXERCISE_TEXT_TTS_SERVICE = (
    APPLICATION_ADMIN_EXERCISE_TEXT_ROOT / "tts_service.py"
)
APPLICATION_ADMIN_AUDIO_MUTATION_SERVICE_MODULES = (
    ADMIN_EXERCISE_TEXT_TTS_SERVICE,
    APPLICATION_ADMIN_USER_DICTIONARY_PROMOTE_ACTION_PATH,
)
AUDIO_STORAGE_PROVIDER_INJECTION_ONLY_MODULES = (
    APP_ROOT / "helpers" / "audio_files.py",
    APPLICATION_ADMIN_DICTIONARY_SERVICE_PATH,
    APPLICATION_ADMIN_SETTINGS_SERVICE_PATH,
    USER_IMPORT_USER_DICTIONARY_BUILD_SERVICE_PATH,
    DATA_ACCESS_ROOT / "admin_dictionary.py",
    DATA_ACCESS_USER_DICTIONARY_MODULE,
    DATA_ACCESS_ROOT / "user_import_jobs.py",
)
ADMIN_EXERCISE_TEXT_CONTENT_VALIDATORS_MODULE = (
    APPLICATION_ADMIN_EXERCISE_TEXT_ROOT / "content_jsonb.py"
)
ADMIN_EXERCISE_TEXT_PROVIDER_PORTS_MODULE = (
    APPLICATION_ADMIN_EXERCISE_TEXT_ROOT / "providers.py"
)
ADMIN_EXERCISE_TEXT_PROMPTS_MODULE = APPLICATION_ADMIN_EXERCISE_TEXT_ROOT / "prompts.py"
ADMIN_EXERCISE_TEXT_APPLICATION_BOUNDARY_MODULES = tuple(
    sorted(APPLICATION_ADMIN_EXERCISE_TEXT_ROOT.rglob("*.py"))
)
EXTERNAL_EXERCISE_TEXT_PROVIDER_ADAPTER = APP_ROOT / "external_providers" / "exercise_texts.py"
EMBEDDING_SMOKE_MODULE = APP_ROOT / "embedding_smoke.py"
LEARNING_SERVICE_MODULE = APP_ROOT / "learning_service.py"
LEGACY_REPOSITORIES_MODULE = APP_ROOT / "repositories.py"
USER_IMPORT_SCHEDULED_RUNTIME_SERVICE_MODULE = APP_ROOT / "application" / "scheduled_runtime" / "user_import_service.py"
COMPOSITION_ROOT_MODULE = APP_ROOT / "composition" / "root.py"
CLIENT_WEB_PROVIDER_ADAPTERS_COMPOSITION_MODULE = (
    APP_ROOT / "composition" / "client_web_provider_adapters.py"
)
USER_IMPORT_PROVIDER_ADAPTERS_COMPOSITION_MODULE = (
    APP_ROOT / "composition" / "user_import_provider_adapters.py"
)
COMPOSITION_PACKAGE_FACADE_MODULE = APP_ROOT / "composition" / "__init__.py"
COMPOSITION_ROOT_ALLOWED_APP_IMPORTS = {
    "app.application.dispatch_lock",
    "app.config",
    "app.data_access.provider",
    "app.orm",
}
MAIN_MODULE = APP_ROOT / "main.py"
BILLING_RECONCILIATION_WORKER_MODULE = APP_ROOT / "billing_reconciliation_worker_main.py"
BOUND_GOOGLE_DOC_SYNC_WORKER_MODULE = APP_ROOT / "bound_google_doc_sync_worker_main.py"
EMBEDDING_WORKER_MODULE = APP_ROOT / "embedding_worker_main.py"
IMPORT_SCHEDULER_WORKER_MODULE = APP_ROOT / "import_scheduler_worker_main.py"
POST_UPGRADE_RESCAN_WORKER_MODULE = APP_ROOT / "post_upgrade_rescan_worker_main.py"
SUBSCRIPTION_MAINTENANCE_WORKER_MODULE = (
    APP_ROOT / "subscription_maintenance_worker_main.py"
)
USER_IMPORTS_MODULE = APP_ROOT / "user_imports.py"
USER_IMPORT_PACKAGE_FACADE_MODULE = APP_ROOT / "user_import" / "__init__.py"
USER_IMPORT_SERVICES_PACKAGE_FACADE_MODULE = APP_ROOT / "user_import" / "services" / "__init__.py"
USER_IMPORT_HELPERS_PACKAGE_FACADE_MODULE = APP_ROOT / "user_import" / "helpers" / "__init__.py"
USER_IMPORT_PROVIDERS_MODULE = APP_ROOT / "user_import" / "providers.py"
BILLING_SERVICES_PACKAGE_FACADE_MODULE = APP_ROOT / "billing" / "services" / "__init__.py"
MONOBANK_PROVIDER_PACKAGE_FACADE_MODULE = (
    APP_ROOT / "billing" / "providers" / "monobank" / "__init__.py"
)
API_HELPERS_PACKAGE_FACADE_MODULE = APP_ROOT / "api_helpers" / "__init__.py"
LEGACY_PROVIDER_EXPORTS_MODULE = APP_ROOT / "user_import" / "legacy_provider_exports.py"
EXTERNAL_PROVIDER_PRICING_SNAPSHOTS_PATH = (
    APP_ROOT / "external_providers" / "pricing_snapshots.py"
)
RETIRED_PROVIDER_REFERENCE_MODULE_PATHS = (
    APPLICATION_ADMIN_SETTINGS_PROVIDER_REFERENCE_PATH,
    APP_ROOT / "external_providers" / "registry.py",
    APP_ROOT / "external_providers" / "settings.py",
    APP_ROOT / "external_providers" / "model_catalog.py",
    APP_ROOT / "external_providers" / "pricing.py",
)
RETIRED_PROVIDER_REFERENCE_IMPORT_MODULES = frozenset(
    {
        "app.application.admin.settings.provider_reference",
        "app.external_providers.registry",
        "app.external_providers.settings",
        "app.external_providers.model_catalog",
        "app.external_providers.pricing",
    }
)
RUNTIME_STATE_FACADE_MODULE = "app.db_facades.runtime_state"
COMPOSITION_CLIENT_WEB_IMPORT_EVENTS_IMPORT_MODULE = (
    "app.composition.client_web_import_events"
)
DATABASE_PROVIDER_MODULE = "app.data_access.provider"
DATABASE_PROVIDER_ALLOWED_PUBLIC_NON_PROPERTY_METHODS = {
    "__init__",
    "connect",
    "close",
    "run_migrations",
    "session",
}
DB_FACADES_ROOT = APP_ROOT / "db_facades"
REMOVED_DATABASE_LOG_FACADE_MODULES = {
    "app.db_facades.admin_logs",
    "app.db_facades.error_logs",
}
REMOVED_DATABASE_LOG_FACADE_METHOD_NAMES = {
    "create_web_login_history",
    "get_admin_error_log_filter_metadata",
    "list_admin_error_logs",
    "list_latest_web_login_history_for_user",
    "list_web_login_history",
    "log_error",
}
REMOVED_BOT_MESSAGE_DATABASE_FACADE_MODULES = {
    "app.db_facades.bot_messages",
}
REMOVED_BOT_MESSAGE_DATABASE_FACADE_NAMES = {
    "BotMessageDatabaseFacade",
    "bot_messages",
}
REMOVED_BOT_MESSAGE_DATABASE_FACADE_METHOD_NAMES = {
    "create_bot_message_log",
    "get_bot_message_log",
    "get_due_bot_message_cleanup",
    "get_latest_active_bot_screen",
    "list_active_bot_messages",
    "save_bot_message_cleanup_result",
}
REMOVED_ADMIN_AUTH_DATABASE_FACADE_NAMES = {
    "AdminAuthDatabaseFacade",
    "admin_auth",
}
REMOVED_ADMIN_AUTH_DATABASE_FACADE_METHOD_NAMES = {
    "consume_admin_magic_link",
    "consume_admin_otp_challenge",
    "create_admin_magic_link",
    "create_admin_otp_challenge",
    "create_admin_session",
    "ensure_dev_admin_user",
    "get_active_admin_magic_link_by_token_hash",
    "get_active_admin_session_by_token_hash",
    "get_admin_credential",
    "get_admin_otp_challenge",
    "increment_admin_otp_attempts",
    "revoke_admin_session",
    "revoke_admin_session_by_token_match",
    "save_admin_otp_message_id",
    "schedule_admin_bot_restore",
    "set_admin_password_hash",
    "touch_admin_session",
}
ADMIN_SERVICE_MODULE = APP_ROOT / "admin_service.py"
API_MODULE = APP_ROOT / "api.py"
ADMIN_ROUTER_MODULE = APP_ROOT / "admin_api" / "router.py"
CLIENT_API_ROUTER_MODULE = APP_ROOT / "client_api" / "router.py"
CLIENT_WEB_ROUTER_MODULE = APP_ROOT / "client_api" / "client_web" / "router.py"
LIVE_CLIENT_API_PYTHON_FILES = (
    CLIENT_API_ROUTER_MODULE,
    CLIENT_API_INTERNAL_AUTH_MODULE,
    CLIENT_WEB_ROUTER_MODULE,
    CLIENT_WEB_SCHEMAS_MODULE,
    APP_ROOT / "client_api" / "client_web" / "students" / "router.py",
)
TELEGRAM_TRANSIENT_HELPER_MODULE = APP_ROOT / "helpers" / "telegram_transient.py"

LEARNING_SERVICE_COMPOSITION_ENTRYPOINTS = set()

EXTERNAL_PROVIDER_IMPORT_BOUNDARY_FILES = {
    Path("composition/admin.py"),
    Path("external_providers/exercise_texts.py"),
    CLIENT_WEB_PROVIDER_ADAPTERS_COMPOSITION_MODULE.relative_to(APP_ROOT),
    USER_IMPORT_PROVIDER_ADAPTERS_COMPOSITION_MODULE.relative_to(APP_ROOT),
    Path("composition/provider_helpers.py"),
}

HTTP_TRANSPORT_BOUNDARY_DIRS = {
    Path("billing/providers"),
    Path("external_providers"),
}

HTTP_TRANSPORT_BOUNDARY_FILES = {
    Path("external_providers/exercise_texts.py"),
    Path("bot_http_transport.py"),
    CLIENT_WEB_PROVIDER_ADAPTERS_COMPOSITION_MODULE.relative_to(APP_ROOT),
    USER_IMPORT_PROVIDER_ADAPTERS_COMPOSITION_MODULE.relative_to(APP_ROOT),
    Path("helpers/external_error_text.py"),
    Path("telegram_gateway.py"),
}

TELEGRAM_GATEWAY_IMPORT_BOUNDARY_FILES = {
    Path("composition/admin.py"),
    CLIENT_WEB_PROVIDER_ADAPTERS_COMPOSITION_MODULE.relative_to(APP_ROOT),
}
BILLING_SERVICES_ROOT = APP_ROOT / "billing" / "services"
BILLING_CHECKOUT_SERVICE_PATH = BILLING_SERVICES_ROOT / "checkout_service.py"
BILLING_FISCAL_CHECK_DELIVERY_PATH = BILLING_SERVICES_ROOT / "fiscal_check_delivery.py"
BILLING_HISTORY_SERVICE_PATH = BILLING_SERVICES_ROOT / "history_service.py"
BILLING_NOTIFICATION_SERVICE_PATH = BILLING_SERVICES_ROOT / "notification_service.py"
BILLING_PAYMENT_STATUS_SERVICE_PATH = BILLING_SERVICES_ROOT / "payment_status.py"
BILLING_PROVIDER_PORT_PATH = BILLING_SERVICES_ROOT / "provider_port.py"
BILLING_PAYMENT_STATUS_POLLING_SERVICE_PATH = (
    BILLING_SERVICES_ROOT / "status_service.py"
)
BILLING_RECONCILIATION_SERVICE_PATH = BILLING_SERVICES_ROOT / "reconciliation_service.py"
BILLING_RECEIPT_RETRIEVAL_SERVICE_PATH = (
    BILLING_SERVICES_ROOT / "receipt_retrieval_service.py"
)
BILLING_WEBHOOK_SERVICE_PATH = BILLING_SERVICES_ROOT / "webhook_service.py"
SUBSCRIPTION_USER_ENTITLEMENTS_PATH = (
    APP_ROOT / "subscriptions" / "user_entitlements.py"
)
SUBSCRIPTION_PAYWALL_MODULE = APP_ROOT / "subscriptions" / "paywall.py"
SUBSCRIPTION_PERIODS_MODULE = APP_ROOT / "subscriptions" / "periods.py"

LOWER_LAYER_ROOTS = (
    APP_ROOT / "acl",
    APP_ROOT / "application",
    DATA_ACCESS_ROOT,
    APP_ROOT / "domain",
    GENERIC_HELPERS_ROOT,
    APP_ROOT / "marketing",
    APP_ROOT / "reference",
    APP_ROOT / "support",
    USER_IMPORT_SERVICES_ROOT,
    VALIDATION_ROOT,
    VALIDATORS_ROOT,
)
LOWER_LAYER_FILES = (
    APP_ROOT / "billing" / "services" / "checkout_service.py",
    APP_ROOT / "billing" / "services" / "history_service.py",
    APP_ROOT / "billing" / "services" / "status_service.py",
    APP_ROOT / "billing" / "services" / "webhook_service.py",
    APP_ROOT / "billing" / "runtime_settings.py",
    APP_ROOT / "subscriptions" / "plan_limits.py",
    APP_ROOT / "subscriptions" / "paywall.py",
    APP_ROOT / "subscriptions" / "runtime_settings.py",
    APP_ROOT / "user_import" / "runtime_settings.py",
)


def test_readme_concrete_app_path_references_exist() -> None:
    offenders = [
        f"{README_PATH.relative_to(APP_ROOT.parent).as_posix()}: `{reference}`"
        for reference in _readme_concrete_app_path_references(
            README_PATH.read_text(encoding="utf-8")
        )
        if not (APP_ROOT.parent / reference).exists()
    ]

    assert offenders == []


def test_readme_concrete_app_path_reference_detection_skips_patterns() -> None:
    markdown = (
        "`app/foo.py` `app/admin_api/` `app/composition/*.py` "
        "`app/**/router.py` `app/bot_runtime/*` `app/client_api/[name].py` "
        "`scripts/task.py`"
    )

    assert _readme_concrete_app_path_references(markdown) == [
        "app/foo.py",
        "app/admin_api/",
    ]


def test_readme_does_not_reference_missing_local_documentation_directory() -> None:
    assert "`documentation/`" not in README_PATH.read_text(encoding="utf-8")


def test_readme_backend_module_map_mentions_required_module_families() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    missing_references = [
        reference
        for reference in REQUIRED_README_BACKEND_MODULE_MAP_REFERENCES
        if reference not in readme
    ]

    assert missing_references == []


def test_raw_sql_usage_is_confined_to_data_access_models_and_orm() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if _is_raw_sql_allowed_path(path):
            continue
        relative_path = path.relative_to(APP_ROOT)
        raw_sql_lines = _raw_sql_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in raw_sql_lines)

    assert offenders == []


def test_data_access_user_dictionary_status_constants_are_reexported_from_domain_constants() -> None:
    tree = ast.parse(
        DATA_ACCESS_USER_DICTIONARY_MODULE.read_text(encoding="utf-8"),
        filename=str(DATA_ACCESS_USER_DICTIONARY_MODULE),
    )
    imported_names = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        module = _resolve_import_from_module(DATA_ACCESS_USER_DICTIONARY_MODULE, node)
        if module != "app.domain.user_dictionary.constants":
            continue
        imported_names.update(
            alias.asname or alias.name
            for alias in node.names
            if alias.name in USER_DICTIONARY_STATUS_CONSTANT_NAMES
        )

    assert sorted(USER_DICTIONARY_STATUS_CONSTANT_NAMES - imported_names) == []


def test_data_access_user_dictionary_assignment_source_constants_are_reexported_from_domain_constants() -> None:
    offenders = []
    for path, required_names in DATA_ACCESS_USER_DICTIONARY_ASSIGNMENT_SOURCE_REEXPORTS.items():
        imported_names = _same_public_name_imported_names_from_module(
            path,
            "app.domain.user_dictionary.constants",
            required_names,
        )
        relative_path = path.relative_to(APP_ROOT.parent)
        offenders.extend(
            f"{relative_path.as_posix()}: missing app.domain.user_dictionary.constants.{name}"
            for name in sorted(required_names - imported_names)
        )

    assert offenders == []


def test_data_access_user_dictionary_does_not_assign_status_constants_locally() -> None:
    offenders = [
        f"app/{DATA_ACCESS_USER_DICTIONARY_MODULE.relative_to(APP_ROOT).as_posix()}:{line}: {name}"
        for line, name in _user_dictionary_status_assignment_lines(DATA_ACCESS_USER_DICTIONARY_MODULE)
    ]

    assert offenders == []


def test_data_access_user_dictionary_does_not_assign_assignment_source_constants_locally() -> None:
    offenders = []
    for path in DATA_ACCESS_USER_DICTIONARY_ASSIGNMENT_SOURCE_REEXPORTS:
        relative_path = path.relative_to(APP_ROOT.parent)
        offenders.extend(
            f"{relative_path.as_posix()}:{line}: {name}"
            for line, name in _top_level_name_binding_lines(
                path,
                USER_DICTIONARY_ASSIGNMENT_SOURCE_CONSTANT_NAMES,
            )
        )

    assert offenders == []


def test_non_data_access_app_modules_do_not_import_user_dictionary_statuses_from_data_access() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        if relative_path.parts[0] == "data_access":
            continue
        import_lines = _data_access_user_dictionary_status_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_non_data_access_app_modules_do_not_import_user_dictionary_assignment_sources_from_data_access() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        if relative_path.parts[0] == "data_access":
            continue
        import_lines = _data_access_user_dictionary_assignment_source_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_user_word_assignment_status_filters_use_domain_constants() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        offenders.extend(
            f"{relative_path.as_posix()}:{line}: inline UserWordAssignment.status literal {value!r}"
            for line, value in _inline_user_word_assignment_status_literal_lines(path)
        )

    assert offenders == []


def test_user_import_preparation_service_does_not_import_data_access_user_dictionary_constants() -> None:
    forbidden_modules = {
        "app.data_access.user_dictionary",
        "app.data_access.user_dictionary_assignments",
        "app.data_access.user_dictionary_constants",
    }
    relative_path = USER_IMPORT_PREPARATION_SERVICE_PATH.relative_to(APP_ROOT)
    offenders = []
    for forbidden_module in sorted(forbidden_modules):
        offenders.extend(
            f"app/{relative_path.as_posix()}:{line}: {forbidden_module}"
            for line in _concrete_module_import_lines(
                USER_IMPORT_PREPARATION_SERVICE_PATH,
                forbidden_module,
            )
        )

    assert offenders == []


def test_user_dictionary_status_assignment_detection_catches_top_level_assignments(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "USER_DICTIONARY_READY = 'ready_for_rotation'\n"
        "USER_DICTIONARY_STATUSES: tuple[str, ...] = (USER_DICTIONARY_READY,)\n"
        "def build():\n"
        "    USER_DICTIONARY_REJECTED = 'local value is not a module constant'\n",
        encoding="utf-8",
    )

    assert _user_dictionary_status_assignment_lines(module_path) == [
        (1, "USER_DICTIONARY_READY"),
        (2, "USER_DICTIONARY_STATUSES"),
    ]


def test_user_dictionary_status_data_access_import_detection_catches_status_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.data_access.user_dictionary import USER_DICTIONARY_READY\n"
        "from app.data_access.user_dictionary import USER_DICTIONARY_STATUSES as STATUSES\n"
        "from app.data_access.user_dictionary import USER_WORD_SOURCE_USER\n"
        "from app.data_access import user_dictionary as ud\n"
        "value = USER_DICTIONARY_READY\n"
        "statuses = STATUSES\n"
        "source = USER_WORD_SOURCE_USER\n"
        "queued = ud.USER_DICTIONARY_QUEUED_DETAILS\n",
        encoding="utf-8",
    )

    assert _data_access_user_dictionary_status_import_lines(module_path) == [1, 2, 5, 6, 8]


def test_user_dictionary_status_data_access_import_detection_allows_domain_and_assignment_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.data_access.user_dictionary import USER_WORD_SOURCE_USER\n"
        "from app.domain.user_dictionary.constants import USER_DICTIONARY_READY\n"
        "value = (USER_WORD_SOURCE_USER, USER_DICTIONARY_READY)\n",
        encoding="utf-8",
    )

    assert _data_access_user_dictionary_status_import_lines(module_path) == []


def test_user_dictionary_assignment_source_data_access_import_detection_catches_assignment_source_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.data_access.user_dictionary import USER_WORD_SOURCE_USER\n"
        "from app.data_access.user_dictionary_assignments import USER_WORD_ASSIGNMENT_AVAILABLE as AVAILABLE\n"
        "from app.data_access.user_dictionary_constants import USER_WORD_ASSIGNMENT_HIDDEN, USER_WORD_SOURCE_CORE\n"
        "from app.data_access import user_dictionary as user_dictionary_data_access\n"
        "import app.data_access.user_dictionary_constants as user_dictionary_constants\n"
        "source = USER_WORD_SOURCE_USER\n"
        "available = AVAILABLE\n"
        "hidden = USER_WORD_ASSIGNMENT_HIDDEN\n"
        "core = USER_WORD_SOURCE_CORE\n"
        "waiting = user_dictionary_data_access.USER_WORD_ASSIGNMENT_WAITING\n"
        "archived = user_dictionary_constants.USER_WORD_ASSIGNMENT_ARCHIVED\n",
        encoding="utf-8",
    )

    assert _data_access_user_dictionary_assignment_source_import_lines(module_path) == [
        1,
        2,
        3,
        6,
        7,
        8,
        9,
        10,
        11,
    ]


def test_user_dictionary_assignment_source_data_access_import_detection_allows_domain_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.domain.user_dictionary.constants import USER_WORD_ASSIGNMENT_AVAILABLE, USER_WORD_SOURCE_USER\n"
        "value = (USER_WORD_ASSIGNMENT_AVAILABLE, USER_WORD_SOURCE_USER)\n",
        encoding="utf-8",
    )

    assert _data_access_user_dictionary_assignment_source_import_lines(module_path) == []


def test_user_word_assignment_status_literal_detection_catches_inline_filters(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.models import UserWordAssignment as Assignment\n"
        "def wrong_available():\n"
        "    return Assignment.status == 'available'\n"
        "def wrong_current_literal():\n"
        "    return 'available_for_rotation' == Assignment.status\n"
        "def wrong_in_filter():\n"
        "    return Assignment.status.in_(['available'])\n"
        "def ok_domain_constant(status):\n"
        "    return Assignment.status == status\n"
        "def unrelated(status):\n"
        "    return status == 'available'\n",
        encoding="utf-8",
    )

    assert _inline_user_word_assignment_status_literal_lines(module_path) == [
        (3, "available"),
        (5, "available_for_rotation"),
        (7, "available"),
    ]


def test_same_public_name_import_detection_counts_same_name_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.domain.user_dictionary.constants import USER_WORD_SOURCE_USER\n"
        "from app.domain.user_dictionary.constants import USER_WORD_SOURCE_CORE as USER_WORD_SOURCE_CORE\n",
        encoding="utf-8",
    )

    assert _same_public_name_imported_names_from_module(
        module_path,
        "app.domain.user_dictionary.constants",
        USER_WORD_SOURCE_CONSTANT_NAMES,
    ) == {
        "USER_WORD_SOURCE_CORE",
        "USER_WORD_SOURCE_USER",
    }


def test_same_public_name_import_detection_ignores_aliases_and_qualified_references(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.domain.user_dictionary.constants import USER_WORD_SOURCE_USER as OTHER_NAME\n"
        "import app.domain.user_dictionary.constants as domain_constants\n"
        "source = domain_constants.USER_WORD_SOURCE_CORE\n",
        encoding="utf-8",
    )

    assert (
        _same_public_name_imported_names_from_module(
            module_path,
            "app.domain.user_dictionary.constants",
            USER_WORD_SOURCE_CONSTANT_NAMES,
        )
        == set()
    )


def test_raw_sql_detection_catches_direct_text_imports_and_calls(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from sqlalchemy import text\n"
        "from sqlalchemy import text as sql_text\n"
        "def build(session, conn):\n"
        "    session.execute(text('select 1'))\n"
        "    session.execute(sql_text('select 2'))\n"
        "    conn.exec_driver_sql('select 3')\n",
        encoding="utf-8",
    )

    assert _raw_sql_reference_lines(module_path) == [1, 2, 4, 5, 6]


def test_raw_sql_detection_catches_sqlalchemy_alias_text_calls(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "import sqlalchemy\n"
        "import sqlalchemy as sa\n"
        "def build():\n"
        "    sqlalchemy.text('select 1')\n"
        "    sa.text('select 2')\n",
        encoding="utf-8",
    )

    assert _raw_sql_reference_lines(module_path) == [4, 5]


def test_raw_sql_detection_catches_alternate_sqlalchemy_text_imports_and_calls(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from sqlalchemy.sql import text\n"
        "from sqlalchemy.sql import text as sql_text\n"
        "from sqlalchemy.sql.expression import text as expression_text\n"
        "from sqlalchemy.sql.expression import *\n"
        "import sqlalchemy.sql as sql\n"
        "import sqlalchemy.sql.expression as expression\n"
        "def build():\n"
        "    text('select 1')\n"
        "    sql_text('select 2')\n"
        "    expression_text('select 3')\n"
        "    sql.text('select 4')\n"
        "    expression.text('select 5')\n",
        encoding="utf-8",
    )

    assert _raw_sql_reference_lines(module_path) == [1, 2, 3, 4, 8, 9, 10, 11, 12]


def test_raw_sql_detection_allows_sqlalchemy_core_imports_and_execute_calls(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from sqlalchemy import delete, func, select\n"
        "from sqlalchemy.exc import SQLAlchemyError\n"
        "def load(session, User):\n"
        "    session.execute(select(User).where(User.id == 1))\n"
        "    session.execute(delete(User))\n"
        "    return func.count(User.id), SQLAlchemyError\n",
        encoding="utf-8",
    )

    assert _raw_sql_reference_lines(module_path) == []


def test_learning_service_imports_are_confined_to_composition_entrypoints() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        if relative_path in LEARNING_SERVICE_COMPOSITION_ENTRYPOINTS:
            continue
        import_lines = _learning_service_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_scripts_do_not_import_learning_service_legacy_facade() -> None:
    offenders = []
    for path in sorted(SCRIPTS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        import_lines = _learning_service_import_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_learning_service_legacy_facade_is_removed() -> None:
    assert not LEARNING_SERVICE_MODULE.exists()


def test_legacy_repository_placeholder_module_is_removed() -> None:
    assert not LEGACY_REPOSITORIES_MODULE.exists()


def test_production_code_does_not_import_legacy_repository_placeholder() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_repositories_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_user_import_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _user_import_package_facade_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_bot_runtime_package_facade_is_removed() -> None:
    assert not BOT_RUNTIME_PACKAGE_FACADE_MODULE.exists()


def test_app_tests_and_scripts_do_not_import_bot_runtime_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _bot_runtime_package_facade_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_bot_runtime_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.bot_runtime import application\n"
        "import app.bot_runtime\n"
        "import app.bot_runtime as bot_runtime\n"
        "from app import bot_runtime\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "bot_runtime" / "module.py"
    nested_module_path = app_root / "bot_runtime" / "subpackage" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text("from . import application\n", encoding="utf-8")
    nested_module_path.write_text("from .. import application\n", encoding="utf-8")

    assert _bot_runtime_package_facade_import_lines(module_path) == [1, 2, 3, 4]
    assert _bot_runtime_package_facade_import_lines(root_module_path) == [1]
    assert _bot_runtime_package_facade_import_lines(nested_module_path) == [1]


def test_bot_runtime_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.bot_runtime.screen_delivery import render_screen\n"
        "import app.bot_runtime.application as runtime_application\n"
        "import app.bot_runtime.handlers\n",
        encoding="utf-8",
    )

    assert _bot_runtime_package_facade_import_lines(module_path) == []


def test_app_tests_scripts_and_word_base_do_not_import_api_package_facades() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _api_package_facade_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_removed_api_package_facades() -> None:
    offenders = []
    marker_paths = {
        module_path
        for module_path, _ in REMOVED_API_PACKAGE_FACADES
    }
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            if path in marker_paths:
                continue
            relative_path = path.relative_to(APP_ROOT.parent)
            for _, package_name in REMOVED_API_PACKAGE_FACADES:
                allowed_import_from_names = (
                    ADMIN_API_SETTINGS_ALLOWED_PACKAGE_IMPORT_NAMES
                    if package_name == ADMIN_API_SETTINGS_PACKAGE_NAME
                    else frozenset()
                )
                import_lines = _package_facade_import_lines(
                    path,
                    package_name,
                    allowed_import_from_names=allowed_import_from_names,
                )
                offenders.extend(
                    f"{relative_path.as_posix()}:{line}: {package_name}"
                    for line in import_lines
                )

    assert offenders == []


def test_removed_api_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.settings import services\n"
        "from app.admin_api.settings import validators as settings_validators\n"
        "import app.admin_api.settings\n"
        "import app.admin_api.settings as admin_settings\n"
        "from app.admin_api import settings\n"
        "from app.admin_api import settings as admin_settings\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.admin_api.settings",
    ) == [1, 2, 3, 4, 5, 6]


def test_removed_api_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.settings.router import build_settings_router\n"
        "from app.admin_api.settings.http_errors import admin_settings_http_exception\n"
        "from app.application.admin.settings.action_otp import AdminSettingsActionOtpVerifier\n"
        "import app.admin_api.settings.router as settings_router\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.admin_api.settings") == []


def test_api_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api import build_admin_router\n"
        "import app.admin_api\n"
        "import app.admin_api as admin_api\n"
        "from app import admin_api\n"
        "from app.client_api import build_client_router\n"
        "import app.client_api\n"
        "import app.client_api as client_api\n"
        "from app import client_api\n",
        encoding="utf-8",
    )

    assert _api_package_facade_import_lines(module_path) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    ]


def test_api_package_facade_import_detection_allows_router_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.router import build_admin_router\n"
        "from app.client_api.router import build_client_router\n"
        "import app.admin_api.router as admin_router\n"
        "import app.client_api.router as client_router\n",
        encoding="utf-8",
    )

    assert _api_package_facade_import_lines(module_path) == []


@pytest.mark.parametrize(
    "module_path",
    [module_path for module_path, _ in EMPTY_MARKER_PACKAGE_FACADES],
)
def test_empty_marker_package_facades_are_removed(module_path: Path) -> None:
    assert not module_path.exists()


@pytest.mark.parametrize(("facade_module", "package_name"), EMPTY_MARKER_PACKAGE_FACADES)
def test_app_tests_scripts_and_word_base_do_not_import_empty_marker_package_facades(
    facade_module: Path,
    package_name: str,
) -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            if path == facade_module:
                continue
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, package_name)
            offenders.extend(
                f"{relative_path.as_posix()}:{line}: {package_name}"
                for line in import_lines
            )

    assert offenders == []


@pytest.mark.parametrize(
    "package_name",
    [package_name for _, package_name in EMPTY_MARKER_PACKAGE_FACADES],
)
def test_empty_marker_package_facade_import_detection_catches_broad_imports(
    package_name: str,
    tmp_path: Path,
) -> None:
    parent_module, _, package_basename = package_name.rpartition(".")
    module_path = tmp_path / "module.py"
    module_path.write_text(
        f"from {package_name} import FacadeExport\n"
        f"import {package_name}\n"
        f"import {package_name} as package_facade\n"
        f"from {parent_module} import {package_basename}\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, package_name) == [1, 2, 3, 4]


def test_empty_marker_package_facade_import_detection_allows_concrete_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.auth.identity import UserIdentity\n"
        "import app.auth.identity as identity\n"
        "from app.domain.provider_settings import DEFAULT_OPENAI_API_URL\n"
        "import app.domain.provider_settings as provider_settings\n"
        "from app.domain.user_dictionary.constants import USER_DICTIONARY_READY\n"
        "import app.domain.user_dictionary.constants as user_dictionary_constants\n"
        "from app.domain.user_import.prompts import build_user_import_openai_prompt\n"
        "import app.domain.user_import.text_parser as text_parser\n"
        "from app.marketing.runtime_settings import read_marketing_runtime_settings\n"
        "import app.marketing.runtime_settings as marketing_runtime_settings\n"
        "from app.data_access.provider import Database\n"
        "import app.data_access.provider as data_access_provider\n",
        encoding="utf-8",
    )

    assert {
        package_name: _package_facade_import_lines(module_path, package_name)
        for _, package_name in EMPTY_MARKER_PACKAGE_FACADES
    } == {
        package_name: []
        for _, package_name in EMPTY_MARKER_PACKAGE_FACADES
    }


def test_api_helpers_package_facade_is_removed() -> None:
    assert not API_HELPERS_PACKAGE_FACADE_MODULE.exists()


def test_helpers_package_facade_is_removed() -> None:
    assert not HELPERS_PACKAGE_FACADE_MODULE.exists()


def test_validators_package_facade_is_removed() -> None:
    assert not VALIDATORS_PACKAGE_FACADE_MODULE.exists()


def test_validation_package_facade_is_removed() -> None:
    assert not VALIDATION_PACKAGE_FACADE_MODULE.exists()


def test_external_providers_embeddings_package_facade_is_removed() -> None:
    assert not EXTERNAL_PROVIDERS_EMBEDDINGS_PACKAGE_FACADE_MODULE.exists()


def test_user_import_helpers_package_facade_is_removed() -> None:
    assert not USER_IMPORT_HELPERS_PACKAGE_FACADE_MODULE.exists()


def test_user_import_package_facade_is_removed() -> None:
    assert not USER_IMPORT_PACKAGE_FACADE_MODULE.exists()


def test_user_import_services_package_facade_is_removed() -> None:
    assert not USER_IMPORT_SERVICES_PACKAGE_FACADE_MODULE.exists()


def test_composition_package_facade_is_removed() -> None:
    assert not COMPOSITION_PACKAGE_FACADE_MODULE.exists()


@pytest.mark.parametrize(
    ("marker_name", "target_module", "is_valid"),
    (
        ("RETIRED_APPLICATION_MODULE", "app.application.client.imports", True),
        ("RETIRED_COMPOSITION_MODULE", "app.composition.client_imports", True),
        ("RETIRED_APPLICATION_MODULE", "app.composition.client_imports", False),
        ("RETIRED_COMPOSITION_MODULE", "app.application.client.imports", False),
    ),
    ids=(
        "application-marker-application-target",
        "composition-marker-composition-target",
        "application-marker-composition-target",
        "composition-marker-application-target",
    ),
)
def test_marker_only_package_facade_guard_matches_marker_name_to_target_prefix(
    tmp_path: Path,
    marker_name: str,
    target_module: str,
    is_valid: bool,
) -> None:
    module_path = tmp_path / "__init__.py"
    module_path.write_text(
        f'"""Retired facade."""\n{marker_name} = "{target_module}"\n',
        encoding="utf-8",
    )

    expected = [] if is_valid else [f"{module_path}:2: invalid retired target marker"]

    assert _marker_only_package_facade_shape_violations(module_path) == expected


def test_application_package_facade_is_removed() -> None:
    assert not APPLICATION_PACKAGE_FACADE_MODULE.exists()


def test_application_admin_package_facade_is_removed() -> None:
    assert not APPLICATION_ADMIN_PACKAGE_FACADE_MODULE.exists()


def test_application_client_runtime_package_facade_is_removed() -> None:
    assert not APPLICATION_CLIENT_RUNTIME_PACKAGE_FACADE_MODULE.exists()


def test_application_client_package_facade_is_removed() -> None:
    assert not APPLICATION_CLIENT_PACKAGE_FACADE_MODULE.exists()


def test_application_client_learning_package_facade_is_removed() -> None:
    assert not APPLICATION_CLIENT_LEARNING_PACKAGE_FACADE_MODULE.exists()


def test_application_client_reminders_package_facade_is_removed() -> None:
    assert not APPLICATION_CLIENT_REMINDERS_PACKAGE_FACADE_MODULE.exists()


def test_application_client_ui_package_facade_is_removed() -> None:
    assert not APPLICATION_CLIENT_UI_PACKAGE_FACADE_MODULE.exists()


def test_application_client_web_package_facade_is_removed() -> None:
    assert not APPLICATION_CLIENT_WEB_PACKAGE_FACADE_MODULE.exists()


def test_application_client_import_package_facade_is_removed() -> None:
    assert not APPLICATION_CLIENT_IMPORT_PACKAGE_FACADE_MODULE.exists()


def test_application_scheduled_runtime_package_facade_is_removed() -> None:
    assert not APPLICATION_SCHEDULED_RUNTIME_PACKAGE_FACADE_MODULE.exists()


def test_serialization_package_facade_is_removed() -> None:
    assert not SERIALIZATION_PACKAGE_FACADE_MODULE.exists()


def test_reference_package_facade_is_removed() -> None:
    assert not REFERENCE_PACKAGE_FACADE_MODULE.exists()


def test_acl_package_facade_is_removed() -> None:
    assert not ACL_PACKAGE_FACADE_MODULE.exists()


def test_external_providers_package_facade_is_removed() -> None:
    assert not EXTERNAL_PROVIDERS_PACKAGE_FACADE_MODULE.exists()


def test_external_providers_video_sessions_package_facade_is_removed() -> None:
    assert not EXTERNAL_PROVIDERS_VIDEO_SESSIONS_PACKAGE_FACADE_MODULE.exists()


def test_subscriptions_package_facade_is_removed() -> None:
    assert not SUBSCRIPTIONS_PACKAGE_FACADE_MODULE.exists()


def test_support_package_facade_is_removed() -> None:
    assert not SUPPORT_PACKAGE_FACADE_MODULE.exists()


def test_billing_package_facade_is_removed() -> None:
    assert not BILLING_PACKAGE_FACADE_MODULE.exists()


def test_billing_helpers_package_facade_is_removed() -> None:
    assert not BILLING_HELPERS_PACKAGE_FACADE_MODULE.exists()


def test_billing_providers_package_facade_is_removed() -> None:
    assert not BILLING_PROVIDERS_PACKAGE_FACADE_MODULE.exists()


def test_billing_http_router_lives_in_public_api_module() -> None:
    assert BILLING_API_ROUTER_MODULE.exists()
    assert not BILLING_RETIRED_ROUTER_MODULE.exists()


def test_billing_package_does_not_contain_http_router_modules() -> None:
    offenders = [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted(BILLING_ROOT.rglob("*.py"))
        if "router" in path.stem
    ]

    assert offenders == []


def test_billing_package_does_not_import_http_framework() -> None:
    offenders = []
    for path in sorted(BILLING_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        offenders.extend(
            f"app/{relative_path.as_posix()}:{line}"
            for line in _http_framework_import_lines(path)
        )

    assert offenders == []


def test_security_package_facade_is_removed() -> None:
    assert not SECURITY_PACKAGE_FACADE_MODULE.exists()


def test_admin_api_package_facade_is_removed() -> None:
    assert not ADMIN_API_PACKAGE_FACADE_MODULE.exists()


def test_client_api_package_facade_is_removed() -> None:
    assert not CLIENT_API_PACKAGE_FACADE_MODULE.exists()


def test_client_api_does_not_import_admin_api_modules() -> None:
    offenders = []
    for path in sorted((APP_ROOT / "client_api").rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _concrete_module_import_lines(path, "app.admin_api")
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_client_api_python_files_match_live_allowlist() -> None:
    actual = [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted((APP_ROOT / "client_api").rglob("*.py"))
    ]
    expected = [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted(LIVE_CLIENT_API_PYTHON_FILES)
    ]

    assert actual == expected


@pytest.mark.parametrize(
    "module_path",
    [
        module_path
        for module_path, _ in REMOVED_API_PACKAGE_FACADES
    ],
)
def test_removed_api_package_facades_are_removed(
    module_path: Path,
) -> None:
    assert not module_path.exists()


@pytest.mark.parametrize(
    "module_path",
    [
        module_path
        for module_path, *_ in RETIRED_ADMIN_TOP_LEVEL_PACKAGE_FACADES
    ],
)
def test_retired_admin_top_level_package_facades_are_removed(
    module_path: Path,
) -> None:
    assert not module_path.exists()


def test_retired_admin_helpers_package_is_removed() -> None:
    assert not RETIRED_ADMIN_HELPERS_ROOT.exists()


def test_retired_admin_permission_helper_modules_are_removed() -> None:
    for path in (RETIRED_ADMIN_PERMISSION_CHECKS_MODULE, RETIRED_ADMIN_PERMISSIONS_HELPER_MODULE):
        assert not path.exists()


def test_admin_api_contains_no_business_subdirectories() -> None:
    offenders = [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted(ADMIN_API_ROOT.rglob("*"))
        if path.is_dir() and path.name in ADMIN_API_FORBIDDEN_BUSINESS_DIR_NAMES
    ]

    assert offenders == []


def test_admin_api_composition_module_is_retired() -> None:
    assert not RETIRED_ADMIN_API_COMPOSITION_MODULE.exists()


def test_app_tests_and_scripts_do_not_import_retired_admin_api_composition() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                "app.admin_api.composition",
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_admin_bootstrap_package_contains_only_router_module() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted((APP_ROOT / "admin_api" / "bootstrap").rglob("*.py"))
    ] == ["admin_api/bootstrap/router.py"]


@pytest.mark.parametrize(
    "path",
    (
        ADMIN_BOOTSTRAP_PACKAGE_FACADE_MODULE,
        ADMIN_BOOTSTRAP_ACTIONS_ROOT,
        ADMIN_BOOTSTRAP_HELPERS_ROOT,
        ADMIN_BOOTSTRAP_SERVICES_ROOT,
        ADMIN_BOOTSTRAP_SERVICE_MODULE,
        ADMIN_BOOTSTRAP_VALIDATORS_ROOT,
    ),
)
def test_retired_admin_bootstrap_facade_internal_packages_and_service_are_removed(
    path: Path,
) -> None:
    assert not path.exists()


@pytest.mark.parametrize(
    "path",
    (
        RETIRED_ADMIN_AUTH_SERVICES_ROOT,
        RETIRED_ADMIN_AUTH_HELPERS_ROOT,
        RETIRED_ADMIN_AUTH_VALIDATORS_ROOT,
    ),
)
def test_retired_admin_auth_internal_packages_are_removed(path: Path) -> None:
    assert not path.exists() or sorted(path.rglob("*.py")) == []


@pytest.mark.parametrize(
    "path",
    (
        RETIRED_ADMIN_AUTH_ERRORS_MODULE,
        RETIRED_ADMIN_AUTH_GATEWAYS_MODULE,
    ),
)
def test_retired_admin_auth_internal_modules_are_removed(path: Path) -> None:
    assert not path.exists()


def test_admin_dashboard_top_level_package_facade_is_removed() -> None:
    assert not ADMIN_DASHBOARD_PACKAGE_FACADE_MODULE.exists()


def test_admin_ai_usage_services_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_AI_USAGE_SERVICES_ROOT.exists()
        or sorted(RETIRED_ADMIN_AI_USAGE_SERVICES_ROOT.rglob("*.py")) == []
    )


def test_admin_ai_usage_package_contains_only_router_and_http_errors_modules() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted(ADMIN_API_AI_USAGE_ROOT.rglob("*.py"))
    ] == [
        "admin_api/ai_usage/http_errors.py",
        "admin_api/ai_usage/router.py",
    ]


def test_retired_admin_ai_usage_facade_and_action_otp_are_removed() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in (
            RETIRED_ADMIN_AI_USAGE_PACKAGE_FACADE_MODULE,
            RETIRED_ADMIN_AI_USAGE_ACTION_OTP_MODULE,
        )
        if path.exists()
    ] == []


def test_admin_dashboard_services_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_DASHBOARD_SERVICES_ROOT.exists()
        or sorted(RETIRED_ADMIN_DASHBOARD_SERVICES_ROOT.rglob("*.py")) == []
    )


def test_admin_billing_package_contains_only_router_and_http_errors_modules() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted(ADMIN_API_BILLING_ROOT.rglob("*.py"))
    ] == [
        "admin_api/billing/http_errors.py",
        "admin_api/billing/router.py",
    ]


def test_retired_admin_billing_package_facade_is_removed() -> None:
    assert not RETIRED_ADMIN_BILLING_PACKAGE_FACADE_MODULE.exists()


def test_admin_billing_services_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_BILLING_SERVICES_ROOT.exists()
        or sorted(RETIRED_ADMIN_BILLING_SERVICES_ROOT.rglob("*.py")) == []
    )


def test_admin_settings_package_contains_only_router_and_http_errors_modules() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted(ADMIN_API_SETTINGS_ROOT.rglob("*.py"))
    ] == [
        "admin_api/settings/http_errors.py",
        "admin_api/settings/router.py",
    ]


def test_retired_admin_settings_action_otp_module_is_removed() -> None:
    assert not RETIRED_ADMIN_SETTINGS_ACTION_OTP_MODULE.exists()


@pytest.mark.parametrize(
    "removed_root",
    (
        RETIRED_ADMIN_DICTIONARY_ACTIONS_ROOT,
        RETIRED_ADMIN_DICTIONARY_SERVICES_ROOT,
        RETIRED_ADMIN_DICTIONARY_HELPERS_ROOT,
        RETIRED_ADMIN_DICTIONARY_VALIDATORS_ROOT,
        RETIRED_ADMIN_VALIDATORS_ROOT,
        RETIRED_ADMIN_USERS_PACKAGE_FACADE_MODULE,
        RETIRED_ADMIN_USER_ACTIONS_ROOT,
        RETIRED_ADMIN_USER_SERVICES_ROOT,
        RETIRED_ADMIN_USER_HELPERS_ROOT,
        RETIRED_ADMIN_USER_VALIDATORS_ROOT,
        RETIRED_ADMIN_USER_DICTIONARY_ACTIONS_ROOT,
        RETIRED_ADMIN_USER_DICTIONARY_SERVICES_ROOT,
    )
)
def test_retired_admin_api_packages_are_removed(removed_root: Path) -> None:
    assert not removed_root.exists()


def test_admin_entity_services_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_ENTITY_SERVICES_ROOT.exists()
        or sorted(RETIRED_ADMIN_ENTITY_SERVICES_ROOT.rglob("*.py")) == []
    )


def test_admin_exercise_text_api_package_contains_only_http_modules() -> None:
    assert [
        path.relative_to(ADMIN_API_EXERCISE_TEXT_ROOT).as_posix()
        for path in sorted(ADMIN_API_EXERCISE_TEXT_ROOT.rglob("*.py"))
    ] == ["http_errors.py", "router.py", "schemas.py"]


@pytest.mark.parametrize(
    "removed_path",
    RETIRED_ADMIN_EXERCISE_TEXT_PATHS,
    ids=lambda path: path.relative_to(APP_ROOT).as_posix(),
)
def test_retired_admin_exercise_text_modules_are_removed(removed_path: Path) -> None:
    assert not removed_path.exists()


def test_admin_exercise_text_http_errors_import_application_errors() -> None:
    path = ADMIN_API_EXERCISE_TEXT_ROOT / "http_errors.py"
    direct_imports = {module for _line, module in _direct_import_modules(path)}

    assert "app.application.admin.exercise_texts.errors" in direct_imports
    assert _concrete_module_import_lines(path, "app.admin_api.exercise_texts.errors") == []


def test_admin_settings_services_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_SETTINGS_SERVICES_ROOT.exists()
        or sorted(RETIRED_ADMIN_SETTINGS_SERVICES_ROOT.rglob("*.py")) == []
    )


def test_admin_settings_validators_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_SETTINGS_VALIDATORS_ROOT.exists()
        or sorted(RETIRED_ADMIN_SETTINGS_VALIDATORS_ROOT.rglob("*.py")) == []
    )


def test_admin_imports_package_contains_only_router_and_http_errors_modules() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in sorted(ADMIN_API_IMPORTS_ROOT.rglob("*.py"))
    ] == [
        "admin_api/imports/http_errors.py",
        "admin_api/imports/router.py",
    ]


def test_retired_admin_import_facade_helpers_and_validators_are_removed() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in RETIRED_ADMIN_IMPORT_FACADE_HELPER_VALIDATOR_PATHS
        if path.exists()
    ] == []


def test_admin_import_services_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_IMPORT_SERVICES_ROOT.exists()
        or sorted(RETIRED_ADMIN_IMPORT_SERVICES_ROOT.rglob("*.py")) == []
    )


def test_admin_log_services_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_LOG_SERVICES_ROOT.exists()
        or sorted(RETIRED_ADMIN_LOG_SERVICES_ROOT.rglob("*.py")) == []
    )


def test_admin_read_services_package_is_removed() -> None:
    assert (
        not RETIRED_ADMIN_READ_SERVICES_ROOT.exists()
        or sorted(RETIRED_ADMIN_READ_SERVICES_ROOT.rglob("*.py")) == []
    )


def test_admin_read_marker_only_package_helper_and_validator_files_are_removed() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in RETIRED_ADMIN_READ_MARKER_ONLY_PATHS
        if path.exists()
    ] == []


def test_client_web_settings_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_WEB_SETTINGS_SERVICE_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_WEB_SETTINGS_SERVICE_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_WEB_SETTINGS_SERVICE_MODULE)
            )
        )
    ]

    assert offenders == []


def test_client_web_settings_service_uses_composed_entitlement_provider() -> None:
    offenders = _source_fragment_offenders(
        APPLICATION_CLIENT_WEB_SETTINGS_SERVICE_MODULE,
        (
            "UserEntitlementResolver",
            "PlanLimitSettingsValidationError",
            "read_user_uuid",
            "ClientWebSettingsSubscriptionsPort",
            "self.db.subscriptions",
        ),
    )

    assert offenders == []


def test_client_web_settings_dependencies_stay_in_settings_database_port() -> None:
    database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_SETTINGS_SERVICE_MODULE,
        "ClientWebSettingsDatabasePort",
    )

    assert database_annotations == {
        "settings",
        "app_settings",
        "user_profiles",
        "user_learning_settings",
        "learning_levels",
        "task_logs",
    }


def test_client_web_settings_service_call_sites_pass_entitlement_provider() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            import_aliases = _import_alias_map(module, path)
            relative_path = path.relative_to(APP_ROOT.parent)
            for node in ast.walk(module):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _resolve_import_alias_name(_attribute_chain_name(node.func), import_aliases)
                if call_name not in {
                    "ClientWebSettingsService",
                    "app.application.client_web.settings_service.ClientWebSettingsService",
                }:
                    continue
                keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
                if "entitlement_provider" not in keyword_names:
                    offenders.append(f"{relative_path.as_posix()}:{node.lineno}")

    assert offenders == []


def test_client_web_plan_service_uses_composed_account_provider() -> None:
    offenders = _source_fragment_offenders(
        APPLICATION_CLIENT_WEB_PLAN_SERVICE_MODULE,
        ("read_user_uuid",),
    )
    offenders.extend(
        _self_db_dependency_accesses(
            APPLICATION_CLIENT_WEB_PLAN_SERVICE_MODULE,
            "ClientWebPlanService",
            frozenset({"user_profiles", "subscriptions", "billing"}),
        )
    )

    assert offenders == []


def test_client_web_plan_dependencies_stay_in_plan_database_port() -> None:
    database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_PLAN_SERVICE_MODULE,
        "ClientWebPlanDatabasePort",
    )

    assert {"user_profiles", "subscriptions", "billing"}.isdisjoint(database_annotations)
    assert database_annotations == {"app_settings", "settings"}


def test_client_web_plan_service_call_sites_pass_account_provider() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            import_aliases = _import_alias_map(module, path)
            relative_path = path.relative_to(APP_ROOT.parent)
            for node in ast.walk(module):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _resolve_import_alias_name(_attribute_chain_name(node.func), import_aliases)
                if call_name not in {
                    "ClientWebPlanService",
                    "app.application.client_web.plan_service.ClientWebPlanService",
                }:
                    continue
                keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
                if "account_provider" not in keyword_names:
                    offenders.append(f"{relative_path.as_posix()}:{node.lineno}")

    assert offenders == []


@pytest.mark.parametrize(
    "module_path",
    APPLICATION_CLIENT_WEB_AUTH_MODULES,
    ids=lambda path: path.stem,
)
def test_client_web_auth_application_modules_stay_out_of_api_layer(
    module_path: Path,
) -> None:
    relative_path = module_path.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(module_path)
                + _interface_api_import_lines(module_path)
                + _telegram_gateway_import_lines(module_path)
                + _external_provider_import_lines(module_path)
            )
        )
    ]

    assert offenders == []


def test_client_web_auth_session_lifecycle_methods_live_on_session_service() -> None:
    _, auth_service_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_AUTH_SERVICE_MODULE,
        "ClientWebAuthService",
    )
    _, session_service_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_AUTH_SESSION_SERVICE_MODULE,
        "ClientWebAuthSessionService",
    )
    public_facade_methods = {"get_session_user", "logout"}
    moved_private_methods = {
        "_build_teacher_referral_url",
    }
    session_contract_methods = {
        "create_session_token",
        "log_login_event",
        "with_auth_flags",
    }
    retired_auth_private_methods = {
        "_create_session_token",
        "_log_login_event",
        "_with_auth_flags",
        "_build_teacher_referral_url",
    }

    assert public_facade_methods.issubset(auth_service_methods)
    assert retired_auth_private_methods.isdisjoint(auth_service_methods)
    assert public_facade_methods.union(moved_private_methods, session_contract_methods).issubset(
        session_service_methods
    )


def test_client_web_auth_session_service_does_not_import_concrete_storage() -> None:
    forbidden_roots = {
        "app.models",
        "sqlalchemy",
    }
    import_lines = (
        _database_provider_import_lines(APPLICATION_CLIENT_WEB_AUTH_SESSION_SERVICE_MODULE)
        + _legacy_repositories_import_lines(APPLICATION_CLIENT_WEB_AUTH_SESSION_SERVICE_MODULE)
    )
    for forbidden_root in sorted(forbidden_roots):
        import_lines.extend(
            _concrete_module_import_lines(
                APPLICATION_CLIENT_WEB_AUTH_SESSION_SERVICE_MODULE,
                forbidden_root,
            )
        )
    offenders = [
        f"app/{APPLICATION_CLIENT_WEB_AUTH_SESSION_SERVICE_MODULE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in sorted(set(import_lines))
    ]

    assert offenders == []


@pytest.mark.parametrize(
    "module_path",
    AUTH_PRIMITIVES_MODULES,
    ids=lambda path: path.stem,
)
def test_auth_primitives_stay_framework_and_api_neutral(module_path: Path) -> None:
    relative_path = module_path.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(module_path)
                + _interface_api_import_lines(module_path)
                + _telegram_gateway_import_lines(module_path)
                + _external_provider_import_lines(module_path)
            )
        )
    ]

    assert offenders == []


def test_client_bootstrap_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_BOOTSTRAP_SERVICE_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_BOOTSTRAP_SERVICE_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_BOOTSTRAP_SERVICE_MODULE)
                + _telegram_gateway_import_lines(APPLICATION_CLIENT_BOOTSTRAP_SERVICE_MODULE)
                + _external_provider_import_lines(APPLICATION_CLIENT_BOOTSTRAP_SERVICE_MODULE)
            )
        )
    ]

    assert offenders == []


def test_client_learning_web_link_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_LEARNING_WEB_LINK_SERVICE_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_LEARNING_WEB_LINK_SERVICE_MODULE)
                + _interface_api_import_lines(
                    APPLICATION_CLIENT_LEARNING_WEB_LINK_SERVICE_MODULE
                )
                + _telegram_gateway_import_lines(
                    APPLICATION_CLIENT_LEARNING_WEB_LINK_SERVICE_MODULE
                )
                + _external_provider_import_lines(
                    APPLICATION_CLIENT_LEARNING_WEB_LINK_SERVICE_MODULE
                )
            )
        )
    ]

    assert offenders == []


@pytest.mark.parametrize(
    "module_path",
    APPLICATION_CLIENT_LEARNING_MENU_MODULES,
    ids=lambda path: path.stem,
)
def test_client_learning_application_modules_stay_out_of_api_layer(
    module_path: Path,
) -> None:
    relative_path = module_path.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _http_framework_import_lines(module_path)
                + _interface_api_import_lines(module_path)
                + _telegram_gateway_import_lines(module_path)
                + _external_provider_import_lines(module_path)
            )
        )
    ]

    assert offenders == []


@pytest.mark.parametrize(
    "module_path",
    APPLICATION_CLIENT_LEARNING_PRESENTATION_MODULES,
    ids=lambda path: path.stem,
)
def test_client_learning_presentation_application_modules_do_not_import_client_api(
    module_path: Path,
) -> None:
    relative_path = module_path.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(module_path)
        if module == "app.client_api" or module.startswith("app.client_api.")
    ]

    assert offenders == []


def test_client_learning_completion_application_service_does_not_import_data_access() -> None:
    relative_path = APPLICATION_CLIENT_LEARNING_COMPLETION_SERVICE_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(
            APPLICATION_CLIENT_LEARNING_COMPLETION_SERVICE_MODULE
        )
        if module == "app.data_access" or module.startswith("app.data_access.")
    ]

    assert offenders == []


@pytest.mark.parametrize(
    "module_path",
    APPLICATION_CLIENT_LEARNING_PLANNING_MODULES,
    ids=lambda path: path.stem,
)
def test_client_learning_planning_application_modules_do_not_import_client_api(
    module_path: Path,
) -> None:
    relative_path = module_path.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(module_path)
        if module == "app.client_api" or module.startswith("app.client_api.")
    ]

    assert offenders == []


def test_client_learning_planning_application_service_does_not_import_data_access() -> None:
    relative_path = APPLICATION_CLIENT_LEARNING_PLANNING_SERVICE_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(
            APPLICATION_CLIENT_LEARNING_PLANNING_SERVICE_MODULE
        )
        if module == "app.data_access" or module.startswith("app.data_access.")
    ]

    assert offenders == []


def test_client_learning_summary_application_service_does_not_import_data_access_or_client_api() -> None:
    relative_path = APPLICATION_CLIENT_LEARNING_SUMMARY_SERVICE_MODULE.relative_to(APP_ROOT)
    forbidden_roots = ("app.client_api", "app.data_access")
    offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(
            APPLICATION_CLIENT_LEARNING_SUMMARY_SERVICE_MODULE
        )
        if module in forbidden_roots
        or any(module.startswith(f"{root}.") for root in forbidden_roots)
    ]

    assert offenders == []


@pytest.mark.parametrize(
    "module_path",
    APPLICATION_CLIENT_REMINDER_MODULES,
    ids=lambda path: path.stem,
)
def test_client_reminder_application_modules_stay_out_of_api_data_access_and_transport_layers(
    module_path: Path,
) -> None:
    relative_path = module_path.relative_to(APP_ROOT)
    forbidden_roots = ("app.client_api", "app.data_access")
    direct_import_offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(module_path)
        if module in forbidden_roots
        or any(module.startswith(f"{root}.") for root in forbidden_roots)
    ]
    boundary_import_lines = sorted(
        set(
            _http_framework_import_lines(module_path)
            + _httpx_transport_usage_lines(module_path)
            + _telegram_gateway_import_lines(module_path)
            + _external_provider_import_lines(module_path)
        )
    )
    offenders = direct_import_offenders + [
        f"app/{relative_path.as_posix()}:{line}: transport/provider boundary"
        for line in boundary_import_lines
    ]

    assert offenders == []


def test_client_ui_choice_controls_application_helper_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_UI_CHOICE_CONTROLS_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _http_framework_import_lines(APPLICATION_CLIENT_UI_CHOICE_CONTROLS_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_UI_CHOICE_CONTROLS_MODULE)
                + _telegram_gateway_import_lines(APPLICATION_CLIENT_UI_CHOICE_CONTROLS_MODULE)
                + _external_provider_import_lines(
                    APPLICATION_CLIENT_UI_CHOICE_CONTROLS_MODULE
                )
            )
        )
    ]

    assert offenders == []


@pytest.mark.parametrize(
    "module_path",
    APPLICATION_CLIENT_WEB_LEARNING_MODULES,
    ids=lambda path: path.stem,
)
def test_client_web_learning_application_modules_stay_out_of_api_layer(
    module_path: Path,
) -> None:
    relative_path = module_path.relative_to(APP_ROOT)
    data_access_import_offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(module_path)
        if module == "app.data_access" or module.startswith("app.data_access.")
    ]
    api_boundary_offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(module_path)
                + _interface_api_import_lines(module_path)
                + _telegram_gateway_import_lines(module_path)
            )
        )
    ]
    offenders = data_access_import_offenders + api_boundary_offenders

    assert offenders == []


@pytest.mark.parametrize(
    "module_path",
    APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_MODULES,
    ids=lambda path: path.stem,
)
def test_client_web_teacher_student_application_modules_stay_out_of_api_layer(
    module_path: Path,
) -> None:
    relative_path = module_path.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(module_path)
                + _interface_api_import_lines(module_path)
                + _telegram_gateway_import_lines(module_path)
                + _external_provider_import_lines(module_path)
            )
        )
    ]

    assert offenders == []


def test_client_web_import_errors_application_module_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_WEB_IMPORT_ERRORS_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_WEB_IMPORT_ERRORS_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_WEB_IMPORT_ERRORS_MODULE)
            )
        )
    ]

    assert offenders == []


def test_client_import_notification_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_SCHEDULED_RUNTIME_IMPORT_NOTIFICATION_SERVICE_MODULE.relative_to(
        APP_ROOT
    )
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(
                    APPLICATION_SCHEDULED_RUNTIME_IMPORT_NOTIFICATION_SERVICE_MODULE
                )
                + _interface_api_import_lines(
                    APPLICATION_SCHEDULED_RUNTIME_IMPORT_NOTIFICATION_SERVICE_MODULE
                )
            )
        )
    ]

    assert offenders == []


def test_client_import_action_payload_application_module_stays_out_of_api_data_access_and_transport_layers() -> None:
    relative_path = APPLICATION_CLIENT_IMPORT_ACTION_PAYLOAD_MODULE.relative_to(APP_ROOT)
    forbidden_roots = ("app.client_api", "app.data_access")
    direct_import_offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(
            APPLICATION_CLIENT_IMPORT_ACTION_PAYLOAD_MODULE
        )
        if module in forbidden_roots
        or any(module.startswith(f"{root}.") for root in forbidden_roots)
    ]
    api_boundary_offenders = [
        f"app/{relative_path.as_posix()}:{line}: interface API/FastAPI"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_IMPORT_ACTION_PAYLOAD_MODULE)
                + _interface_api_import_lines(
                    APPLICATION_CLIENT_IMPORT_ACTION_PAYLOAD_MODULE
                )
            )
        )
    ]

    assert direct_import_offenders + api_boundary_offenders == []


def test_client_import_text_input_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_IMPORT_TEXT_INPUT_SERVICE_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_IMPORT_TEXT_INPUT_SERVICE_MODULE)
                + _interface_api_import_lines(
                    APPLICATION_CLIENT_IMPORT_TEXT_INPUT_SERVICE_MODULE
                )
            )
        )
    ]

    assert offenders == []


def test_client_import_screen_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_IMPORT_SCREEN_SERVICE_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_IMPORT_SCREEN_SERVICE_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_IMPORT_SCREEN_SERVICE_MODULE)
            )
        )
    ]

    assert offenders == []


def test_client_import_read_action_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_IMPORT_READ_ACTION_SERVICE_MODULE.relative_to(
        APP_ROOT
    )
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_IMPORT_READ_ACTION_SERVICE_MODULE)
                + _interface_api_import_lines(
                    APPLICATION_CLIENT_IMPORT_READ_ACTION_SERVICE_MODULE
                )
            )
        )
    ]

    assert offenders == []


def test_client_import_mutation_action_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_IMPORT_MUTATION_ACTION_SERVICE_MODULE.relative_to(
        APP_ROOT
    )
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(
                    APPLICATION_CLIENT_IMPORT_MUTATION_ACTION_SERVICE_MODULE
                )
                + _interface_api_import_lines(
                    APPLICATION_CLIENT_IMPORT_MUTATION_ACTION_SERVICE_MODULE
                )
            )
        )
    ]

    assert offenders == []


def test_client_bot_message_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_BOT_MESSAGE_SERVICE_MODULE.relative_to(APP_ROOT)
    data_access_import_offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(APPLICATION_CLIENT_BOT_MESSAGE_SERVICE_MODULE)
        if module == "app.data_access" or module.startswith("app.data_access.")
    ]
    api_boundary_offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_BOT_MESSAGE_SERVICE_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_BOT_MESSAGE_SERVICE_MODULE)
            )
        )
    ]
    offenders = data_access_import_offenders + api_boundary_offenders

    assert offenders == []


def test_client_admin_restore_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_ADMIN_RESTORE_SERVICE_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_ADMIN_RESTORE_SERVICE_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_ADMIN_RESTORE_SERVICE_MODULE)
            )
        )
    ]

    assert offenders == []


def test_client_text_action_application_service_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_RUNTIME_TEXT_ACTION_SERVICE_MODULE.relative_to(
        APP_ROOT
    )
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_RUNTIME_TEXT_ACTION_SERVICE_MODULE)
                + _interface_api_import_lines(
                    APPLICATION_CLIENT_RUNTIME_TEXT_ACTION_SERVICE_MODULE
                )
            )
        )
    ]

    assert offenders == []


def test_billing_services_package_facade_is_removed() -> None:
    assert not BILLING_SERVICES_PACKAGE_FACADE_MODULE.exists()


def test_monobank_provider_package_facade_is_removed() -> None:
    assert not MONOBANK_PROVIDER_PACKAGE_FACADE_MODULE.exists()


def test_app_tests_and_scripts_do_not_import_api_helpers_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.api_helpers")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_helpers_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.helpers")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_validators_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.validators")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_validation_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.validation")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_external_providers_embeddings_package_facade() -> None:
    offenders = []
    package_name = "app.external_providers.embeddings"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, package_name)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_retired_admin_dictionary_helpers() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(path, "app.admin_api.dictionary.helpers")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_user_import_helpers_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.user_import.helpers")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_admin_auth_helpers_package_facade() -> None:
    package_name = "app.admin_api.auth." "helpers"
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, package_name)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_retired_admin_dictionary_services() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(path, "app.admin_api.dictionary.services")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_retired_admin_dictionary_actions() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(path, "app.admin_api.dictionary.actions")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_retired_admin_validators() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(path, "app.admin_api.validators")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


@pytest.mark.parametrize(
    "retired_module",
    (
        "app.admin_api.users.actions",
        "app.admin_api.users.services",
        "app.admin_api.users.helpers",
        "app.admin_api.users.validators",
    ),
)
def test_app_tests_scripts_and_word_base_do_not_import_retired_admin_user_business_modules(
    retired_module: str,
) -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(path, retired_module)
            offenders.extend(f"{relative_path.as_posix()}:{line}: {retired_module}" for line in import_lines)

    assert offenders == []


@pytest.mark.parametrize(
    "retired_module",
    (
        "app.admin_api.user_dictionary.actions",
        "app.admin_api.user_dictionary.services",
    ),
)
def test_app_tests_scripts_and_word_base_do_not_import_retired_admin_user_dictionary_business_modules(
    retired_module: str,
) -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(path, retired_module)
            offenders.extend(f"{relative_path.as_posix()}:{line}: {retired_module}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_support_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.support")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_billing_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            if path == BILLING_PACKAGE_FACADE_MODULE:
                continue
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.billing")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_billing_helpers_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.billing.helpers")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_billing_providers_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.billing.providers")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_monobank_provider_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _monobank_provider_package_facade_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_security_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.security")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_word_base_do_not_import_video_sessions_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(
                path,
                "app.external_providers.video_sessions",
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_video_sessions_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.external_providers.video_sessions import GoogleCalendarMeetProvider\n"
        "import app.external_providers.video_sessions\n"
        "import app.external_providers.video_sessions as video_sessions\n"
        "from app.external_providers import video_sessions\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.external_providers.video_sessions",
    ) == [1, 2, 3, 4]


def test_video_sessions_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.external_providers.video_sessions.google_calendar_meet "
        "import GoogleCalendarMeetProvider\n"
        "import app.external_providers.video_sessions.google_calendar_meet\n"
        "import app.external_providers.video_sessions.google_calendar_meet "
        "as google_calendar_meet\n",
        encoding="utf-8",
    )

    assert (
        _package_facade_import_lines(
            module_path,
            "app.external_providers.video_sessions",
        )
        == []
    )


def test_support_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.support import DEFAULT_SUPPORT_URL\n"
        "import app.support\n"
        "import app.support as support\n"
        "from app import support\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "support" / "module.py"
    nested_module_path = app_root / "support" / "subpackage" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text("from . import runtime_settings\n", encoding="utf-8")
    nested_module_path.write_text("from .. import runtime_settings\n", encoding="utf-8")

    assert _package_facade_import_lines(module_path, "app.support") == [1, 2, 3, 4]
    assert _package_facade_import_lines(root_module_path, "app.support") == [1]
    assert _package_facade_import_lines(nested_module_path, "app.support") == [1]


def test_support_package_facade_import_detection_allows_runtime_settings_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.support.runtime_settings import DEFAULT_SUPPORT_URL\n"
        "import app.support.runtime_settings\n"
        "import app.support.runtime_settings as support_runtime_settings\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.support") == []


def test_billing_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing import DEFAULT_BILLING_RUNTIME_SETTINGS\n"
        "import app.billing\n"
        "import app.billing as billing\n"
        "from app import billing\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.billing") == [1, 2, 3, 4]


def test_billing_package_facade_import_detection_allows_runtime_settings_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.runtime_settings import DEFAULT_BILLING_RUNTIME_SETTINGS\n"
        "import app.billing.runtime_settings\n"
        "import app.billing.runtime_settings as billing_runtime_settings\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.billing") == []


def test_billing_helpers_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.helpers import amounts\n"
        "import app.billing.helpers\n"
        "import app.billing.helpers as billing_helpers\n"
        "from app.billing import helpers\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.billing.helpers") == [
        1,
        2,
        3,
        4,
    ]


def test_billing_helpers_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.helpers.amounts import kopecks_to_major_units\n"
        "from app.billing.helpers.receipt_notifications import receipt_summary\n"
        "import app.billing.helpers.amounts\n"
        "import app.billing.helpers.receipt_notifications as receipt_notifications\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.billing.helpers") == []


def test_billing_providers_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers import monobank\n"
        "import app.billing.providers\n"
        "import app.billing.providers as billing_providers\n"
        "from app.billing import providers\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.billing.providers") == [
        1,
        2,
        3,
        4,
    ]


def test_billing_providers_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank.factory import build_monobank_client\n"
        "from app.billing.providers.monobank.provider import MonobankCheckoutProvider\n"
        "import app.billing.providers.monobank.factory\n"
        "import app.billing.providers.monobank.provider as monobank_provider\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.billing.providers") == []


def test_monobank_provider_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank import build_monobank_client\n"
        "from app.billing.providers.monobank import client\n"
        "import app.billing.providers.monobank\n"
        "import app.billing.providers.monobank as monobank_provider\n"
        "from app.billing.providers import monobank\n",
        encoding="utf-8",
    )

    assert _monobank_provider_package_facade_import_lines(module_path) == [
        1,
        2,
        3,
        4,
        5,
    ]


def test_monobank_provider_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank.factory import build_monobank_client\n"
        "from app.billing.providers.monobank.provider import MonobankCheckoutProvider\n"
        "from app.billing.providers.monobank.signature "
        "import verify_monobank_webhook_signature\n"
        "from app.billing.providers.monobank.client import MonobankClient\n"
        "from app.billing.providers.monobank.audit import MonobankAuditContext\n"
        "import app.billing.providers.monobank.factory\n"
        "import app.billing.providers.monobank.provider as monobank_provider\n"
        "import app.billing.providers.monobank.signature as monobank_signature\n"
        "import app.billing.providers.monobank.client as monobank_client\n"
        "import app.billing.providers.monobank.audit as monobank_audit\n",
        encoding="utf-8",
    )

    assert _monobank_provider_package_facade_import_lines(module_path) == []


def test_security_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.security import TokenCipher\n"
        "import app.security\n"
        "import app.security as security\n"
        "from app import security\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.security") == [1, 2, 3, 4]


def test_security_package_facade_import_detection_allows_token_cipher_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.security.token_cipher import TokenCipher\n"
        "import app.security.token_cipher\n"
        "import app.security.token_cipher as token_cipher\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.security") == []


def test_app_tests_and_scripts_do_not_import_removed_admin_entity_services_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.entity.services"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(path, forbidden_module)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_removed_admin_exercise_text_services() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                "app.admin_api.exercise_texts.services",
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_composition_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.composition")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def _application_package_facade_import_offenders(
    package_name: str,
    facade_module: Path,
) -> list[str]:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            if path == facade_module:
                continue
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, package_name)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)
    return offenders


def test_app_tests_scripts_and_word_base_do_not_import_application_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application",
        APPLICATION_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_admin_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.admin",
        APPLICATION_ADMIN_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_client_runtime_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.client_runtime",
        APPLICATION_CLIENT_RUNTIME_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_client_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.client",
        APPLICATION_CLIENT_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_client_learning_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.client_learning",
        APPLICATION_CLIENT_LEARNING_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_client_reminders_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.client_reminders",
        APPLICATION_CLIENT_REMINDERS_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_client_ui_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.client_ui",
        APPLICATION_CLIENT_UI_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_client_web_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.client_web",
        APPLICATION_CLIENT_WEB_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_client_import_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.client_import",
        APPLICATION_CLIENT_IMPORT_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_application_scheduled_runtime_package_facade() -> None:
    offenders = _application_package_facade_import_offenders(
        "app.application.scheduled_runtime",
        APPLICATION_SCHEDULED_RUNTIME_PACKAGE_FACADE_MODULE,
    )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_serialization_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(
                path,
                "app.serialization",
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_reference_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.reference")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_acl_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.acl")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_external_providers_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.external_providers")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_subscriptions_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.subscriptions")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


@pytest.mark.parametrize(
    "package_name",
    [package_name for _, package_name in APPLICATION_PACKAGE_FACADES],
)
def test_application_package_facade_import_detection_catches_broad_absolute_imports(
    package_name: str,
    tmp_path: Path,
) -> None:
    parent_module, _, package_basename = package_name.rpartition(".")
    module_path = tmp_path / "module.py"
    module_path.write_text(
        f"from {package_name} import RetiredFacadeExport\n"
        f"import {package_name}\n"
        f"import {package_name} as package_facade\n"
        f"from {parent_module} import {package_basename}\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, package_name) == [1, 2, 3, 4]


@pytest.mark.parametrize(
    ("package_name", "submodule_name"),
    [
        ("app.application", "dispatch_lock"),
        ("app.application.admin", "permissions"),
        ("app.application.client", "bot_message_service"),
        ("app.application.client_import", "action_payload"),
        ("app.application.client_learning", "action_payload"),
        ("app.application.client_reminders", "action_payload"),
        ("app.application.client_runtime", "input_service"),
        ("app.application.client_ui", "choice_controls"),
        ("app.application.client_web", "settings_service"),
        ("app.application.scheduled_runtime", "import_notification_service"),
    ],
)
def test_application_package_facade_import_detection_allows_concrete_submodule_imports(
    package_name: str,
    submodule_name: str,
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        f"from {package_name}.{submodule_name} import DirectDependency\n"
        f"import {package_name}.{submodule_name} as direct_dependency\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, package_name) == []


def test_application_client_runtime_package_facade_import_detection_catches_broad_absolute_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.client_runtime import ClientRuntimeInputService\n"
        "import app.application.client_runtime\n"
        "import app.application.client_runtime as client_runtime\n"
        "from app.application import client_runtime\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.application.client_runtime",
    ) == [1, 2, 3, 4]


def test_application_scheduled_runtime_package_facade_import_detection_catches_broad_absolute_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.scheduled_runtime import BillingNotificationRuntimeService\n"
        "import app.application.scheduled_runtime\n"
        "import app.application.scheduled_runtime as scheduled_runtime\n"
        "from app.application import scheduled_runtime\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.application.scheduled_runtime",
    ) == [1, 2, 3, 4]


def test_serialization_package_facade_import_detection_catches_broad_absolute_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.serialization import normalize_json_datetimes\n"
        "import app.serialization\n"
        "import app.serialization as serialization\n"
        "from app import serialization\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.serialization",
    ) == [1, 2, 3, 4]


def test_reference_package_facade_import_detection_catches_broad_absolute_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app." "reference import AppReference\n"
        "import app." "reference\n"
        "import app." "reference as reference\n"
        "from app import " "reference\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.reference") == [1, 2, 3, 4]


def test_acl_package_facade_import_detection_catches_broad_absolute_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.acl import AclProcessor\n"
        "import app.acl\n"
        "import app.acl as acl\n"
        "from app import acl\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.acl") == [1, 2, 3, 4]


def test_external_providers_package_facade_import_detection_catches_broad_absolute_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.external_providers import user_import_openai\n"
        "import app.external_providers\n"
        "import app.external_providers as external_providers\n"
        "from app import external_providers\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.external_providers") == [
        1,
        2,
        3,
        4,
    ]


def test_subscriptions_package_facade_import_detection_catches_broad_absolute_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.subscriptions import SubscriptionMaintenanceService\n"
        "import app.subscriptions\n"
        "import app.subscriptions as subscriptions\n"
        "from app import subscriptions\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.subscriptions") == [
        1,
        2,
        3,
        4,
    ]


def test_application_client_runtime_package_facade_import_detection_catches_relative_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    package_module_path = app_root / "application" / "client_runtime" / "module.py"
    nested_module_path = (
        app_root / "application" / "client_runtime" / "subpackage" / "module.py"
    )
    application_module_path = app_root / "application" / "module.py"
    package_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    package_module_path.write_text(
        "from . import ClientRuntimeInputService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import ClientRuntimeInputService\n",
        encoding="utf-8",
    )
    application_module_path.write_text(
        "from . import client_runtime\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        package_module_path,
        "app.application.client_runtime",
    ) == [1]
    assert _package_facade_import_lines(
        nested_module_path,
        "app.application.client_runtime",
    ) == [1]
    assert _package_facade_import_lines(
        application_module_path,
        "app.application.client_runtime",
    ) == [1]


def test_application_scheduled_runtime_package_facade_import_detection_catches_relative_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    package_module_path = app_root / "application" / "scheduled_runtime" / "module.py"
    nested_module_path = (
        app_root / "application" / "scheduled_runtime" / "subpackage" / "module.py"
    )
    application_module_path = app_root / "application" / "module.py"
    package_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    package_module_path.write_text(
        "from . import BillingNotificationRuntimeService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import BillingNotificationRuntimeService\n",
        encoding="utf-8",
    )
    application_module_path.write_text(
        "from . import scheduled_runtime\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        package_module_path,
        "app.application.scheduled_runtime",
    ) == [1]
    assert _package_facade_import_lines(
        nested_module_path,
        "app.application.scheduled_runtime",
    ) == [1]
    assert _package_facade_import_lines(
        application_module_path,
        "app.application.scheduled_runtime",
    ) == [1]


def test_serialization_package_facade_import_detection_catches_relative_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    package_module_path = app_root / "serialization" / "module.py"
    nested_module_path = app_root / "serialization" / "subpackage" / "module.py"
    app_module_path = app_root / "module.py"
    package_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    package_module_path.write_text(
        "from . import normalize_json_datetimes\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import normalize_json_datetimes\n",
        encoding="utf-8",
    )
    app_module_path.write_text(
        "from . import serialization\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        package_module_path,
        "app.serialization",
    ) == [1]
    assert _package_facade_import_lines(
        nested_module_path,
        "app.serialization",
    ) == [1]
    assert _package_facade_import_lines(
        app_module_path,
        "app.serialization",
    ) == [1]


def test_reference_package_facade_import_detection_catches_relative_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    package_module_path = app_root / "reference" / "module.py"
    nested_module_path = app_root / "reference" / "subpackage" / "module.py"
    app_module_path = app_root / "module.py"
    package_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    package_module_path.write_text(
        "from . import AppReference\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import AppReference\n",
        encoding="utf-8",
    )
    app_module_path.write_text(
        "from . import reference\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(package_module_path, "app.reference") == [1]
    assert _package_facade_import_lines(nested_module_path, "app.reference") == [1]
    assert _package_facade_import_lines(app_module_path, "app.reference") == [1]


def test_acl_package_facade_import_detection_catches_relative_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    package_module_path = app_root / "acl" / "module.py"
    nested_module_path = app_root / "acl" / "subpackage" / "module.py"
    app_module_path = app_root / "module.py"
    package_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    package_module_path.write_text(
        "from . import AclProcessor\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import AclProcessor\n",
        encoding="utf-8",
    )
    app_module_path.write_text(
        "from . import acl\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(package_module_path, "app.acl") == [1]
    assert _package_facade_import_lines(nested_module_path, "app.acl") == [1]
    assert _package_facade_import_lines(app_module_path, "app.acl") == [1]


def test_external_providers_package_facade_import_detection_catches_relative_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    package_module_path = app_root / "external_providers" / "module.py"
    nested_module_path = app_root / "external_providers" / "subpackage" / "module.py"
    app_module_path = app_root / "module.py"
    package_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    package_module_path.write_text(
        "from . import user_import_openai\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import user_import_openai\n",
        encoding="utf-8",
    )
    app_module_path.write_text(
        "from . import external_providers\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(package_module_path, "app.external_providers") == [
        1
    ]
    assert _package_facade_import_lines(nested_module_path, "app.external_providers") == [
        1
    ]
    assert _package_facade_import_lines(app_module_path, "app.external_providers") == [1]


def test_subscriptions_package_facade_import_detection_catches_relative_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    package_module_path = app_root / "subscriptions" / "module.py"
    nested_module_path = app_root / "subscriptions" / "subpackage" / "module.py"
    app_module_path = app_root / "module.py"
    package_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    package_module_path.write_text(
        "from . import SubscriptionMaintenanceService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import SubscriptionMaintenanceService\n",
        encoding="utf-8",
    )
    app_module_path.write_text(
        "from . import subscriptions\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(package_module_path, "app.subscriptions") == [1]
    assert _package_facade_import_lines(nested_module_path, "app.subscriptions") == [1]
    assert _package_facade_import_lines(app_module_path, "app.subscriptions") == [1]


def test_application_client_runtime_package_facade_import_detection_allows_concrete_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.client_runtime.input_service import "
        "ClientRuntimeInputService\n"
        "import app.application.client_runtime.input_service as input_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    relative_module_path = app_root / "application" / "client_runtime" / "module.py"
    relative_module_path.parent.mkdir(parents=True)
    relative_module_path.write_text(
        "from .input_service import ClientRuntimeInputService\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.application.client_runtime",
    ) == []
    assert _package_facade_import_lines(
        relative_module_path,
        "app.application.client_runtime",
    ) == []


def test_application_scheduled_runtime_package_facade_import_detection_allows_concrete_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.scheduled_runtime.billing_notification_service import "
        "BillingNotificationRuntimeService\n"
        "from app.application.scheduled_runtime.import_notification_service import "
        "ClientImportNotificationService\n"
        "import app.application.scheduled_runtime.billing_reconciliation_service "
        "as reconciliation_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    relative_module_path = app_root / "application" / "scheduled_runtime" / "module.py"
    relative_module_path.parent.mkdir(parents=True)
    relative_module_path.write_text(
        "from .subscription_maintenance_service import "
        "SubscriptionMaintenanceRuntimeService\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.application.scheduled_runtime",
    ) == []
    assert _package_facade_import_lines(
        relative_module_path,
        "app.application.scheduled_runtime",
    ) == []


def test_serialization_package_facade_import_detection_allows_concrete_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.serialization.json_datetimes import normalize_json_datetimes\n"
        "import app.serialization.json_datetimes as json_datetimes\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    relative_module_path = app_root / "serialization" / "module.py"
    relative_module_path.parent.mkdir(parents=True)
    relative_module_path.write_text(
        "from .json_datetimes import normalize_json_datetimes\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.serialization",
    ) == []
    assert _package_facade_import_lines(
        relative_module_path,
        "app.serialization",
    ) == []


def test_reference_package_facade_import_detection_allows_concrete_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.reference.service import AppReference\n"
        "from app.reference.learning_flow import READY_STAGES\n"
        "from app.reference.scheduling import HOURS_BY_PERIOD\n"
        "from app.reference.labels import format_category_labels\n"
        "import app.reference.service as reference_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    relative_module_path = app_root / "reference" / "module.py"
    relative_module_path.parent.mkdir(parents=True)
    relative_module_path.write_text(
        "from .service import AppReference\n"
        "from .learning_flow import READY_STAGES\n"
        "from .scheduling import HOURS_BY_PERIOD\n"
        "from .labels import format_category_labels\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.reference") == []
    assert _package_facade_import_lines(relative_module_path, "app.reference") == []


def test_acl_package_facade_import_detection_allows_concrete_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.acl.processor import AclProcessor\n"
        "import app.acl.processor as acl_processor\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    relative_module_path = app_root / "acl" / "module.py"
    relative_module_path.parent.mkdir(parents=True)
    relative_module_path.write_text(
        "from .processor import AclProcessor\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.acl") == []
    assert _package_facade_import_lines(relative_module_path, "app.acl") == []


def test_external_providers_package_facade_import_detection_allows_concrete_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.external_providers.user_import_openai import DEFAULT_OPENAI_API_URL\n"
        "from app.external_providers.user_import_google_tts import synthesize_google_tts\n"
        "import app.external_providers.user_import_openai as user_import_openai\n"
        "import app.external_providers.user_import_google_tts as user_import_google_tts\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    relative_module_path = app_root / "external_providers" / "module.py"
    relative_module_path.parent.mkdir(parents=True)
    relative_module_path.write_text(
        "from .user_import_openai import DEFAULT_OPENAI_API_URL\n"
        "from .user_import_google_tts import synthesize_google_tts\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.external_providers") == []
    assert _package_facade_import_lines(relative_module_path, "app.external_providers") == []


def test_subscriptions_package_facade_import_detection_allows_concrete_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.subscriptions.maintenance import SubscriptionMaintenanceService\n"
        "from app.subscriptions.user_entitlements import UserEntitlementResolver\n"
        "import app.subscriptions.maintenance as subscription_maintenance\n"
        "import app.subscriptions.user_entitlements as user_entitlements\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    relative_module_path = app_root / "subscriptions" / "module.py"
    relative_module_path.parent.mkdir(parents=True)
    relative_module_path.write_text(
        "from .maintenance import SubscriptionMaintenanceService\n"
        "from .user_entitlements import UserEntitlementResolver\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.subscriptions") == []
    assert _package_facade_import_lines(relative_module_path, "app.subscriptions") == []


def test_app_tests_scripts_and_word_base_do_not_import_admin_bootstrap_services_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(
                path,
                "app.admin_api.bootstrap.services",
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_admin_bootstrap_api_service_module() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _admin_bootstrap_api_service_module_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_removed_admin_auth_modules() -> None:
    offenders = []
    forbidden_modules = (
        "app.admin_api.auth.services",
        "app.admin_api.auth.helpers",
        "app.admin_api.auth.validators",
        "app.admin_api.auth.errors",
        "app.admin_api.auth.gateways",
    )
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            for forbidden_module in forbidden_modules:
                import_lines = _concrete_module_import_lines(path, forbidden_module)
                offenders.extend(
                    f"{relative_path.as_posix()}:{line}: {forbidden_module}"
                    for line in import_lines
                )

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_removed_admin_ai_usage_services_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.ai_usage.services"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                forbidden_module,
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_retired_admin_ai_usage_api_modules() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _retired_admin_ai_usage_facade_action_otp_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_retired_admin_settings_api_modules() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _retired_admin_settings_facade_action_otp_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_removed_admin_dashboard_services_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.dashboard.services"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                forbidden_module,
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_removed_admin_billing_services_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.billing.services"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                forbidden_module,
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_retired_admin_billing_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _retired_admin_billing_facade_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_removed_admin_settings_services_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.settings.services"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                forbidden_module,
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_removed_admin_settings_validators_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.settings.validators"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                forbidden_module,
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_removed_admin_exercise_text_validators() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                "app.admin_api.exercise_texts.validators",
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_removed_admin_import_services_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.imports.services"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                forbidden_module,
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_retired_admin_import_facades() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _retired_admin_import_facade_helper_validator_import_lines(
                path
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_removed_admin_log_services_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.logs.services"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                forbidden_module,
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_removed_admin_read_services_modules() -> None:
    offenders = []
    forbidden_module = "app.admin_api.read.services"
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(
                path,
                forbidden_module,
            )
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_retired_admin_top_level_package_facades() -> None:
    offenders = []
    marker_paths = {
        module_path
        for module_path, *_ in RETIRED_ADMIN_TOP_LEVEL_PACKAGE_FACADES
    }
    package_names = [
        package_name
        for _, package_name, *_ in RETIRED_ADMIN_TOP_LEVEL_PACKAGE_FACADES
    ]
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            if path in marker_paths:
                continue
            relative_path = path.relative_to(APP_ROOT.parent)
            for package_name in package_names:
                import_lines = _package_facade_import_lines(path, package_name)
                offenders.extend(
                    f"{relative_path.as_posix()}:{line}: {package_name}"
                    for line in import_lines
                )

    assert offenders == []


def test_app_tests_scripts_and_word_base_do_not_import_retired_admin_helpers_modules() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _concrete_module_import_lines(path, RETIRED_ADMIN_HELPERS_PACKAGE_NAME)
            offenders.extend(
                f"{relative_path.as_posix()}:{line}: {RETIRED_ADMIN_HELPERS_PACKAGE_NAME}"
                for line in import_lines
            )

    assert offenders == []


def test_app_tests_and_scripts_do_not_import_billing_services_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _package_facade_import_lines(path, "app.billing.services")
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_api_helpers_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.api_helpers import build_audio_response\n"
        "from app.api_helpers import build_audio_response as build_audio\n"
        "import app.api_helpers\n"
        "import app.api_helpers as api_helpers\n"
        "from app import api_helpers\n"
        "from app import api_helpers as helpers\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "client_api" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text("from .api_helpers import build_audio_response\n", encoding="utf-8")
    nested_module_path.write_text("from ..api_helpers import build_audio_response\n", encoding="utf-8")

    assert _package_facade_import_lines(module_path, "app.api_helpers") == [1, 2, 3, 4, 5, 6]
    assert _package_facade_import_lines(root_module_path, "app.api_helpers") == [1]
    assert _package_facade_import_lines(nested_module_path, "app.api_helpers") == [1]


def test_api_helpers_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.api_helpers.audio_response import build_audio_response\n"
        "from app.api_helpers.request_validation import ensure_allowed_values\n"
        "import app.api_helpers.audio_response\n"
        "import app.api_helpers.request_validation as request_validation\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.api_helpers") == []


def test_helpers_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.helpers import external_error_text\n"
        "from app.helpers import external_error_text as error_text_helpers\n"
        "import app.helpers\n"
        "import app.helpers as helpers\n"
        "from app import helpers\n"
        "from app import helpers as helper_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "user_import" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .helpers import external_error_text\n"
        "from . import helpers\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..helpers import external_error_text\n"
        "from .. import helpers\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.helpers") == [1, 2, 3, 4, 5, 6]
    assert _package_facade_import_lines(root_module_path, "app.helpers") == [1, 2]
    assert _package_facade_import_lines(nested_module_path, "app.helpers") == [1, 2]


def test_helpers_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.helpers.external_error_text import sanitize_external_error_text\n"
        "import app.helpers.external_error_text\n"
        "import app.helpers.external_error_text as external_error_text\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    helpers_module_path = app_root / "helpers" / "module.py"
    nested_module_path = app_root / "user_import" / "module.py"
    helpers_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .helpers.external_error_text import sanitize_external_error_text\n",
        encoding="utf-8",
    )
    helpers_module_path.write_text(
        "from .external_error_text import sanitize_external_error_text\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..helpers.external_error_text import sanitize_external_error_text\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.helpers") == []
    assert _package_facade_import_lines(root_module_path, "app.helpers") == []
    assert _package_facade_import_lines(helpers_module_path, "app.helpers") == []
    assert _package_facade_import_lines(nested_module_path, "app.helpers") == []


def test_validators_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.validators import user_import_provider_results\n"
        "from app.validators import user_import_provider_results as provider_results\n"
        "import app.validators\n"
        "import app.validators as validators\n"
        "from app import validators\n"
        "from app import validators as validators_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "user_import" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .validators import user_import_provider_results\n"
        "from . import validators\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..validators import user_import_provider_results\n"
        "from .. import validators\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.validators") == [1, 2, 3, 4, 5, 6]
    assert _package_facade_import_lines(root_module_path, "app.validators") == [1, 2]
    assert _package_facade_import_lines(nested_module_path, "app.validators") == [1, 2]


def test_validators_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.validators.user_import_provider_results import AIImportValidationResult\n"
        "import app.validators.user_import_provider_results\n"
        "import app.validators.user_import_provider_results as provider_results\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    validators_module_path = app_root / "validators" / "module.py"
    nested_module_path = app_root / "user_import" / "module.py"
    validators_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .validators.user_import_provider_results import AIImportValidationResult\n",
        encoding="utf-8",
    )
    validators_module_path.write_text(
        "from .user_import_provider_results import AIImportValidationResult\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..validators.user_import_provider_results import AIImportValidationResult\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.validators") == []
    assert _package_facade_import_lines(root_module_path, "app.validators") == []
    assert _package_facade_import_lines(validators_module_path, "app.validators") == []
    assert _package_facade_import_lines(nested_module_path, "app.validators") == []


def test_validation_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.validation import request_values\n"
        "from app.validation import request_values as request_validation\n"
        "import app.validation\n"
        "import app.validation as validation\n"
        "from app import validation\n"
        "from app import validation as validation_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "api_helpers" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .validation import request_values\n"
        "from . import validation\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..validation import request_values\n"
        "from .. import validation\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.validation") == [1, 2, 3, 4, 5, 6]
    assert _package_facade_import_lines(root_module_path, "app.validation") == [1, 2]
    assert _package_facade_import_lines(nested_module_path, "app.validation") == [1, 2]


def test_validation_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.validation.request_values import ensure_allowed_value\n"
        "import app.validation.request_values\n"
        "import app.validation.request_values as request_values\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    validation_module_path = app_root / "validation" / "module.py"
    nested_module_path = app_root / "api_helpers" / "module.py"
    validation_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .validation.request_values import ensure_allowed_value\n",
        encoding="utf-8",
    )
    validation_module_path.write_text(
        "from .request_values import ensure_allowed_value\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..validation.request_values import ensure_allowed_value\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.validation") == []
    assert _package_facade_import_lines(root_module_path, "app.validation") == []
    assert _package_facade_import_lines(validation_module_path, "app.validation") == []
    assert _package_facade_import_lines(nested_module_path, "app.validation") == []


def test_external_providers_embeddings_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_name = "app.external_providers.embeddings"
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.external_providers.embeddings import local_sentence_transformers\n"
        "from app.external_providers.embeddings import local_sentence_transformers as lst\n"
        "import app.external_providers.embeddings\n"
        "import app.external_providers.embeddings as embeddings\n"
        "from app.external_providers import embeddings\n"
        "from app.external_providers import embeddings as embedding_providers\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    external_providers_module_path = app_root / "external_providers" / "module.py"
    nested_module_path = app_root / "external_providers" / "adapters" / "module.py"
    external_providers_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    external_providers_module_path.write_text(
        "from .embeddings import local_sentence_transformers\n"
        "from . import embeddings\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..embeddings import local_sentence_transformers\n"
        "from .. import embeddings\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, package_name) == [1, 2, 3, 4, 5, 6]
    assert _package_facade_import_lines(external_providers_module_path, package_name) == [1, 2]
    assert _package_facade_import_lines(nested_module_path, package_name) == [1, 2]


def test_external_providers_embeddings_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_name = "app.external_providers.embeddings"
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.external_providers.embeddings.local_sentence_transformers import build_embedding\n"
        "import app.external_providers.embeddings.local_sentence_transformers\n"
        "import app.external_providers.embeddings.local_sentence_transformers as lst\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    external_providers_module_path = app_root / "external_providers" / "module.py"
    embeddings_module_path = app_root / "external_providers" / "embeddings" / "module.py"
    nested_module_path = app_root / "external_providers" / "adapters" / "module.py"
    embeddings_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    external_providers_module_path.write_text(
        "from .embeddings.local_sentence_transformers import build_embedding\n",
        encoding="utf-8",
    )
    embeddings_module_path.write_text(
        "from .local_sentence_transformers import build_embedding\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..embeddings.local_sentence_transformers import build_embedding\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, package_name) == []
    assert _package_facade_import_lines(external_providers_module_path, package_name) == []
    assert _package_facade_import_lines(embeddings_module_path, package_name) == []
    assert _package_facade_import_lines(nested_module_path, package_name) == []


def test_composition_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.composition import configure_learning_service\n"
        "from app.composition import configure_learning_service as configure_service\n"
        "from app.composition import root\n"
        "import app.composition\n"
        "import app.composition as composition\n"
        "from app import composition\n"
        "from app import composition as composition_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    composition_module_path = app_root / "composition" / "module.py"
    nested_module_path = app_root / "composition" / "subpackage" / "module.py"
    composition_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .composition import configure_learning_service\n"
        "from . import composition as composition_package\n",
        encoding="utf-8",
    )
    composition_module_path.write_text(
        "from . import configure_learning_service\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import configure_learning_service\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.composition",
    ) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert _package_facade_import_lines(
        root_module_path,
        "app.composition",
    ) == [1, 2]
    assert _package_facade_import_lines(
        composition_module_path,
        "app.composition",
    ) == [1]
    assert _package_facade_import_lines(
        nested_module_path,
        "app.composition",
    ) == [1]


def test_composition_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.composition.root import build_learning_runtime\n"
        "import app.composition.root as composition_root\n"
        "from app.composition.client_reminders import configure_client_reminder_runtime\n"
        "import app.composition.client_reminders as client_reminders\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    composition_module_path = app_root / "composition" / "module.py"
    nested_module_path = app_root / "composition" / "subpackage" / "module.py"
    composition_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    composition_module_path.write_text("from .root import build_learning_runtime\n", encoding="utf-8")
    nested_module_path.write_text(
        "from ..root import build_learning_runtime\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.composition") == []
    assert _package_facade_import_lines(
        composition_module_path,
        "app.composition",
    ) == []
    assert _package_facade_import_lines(
        nested_module_path,
        "app.composition",
    ) == []


def test_removed_admin_log_services_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    removed_admin_log_services_package = "app.admin_api.logs.services"
    admin_log_package = "app.admin_api.logs"
    module_path.write_text(
        f"from {removed_admin_log_services_package} import AdminLogReadService\n"
        f"from {removed_admin_log_services_package} import AdminLogReadService as LogReadService\n"
        f"from {removed_admin_log_services_package}.errors import AdminLogReadError\n"
        f"from {removed_admin_log_services_package}.read_service import AdminLogReadService\n"
        f"import {removed_admin_log_services_package}\n"
        f"import {removed_admin_log_services_package} as log_services\n"
        f"import {removed_admin_log_services_package}.errors as log_errors\n"
        f"import {removed_admin_log_services_package}.read_service as log_read_service\n"
        f"from {admin_log_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    logs_module_path = app_root / "admin_api" / "logs" / "module.py"
    nested_module_path = app_root / "admin_api" / "logs" / "routes" / "module.py"
    services_module_path = app_root / "admin_api" / "logs" / "services" / "module.py"
    logs_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    logs_module_path.write_text(
        "from .services import AdminLogReadService\n"
        "from .services.errors import AdminLogReadError\n"
        "from .services.read_service import AdminLogReadService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminLogReadService\n"
        "from ..services.errors import AdminLogReadError\n"
        "from ..services.read_service import AdminLogReadService\n"
        "from .. import services\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from . import errors\n"
        "from . import read_service\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.logs.services",
    ) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert _concrete_module_import_lines(
        logs_module_path,
        "app.admin_api.logs.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.logs.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.logs.services",
    ) == [1, 2]


def test_removed_admin_log_services_import_detection_ignores_application_logs_modules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.admin.logs.errors import AdminLogReadError\n"
        "from app.application.admin.logs.read_service import AdminLogReadService\n"
        "import app.application.admin.logs.errors as log_errors\n"
        "import app.application.admin.logs.read_service as log_read_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    logs_module_path = app_root / "admin_api" / "logs" / "module.py"
    nested_module_path = app_root / "admin_api" / "logs" / "routes" / "module.py"
    services_module_path = app_root / "admin_api" / "logs" / "services" / "module.py"
    logs_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    logs_module_path.write_text(
        "from app.application.admin.logs.errors import AdminLogReadError\n"
        "from app.application.admin.logs.read_service import AdminLogReadService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from app.application.admin.logs.errors import AdminLogReadError\n"
        "from app.application.admin.logs.read_service import AdminLogReadService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from app.application.admin.logs.errors import AdminLogReadError\n"
        "from app.application.admin.logs.read_service import AdminLogReadService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.logs.services",
    ) == []
    assert _concrete_module_import_lines(
        logs_module_path,
        "app.admin_api.logs.services",
    ) == []
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.logs.services",
    ) == []
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.logs.services",
    ) == []


def test_removed_admin_bootstrap_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_bootstrap_package = "app.admin_api.bootstrap"
    module_path.write_text(
        f"from {admin_bootstrap_package} import AdminBootstrapService\n"
        f"from {admin_bootstrap_package} import services\n"
        f"import {admin_bootstrap_package}\n"
        f"import {admin_bootstrap_package} as bootstrap\n"
        "from app.admin_api import bootstrap\n"
        "from app.admin_api import bootstrap as admin_bootstrap\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    parent_module_path = app_root / "admin_api" / "module.py"
    bootstrap_module_path = app_root / "admin_api" / "bootstrap" / "module.py"
    nested_module_path = app_root / "admin_api" / "bootstrap" / "flows" / "module.py"
    parent_module_path.parent.mkdir(parents=True)
    bootstrap_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    parent_module_path.write_text("from . import bootstrap\n", encoding="utf-8")
    bootstrap_module_path.write_text("from . import services\n", encoding="utf-8")
    nested_module_path.write_text("from .. import services\n", encoding="utf-8")

    assert _package_facade_import_lines(module_path, "app.admin_api.bootstrap") == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert _package_facade_import_lines(
        parent_module_path,
        "app.admin_api.bootstrap",
    ) == [1]
    assert _package_facade_import_lines(
        bootstrap_module_path,
        "app.admin_api.bootstrap",
    ) == [1]
    assert _package_facade_import_lines(
        nested_module_path,
        "app.admin_api.bootstrap",
    ) == [1]


def test_removed_admin_bootstrap_package_facade_import_detection_allows_router_and_application_service_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.bootstrap.router import build_bootstrap_router\n"
        "from app.application.admin.bootstrap_service import AdminBootstrapService\n"
        "import app.admin_api.bootstrap.router as bootstrap_router\n"
        "import app.application.admin.bootstrap_service as bootstrap_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    bootstrap_module_path = app_root / "admin_api" / "bootstrap" / "module.py"
    nested_module_path = app_root / "admin_api" / "bootstrap" / "flows" / "module.py"
    bootstrap_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    bootstrap_module_path.write_text(
        "from .router import build_bootstrap_router\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..router import build_bootstrap_router\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.admin_api.bootstrap") == []
    assert _package_facade_import_lines(
        bootstrap_module_path,
        "app.admin_api.bootstrap",
    ) == []
    assert _package_facade_import_lines(
        nested_module_path,
        "app.admin_api.bootstrap",
    ) == []


def test_admin_bootstrap_services_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_bootstrap_services_package = "app.admin_api.bootstrap.services"
    admin_bootstrap_package = "app.admin_api.bootstrap"
    module_path.write_text(
        f"from {admin_bootstrap_services_package} import AdminBootstrapService\n"
        f"from {admin_bootstrap_services_package} import AdminBootstrapService as BootstrapService\n"
        f"import {admin_bootstrap_services_package}\n"
        f"import {admin_bootstrap_services_package} as bootstrap_services\n"
        f"from {admin_bootstrap_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    bootstrap_module_path = app_root / "admin_api" / "bootstrap" / "module.py"
    nested_module_path = app_root / "admin_api" / "bootstrap" / "flows" / "module.py"
    bootstrap_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    bootstrap_module_path.write_text(
        "from .services import AdminBootstrapService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminBootstrapService\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.admin_api.bootstrap.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _package_facade_import_lines(
        bootstrap_module_path,
        "app.admin_api.bootstrap.services",
    ) == [1, 2]
    assert _package_facade_import_lines(
        nested_module_path,
        "app.admin_api.bootstrap.services",
    ) == [1, 2]


def test_admin_bootstrap_services_package_facade_import_detection_allows_application_service_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.admin.bootstrap_service import AdminBootstrapService\n"
        "import app.application.admin.bootstrap_service as bootstrap_service\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(
        module_path,
        "app.admin_api.bootstrap.services",
    ) == []


def test_admin_bootstrap_api_service_module_import_detection_catches_old_module_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.bootstrap.services.bootstrap_service import AdminBootstrapService\n"
        "import app.admin_api.bootstrap.services.bootstrap_service as bootstrap_service\n"
        "from app.admin_api.bootstrap.services import bootstrap_service\n"
        "from app.admin_api.bootstrap.services import bootstrap_service as bootstrap_module\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    bootstrap_module_path = app_root / "admin_api" / "bootstrap" / "module.py"
    bootstrap_nested_module_path = app_root / "admin_api" / "bootstrap" / "flows" / "module.py"
    services_module_path = app_root / "admin_api" / "bootstrap" / "services" / "module.py"
    services_nested_module_path = app_root / "admin_api" / "bootstrap" / "services" / "nested" / "module.py"
    bootstrap_module_path.parent.mkdir(parents=True)
    bootstrap_nested_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    services_nested_module_path.parent.mkdir(parents=True)
    bootstrap_module_path.write_text(
        "from .services.bootstrap_service import AdminBootstrapService\n"
        "from .services import bootstrap_service\n",
        encoding="utf-8",
    )
    bootstrap_nested_module_path.write_text(
        "from ..services.bootstrap_service import AdminBootstrapService\n"
        "from ..services import bootstrap_service\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .bootstrap_service import AdminBootstrapService\n"
        "from . import bootstrap_service\n",
        encoding="utf-8",
    )
    services_nested_module_path.write_text(
        "from ..bootstrap_service import AdminBootstrapService\n"
        "from .. import bootstrap_service\n",
        encoding="utf-8",
    )

    assert _admin_bootstrap_api_service_module_import_lines(module_path) == [1, 2, 3, 4]
    assert _admin_bootstrap_api_service_module_import_lines(bootstrap_module_path) == [1, 2]
    assert _admin_bootstrap_api_service_module_import_lines(bootstrap_nested_module_path) == [1, 2]
    assert _admin_bootstrap_api_service_module_import_lines(services_module_path) == [1, 2]
    assert _admin_bootstrap_api_service_module_import_lines(services_nested_module_path) == [1, 2]


def test_admin_bootstrap_api_service_module_import_detection_allows_application_service_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.admin.bootstrap_service import AdminBootstrapService\n"
        "import app.application.admin.bootstrap_service as bootstrap_service\n",
        encoding="utf-8",
    )

    assert _admin_bootstrap_api_service_module_import_lines(module_path) == []


def test_removed_admin_auth_module_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_auth_package = "app.admin_api.auth"
    module_path.write_text(
        "from app.admin_api.auth.services import AdminAuthService\n"
        "from app.admin_api.auth.services.auth_service import AdminAuthService\n"
        "import app.admin_api.auth.services.auth_service as auth_service\n"
        f"from {admin_auth_package} import services\n"
        f"from {admin_auth_package} import services as auth_services\n"
        "from app.admin_api.auth.errors import AdminAuthUnauthorizedError\n"
        "import app.admin_api.auth.errors as auth_errors\n"
        f"from {admin_auth_package} import errors\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    auth_module_path = app_root / "admin_api" / "auth" / "module.py"
    nested_module_path = app_root / "admin_api" / "auth" / "flows" / "module.py"
    auth_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    auth_module_path.write_text(
        "from .services.auth_service import AdminAuthService\n"
        "from . import services\n"
        "from .errors import AdminAuthValidationError\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import auth_service\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.auth.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.auth.errors",
    ) == [6, 7, 8]
    assert _concrete_module_import_lines(
        auth_module_path,
        "app.admin_api.auth.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        auth_module_path,
        "app.admin_api.auth.errors",
    ) == [3]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.auth.services",
    ) == [1, 2]


def test_removed_admin_auth_import_detection_allows_application_auth_modules(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.admin.auth.auth_service import AdminAuthService\n"
        "from app.application.admin.auth.errors import AdminAuthUnauthorizedError\n"
        "from app.application.admin.auth.target_path import normalize_admin_target_path\n"
        "import app.application.admin.auth.auth_service as auth_service\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, "app.admin_api.auth.services") == []
    assert _concrete_module_import_lines(module_path, "app.admin_api.auth.errors") == []
    assert _concrete_module_import_lines(module_path, "app.admin_api.auth.validators") == []


def test_removed_admin_ai_usage_services_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    removed_admin_ai_usage_services_package = "app.admin_api.ai_usage.services"
    admin_ai_usage_package = "app.admin_api.ai_usage"
    module_path.write_text(
        f"from {removed_admin_ai_usage_services_package} import AdminAIUsageReadError\n"
        f"from {removed_admin_ai_usage_services_package} import AdminAIUsageReadService as AIUsageReadService\n"
        f"import {removed_admin_ai_usage_services_package}\n"
        f"import {removed_admin_ai_usage_services_package} as ai_usage_services\n"
        f"from {admin_ai_usage_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    ai_usage_module_path = app_root / "admin_api" / "ai_usage" / "module.py"
    nested_module_path = app_root / "admin_api" / "ai_usage" / "flows" / "module.py"
    ai_usage_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    ai_usage_module_path.write_text(
        "from .services import AdminAIUsageReadError\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminAIUsageReadError\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.ai_usage.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        ai_usage_module_path,
        "app.admin_api.ai_usage.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.ai_usage.services",
    ) == [1, 2]


def test_removed_admin_ai_usage_services_import_detection_catches_relative_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.ai_usage.services.errors import AdminAIUsageReadError\n"
        "import app.admin_api.ai_usage.services.errors as ai_usage_errors\n"
        "from app.admin_api.ai_usage.services.read_service import AdminAIUsageReadService\n"
        "import app.admin_api.ai_usage.services.read_service as read_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    ai_usage_module_path = app_root / "admin_api" / "ai_usage" / "module.py"
    services_module_path = app_root / "admin_api" / "ai_usage" / "services" / "module.py"
    nested_module_path = app_root / "admin_api" / "ai_usage" / "flows" / "module.py"
    ai_usage_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    ai_usage_module_path.write_text(
        "from .services.errors import AdminAIUsageReadError\n"
        "from .services.read_service import AdminAIUsageReadService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .errors import AdminAIUsageReadError\n"
        "from .read_service import AdminAIUsageReadService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.errors import AdminAIUsageReadError\n"
        "from ..services.read_service import AdminAIUsageReadService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.ai_usage.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        ai_usage_module_path,
        "app.admin_api.ai_usage.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.ai_usage.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.ai_usage.services",
    ) == [1, 2]


def test_retired_admin_ai_usage_facade_action_otp_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.ai_usage import AdminAIUsageActionOtpVerifier\n"
        "from app.admin_api.ai_usage import action_otp\n"
        "from app.admin_api.ai_usage.action_otp import AdminAIUsageActionOtpVerifier\n"
        "import app.admin_api.ai_usage\n"
        "import app.admin_api.ai_usage as ai_usage\n"
        "import app.admin_api.ai_usage.action_otp as action_otp\n"
        "from app.admin_api import ai_usage\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    ai_usage_module_path = app_root / "admin_api" / "ai_usage" / "module.py"
    nested_module_path = app_root / "admin_api" / "ai_usage" / "flows" / "module.py"
    ai_usage_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    ai_usage_module_path.write_text(
        "from . import action_otp\n"
        "from .action_otp import AdminAIUsageActionOtpVerifier\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import action_otp\n"
        "from ..action_otp import AdminAIUsageActionOtpVerifier\n",
        encoding="utf-8",
    )

    assert _retired_admin_ai_usage_facade_action_otp_import_lines(module_path) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert _retired_admin_ai_usage_facade_action_otp_import_lines(
        ai_usage_module_path,
    ) == [1, 2]
    assert _retired_admin_ai_usage_facade_action_otp_import_lines(
        nested_module_path,
    ) == [1, 2]


def test_retired_admin_ai_usage_facade_action_otp_import_detection_allows_live_modules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.ai_usage.router import build_ai_usage_router\n"
        "from app.admin_api.ai_usage.http_errors import admin_ai_usage_read_error_status_code\n"
        "from app.admin_api.ai_usage import router, http_errors\n"
        "import app.admin_api.ai_usage.router as ai_usage_router\n"
        "import app.admin_api.ai_usage.http_errors as ai_usage_http_errors\n"
        "from app.application.admin.ai_usage.action_otp import AdminAIUsageActionOtpVerifier\n"
        "from app.application.admin.ai_usage.read_service import AdminAIUsageReadService\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    ai_usage_module_path = app_root / "admin_api" / "ai_usage" / "module.py"
    nested_module_path = app_root / "admin_api" / "ai_usage" / "flows" / "module.py"
    ai_usage_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    ai_usage_module_path.write_text(
        "from .router import build_ai_usage_router\n"
        "from .http_errors import admin_ai_usage_read_error_status_code\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..router import build_ai_usage_router\n"
        "from ..http_errors import admin_ai_usage_read_error_status_code\n",
        encoding="utf-8",
    )

    assert _retired_admin_ai_usage_facade_action_otp_import_lines(module_path) == []
    assert _retired_admin_ai_usage_facade_action_otp_import_lines(
        ai_usage_module_path,
    ) == []
    assert _retired_admin_ai_usage_facade_action_otp_import_lines(
        nested_module_path,
    ) == []


def test_retired_admin_settings_facade_action_otp_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.settings import AdminSettingsActionOtpVerifier\n"
        "from app.admin_api.settings import action_otp\n"
        "from app.admin_api.settings.action_otp import AdminSettingsActionOtpVerifier\n"
        "import app.admin_api.settings\n"
        "import app.admin_api.settings as admin_settings\n"
        "import app.admin_api.settings.action_otp as action_otp\n"
        "from app.admin_api import settings\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    settings_module_path = app_root / "admin_api" / "settings" / "module.py"
    nested_module_path = app_root / "admin_api" / "settings" / "flows" / "module.py"
    settings_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    settings_module_path.write_text(
        "from . import action_otp\n"
        "from .action_otp import AdminSettingsActionOtpVerifier\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import action_otp\n"
        "from ..action_otp import AdminSettingsActionOtpVerifier\n",
        encoding="utf-8",
    )

    assert _retired_admin_settings_facade_action_otp_import_lines(module_path) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert _retired_admin_settings_facade_action_otp_import_lines(
        settings_module_path,
    ) == [1, 2]
    assert _retired_admin_settings_facade_action_otp_import_lines(
        nested_module_path,
    ) == [1, 2]


def test_retired_admin_settings_facade_action_otp_import_detection_allows_live_modules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.settings.router import build_settings_router\n"
        "from app.admin_api.settings.http_errors import admin_settings_http_exception\n"
        "from app.admin_api.settings import router, http_errors\n"
        "import app.admin_api.settings.router as settings_router\n"
        "import app.admin_api.settings.http_errors as settings_http_errors\n"
        "from app.application.admin.settings.action_otp import AdminSettingsActionOtpVerifier\n"
        "from app.application.admin.settings.settings_service import AdminSettingsService\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    settings_module_path = app_root / "admin_api" / "settings" / "module.py"
    nested_module_path = app_root / "admin_api" / "settings" / "flows" / "module.py"
    settings_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    settings_module_path.write_text(
        "from . import router\n"
        "from .router import build_settings_router\n"
        "from . import http_errors\n"
        "from .http_errors import admin_settings_http_exception\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import router\n"
        "from ..router import build_settings_router\n"
        "from .. import http_errors\n"
        "from ..http_errors import admin_settings_http_exception\n",
        encoding="utf-8",
    )

    assert _retired_admin_settings_facade_action_otp_import_lines(module_path) == []
    assert _retired_admin_settings_facade_action_otp_import_lines(
        settings_module_path,
    ) == []
    assert _retired_admin_settings_facade_action_otp_import_lines(
        nested_module_path,
    ) == []


def test_removed_admin_dashboard_services_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_dashboard_services_package = "app.admin_api.dashboard.services"
    admin_dashboard_package = "app.admin_api.dashboard"
    module_path.write_text(
        f"from {admin_dashboard_services_package} import AdminDashboardError\n"
        f"from {admin_dashboard_services_package} import AdminDashboardService as DashboardService\n"
        f"import {admin_dashboard_services_package}\n"
        f"import {admin_dashboard_services_package} as dashboard_services\n"
        f"from {admin_dashboard_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    dashboard_module_path = app_root / "admin_api" / "dashboard" / "module.py"
    nested_module_path = app_root / "admin_api" / "dashboard" / "flows" / "module.py"
    dashboard_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    dashboard_module_path.write_text(
        "from .services import AdminDashboardError\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminDashboardError\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.dashboard.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        dashboard_module_path,
        "app.admin_api.dashboard.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.dashboard.services",
    ) == [1, 2]


def test_removed_admin_dashboard_services_import_detection_catches_relative_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.dashboard.services.errors import AdminDashboardError\n"
        "import app.admin_api.dashboard.services.errors as dashboard_errors\n"
        "from app.admin_api.dashboard.services.dashboard_service import AdminDashboardService\n"
        "import app.admin_api.dashboard.services.dashboard_service as dashboard_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    dashboard_module_path = app_root / "admin_api" / "dashboard" / "module.py"
    services_module_path = app_root / "admin_api" / "dashboard" / "services" / "module.py"
    nested_module_path = app_root / "admin_api" / "dashboard" / "flows" / "module.py"
    application_dashboard_module_path = app_root / "application" / "admin" / "dashboard" / "module.py"
    dashboard_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    application_dashboard_module_path.parent.mkdir(parents=True)
    dashboard_module_path.write_text(
        "from .services.errors import AdminDashboardError\n"
        "from .services.dashboard_service import AdminDashboardService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .errors import AdminDashboardError\n"
        "from .dashboard_service import AdminDashboardService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.errors import AdminDashboardError\n"
        "from ..services.dashboard_service import AdminDashboardService\n",
        encoding="utf-8",
    )
    application_dashboard_module_path.write_text(
        "from .errors import AdminDashboardError\n"
        "from .dashboard_service import AdminDashboardService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.dashboard.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        dashboard_module_path,
        "app.admin_api.dashboard.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.dashboard.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.dashboard.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        application_dashboard_module_path,
        "app.admin_api.dashboard.services",
    ) == []


def test_removed_admin_billing_services_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    removed_admin_billing_services_package = "app.admin_api.billing.services"
    admin_billing_package = "app.admin_api.billing"
    module_path.write_text(
        f"from {removed_admin_billing_services_package} import AdminBillingReadError\n"
        f"from {removed_admin_billing_services_package} import AdminBillingReadService as BillingReadService\n"
        f"import {removed_admin_billing_services_package}\n"
        f"import {removed_admin_billing_services_package} as billing_services\n"
        f"from {admin_billing_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    billing_module_path = app_root / "admin_api" / "billing" / "module.py"
    nested_module_path = app_root / "admin_api" / "billing" / "flows" / "module.py"
    billing_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    billing_module_path.write_text(
        "from .services import AdminBillingReadError\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminBillingReadError\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.billing.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        billing_module_path,
        "app.admin_api.billing.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.billing.services",
    ) == [1, 2]


def test_removed_admin_billing_services_import_detection_catches_relative_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.billing.services.errors import AdminBillingReadError\n"
        "import app.admin_api.billing.services.errors as billing_errors\n"
        "from app.admin_api.billing.services.read_service import AdminBillingReadService\n"
        "import app.admin_api.billing.services.read_service as read_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    billing_module_path = app_root / "admin_api" / "billing" / "module.py"
    services_module_path = app_root / "admin_api" / "billing" / "services" / "module.py"
    nested_module_path = app_root / "admin_api" / "billing" / "flows" / "module.py"
    billing_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    billing_module_path.write_text(
        "from .services.errors import AdminBillingReadError\n"
        "from .services.read_service import AdminBillingReadService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .errors import AdminBillingReadError\n"
        "from .read_service import AdminBillingReadService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.errors import AdminBillingReadError\n"
        "from ..services.read_service import AdminBillingReadService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.billing.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        billing_module_path,
        "app.admin_api.billing.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.billing.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.billing.services",
    ) == [1, 2]


def test_retired_admin_billing_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.billing import build_billing_router\n"
        "from app.admin_api.billing import build_billing_router as build_router\n"
        "from app.admin_api.billing import *\n"
        "import app.admin_api.billing\n"
        "import app.admin_api.billing as admin_billing\n"
        "from app.admin_api import billing\n"
        "from app.admin_api import billing as admin_billing\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    billing_module_path = app_root / "admin_api" / "billing" / "module.py"
    nested_module_path = app_root / "admin_api" / "billing" / "flows" / "module.py"
    billing_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    billing_module_path.write_text(
        "from . import build_billing_router\n"
        "from . import router\n"
        "from .router import build_billing_router\n"
        "from . import http_errors\n"
        "from .http_errors import admin_billing_read_error_status_code\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import build_billing_router\n"
        "from .. import router\n"
        "from ..router import build_billing_router\n"
        "from .. import http_errors\n"
        "from ..http_errors import admin_billing_read_error_status_code\n",
        encoding="utf-8",
    )

    assert _retired_admin_billing_facade_import_lines(module_path) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert _retired_admin_billing_facade_import_lines(billing_module_path) == [1]
    assert _retired_admin_billing_facade_import_lines(nested_module_path) == [1]


def test_retired_admin_billing_facade_import_detection_allows_concrete_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.billing.router import build_billing_router\n"
        "import app.admin_api.billing.router as billing_router\n"
        "from app.admin_api.billing.http_errors import admin_billing_read_error_status_code\n"
        "import app.admin_api.billing.http_errors as billing_http_errors\n"
        "from app.admin_api.billing import router\n"
        "from app.admin_api.billing import http_errors as billing_http_errors\n"
        "from app.application.admin.billing import read_service\n"
        "from app.application.admin.billing.read_service import AdminBillingReadService\n"
        "import app.application.admin.billing.errors as billing_errors\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    billing_module_path = app_root / "admin_api" / "billing" / "module.py"
    nested_module_path = app_root / "admin_api" / "billing" / "flows" / "module.py"
    billing_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    billing_module_path.write_text(
        "from . import router\n"
        "from .router import build_billing_router\n"
        "from . import http_errors\n"
        "from .http_errors import admin_billing_read_error_status_code\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import router\n"
        "from ..router import build_billing_router\n"
        "from .. import http_errors\n"
        "from ..http_errors import admin_billing_read_error_status_code\n",
        encoding="utf-8",
    )

    assert _retired_admin_billing_facade_import_lines(module_path) == []
    assert _retired_admin_billing_facade_import_lines(billing_module_path) == []
    assert _retired_admin_billing_facade_import_lines(nested_module_path) == []


def test_retired_admin_dictionary_services_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_dictionary_services_package = "app.admin_api.dictionary.services"
    admin_dictionary_package = "app.admin_api.dictionary"
    module_path.write_text(
        f"from {admin_dictionary_services_package} import AdminDictionaryService\n"
        f"from {admin_dictionary_services_package} import AdminDictionaryReadService as DictionaryReadService\n"
        f"import {admin_dictionary_services_package}\n"
        f"import {admin_dictionary_services_package} as dictionary_services\n"
        f"from {admin_dictionary_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    dictionary_module_path = app_root / "admin_api" / "dictionary" / "module.py"
    nested_module_path = app_root / "admin_api" / "dictionary" / "flows" / "module.py"
    dictionary_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    dictionary_module_path.write_text(
        "from .services import AdminDictionaryService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminDictionaryService\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.dictionary.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        dictionary_module_path,
        "app.admin_api.dictionary.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.dictionary.services",
    ) == [1, 2]


def test_retired_admin_dictionary_services_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.dictionary.services.errors import AdminDictionaryServiceError\n"
        "import app.admin_api.dictionary.services.errors as dictionary_errors\n"
        "from app.admin_api.dictionary.services.dictionary_service import AdminDictionaryService\n"
        "import app.admin_api.dictionary.services.dictionary_service as dictionary_service\n"
        "from app.admin_api.dictionary.services.read_service import AdminDictionaryReadService\n"
        "import app.admin_api.dictionary.services.read_service as read_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    dictionary_module_path = app_root / "admin_api" / "dictionary" / "module.py"
    services_module_path = app_root / "admin_api" / "dictionary" / "services" / "module.py"
    nested_module_path = app_root / "admin_api" / "dictionary" / "flows" / "module.py"
    dictionary_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    dictionary_module_path.write_text(
        "from .services.errors import AdminDictionaryServiceError\n"
        "from .services.dictionary_service import AdminDictionaryService\n"
        "from .services.read_service import AdminDictionaryReadService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .errors import AdminDictionaryServiceError\n"
        "from .dictionary_service import AdminDictionaryService\n"
        "from .read_service import AdminDictionaryReadService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.errors import AdminDictionaryServiceError\n"
        "from ..services.dictionary_service import AdminDictionaryService\n"
        "from ..services.read_service import AdminDictionaryReadService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.dictionary.services",
    ) == [1, 2, 3, 4, 5, 6]
    assert _concrete_module_import_lines(
        dictionary_module_path,
        "app.admin_api.dictionary.services",
    ) == [1, 2, 3]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.dictionary.services",
    ) == [1, 2, 3]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.dictionary.services",
    ) == [1, 2, 3]


def test_removed_admin_entity_services_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_entity_services_package = "app.admin_api.entity.services"
    admin_entity_package = "app.admin_api.entity"
    module_path.write_text(
        f"from {admin_entity_services_package} import AdminEntityService\n"
        f"from {admin_entity_services_package} import AdminEntityError as EntityError\n"
        f"from {admin_entity_services_package}.errors import AdminEntityError\n"
        f"from {admin_entity_services_package}.entity_service import AdminEntityService\n"
        f"import {admin_entity_services_package}\n"
        f"import {admin_entity_services_package} as entity_services\n"
        f"import {admin_entity_services_package}.errors as entity_errors\n"
        f"import {admin_entity_services_package}.entity_service as entity_service\n"
        f"from {admin_entity_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    entity_module_path = app_root / "admin_api" / "entity" / "module.py"
    nested_module_path = app_root / "admin_api" / "entity" / "flows" / "module.py"
    entity_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    entity_module_path.write_text(
        "from .services import AdminEntityService\n"
        "from .services.errors import AdminEntityError\n"
        "from .services.entity_service import AdminEntityService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminEntityService\n"
        "from ..services.errors import AdminEntityError\n"
        "from ..services.entity_service import AdminEntityService\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.entity.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
    ]
    assert _concrete_module_import_lines(
        entity_module_path,
        "app.admin_api.entity.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.entity.services",
    ) == [1, 2, 3, 4]


def test_removed_admin_entity_services_import_detection_ignores_application_entity_modules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.admin.entity.errors import AdminEntityError\n"
        "import app.application.admin.entity.errors as entity_errors\n"
        "from app.application.admin.entity.entity_service import AdminEntityService\n"
        "import app.application.admin.entity.entity_service as entity_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    entity_module_path = app_root / "admin_api" / "entity" / "module.py"
    services_module_path = app_root / "admin_api" / "entity" / "services" / "module.py"
    nested_module_path = app_root / "admin_api" / "entity" / "flows" / "module.py"
    entity_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    entity_module_path.write_text(
        "from app.application.admin.entity.errors import AdminEntityError\n"
        "from app.application.admin.entity.entity_service import AdminEntityService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from app.application.admin.entity.errors import AdminEntityError\n"
        "from app.application.admin.entity.entity_service import AdminEntityService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from app.application.admin.entity.errors import AdminEntityError\n"
        "from app.application.admin.entity.entity_service import AdminEntityService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.entity.services",
    ) == []
    assert _concrete_module_import_lines(
        entity_module_path,
        "app.admin_api.entity.services",
    ) == []
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.entity.services",
    ) == []
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.entity.services",
    ) == []


def test_removed_admin_exercise_text_services_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_exercise_text_services_package = "app.admin_api.exercise_texts.services"
    admin_exercise_text_package = "app.admin_api.exercise_texts"
    module_path.write_text(
        f"from {admin_exercise_text_services_package} import AdminExerciseTextService\n"
        f"from {admin_exercise_text_services_package} import AdminExerciseTextService as ExerciseTextService\n"
        f"import {admin_exercise_text_services_package}\n"
        f"import {admin_exercise_text_services_package} as exercise_text_services\n"
        f"from {admin_exercise_text_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    exercise_text_module_path = app_root / "admin_api" / "exercise_texts" / "module.py"
    services_module_path = (
        app_root / "admin_api" / "exercise_texts" / "services" / "module.py"
    )
    nested_module_path = (
        app_root / "admin_api" / "exercise_texts" / "flows" / "module.py"
    )
    exercise_text_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    exercise_text_module_path.write_text(
        "from .services import AdminExerciseTextService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from . import exercise_text_service\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminExerciseTextService\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.exercise_texts.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        exercise_text_module_path,
        "app.admin_api.exercise_texts.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.exercise_texts.services",
    ) == [1]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.exercise_texts.services",
    ) == [1, 2]


def test_removed_admin_exercise_text_services_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.exercise_texts.errors import AdminExerciseTextServiceError\n"
        "import app.admin_api.exercise_texts.errors as exercise_text_errors\n"
        "from app.admin_api.exercise_texts.services.exercise_text_service import AdminExerciseTextService\n"
        "import app.admin_api.exercise_texts.services.exercise_text_service as exercise_text_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    exercise_text_module_path = app_root / "admin_api" / "exercise_texts" / "module.py"
    services_module_path = (
        app_root / "admin_api" / "exercise_texts" / "services" / "module.py"
    )
    nested_module_path = (
        app_root / "admin_api" / "exercise_texts" / "flows" / "module.py"
    )
    exercise_text_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    exercise_text_module_path.write_text(
        "from .errors import AdminExerciseTextServiceError\n"
        "from .services.exercise_text_service import AdminExerciseTextService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from ..errors import AdminExerciseTextServiceError\n"
        "from .exercise_text_service import AdminExerciseTextService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..errors import AdminExerciseTextServiceError\n"
        "from ..services.exercise_text_service import AdminExerciseTextService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.exercise_texts.services",
    ) == [3, 4]
    assert _concrete_module_import_lines(
        exercise_text_module_path,
        "app.admin_api.exercise_texts.services",
    ) == [2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.exercise_texts.services",
    ) == [2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.exercise_texts.services",
    ) == [2]


def test_retired_admin_user_dictionary_services_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_user_dictionary_services_package = "app.admin_api.user_dictionary.services"
    admin_user_dictionary_package = "app.admin_api.user_dictionary"
    module_path.write_text(
        f"from {admin_user_dictionary_services_package} import AdminUserDictionaryReadService\n"
        f"from {admin_user_dictionary_services_package} import AdminUserDictionaryReadError as ReadError\n"
        f"from {admin_user_dictionary_services_package} import errors\n"
        f"from {admin_user_dictionary_services_package} import read_service as user_dictionary_read_service\n"
        f"import {admin_user_dictionary_services_package}\n"
        f"import {admin_user_dictionary_services_package} as user_dictionary_services\n"
        f"from {admin_user_dictionary_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    user_dictionary_module_path = app_root / "admin_api" / "user_dictionary" / "module.py"
    services_module_path = (
        app_root / "admin_api" / "user_dictionary" / "services" / "module.py"
    )
    nested_module_path = app_root / "admin_api" / "user_dictionary" / "flows" / "module.py"
    user_dictionary_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    user_dictionary_module_path.write_text(
        "from .services import AdminUserDictionaryReadService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from . import errors\n"
        "from . import read_service as user_dictionary_read_service\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminUserDictionaryReadService\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.user_dictionary.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert _concrete_module_import_lines(
        user_dictionary_module_path,
        "app.admin_api.user_dictionary.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.user_dictionary.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.user_dictionary.services",
    ) == [1, 2]


def test_retired_admin_user_dictionary_services_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.user_dictionary.services.errors import AdminUserDictionaryReadError\n"
        "import app.admin_api.user_dictionary.services.errors as user_dictionary_errors\n"
        "from app.admin_api.user_dictionary.services.read_service import AdminUserDictionaryReadService\n"
        "import app.admin_api.user_dictionary.services.read_service as read_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    user_dictionary_module_path = app_root / "admin_api" / "user_dictionary" / "module.py"
    services_module_path = (
        app_root / "admin_api" / "user_dictionary" / "services" / "module.py"
    )
    nested_module_path = app_root / "admin_api" / "user_dictionary" / "flows" / "module.py"
    user_dictionary_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    user_dictionary_module_path.write_text(
        "from .services.errors import AdminUserDictionaryReadError\n"
        "from .services.read_service import AdminUserDictionaryReadService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .errors import AdminUserDictionaryReadError\n"
        "from .read_service import AdminUserDictionaryReadService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.errors import AdminUserDictionaryReadError\n"
        "from ..services.read_service import AdminUserDictionaryReadService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.user_dictionary.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        user_dictionary_module_path,
        "app.admin_api.user_dictionary.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.user_dictionary.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.user_dictionary.services",
    ) == [1, 2]


def test_removed_admin_settings_services_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_settings_services_package = "app.admin_api.settings.services"
    admin_settings_package = "app.admin_api.settings"
    module_path.write_text(
        f"from {admin_settings_services_package} import AdminSettingsService\n"
        f"from {admin_settings_services_package} import AdminSettingsService as SettingsService\n"
        f"import {admin_settings_services_package}\n"
        f"import {admin_settings_services_package} as settings_services\n"
        f"from {admin_settings_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    settings_module_path = app_root / "admin_api" / "settings" / "module.py"
    nested_module_path = app_root / "admin_api" / "settings" / "flows" / "module.py"
    settings_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    settings_module_path.write_text(
        "from .services import AdminSettingsService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminSettingsService\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.settings.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        settings_module_path,
        "app.admin_api.settings.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.settings.services",
    ) == [1, 2]


def test_removed_admin_settings_services_import_detection_catches_relative_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.settings.services.settings_service import AdminSettingsService\n"
        "import app.admin_api.settings.services.settings_service as settings_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    settings_module_path = app_root / "admin_api" / "settings" / "module.py"
    services_module_path = app_root / "admin_api" / "settings" / "services" / "module.py"
    nested_module_path = app_root / "admin_api" / "settings" / "flows" / "module.py"
    settings_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    settings_module_path.write_text(
        "from .services.settings_service import AdminSettingsService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .settings_service import AdminSettingsService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.settings_service import AdminSettingsService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.settings.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        settings_module_path,
        "app.admin_api.settings.services",
    ) == [1]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.settings.services",
    ) == [1]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.settings.services",
    ) == [1]


def test_removed_admin_settings_validators_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_name = "app.admin_api.settings.validators"
    parent_package_name = "app.admin_api.settings"
    module_path = tmp_path / "module.py"
    module_path.write_text(
        f"from {package_name} import normalize_provider_settings_payload\n"
        f"from {package_name} import normalize_settings_payload as normalize_settings\n"
        f"from {package_name} import settings\n"
        f"import {package_name}\n"
        f"import {package_name} as settings_validators\n"
        f"from {parent_package_name} import validators\n"
        f"from {parent_package_name} import validators as settings_validators\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    current_module = __import__(__name__, fromlist=["APP_ROOT"])
    monkeypatch.setattr(current_module, "APP_ROOT", app_root)
    settings_module_path = app_root / "admin_api" / "settings" / "module.py"
    validators_module_path = (
        app_root / "admin_api" / "settings" / "validators" / "module.py"
    )
    nested_module_path = app_root / "admin_api" / "settings" / "flows" / "module.py"
    settings_module_path.parent.mkdir(parents=True)
    validators_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    settings_module_path.write_text(
        "from .validators import normalize_settings_payload\n"
        "from . import validators\n",
        encoding="utf-8",
    )
    validators_module_path.write_text(
        "from . import settings\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..validators import normalize_provider_settings_payload\n"
        "from .. import validators\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, package_name) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert _concrete_module_import_lines(settings_module_path, package_name) == [1, 2]
    assert _concrete_module_import_lines(validators_module_path, package_name) == [1]
    assert _concrete_module_import_lines(nested_module_path, package_name) == [1, 2]


def test_removed_admin_settings_validators_import_detection_catches_relative_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_name = "app.admin_api.settings.validators"
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.settings.validators.settings import normalize_provider_settings_payload\n"
        "from app.admin_api.settings.validators.settings import normalize_settings_payload\n"
        "import app.admin_api.settings.validators.settings as settings_validators\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    current_module = __import__(__name__, fromlist=["APP_ROOT"])
    monkeypatch.setattr(current_module, "APP_ROOT", app_root)
    settings_module_path = app_root / "admin_api" / "settings" / "module.py"
    validators_module_path = (
        app_root / "admin_api" / "settings" / "validators" / "module.py"
    )
    nested_module_path = app_root / "admin_api" / "settings" / "flows" / "module.py"
    settings_module_path.parent.mkdir(parents=True)
    validators_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    settings_module_path.write_text(
        "from .validators.settings import normalize_settings_payload\n",
        encoding="utf-8",
    )
    validators_module_path.write_text(
        "from .settings import normalize_provider_settings_payload\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..validators.settings import normalize_provider_settings_payload\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, package_name) == [1, 2, 3]
    assert _concrete_module_import_lines(settings_module_path, package_name) == [1]
    assert _concrete_module_import_lines(validators_module_path, package_name) == [1]
    assert _concrete_module_import_lines(nested_module_path, package_name) == [1]


def test_removed_admin_exercise_text_validators_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_name = "app.admin_api.exercise_texts.validators"
    parent_package_name = "app.admin_api.exercise_texts"
    module_path = tmp_path / "module.py"
    module_path.write_text(
        f"from {package_name} import validate_content_document\n"
        f"from {package_name} import ExerciseTextContentValidationError as ContentError\n"
        f"from {package_name} import content_jsonb\n"
        f"import {package_name}\n"
        f"import {package_name} as exercise_text_validators\n"
        f"from {parent_package_name} import validators\n"
        f"from {parent_package_name} import validators as exercise_text_validators\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    current_module = __import__(__name__, fromlist=["APP_ROOT"])
    monkeypatch.setattr(current_module, "APP_ROOT", app_root)
    exercise_texts_module_path = app_root / "admin_api" / "exercise_texts" / "module.py"
    validators_module_path = (
        app_root / "admin_api" / "exercise_texts" / "validators" / "module.py"
    )
    nested_module_path = (
        app_root / "admin_api" / "exercise_texts" / "flows" / "module.py"
    )
    exercise_texts_module_path.parent.mkdir(parents=True)
    validators_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    exercise_texts_module_path.write_text(
        "from .validators import validate_content_document\n"
        "from . import validators\n",
        encoding="utf-8",
    )
    validators_module_path.write_text(
        "from . import content_jsonb\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..validators import collect_content_validation_errors\n"
        "from .. import validators\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, package_name) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert _concrete_module_import_lines(exercise_texts_module_path, package_name) == [
        1,
        2,
    ]
    assert _concrete_module_import_lines(validators_module_path, package_name) == [1]
    assert _concrete_module_import_lines(nested_module_path, package_name) == [1, 2]


def test_removed_admin_exercise_text_validators_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    package_name = "app.admin_api.exercise_texts.validators"
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.exercise_texts.validators.content_jsonb import validate_content_document\n"
        "from app.admin_api.exercise_texts.validators.content_jsonb import collect_content_validation_errors\n"
        "import app.admin_api.exercise_texts.validators.content_jsonb as content_validators\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    current_module = __import__(__name__, fromlist=["APP_ROOT"])
    monkeypatch.setattr(current_module, "APP_ROOT", app_root)
    exercise_texts_module_path = app_root / "admin_api" / "exercise_texts" / "module.py"
    validators_module_path = (
        app_root / "admin_api" / "exercise_texts" / "validators" / "module.py"
    )
    nested_module_path = (
        app_root / "admin_api" / "exercise_texts" / "flows" / "module.py"
    )
    exercise_texts_module_path.parent.mkdir(parents=True)
    validators_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    exercise_texts_module_path.write_text(
        "from .validators.content_jsonb import validate_content_document\n",
        encoding="utf-8",
    )
    validators_module_path.write_text(
        "from .content_jsonb import collect_content_validation_errors\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..validators.content_jsonb import validate_content_document\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, package_name) == [1, 2, 3]
    assert _concrete_module_import_lines(exercise_texts_module_path, package_name) == [1]
    assert _concrete_module_import_lines(validators_module_path, package_name) == [1]
    assert _concrete_module_import_lines(nested_module_path, package_name) == [1]


def test_removed_admin_read_services_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    removed_admin_read_services_package = "app.admin_api.read.services"
    admin_read_package = "app.admin_api.read"
    module_path.write_text(
        f"from {removed_admin_read_services_package} import AdminReadError\n"
        f"from {removed_admin_read_services_package} import AdminReadService as ReadService\n"
        f"from {removed_admin_read_services_package}.errors import AdminReadError\n"
        f"from {removed_admin_read_services_package}.read_service import AdminReadService\n"
        f"import {removed_admin_read_services_package}\n"
        f"import {removed_admin_read_services_package} as read_services\n"
        f"import {removed_admin_read_services_package}.errors as read_errors\n"
        f"import {removed_admin_read_services_package}.read_service as read_service\n"
        f"from {admin_read_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    read_module_path = app_root / "admin_api" / "read" / "module.py"
    nested_module_path = app_root / "admin_api" / "read" / "flows" / "module.py"
    read_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    read_module_path.write_text(
        "from .services import AdminReadError\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminReadError\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.read.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
    ]
    assert _concrete_module_import_lines(
        read_module_path,
        "app.admin_api.read.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.read.services",
    ) == [1, 2]


def test_removed_admin_read_services_import_detection_allows_application_read_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.application.admin.read.errors import AdminReadError\n"
        "import app.application.admin.read.errors as read_errors\n"
        "from app.application.admin.read.read_service import AdminReadService\n"
        "import app.application.admin.read.read_service as read_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    read_module_path = app_root / "application" / "admin" / "read" / "module.py"
    nested_module_path = app_root / "application" / "admin" / "flows" / "module.py"
    read_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    read_module_path.write_text(
        "from .errors import AdminReadError\n"
        "from .read_service import AdminReadService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .read.errors import AdminReadError\n"
        "from .read.read_service import AdminReadService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.read.services",
    ) == []
    assert _concrete_module_import_lines(
        read_module_path,
        "app.admin_api.read.services",
    ) == []
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.read.services",
    ) == []


def test_retired_admin_import_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.imports import build_imports_router\n"
        "from app.admin_api.imports import build_imports_router as build_router\n"
        "import app.admin_api.imports\n"
        "import app.admin_api.imports as admin_imports\n"
        "from app.admin_api import imports\n"
        "from app.admin_api import imports as admin_imports\n"
        "from app.admin_api.imports.helpers import normalize_import_query\n"
        "import app.admin_api.imports.helpers\n"
        "import app.admin_api.imports.helpers as import_helpers\n"
        "from app.admin_api.imports import helpers\n"
        "from app.admin_api.imports.validators import validate_import_query\n"
        "import app.admin_api.imports.validators as import_validators\n"
        "from app.admin_api.imports import validators as import_validators\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    imports_module_path = app_root / "admin_api" / "imports" / "module.py"
    nested_module_path = app_root / "admin_api" / "imports" / "flows" / "module.py"
    imports_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    imports_module_path.write_text(
        "from . import helpers\n"
        "from .helpers import normalize_import_query\n"
        "from . import validators\n"
        "from .validators import validate_import_query\n"
        "from . import router\n"
        "from .router import build_imports_router\n"
        "from . import http_errors\n"
        "from .http_errors import admin_import_read_error_status_code\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import helpers\n"
        "from ..helpers import normalize_import_query\n"
        "from .. import validators\n"
        "from ..validators import validate_import_query\n"
        "from .. import router\n"
        "from ..router import build_imports_router\n",
        encoding="utf-8",
    )

    assert _retired_admin_import_facade_helper_validator_import_lines(
        module_path
    ) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
    ]
    assert _retired_admin_import_facade_helper_validator_import_lines(
        imports_module_path
    ) == [1, 2, 3, 4]
    assert _retired_admin_import_facade_helper_validator_import_lines(
        nested_module_path
    ) == [1, 2, 3, 4]


def test_retired_admin_import_facade_import_detection_allows_concrete_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.imports.router import build_imports_router\n"
        "import app.admin_api.imports.router as imports_router\n"
        "from app.admin_api.imports.http_errors import admin_import_read_error_status_code\n"
        "import app.admin_api.imports.http_errors as import_http_errors\n"
        "from app.admin_api.imports import router\n"
        "from app.admin_api.imports import http_errors as import_http_errors\n"
        "from app.application.admin.imports import read_service\n"
        "from app.application.admin.imports.read_service import AdminImportReadService\n"
        "import app.application.admin.imports.errors as import_errors\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    imports_module_path = app_root / "admin_api" / "imports" / "module.py"
    nested_module_path = app_root / "admin_api" / "imports" / "flows" / "module.py"
    imports_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    imports_module_path.write_text(
        "from . import router\n"
        "from .router import build_imports_router\n"
        "from . import http_errors\n"
        "from .http_errors import admin_import_read_error_status_code\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from .. import router\n"
        "from ..router import build_imports_router\n"
        "from .. import http_errors\n"
        "from ..http_errors import admin_import_read_error_status_code\n",
        encoding="utf-8",
    )

    assert _retired_admin_import_facade_helper_validator_import_lines(module_path) == []
    assert _retired_admin_import_facade_helper_validator_import_lines(
        imports_module_path
    ) == []
    assert _retired_admin_import_facade_helper_validator_import_lines(
        nested_module_path
    ) == []


def test_removed_admin_import_services_import_detection_catches_broad_imports_and_submodules(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    removed_admin_import_services_package = "app.admin_api.imports.services"
    admin_import_package = "app.admin_api.imports"
    module_path.write_text(
        f"from {removed_admin_import_services_package} import AdminImportReadError\n"
        f"from {removed_admin_import_services_package} import AdminImportReadService as ImportReadService\n"
        f"import {removed_admin_import_services_package}\n"
        f"import {removed_admin_import_services_package} as import_services\n"
        f"from {admin_import_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    imports_module_path = app_root / "admin_api" / "imports" / "module.py"
    nested_module_path = app_root / "admin_api" / "imports" / "flows" / "module.py"
    imports_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    imports_module_path.write_text(
        "from .services import AdminImportReadError\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminImportReadError\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.imports.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        imports_module_path,
        "app.admin_api.imports.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.imports.services",
    ) == [1, 2]


def test_removed_admin_import_services_import_detection_catches_relative_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.imports.services.errors import AdminImportReadError\n"
        "import app.admin_api.imports.services.errors as import_errors\n"
        "from app.admin_api.imports.services.read_service import AdminImportReadService\n"
        "import app.admin_api.imports.services.read_service as read_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    imports_module_path = app_root / "admin_api" / "imports" / "module.py"
    services_module_path = app_root / "admin_api" / "imports" / "services" / "module.py"
    nested_module_path = app_root / "admin_api" / "imports" / "flows" / "module.py"
    imports_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    imports_module_path.write_text(
        "from .services.errors import AdminImportReadError\n"
        "from .services.read_service import AdminImportReadService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .errors import AdminImportReadError\n"
        "from .read_service import AdminImportReadService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.errors import AdminImportReadError\n"
        "from ..services.read_service import AdminImportReadService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.imports.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        imports_module_path,
        "app.admin_api.imports.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.imports.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.imports.services",
    ) == [1, 2]


def test_retired_admin_users_services_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    admin_user_services_package = "app.admin_api.users.services"
    admin_users_package = "app.admin_api.users"
    module_path.write_text(
        f"from {admin_user_services_package} import AdminUserReadError\n"
        f"from {admin_user_services_package} import AdminUserReadService as UserReadService\n"
        f"import {admin_user_services_package}\n"
        f"import {admin_user_services_package} as user_services\n"
        f"from {admin_users_package} import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    users_module_path = app_root / "admin_api" / "users" / "module.py"
    nested_module_path = app_root / "admin_api" / "users" / "flows" / "module.py"
    users_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    users_module_path.write_text(
        "from .services import AdminUserReadError\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import AdminUserReadError\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.users.services",
    ) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _concrete_module_import_lines(
        users_module_path,
        "app.admin_api.users.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.users.services",
    ) == [1, 2]


def test_retired_admin_users_services_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.users.services.errors import AdminUserReadError\n"
        "import app.admin_api.users.services.errors as user_errors\n"
        "from app.admin_api.users.services.read_service import AdminUserReadService\n"
        "import app.admin_api.users.services.read_service as read_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    users_module_path = app_root / "admin_api" / "users" / "module.py"
    services_module_path = app_root / "admin_api" / "users" / "services" / "module.py"
    nested_module_path = app_root / "admin_api" / "users" / "flows" / "module.py"
    users_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    users_module_path.write_text(
        "from .services.errors import AdminUserReadError\n"
        "from .services.read_service import AdminUserReadService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .errors import AdminUserReadError\n"
        "from .read_service import AdminUserReadService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.errors import AdminUserReadError\n"
        "from ..services.read_service import AdminUserReadService\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.users.services",
    ) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        users_module_path,
        "app.admin_api.users.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        services_module_path,
        "app.admin_api.users.services",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.users.services",
    ) == [1, 2]


@pytest.mark.parametrize(
    ("module_basename", "exported_name"),
    (
        ("helpers", "AdminUserHelper"),
        ("validators", "AdminUserValidator"),
    ),
)
def test_retired_admin_user_support_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
    module_basename: str,
    exported_name: str,
) -> None:
    module_path = tmp_path / "module.py"
    retired_package = f"app.admin_api.users.{module_basename}"
    admin_users_package = "app.admin_api.users"
    module_path.write_text(
        f"from {retired_package} import {exported_name}\n"
        f"from {retired_package} import {exported_name} as UserSupport\n"
        f"import {retired_package}\n"
        f"import {retired_package} as user_support_package\n"
        f"from {admin_users_package} import {module_basename}\n"
        f"from {admin_users_package} import {module_basename} as support_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    users_module_path = app_root / "admin_api" / "users" / "module.py"
    nested_module_path = app_root / "admin_api" / "users" / "flows" / "module.py"
    users_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    users_module_path.write_text(
        f"from .{module_basename} import {exported_name}\n"
        f"from . import {module_basename}\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        f"from ..{module_basename} import {exported_name}\n"
        f"from .. import {module_basename}\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, retired_package) == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert _concrete_module_import_lines(
        users_module_path,
        retired_package,
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        retired_package,
    ) == [1, 2]


@pytest.mark.parametrize(
    ("module_basename", "submodule_name", "exported_name"),
    (
        ("helpers", "user_helpers", "build_admin_user_payload"),
        ("validators", "user_validators", "validate_admin_user_payload"),
    ),
)
def test_retired_admin_user_support_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
    module_basename: str,
    submodule_name: str,
    exported_name: str,
) -> None:
    module_path = tmp_path / "module.py"
    retired_package = f"app.admin_api.users.{module_basename}"
    module_path.write_text(
        f"from {retired_package}.{submodule_name} import {exported_name}\n"
        f"import {retired_package}.{submodule_name} as user_support\n"
        f"from {retired_package}.errors import AdminUserSupportError\n"
        f"import {retired_package}.errors as support_errors\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    users_module_path = app_root / "admin_api" / "users" / "module.py"
    support_module_path = app_root / "admin_api" / "users" / module_basename / "module.py"
    nested_module_path = app_root / "admin_api" / "users" / "flows" / "module.py"
    users_module_path.parent.mkdir(parents=True)
    support_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    users_module_path.write_text(
        f"from .{module_basename}.{submodule_name} import {exported_name}\n"
        f"from .{module_basename}.errors import AdminUserSupportError\n",
        encoding="utf-8",
    )
    support_module_path.write_text(
        f"from .{submodule_name} import {exported_name}\n"
        "from .errors import AdminUserSupportError\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        f"from ..{module_basename}.{submodule_name} import {exported_name}\n"
        f"from ..{module_basename}.errors import AdminUserSupportError\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, retired_package) == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        users_module_path,
        retired_package,
    ) == [1, 2]
    assert _concrete_module_import_lines(
        support_module_path,
        retired_package,
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        retired_package,
    ) == [1, 2]


@pytest.mark.parametrize(
    ("package_name", "package_parts", "submodule", "exported_name"),
    [
        (package_name, package_parts, submodule, exported_name)
        for _, package_name, package_parts, submodule, exported_name in RETIRED_ADMIN_TOP_LEVEL_PACKAGE_FACADES
    ],
)
def test_retired_admin_top_level_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
    package_name: str,
    package_parts: tuple[str, ...],
    submodule: str,
    exported_name: str,
) -> None:
    module_path = tmp_path / "module.py"
    parent_package, _, package_basename = package_name.rpartition(".")
    subpackage_name = submodule.split(".")[0]
    module_path.write_text(
        f"from {package_name} import {exported_name}\n"
        f"from {package_name} import {exported_name} as Exported\n"
        f"from {package_name} import {subpackage_name}\n"
        f"import {package_name}\n"
        f"import {package_name} as package_facade\n"
        f"from {parent_package} import {package_basename}\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    current_module = __import__(__name__, fromlist=["APP_ROOT"])
    monkeypatch.setattr(current_module, "APP_ROOT", app_root)
    parent_module_path = app_root.joinpath(*package_parts[:-1], "module.py")
    package_module_path = app_root.joinpath(*package_parts, "module.py")
    nested_module_path = app_root.joinpath(*package_parts, "flows", "module.py")
    parent_module_path.parent.mkdir(parents=True)
    package_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    parent_module_path.write_text(
        f"from . import {package_basename}\n",
        encoding="utf-8",
    )
    package_module_path.write_text(
        f"from . import {subpackage_name}\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        f"from .. import {subpackage_name}\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, package_name) == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert _package_facade_import_lines(parent_module_path, package_name) == [1]
    assert _package_facade_import_lines(package_module_path, package_name) == [1]
    assert _package_facade_import_lines(nested_module_path, package_name) == [1]


@pytest.mark.parametrize(
    ("package_name", "package_parts", "submodule", "exported_name"),
    [
        (package_name, package_parts, submodule, exported_name)
        for _, package_name, package_parts, submodule, exported_name in RETIRED_ADMIN_TOP_LEVEL_PACKAGE_FACADES
    ],
)
def test_retired_admin_top_level_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
    monkeypatch,
    package_name: str,
    package_parts: tuple[str, ...],
    submodule: str,
    exported_name: str,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        f"from {package_name}.{submodule} import {exported_name}\n"
        f"import {package_name}.{submodule} as submodule_import\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    current_module = __import__(__name__, fromlist=["APP_ROOT"])
    monkeypatch.setattr(current_module, "APP_ROOT", app_root)
    submodule_parts = submodule.split(".")
    package_module_path = app_root.joinpath(*package_parts, "module.py")
    submodule_container_module_path = app_root.joinpath(
        *package_parts,
        *submodule_parts[:-1],
        "submodule_container.py",
    )
    nested_module_path = app_root.joinpath(*package_parts, "flows", "module.py")
    package_module_path.parent.mkdir(parents=True)
    submodule_container_module_path.parent.mkdir(parents=True, exist_ok=True)
    nested_module_path.parent.mkdir(parents=True)
    package_module_path.write_text(
        f"from .{submodule} import {exported_name}\n",
        encoding="utf-8",
    )
    submodule_container_module_path.write_text(
        f"from .{submodule_parts[-1]} import {exported_name}\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        f"from ..{submodule} import {exported_name}\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, package_name) == []
    assert _package_facade_import_lines(package_module_path, package_name) == []
    assert _package_facade_import_lines(
        submodule_container_module_path,
        package_name,
    ) == []
    assert _package_facade_import_lines(nested_module_path, package_name) == []


def test_billing_services_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.services import BillingWebhookService\n"
        "from app.billing.services import BillingWebhookService as WebhookService\n"
        "import app.billing.services\n"
        "import app.billing.services as billing_services\n"
        "from app.billing import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    billing_module_path = app_root / "billing" / "module.py"
    nested_module_path = app_root / "billing" / "routers" / "module.py"
    billing_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    billing_module_path.write_text(
        "from .services import BillingWebhookService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import BillingWebhookService\n"
        "from .. import services\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.billing.services") == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert _package_facade_import_lines(billing_module_path, "app.billing.services") == [1, 2]
    assert _package_facade_import_lines(nested_module_path, "app.billing.services") == [1, 2]


def test_billing_services_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.services.webhook_service import BillingWebhookService\n"
        "import app.billing.services.webhook_service as webhook_service\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    billing_module_path = app_root / "billing" / "module.py"
    services_module_path = app_root / "billing" / "services" / "module.py"
    nested_module_path = app_root / "billing" / "routers" / "module.py"
    billing_module_path.parent.mkdir(parents=True)
    services_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    billing_module_path.write_text(
        "from .services.webhook_service import BillingWebhookService\n",
        encoding="utf-8",
    )
    services_module_path.write_text(
        "from .webhook_service import BillingWebhookService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services.webhook_service import BillingWebhookService\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.billing.services") == []
    assert _package_facade_import_lines(billing_module_path, "app.billing.services") == []
    assert _package_facade_import_lines(services_module_path, "app.billing.services") == []
    assert _package_facade_import_lines(nested_module_path, "app.billing.services") == []


def test_retired_admin_dictionary_helpers_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.dictionary.helpers import build_audio_response\n"
        "from app.admin_api.dictionary.helpers import build_audio_response as build_audio\n"
        "import app.admin_api.dictionary.helpers\n"
        "import app.admin_api.dictionary.helpers as dictionary_helpers\n"
        "from app.admin_api.dictionary import helpers\n"
        "from app.admin_api.dictionary import helpers as dictionary_helpers\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "admin_api" / "dictionary" / "module.py"
    nested_module_path = app_root / "admin_api" / "dictionary" / "routers" / "module.py"
    root_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text("from . import helpers\n", encoding="utf-8")
    nested_module_path.write_text("from .. import helpers\n", encoding="utf-8")

    assert _concrete_module_import_lines(module_path, "app.admin_api.dictionary.helpers") == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert _concrete_module_import_lines(root_module_path, "app.admin_api.dictionary.helpers") == [1]
    assert _concrete_module_import_lines(nested_module_path, "app.admin_api.dictionary.helpers") == [1]


def test_retired_admin_dictionary_helpers_import_detection_catches_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.dictionary.helpers.audio_response import build_audio_response\n"
        "import app.admin_api.dictionary.helpers.audio_response\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, "app.admin_api.dictionary.helpers") == [1, 2]


def test_removed_admin_auth_helpers_import_detection_catches_broad_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.auth.helpers import normalize_username\n"
        "import app.admin_api.auth.helpers\n"
        "import app.admin_api.auth.helpers as auth_helpers\n"
        "from app.admin_api.auth import helpers\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.auth." "helpers",
    ) == [1, 2, 3, 4]


def test_removed_admin_auth_helpers_import_detection_catches_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.auth.helpers.identity import normalize_username\n"
        "from app.admin_api.auth.helpers.otp import normalize_otp\n"
        "from app.admin_api.auth.helpers.secrets import verify_secret\n"
        "import app.admin_api.auth.helpers.identity as identity\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(
        module_path,
        "app.admin_api.auth." "helpers",
    ) == [1, 2, 3, 4]


def test_retired_admin_dictionary_actions_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.dictionary.actions import AdminDictionaryActionService\n"
        "from app.admin_api.dictionary.actions import AdminDictionaryActionService as ActionService\n"
        "import app.admin_api.dictionary.actions\n"
        "import app.admin_api.dictionary.actions as dictionary_actions_package\n"
        "from app.admin_api.dictionary import actions\n"
        "from app.admin_api.dictionary import actions as actions_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    dictionary_module_path = app_root / "admin_api" / "dictionary" / "module.py"
    nested_module_path = app_root / "admin_api" / "dictionary" / "routers" / "module.py"
    dictionary_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    dictionary_module_path.write_text(
        "from .actions import AdminDictionaryActionService\n"
        "from . import actions\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..actions import AdminDictionaryActionService\n"
        "from .. import actions\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, "app.admin_api.dictionary.actions") == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert _concrete_module_import_lines(
        dictionary_module_path,
        "app.admin_api.dictionary.actions",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.dictionary.actions",
    ) == [1, 2]


def test_retired_admin_dictionary_actions_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.dictionary.actions.dictionary_actions import AdminDictionaryActionService\n"
        "from app.admin_api.dictionary.actions.errors import AdminDictionaryActionError\n"
        "import app.admin_api.dictionary.actions.dictionary_actions as dictionary_actions\n"
        "import app.admin_api.dictionary.actions.errors as action_errors\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    dictionary_module_path = app_root / "admin_api" / "dictionary" / "module.py"
    actions_module_path = app_root / "admin_api" / "dictionary" / "actions" / "module.py"
    nested_module_path = app_root / "admin_api" / "dictionary" / "routers" / "module.py"
    dictionary_module_path.parent.mkdir(parents=True)
    actions_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    dictionary_module_path.write_text(
        "from .actions.dictionary_actions import AdminDictionaryActionService\n"
        "from .actions.errors import AdminDictionaryActionError\n",
        encoding="utf-8",
    )
    actions_module_path.write_text(
        "from .dictionary_actions import AdminDictionaryActionService\n"
        "from .errors import AdminDictionaryActionError\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..actions.dictionary_actions import AdminDictionaryActionService\n"
        "from ..actions.errors import AdminDictionaryActionError\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, "app.admin_api.dictionary.actions") == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        dictionary_module_path,
        "app.admin_api.dictionary.actions",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        actions_module_path,
        "app.admin_api.dictionary.actions",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.dictionary.actions",
    ) == [1, 2]


def test_retired_admin_user_actions_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.users.actions import AdminUserActionService\n"
        "from app.admin_api.users.actions import AdminUserActionService as ActionService\n"
        "import app.admin_api.users.actions\n"
        "import app.admin_api.users.actions as user_actions_package\n"
        "from app.admin_api.users import actions\n"
        "from app.admin_api.users import actions as actions_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    users_module_path = app_root / "admin_api" / "users" / "module.py"
    nested_module_path = app_root / "admin_api" / "users" / "routers" / "module.py"
    users_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    users_module_path.write_text(
        "from .actions import AdminUserActionService\n"
        "from . import actions\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..actions import AdminUserActionService\n"
        "from .. import actions\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, "app.admin_api.users.actions") == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert _concrete_module_import_lines(
        users_module_path,
        "app.admin_api.users.actions",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.users.actions",
    ) == [1, 2]


def test_retired_admin_user_actions_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.users.actions.user_actions import AdminUserActionService\n"
        "from app.admin_api.users.actions.errors import AdminUserActionError\n"
        "import app.admin_api.users.actions.user_actions as user_actions\n"
        "import app.admin_api.users.actions.errors as action_errors\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    users_module_path = app_root / "admin_api" / "users" / "module.py"
    actions_module_path = app_root / "admin_api" / "users" / "actions" / "module.py"
    nested_module_path = app_root / "admin_api" / "users" / "routers" / "module.py"
    users_module_path.parent.mkdir(parents=True)
    actions_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    users_module_path.write_text(
        "from .actions.user_actions import AdminUserActionService\n"
        "from .actions.errors import AdminUserActionError\n",
        encoding="utf-8",
    )
    actions_module_path.write_text(
        "from .user_actions import AdminUserActionService\n"
        "from .errors import AdminUserActionError\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..actions.user_actions import AdminUserActionService\n"
        "from ..actions.errors import AdminUserActionError\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, "app.admin_api.users.actions") == [1, 2, 3, 4]
    assert _concrete_module_import_lines(
        users_module_path,
        "app.admin_api.users.actions",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        actions_module_path,
        "app.admin_api.users.actions",
    ) == [1, 2]
    assert _concrete_module_import_lines(
        nested_module_path,
        "app.admin_api.users.actions",
    ) == [1, 2]


def test_retired_admin_user_dictionary_actions_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    package_name = "app.admin_api.user_dictionary.actions"
    module_path.write_text(
        "from app.admin_api.user_dictionary.actions import AdminUserDictionaryBulkAction\n"
        "from app.admin_api.user_dictionary.actions import AdminUserDictionaryPromoteAction as PromoteAction\n"
        "from app.admin_api.user_dictionary.actions import errors\n"
        "import app.admin_api.user_dictionary.actions\n"
        "import app.admin_api.user_dictionary.actions as user_dictionary_actions_package\n"
        "from app.admin_api.user_dictionary import actions\n"
        "from app.admin_api.user_dictionary import actions as actions_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    user_dictionary_module_path = app_root / "admin_api" / "user_dictionary" / "module.py"
    actions_module_path = app_root / "admin_api" / "user_dictionary" / "actions" / "module.py"
    nested_module_path = app_root / "admin_api" / "user_dictionary" / "routers" / "module.py"
    user_dictionary_module_path.parent.mkdir(parents=True)
    actions_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    user_dictionary_module_path.write_text(
        "from .actions import AdminUserDictionaryBulkAction\n"
        "from . import actions\n",
        encoding="utf-8",
    )
    actions_module_path.write_text(
        "from . import bulk\n"
        "from . import errors\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..actions import AdminUserDictionaryPromoteAction\n"
        "from .. import actions\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, package_name) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert _concrete_module_import_lines(user_dictionary_module_path, package_name) == [1, 2]
    assert _concrete_module_import_lines(actions_module_path, package_name) == [1, 2]
    assert _concrete_module_import_lines(nested_module_path, package_name) == [1, 2]


def test_retired_admin_user_dictionary_actions_import_detection_catches_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    package_name = "app.admin_api.user_dictionary.actions"
    module_path.write_text(
        "from app.admin_api.user_dictionary.actions.bulk import AdminUserDictionaryBulkAction\n"
        "from app.admin_api.user_dictionary.actions.errors import AdminUserDictionaryActionError\n"
        "from app.admin_api.user_dictionary.actions.promote import AdminUserDictionaryPromoteAction\n"
        "import app.admin_api.user_dictionary.actions.bulk as bulk_actions\n"
        "import app.admin_api.user_dictionary.actions.errors as action_errors\n"
        "import app.admin_api.user_dictionary.actions.promote as promote_actions\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    user_dictionary_module_path = app_root / "admin_api" / "user_dictionary" / "module.py"
    actions_module_path = app_root / "admin_api" / "user_dictionary" / "actions" / "module.py"
    nested_module_path = app_root / "admin_api" / "user_dictionary" / "routers" / "module.py"
    user_dictionary_module_path.parent.mkdir(parents=True)
    actions_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    user_dictionary_module_path.write_text(
        "from .actions.bulk import AdminUserDictionaryBulkAction\n"
        "from .actions.errors import AdminUserDictionaryActionError\n"
        "from .actions.promote import AdminUserDictionaryPromoteAction\n",
        encoding="utf-8",
    )
    actions_module_path.write_text(
        "from .bulk import AdminUserDictionaryBulkAction\n"
        "from .errors import AdminUserDictionaryActionError\n"
        "from .promote import AdminUserDictionaryPromoteAction\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..actions.bulk import AdminUserDictionaryBulkAction\n"
        "from ..actions.errors import AdminUserDictionaryActionError\n"
        "from ..actions.promote import AdminUserDictionaryPromoteAction\n",
        encoding="utf-8",
    )

    assert _concrete_module_import_lines(module_path, package_name) == [1, 2, 3, 4, 5, 6]
    assert _concrete_module_import_lines(user_dictionary_module_path, package_name) == [1, 2, 3]
    assert _concrete_module_import_lines(actions_module_path, package_name) == [1, 2, 3]
    assert _concrete_module_import_lines(nested_module_path, package_name) == [1, 2, 3]


def test_user_import_helpers_package_facade_import_detection_catches_broad_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.user_import.helpers import resolve_job_user_uuid\n"
        "from app.user_import.helpers import resolve_job_user_uuid as resolve_user_uuid\n"
        "import app.user_import.helpers\n"
        "import app.user_import.helpers as user_import_helpers\n"
        "from app.user_import import helpers\n"
        "from app.user_import import helpers as helper_package\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    user_import_module_path = app_root / "user_import" / "module.py"
    nested_module_path = app_root / "user_import" / "services" / "module.py"
    user_import_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    user_import_module_path.write_text(
        "from .helpers import resolve_job_user_uuid\n"
        "from . import helpers\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..helpers import resolve_job_user_uuid\n"
        "from .. import helpers\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.user_import.helpers") == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert _package_facade_import_lines(
        user_import_module_path,
        "app.user_import.helpers",
    ) == [1, 2]
    assert _package_facade_import_lines(
        nested_module_path,
        "app.user_import.helpers",
    ) == [1, 2]


def test_user_import_helpers_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.user_import.helpers.job_identity import resolve_job_user_uuid\n"
        "import app.user_import.helpers.job_identity as job_identity\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    user_import_module_path = app_root / "user_import" / "module.py"
    helpers_module_path = app_root / "user_import" / "helpers" / "module.py"
    nested_module_path = app_root / "user_import" / "services" / "module.py"
    user_import_module_path.parent.mkdir(parents=True)
    helpers_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    user_import_module_path.write_text(
        "from .helpers.job_identity import resolve_job_user_uuid\n",
        encoding="utf-8",
    )
    helpers_module_path.write_text(
        "from .job_identity import resolve_job_user_uuid\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..helpers.job_identity import resolve_job_user_uuid\n",
        encoding="utf-8",
    )

    assert _package_facade_import_lines(module_path, "app.user_import.helpers") == []
    assert _package_facade_import_lines(
        user_import_module_path,
        "app.user_import.helpers",
    ) == []
    assert _package_facade_import_lines(
        helpers_module_path,
        "app.user_import.helpers",
    ) == []
    assert _package_facade_import_lines(
        nested_module_path,
        "app.user_import.helpers",
    ) == []


def test_user_import_package_facade_import_detection_catches_direct_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.user_import import UserImportIntakeService\n"
        "import app.user_import\n"
        "import app.user_import as user_import\n"
        "from app import user_import\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "composition" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .user_import import UserImportIntakeService\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..user_import import UserImportIntakeService\n",
        encoding="utf-8",
    )

    assert _user_import_package_facade_import_lines(module_path) == [1, 2, 3, 4]
    assert _user_import_package_facade_import_lines(root_module_path) == [1]
    assert _user_import_package_facade_import_lines(nested_module_path) == [1]


def test_user_import_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.user_import.services.intake_service import UserImportIntakeService\n"
        "from app.user_import.providers import WORD_AUDIO_TASK_KEY\n"
        "from app.user_import.settings import USER_IMPORT_MAX_JOBS_PER_RUN\n"
        "import app.user_import.services.intake_service\n",
        encoding="utf-8",
    )

    assert _user_import_package_facade_import_lines(module_path) == []


def test_app_tests_and_scripts_do_not_import_user_import_services_package_facade() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _user_import_services_package_facade_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_user_import_services_package_facade_import_detection_catches_direct_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.user_import.services import UserImportPreparationService\n"
        "import app.user_import.services\n"
        "import app.user_import.services as services\n"
        "from app.user_import import services\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "user_import" / "module.py"
    nested_module_path = app_root / "user_import" / "subpkg" / "module.py"
    root_module_path.parent.mkdir(parents=True)
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .services import UserImportPreparationService\n"
        "from . import services\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..services import UserImportPreparationService\n",
        encoding="utf-8",
    )

    assert _user_import_services_package_facade_import_lines(module_path) == [1, 2, 3, 4]
    assert _user_import_services_package_facade_import_lines(root_module_path) == [1, 2]
    assert _user_import_services_package_facade_import_lines(nested_module_path) == [1]


def test_user_import_services_package_facade_import_detection_allows_submodule_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.user_import.services.preparation_service import UserImportPreparationService\n"
        "from app.user_import.services.pending_import_enrichment import ImportEnrichmentResult\n"
        "import app.user_import.services.pending_import_enrichment as pending_import_enrichment\n",
        encoding="utf-8",
    )

    assert _user_import_services_package_facade_import_lines(module_path) == []


def test_legacy_repository_placeholder_import_detection_catches_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "import app.repositories\n"
        "import app.repositories.submodule\n"
        "from app.repositories import RepositoryBundle\n"
        "from app import repositories\n",
        encoding="utf-8",
    )
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "client_api" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .repositories import RepositoryBundle\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..repositories import RepositoryBundle\n",
        encoding="utf-8",
    )

    assert _legacy_repositories_import_lines(module_path) == [1, 2, 3, 4]
    assert _legacy_repositories_import_lines(root_module_path) == [1]
    assert _legacy_repositories_import_lines(nested_module_path) == [1]


def test_learning_service_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.learning_service import LearningService\n"
        "from app.learning_service.submodule import X\n"
        "from app import learning_service\n"
        "import app.learning_service\n"
        "import app.learning_service.submodule\n",
        encoding="utf-8",
    )

    assert _learning_service_import_lines(module_path) == [1, 2, 3, 4, 5]


def test_learning_service_import_detection_catches_relative_imports(
    tmp_path: Path, monkeypatch
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "client_api" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text("from .learning_service import LearningService\n", encoding="utf-8")
    nested_module_path.write_text("from ..learning_service import LearningService\n", encoding="utf-8")

    assert _learning_service_import_lines(root_module_path) == [1]
    assert _learning_service_import_lines(nested_module_path) == [1]


def test_app_tests_scripts_and_word_base_do_not_import_user_imports_legacy_facade() -> None:
    offenders = []
    for path in _user_imports_facade_scan_paths():
        relative_path = path.relative_to(APP_ROOT.parent)
        import_lines = _user_imports_facade_import_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_user_imports_facade_scan_skips_ignored_word_base_drafts(
    tmp_path: Path, monkeypatch
) -> None:
    module = __import__(__name__, fromlist=["WORD_BASE_ROOT"])
    word_base_root = tmp_path / "word_base"
    utility_path = word_base_root / "maintenance.py"
    ignored_draft_path = word_base_root / "reading_listening" / "draft.py"
    ignored_draft_path.parent.mkdir(parents=True)
    utility_path.write_text("print('ok')\n", encoding="utf-8")
    ignored_draft_path.write_text("import app.user_imports\n", encoding="utf-8")
    monkeypatch.setattr(module, "WORD_BASE_ROOT", word_base_root)

    assert list(_word_base_user_imports_facade_scan_paths()) == [utility_path]


def test_app_tests_scripts_and_word_base_do_not_static_import_admin_service_retired_facade() -> None:
    offenders = []
    for path in _admin_service_facade_scan_paths():
        relative_path = path.relative_to(APP_ROOT.parent)
        import_lines = _admin_service_facade_import_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_production_code_does_not_import_runtime_state_database_facade() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        import_lines = _specific_module_import_lines(path, {RUNTIME_STATE_FACADE_MODULE})
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_production_code_uses_app_runtime_state_repository_not_database_facade_methods() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        call_lines = _runtime_state_database_facade_method_call_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in call_lines)

    assert offenders == []


def test_production_code_does_not_import_removed_log_database_facades() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        import_lines = _database_log_facade_import_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_production_code_uses_log_repositories_not_removed_database_facade_methods() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        call_lines = _database_log_facade_method_call_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in call_lines)

    assert offenders == []


def test_production_code_does_not_import_removed_bot_message_database_facade() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        import_lines = _bot_message_database_facade_import_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_production_code_uses_bot_message_repository_not_removed_database_facade_methods() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        call_lines = _bot_message_database_facade_method_call_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in call_lines)

    assert offenders == []


def test_production_code_does_not_import_database_facades() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        import_lines = _db_facade_import_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_production_code_uses_admin_auth_repository_not_removed_database_facade_methods() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        call_lines = _admin_auth_database_facade_method_call_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in call_lines)

    assert offenders == []


def test_admin_auth_database_facade_method_detection_uses_old_database_method_names(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "def calls(self, db):\n"
        "    db.get_active_admin_session_by_token_hash(lambda value: True, current_time)\n"
        "    self.db.touch_admin_session(1, current_time)\n"
        "    db.admin_auth.get_active_session_by_token_hash(lambda value: True, current_time)\n"
        "    db.admin_auth.touch_session(1, current_time)\n",
        encoding="utf-8",
    )

    assert _admin_auth_database_facade_method_call_lines(module_path) == [2, 3]


def test_database_facade_modules_are_removed() -> None:
    facade_modules = [
        path.relative_to(APP_ROOT.parent).as_posix()
        for path in sorted(DB_FACADES_ROOT.glob("*.py"))
        if path.name != "__init__.py"
    ]

    assert facade_modules == []


def test_database_provider_exposes_repositories_not_business_facade_methods() -> None:
    relative_path = DATA_ACCESS_PROVIDER_MODULE.relative_to(APP_ROOT.parent)
    offenders = [
        f"{relative_path.as_posix()}:{line}: {method_name}"
        for line, method_name in _database_provider_public_non_property_method_lines(
            DATA_ACCESS_PROVIDER_MODULE
        )
        if method_name not in DATABASE_PROVIDER_ALLOWED_PUBLIC_NON_PROPERTY_METHODS
    ]

    assert offenders == []


def test_database_provider_public_method_detection_ignores_properties_and_private_methods(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "provider.py"
    source = (
        "class Database:\n"
        "    def __init__(self):\n"
        "        pass\n"
        "\n"
        "    @property\n"
        "    def user_dictionary(self):\n"
        "        return object()\n"
        "\n"
        "    def close(self):\n"
        "        pass\n"
        "\n"
        "    def create_user_profile(self):\n"
        "        pass\n"
        "\n"
        "    def _private_helper(self):\n"
        "        pass\n"
    )
    module_path.write_text(source, encoding="utf-8")
    business_method_line = next(
        line_number
        for line_number, line in enumerate(source.splitlines(), start=1)
        if "def create_user_profile" in line
    )

    method_lines = _database_provider_public_non_property_method_lines(module_path)
    method_names = {method_name for _, method_name in method_lines}

    assert (business_method_line, "create_user_profile") in method_lines
    assert "user_dictionary" not in method_names
    assert "_private_helper" not in method_names


def test_app_package_entrypoint_remains_minimal_package_marker() -> None:
    assert _minimal_package_facade_shape_violations(APP_PACKAGE_MARKER_MODULE) == []


def test_storage_package_entrypoint_reexports_audio_provider_boundary() -> None:
    tree = ast.parse(
        STORAGE_PACKAGE_ENTRYPOINT_MODULE.read_text(encoding="utf-8"),
        filename=str(STORAGE_PACKAGE_ENTRYPOINT_MODULE),
    )

    assert (
        _explicit_reexport_wrapper_shape_violations(
            STORAGE_PACKAGE_ENTRYPOINT_MODULE,
            "app.storage.audio",
        )
        == []
    )
    assert set(_module_all_names(tree)) == AUDIO_STORAGE_PROVIDER_IMPORT_NAMES


def test_audio_storage_provider_protocol_does_not_expose_filesystem_path_resolution() -> None:
    protocol_methods = _class_public_method_names(AUDIO_STORAGE_MODULE, "AudioStorageProvider")

    assert "resolve_local_path" not in protocol_methods


def test_models_package_entrypoint_is_controlled_orm_model_export_hub() -> None:
    assert (
        _controlled_model_export_hub_shape_violations(MODELS_PACKAGE_ENTRYPOINT_MODULE)
        == []
    )


def test_controlled_model_export_hub_shape_allows_small_valid_hub(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "__init__.py"
    module_path.write_text(
        '"""ORM model exports."""\n'
        "from app.models.base import Base\n"
        "from app.models.user import User\n"
        "\n"
        '__all__ = ["Base", "User"]\n',
        encoding="utf-8",
    )

    assert _controlled_model_export_hub_shape_violations(module_path) == []


def test_controlled_model_export_hub_shape_catches_unsafe_exports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "__init__.py"
    module_path.write_text(
        "from app.models.base import Base\n"
        "from app.models.user import User as Account\n"
        "from app.models.dictionary import *\n"
        "from app.domain.user import Profile\n"
        "\n"
        '__all__ = ["Base", "User", "Extra"]\n',
        encoding="utf-8",
    )

    assert _controlled_model_export_hub_shape_violations(module_path) == [
        f"{module_path}:2: aliased model export",
        f"{module_path}:3: wildcard model export",
        f"{module_path}:4: unexpected model export source",
        f"{module_path}: __all__ mismatch missing=['Profile'] extra=['Extra']",
    ]


def test_code_does_not_import_legacy_audio_response_helper_path() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _legacy_audio_response_helper_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_runtime_audio_modules_depend_on_audio_storage_provider_boundary() -> None:
    offenders = []
    for path in AUDIO_STORAGE_BOUNDARY_MODULES:
        imported_names = _imported_or_qualified_reference_names_from_module(
            path,
            "app.storage.audio",
            AUDIO_STORAGE_PROVIDER_IMPORT_NAMES,
        )
        if not imported_names:
            offenders.append(path.relative_to(APP_ROOT.parent).as_posix())

    assert offenders == []


def test_application_admin_audio_storage_mutation_services_do_not_bind_filesystem_provider_directly() -> None:
    offenders = []
    for path in APPLICATION_ADMIN_AUDIO_MUTATION_SERVICE_MODULES:
        relative_path = path.relative_to(APP_ROOT.parent)
        reference_lines = _filesystem_audio_storage_provider_reference_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_audio_storage_provider_injection_modules_do_not_bind_filesystem_provider_directly() -> None:
    offenders = []
    for path in AUDIO_STORAGE_PROVIDER_INJECTION_ONLY_MODULES:
        relative_path = path.relative_to(APP_ROOT.parent)
        reference_lines = _filesystem_audio_storage_provider_reference_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_central_audio_storage_factory_clients_do_not_bind_filesystem_provider_directly() -> None:
    offenders = []
    for path in CENTRAL_AUDIO_STORAGE_FACTORY_CLIENT_MODULES:
        relative_path = path.relative_to(APP_ROOT.parent)
        reference_lines = _filesystem_audio_storage_provider_reference_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_app_filesystem_audio_storage_provider_refs_are_limited_to_storage_and_factory_modules() -> None:
    offenders = []
    storage_root = APP_ROOT / "storage"
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path == AUDIO_STORAGE_COMPOSITION_FACTORY_MODULE or path.is_relative_to(storage_root):
            continue
        relative_path = path.relative_to(APP_ROOT.parent)
        reference_lines = _filesystem_audio_storage_provider_reference_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_user_import_google_tts_does_not_bind_filesystem_audio_storage_provider_directly() -> None:
    reference_lines = _filesystem_audio_storage_provider_reference_lines(
        USER_IMPORT_GOOGLE_TTS_PROVIDER_MODULE
    )

    assert reference_lines == []


def test_http_audio_response_helper_does_not_bind_filesystem_audio_storage_provider_directly() -> None:
    module_path = APP_ROOT / "api_helpers" / "audio_response.py"

    assert _filesystem_audio_storage_provider_reference_lines(module_path) == []


def test_app_code_outside_audio_storage_does_not_use_audio_resolve_local_path() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path == AUDIO_STORAGE_MODULE:
            continue
        relative_path = path.relative_to(APP_ROOT.parent)
        reference_lines = _resolve_local_path_attribute_reference_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_audio_storage_resolve_local_path_reference_guard_detects_attribute_use(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "unsafe_audio_service.py"
    module_path.write_text(
        "def unsafe(provider):\n"
        "    provider.resolve_local_path('runtime/audio/word.mp3')\n"
        "    path_resolver = provider.resolve_local_path\n"
        "    text = 'resolve_local_path'\n"
        "    return path_resolver\n",
        encoding="utf-8",
    )

    assert _resolve_local_path_attribute_reference_lines(module_path) == [2, 3]


def test_audio_storage_filesystem_provider_reference_guard_detects_imports_and_references(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "unsafe_audio_service.py"
    module_path.write_text(
        "from app.storage.audio import filesystem_audio_storage_provider as provider\n"
        "from app.storage.audio import FileSystemAudioStorageProvider as Provider\n"
        "import app.storage.audio as audio_storage\n"
        "provider()\n"
        "Provider\n"
        "audio_storage.filesystem_audio_storage_provider\n"
        "audio_storage.FileSystemAudioStorageProvider\n"
        "'filesystem_audio_storage_provider'\n"
        "'FileSystemAudioStorageProvider'\n",
        encoding="utf-8",
    )

    assert _filesystem_audio_storage_provider_reference_lines(module_path) == [
        1,
        2,
        4,
        5,
        6,
        7,
        8,
        9,
    ]


def test_audio_storage_filesystem_provider_reference_guard_detects_storage_facade_imports_and_references(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "unsafe_audio_service.py"
    module_path.write_text(
        "from app.storage import filesystem_audio_storage_provider\n"
        "from app.storage import FileSystemAudioStorageProvider\n"
        "import app.storage as storage\n"
        "storage.filesystem_audio_storage_provider\n"
        "'filesystem_audio_storage_provider'\n"
        "storage.FileSystemAudioStorageProvider\n"
        "'FileSystemAudioStorageProvider'\n",
        encoding="utf-8",
    )

    assert _filesystem_audio_storage_provider_reference_lines(module_path) == [
        1,
        2,
        4,
        5,
        6,
        7,
    ]


def test_bot_runtime_audio_delivery_does_not_bind_filesystem_provider_directly() -> None:
    offenders = []
    for path in BOT_RUNTIME_AUDIO_STORAGE_MODULES:
        relative_path = path.relative_to(APP_ROOT.parent)
        reference_lines = _filesystem_audio_storage_provider_reference_lines(path)
        offenders.extend(
            f"{relative_path.as_posix()}:{line}: filesystem audio storage provider"
            for line in reference_lines
        )

    assert offenders == []


def test_runtime_audio_modules_do_not_mutate_audio_files_directly() -> None:
    offenders = []
    for path in AUDIO_STORAGE_BOUNDARY_MODULES:
        relative_path = path.relative_to(APP_ROOT.parent)
        direct_call_lines = _direct_audio_file_mutation_call_lines(path)
        offenders.extend(
            f"{relative_path.as_posix()}:{line}: {call_name}"
            for line, call_name in direct_call_lines
        )

    assert offenders == []


def test_http_audio_routes_pass_explicit_storage_provider_to_audio_response() -> None:
    offenders = []
    for path in HTTP_AUDIO_RESPONSE_ROUTE_MODULES:
        relative_path = path.relative_to(APP_ROOT.parent)
        missing_provider_lines = _build_audio_response_calls_without_non_null_storage_provider(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in missing_provider_lines)

    assert offenders == []


def test_http_audio_routes_storage_provider_detection_catches_nullable_provider(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "router.py"
    module_path.write_text(
        "from app.api_helpers.audio_response import build_audio_response\n"
        "build_audio_response('runtime/audio/ok.mp3', storage_provider=provider)\n"
        "build_audio_response('runtime/audio/missing.mp3')\n"
        "build_audio_response('runtime/audio/none.mp3', storage_provider=None)\n"
        "build_audio_response('runtime/audio/fallback.mp3', storage_provider=provider or None)\n",
        encoding="utf-8",
    )

    assert _build_audio_response_calls_without_non_null_storage_provider(module_path) == [3, 4, 5]


def test_user_imports_facade_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.user_imports import parse_user_import_text\n"
        "from app.user_imports.submodule import X\n"
        "import app.user_imports as user_imports\n"
        "import app.user_imports.submodule\n"
        "from app import user_imports\n",
        encoding="utf-8",
    )

    assert _user_imports_facade_import_lines(module_path) == [1, 2, 3, 4, 5]


def test_user_imports_facade_import_detection_ignores_strings(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "fixture = 'from app.user_imports import parse_user_import_text'\n",
        encoding="utf-8",
    )

    assert _user_imports_facade_import_lines(module_path) == []


def test_user_imports_facade_import_detection_catches_relative_imports(
    tmp_path: Path, monkeypatch
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "user_import" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text("from .user_imports import parse_user_import_text\n", encoding="utf-8")
    nested_module_path.write_text("from ..user_imports import parse_user_import_text\n", encoding="utf-8")

    assert _user_imports_facade_import_lines(root_module_path) == [1]
    assert _user_imports_facade_import_lines(nested_module_path) == [1]


def test_user_imports_legacy_facade_is_retired_marker() -> None:
    assert _minimal_package_facade_shape_violations(USER_IMPORTS_MODULE) == []


def test_legacy_provider_exports_facade_is_retired_marker() -> None:
    assert _minimal_package_facade_shape_violations(LEGACY_PROVIDER_EXPORTS_MODULE) == []


def test_app_tests_scripts_and_word_base_do_not_import_legacy_provider_exports_facade() -> None:
    offenders = []
    for path in _legacy_provider_exports_facade_scan_paths():
        relative_path = path.relative_to(APP_ROOT.parent)
        import_lines = _legacy_provider_exports_facade_import_lines(path)
        offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_legacy_provider_exports_facade_import_detection_catches_imports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "legacy_provider_exports.py"
    module_path.write_text(
        "from app.user_import.legacy_provider_exports import GoogleDocFetchError\n"
        "from app.user_import.legacy_provider_exports.submodule import Provider\n"
        "import app.user_import.legacy_provider_exports as legacy_provider_exports\n"
        "import app.user_import.legacy_provider_exports.submodule\n"
        "from app.user_import import legacy_provider_exports\n",
        encoding="utf-8",
    )

    assert _legacy_provider_exports_facade_import_lines(module_path) == [1, 2, 3, 4, 5]


def test_legacy_provider_exports_facade_import_detection_ignores_strings(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "fixture = 'from app.user_import.legacy_provider_exports import GoogleDocFetchError'\n",
        encoding="utf-8",
    )

    assert _legacy_provider_exports_facade_import_lines(module_path) == []


def test_legacy_provider_exports_facade_import_detection_catches_relative_imports(
    tmp_path: Path, monkeypatch
) -> None:
    module = __import__(__name__, fromlist=["APP_ROOT"])
    app_root = tmp_path / "app"
    monkeypatch.setattr(module, "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    package_module_path = app_root / "user_import" / "module.py"
    nested_module_path = app_root / "user_import" / "services" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text(
        "from .user_import.legacy_provider_exports import GoogleDocFetchError\n",
        encoding="utf-8",
    )
    package_module_path.write_text(
        "from . import legacy_provider_exports\n",
        encoding="utf-8",
    )
    nested_module_path.write_text(
        "from ..legacy_provider_exports import GoogleDocFetchError\n",
        encoding="utf-8",
    )

    assert _legacy_provider_exports_facade_import_lines(root_module_path) == [1]
    assert _legacy_provider_exports_facade_import_lines(package_module_path) == [1]
    assert _legacy_provider_exports_facade_import_lines(nested_module_path) == [1]


def test_admin_service_facade_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_service import AdminService\n"
        "from app.admin_service.submodule import X\n"
        "from app import admin_service\n"
        "import app.admin_service\n"
        "import app.admin_service.submodule\n",
        encoding="utf-8",
    )

    assert _admin_service_facade_import_lines(module_path) == [1, 2, 3, 4, 5]


def test_admin_service_facade_import_detection_ignores_strings(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "fixture = 'from app.admin_service import AdminService'\n"
        "module_name = 'app.admin_service'\n"
        "service_module = importlib.import_module('app.admin_service')\n",
        encoding="utf-8",
    )

    assert _admin_service_facade_import_lines(module_path) == []


def test_admin_service_facade_import_detection_catches_relative_imports(
    tmp_path: Path, monkeypatch
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    root_module_path = app_root / "module.py"
    nested_module_path = app_root / "admin_api" / "module.py"
    nested_module_path.parent.mkdir(parents=True)
    root_module_path.write_text("from .admin_service import AdminService\n", encoding="utf-8")
    nested_module_path.write_text("from ..admin_service import AdminService\n", encoding="utf-8")

    assert _admin_service_facade_import_lines(root_module_path) == [1]
    assert _admin_service_facade_import_lines(nested_module_path) == [1]


def test_admin_service_retired_facade_is_docstring_only_marker() -> None:
    tree = ast.parse(ADMIN_SERVICE_MODULE.read_text(encoding="utf-8"), filename=str(ADMIN_SERVICE_MODULE))

    assert len(tree.body) == 1
    assert _is_module_docstring_node(tree.body[0])


def test_legacy_audio_response_helper_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.helpers.audio_response import build_audio_response\n"
        "import app.helpers.audio_response\n"
        "import app.helpers.audio_response.submodule\n"
        "from app.helpers.audio_response.submodule import X\n"
        "from app.helpers import audio_response\n"
        "from app.api_helpers.audio_response import build_audio_response\n",
        encoding="utf-8",
    )

    assert _legacy_audio_response_helper_import_lines(module_path) == [1, 2, 3, 4, 5]


def test_lower_layers_and_composition_do_not_import_client_api() -> None:
    offenders = []
    paths = _iter_lower_layer_paths() + sorted((APP_ROOT / "composition").rglob("*.py"))
    for path in paths:
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if _is_client_api_import(module):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_generic_helpers_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(GENERIC_HELPERS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_shared_validators_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(VALIDATORS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_legacy_request_validator_shim_is_retired() -> None:
    assert not LEGACY_REQUEST_VALIDATOR_SHIM_MODULE.exists()


def test_runtime_and_tests_do_not_import_legacy_request_validator_shim() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            relative_path = path.relative_to(APP_ROOT.parent)
            import_lines = _legacy_request_validator_import_lines(path)
            offenders.extend(f"{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_legacy_request_validator_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "import app.validators.request\n"
        "import app.validators.request as request_validator\n"
        "import app.validators.request.submodule\n"
        "from app.validators.request import validate_payload\n"
        "from app.validators.request.submodule import validate_payload\n"
        "from app.validators import request\n"
        "from app.validators import request as request_validator\n",
        encoding="utf-8",
    )

    assert _legacy_request_validator_import_lines(module_path) == [1, 2, 3, 4, 5, 6, 7]


def test_request_value_validators_do_not_import_api_helpers() -> None:
    offenders = [
        f"app/{REQUEST_VALUE_VALIDATORS_MODULE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _api_helper_import_lines(REQUEST_VALUE_VALIDATORS_MODULE)
    ]

    assert offenders == []


def test_lower_layers_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in _iter_lower_layer_paths():
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_auth_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_AUTH_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_auth_modules_do_not_import_interface_or_data_access_packages() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_AUTH_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module in {"app.admin_api", "app.data_access"} or module.startswith(
                ("app.admin_api.", "app.data_access.")
            ):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_auth_collaborators_do_not_import_concrete_database_provider() -> None:
    offenders = []
    for path in APPLICATION_ADMIN_AUTH_COLLABORATOR_MODULES:
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _database_provider_database_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_admin_auth_service_facade_no_longer_owns_extracted_helper_implementation() -> None:
    forbidden_references = {
        "format_otp",
        "hash_token_for_lookup",
        "normalize_admin_target_path",
        "send_tracked_transient_message",
        "validate_password_complexity",
    }
    forbidden_calls = {
        "hmac.compare_digest",
        "urlencode",
    }

    assert _module_reference_name_lines(
        APPLICATION_ADMIN_AUTH_SERVICE_MODULE,
        forbidden_references,
    ) == []
    assert _forbidden_call_name_lines(
        APPLICATION_ADMIN_AUTH_SERVICE_MODULE,
        forbidden_calls,
    ) == []


def test_admin_auth_service_private_helpers_delegate_to_collaborators() -> None:
    method_calls = _class_method_call_names(
        APPLICATION_ADMIN_AUTH_SERVICE_MODULE,
        "AdminAuthService",
    )
    expected_delegate_calls = {
        "_create_session_token": "self.sessions.create_session_token",
        "_set_password_hash": "self.passwords.set_password_hash",
        "_with_auth_flags": "self.passwords.with_auth_flags",
    }

    for method_name, expected_call in expected_delegate_calls.items():
        assert expected_call in method_calls[method_name]


def test_admin_auth_service_exposes_api_public_methods() -> None:
    public_methods = _class_public_method_names(
        APPLICATION_ADMIN_AUTH_SERVICE_MODULE,
        "AdminAuthService",
    )
    required_public_methods = {
        "start_login",
        "verify_otp",
        "create_admin_magic_link_url",
        "consume_magic_link",
        "get_session_user",
        "logout",
        "set_password",
        "update_password",
        "send_otp_message",
        "log_web_login_event",
    }

    assert required_public_methods <= public_methods


def test_admin_composition_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(ADMIN_COMPOSITION_MODULE)
    offenders = [
        f"app/{ADMIN_COMPOSITION_MODULE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_admin_permission_boundary_modules_do_not_import_concrete_database_provider() -> None:
    offenders = []
    for path in (ADMIN_HTTP_PERMISSIONS_MODULE, APPLICATION_ADMIN_PERMISSIONS_MODULE):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _database_provider_database_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_dashboard_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(APPLICATION_ADMIN_DASHBOARD_SERVICE_PATH)
    offenders = [
        f"app/{APPLICATION_ADMIN_DASHBOARD_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_application_admin_dictionary_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(APPLICATION_ADMIN_DICTIONARY_SERVICE_PATH)
    offenders = [
        f"app/{APPLICATION_ADMIN_DICTIONARY_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_application_admin_dictionary_actions_do_not_import_concrete_database_provider() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _database_provider_database_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_user_dictionary_modules_do_not_import_concrete_database_provider() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_USER_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _database_provider_database_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_user_modules_do_not_import_concrete_database_provider() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_USERS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _database_provider_database_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_ai_usage_read_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        APPLICATION_ADMIN_AI_USAGE_READ_SERVICE_PATH
    )
    offenders = [
        f"app/{APPLICATION_ADMIN_AI_USAGE_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_application_admin_billing_read_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        APPLICATION_ADMIN_BILLING_READ_SERVICE_PATH
    )
    offenders = [
        f"app/{APPLICATION_ADMIN_BILLING_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_checkout_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(BILLING_CHECKOUT_SERVICE_PATH)
    offenders = [
        f"app/{BILLING_CHECKOUT_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_checkout_service_does_not_import_subscription_data_access_module() -> None:
    import_lines = _concrete_module_import_lines(
        BILLING_CHECKOUT_SERVICE_PATH,
        "app.data_access.subscriptions",
    )
    offenders = [
        f"app/{BILLING_CHECKOUT_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_add_months_source_of_truth_is_subscription_periods_module() -> None:
    subscription_periods_tree = ast.parse(
        SUBSCRIPTION_PERIODS_MODULE.read_text(encoding="utf-8"),
        filename=str(SUBSCRIPTION_PERIODS_MODULE),
    )
    assert any(
        isinstance(node, ast.FunctionDef) and node.name == "add_months"
        for node in subscription_periods_tree.body
    )

    binding_lines = _top_level_name_binding_lines(
        DATA_ACCESS_SUBSCRIPTIONS_MODULE,
        {"add_months"},
    )
    offenders = [
        f"app/{DATA_ACCESS_SUBSCRIPTIONS_MODULE.relative_to(APP_ROOT).as_posix()}:{line}: {name}"
        for line, name in binding_lines
    ]

    assert offenders == []


def test_paywall_checkout_provider_marker_is_billing_neutral() -> None:
    offenders = []
    for module_path in (
        SUBSCRIPTION_PAYWALL_MODULE,
        APPLICATION_CLIENT_WEB_PLAN_SERVICE_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT).as_posix()
        tree = ast.parse(
            module_path.read_text(encoding="utf-8"),
            filename=str(module_path),
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "mono":
                offenders.append(f"app/{relative_path}:{node.lineno}: literal mono")
            if isinstance(node, ast.Name) and node.id == "CHECKOUT_PROVIDER_MONO":
                offenders.append(
                    f"app/{relative_path}:{node.lineno}: CHECKOUT_PROVIDER_MONO"
                )

    assert offenders == []


def test_billing_history_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(BILLING_HISTORY_SERVICE_PATH)
    offenders = [
        f"app/{BILLING_HISTORY_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_notification_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        BILLING_NOTIFICATION_SERVICE_PATH
    )
    offenders = [
        f"app/{BILLING_NOTIFICATION_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_reconciliation_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        BILLING_RECONCILIATION_SERVICE_PATH
    )
    offenders = [
        f"app/{BILLING_RECONCILIATION_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_reconciliation_service_uses_shared_provider_runtime_boundary() -> None:
    source = BILLING_RECONCILIATION_SERVICE_PATH.read_text(encoding="utf-8")

    assert "resolve_payment_provider_runtime" in source
    assert "_payment_provider_key" not in source
    assert "BILLING_PROVIDER_MONOBANK" not in source


def test_billing_receipt_retrieval_service_uses_shared_provider_runtime_boundary() -> None:
    source = BILLING_RECEIPT_RETRIEVAL_SERVICE_PATH.read_text(encoding="utf-8")

    assert "resolve_payment_provider_runtime" in source
    assert "payment_provider_runtime_is_monobank_test" in source
    assert "_payment_provider_key" not in source
    assert "BILLING_PROVIDER_MONOBANK" not in source
    assert "MONOBANK_MODE_TEST" not in source


def test_billing_webhook_service_uses_shared_provider_runtime_boundary() -> None:
    source = BILLING_WEBHOOK_SERVICE_PATH.read_text(encoding="utf-8")

    assert "resolve_payment_provider_runtime" in source
    assert "provider_runtime.provider_key" in source
    assert "_payment_provider_key" not in source
    assert "BILLING_PROVIDER_MONOBANK" not in source


def test_billing_payment_status_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        BILLING_PAYMENT_STATUS_SERVICE_PATH
    )
    offenders = [
        f"app/{BILLING_PAYMENT_STATUS_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_payment_status_service_keeps_monobank_status_helpers_out() -> None:
    source = BILLING_PAYMENT_STATUS_SERVICE_PATH.read_text(encoding="utf-8")
    import_lines = _concrete_module_import_lines(
        BILLING_PAYMENT_STATUS_SERVICE_PATH,
        "app.domain.billing.monobank_statuses",
    )
    import_offenders = [
        f"app/{BILLING_PAYMENT_STATUS_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]
    forbidden_symbols = [
        "monobank_statuses_domain",
        "apply_monobank_status_payload",
        "normalize_monobank_provider_status",
        "MONOBANK_PROVIDER_STATUSES",
        "MONOBANK_INTERNAL_STATUS_MAP",
    ]
    symbol_offenders = [
        reference for reference in forbidden_symbols if reference in source
    ]

    assert import_offenders == []
    assert symbol_offenders == []
    assert "apply_provider_status_payload" in source


def test_billing_provider_capability_ports_stay_split_by_capability() -> None:
    invoice_status_methods = _class_public_method_names(
        BILLING_PROVIDER_PORT_PATH,
        "BillingInvoiceStatusProviderPort",
    )
    receipt_fiscal_methods = _class_public_method_names(
        BILLING_PROVIDER_PORT_PATH,
        "BillingReceiptFiscalProviderPort",
    )
    public_key_methods = _class_public_method_names(
        BILLING_PROVIDER_PORT_PATH,
        "BillingWebhookPublicKeyProviderPort",
    )

    assert not invoice_status_methods & {
        "get_receipt",
        "fetch_receipt",
        "get_fiscal_checks",
        "fetch_fiscal_checks",
        "get_public_key",
    }
    assert not receipt_fiscal_methods & {
        "create_invoice",
        "get_invoice_status",
        "resolve_payment_status",
        "get_public_key",
    }
    assert public_key_methods == {"get_public_key"}


def test_billing_provider_factory_constructor_annotations_stay_capability_scoped() -> None:
    service_contracts = {
        "BillingPaymentStatusService": (
            BILLING_PAYMENT_STATUS_POLLING_SERVICE_PATH,
            {
                "BillingInvoiceStatusProviderFactory",
                "BillingReceiptFiscalProviderFactory",
            },
        ),
        "BillingReconciliationService": (
            BILLING_RECONCILIATION_SERVICE_PATH,
            {
                "BillingInvoiceStatusProviderFactory",
                "BillingReceiptFiscalProviderFactory",
            },
        ),
        "BillingWebhookService": (
            BILLING_WEBHOOK_SERVICE_PATH,
            {
                "BillingInvoiceStatusProviderFactory",
                "BillingReceiptFiscalProviderFactory",
                "BillingWebhookPublicKeyProviderFactory",
            },
        ),
        "BillingBotNotificationService": (
            BILLING_NOTIFICATION_SERVICE_PATH,
            {"BillingReceiptFiscalProviderFactory"},
        ),
    }
    offenders = []

    for class_name, (path, required_factory_names) in service_contracts.items():
        annotation_names_by_param = _class_init_param_annotation_names(path, class_name)
        annotation_names = {
            name
            for param_annotation_names in annotation_names_by_param.values()
            for name in param_annotation_names
        }
        relative_path = path.relative_to(APP_ROOT).as_posix()
        full_provider_factory_params = [
            param_name
            for param_name, param_annotation_names in annotation_names_by_param.items()
            if "BillingPaymentProviderFactory" in param_annotation_names
        ]

        offenders.extend(
            (
                f"app/{relative_path}:{class_name}.__init__:{param_name}: "
                "uses BillingPaymentProviderFactory"
            )
            for param_name in sorted(full_provider_factory_params)
        )
        offenders.extend(
            f"app/{relative_path}:{class_name}.__init__: missing {factory_name}"
            for factory_name in sorted(required_factory_names - annotation_names)
        )

    assert offenders == []


def test_billing_payment_status_polling_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        BILLING_PAYMENT_STATUS_POLLING_SERVICE_PATH
    )
    offenders = [
        f"app/{BILLING_PAYMENT_STATUS_POLLING_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_fiscal_check_delivery_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        BILLING_FISCAL_CHECK_DELIVERY_PATH
    )
    offenders = [
        f"app/{BILLING_FISCAL_CHECK_DELIVERY_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_receipt_retrieval_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        BILLING_RECEIPT_RETRIEVAL_SERVICE_PATH
    )
    offenders = [
        f"app/{BILLING_RECEIPT_RETRIEVAL_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_billing_webhook_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(BILLING_WEBHOOK_SERVICE_PATH)
    offenders = [
        f"app/{BILLING_WEBHOOK_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_subscription_user_entitlements_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        SUBSCRIPTION_USER_ENTITLEMENTS_PATH
    )
    offenders = [
        f"app/{SUBSCRIPTION_USER_ENTITLEMENTS_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_application_admin_imports_read_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        APPLICATION_ADMIN_IMPORTS_READ_SERVICE_PATH
    )
    offenders = [
        f"app/{APPLICATION_ADMIN_IMPORTS_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_admin_log_read_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        APPLICATION_ADMIN_LOGS_READ_SERVICE_PATH
    )
    offenders = [
        f"app/{APPLICATION_ADMIN_LOGS_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_admin_read_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(APPLICATION_ADMIN_READ_SERVICE_PATH)
    offenders = [
        f"app/{APPLICATION_ADMIN_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_admin_dictionary_read_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        APPLICATION_ADMIN_DICTIONARY_READ_SERVICE_PATH
    )
    offenders = [
        f"app/{APPLICATION_ADMIN_DICTIONARY_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_admin_settings_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        APPLICATION_ADMIN_SETTINGS_SERVICE_PATH
    )
    offenders = [
        f"app/{APPLICATION_ADMIN_SETTINGS_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_application_admin_user_read_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(APPLICATION_ADMIN_USERS_READ_SERVICE_PATH)
    offenders = [
        f"app/{APPLICATION_ADMIN_USERS_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_application_admin_user_dictionary_read_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        APPLICATION_ADMIN_USER_DICTIONARY_READ_SERVICE_PATH
    )
    offenders = [
        f"app/{APPLICATION_ADMIN_USER_DICTIONARY_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_main_entrypoint_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_import_lines(MAIN_MODULE)
    relative_path = MAIN_MODULE.relative_to(APP_ROOT)
    offenders = [f"app/{relative_path.as_posix()}:{line}" for line in import_lines]

    assert offenders == []


def test_billing_reconciliation_worker_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        BILLING_RECONCILIATION_WORKER_MODULE
    )
    relative_path = BILLING_RECONCILIATION_WORKER_MODULE.relative_to(APP_ROOT)
    offenders = [f"app/{relative_path.as_posix()}:{line}" for line in import_lines]

    assert offenders == []


def test_bound_google_doc_sync_worker_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        BOUND_GOOGLE_DOC_SYNC_WORKER_MODULE
    )
    relative_path = BOUND_GOOGLE_DOC_SYNC_WORKER_MODULE.relative_to(APP_ROOT)
    offenders = [f"app/{relative_path.as_posix()}:{line}" for line in import_lines]

    assert offenders == []


def test_embedding_worker_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_import_lines(EMBEDDING_WORKER_MODULE)
    relative_path = EMBEDDING_WORKER_MODULE.relative_to(APP_ROOT)
    offenders = [f"app/{relative_path.as_posix()}:{line}" for line in import_lines]

    assert offenders == []


def test_subscription_maintenance_worker_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        SUBSCRIPTION_MAINTENANCE_WORKER_MODULE
    )
    relative_path = SUBSCRIPTION_MAINTENANCE_WORKER_MODULE.relative_to(APP_ROOT)
    offenders = [f"app/{relative_path.as_posix()}:{line}" for line in import_lines]

    assert offenders == []


def test_import_scheduler_worker_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        IMPORT_SCHEDULER_WORKER_MODULE
    )
    relative_path = IMPORT_SCHEDULER_WORKER_MODULE.relative_to(APP_ROOT)
    offenders = [f"app/{relative_path.as_posix()}:{line}" for line in import_lines]

    assert offenders == []


def test_post_upgrade_rescan_worker_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        POST_UPGRADE_RESCAN_WORKER_MODULE
    )
    relative_path = POST_UPGRADE_RESCAN_WORKER_MODULE.relative_to(APP_ROOT)
    offenders = [f"app/{relative_path.as_posix()}:{line}" for line in import_lines]

    assert offenders == []


def test_database_provider_imports_are_confined_to_composition_root() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path == COMPOSITION_ROOT_MODULE:
            continue
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _database_provider_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_composition_root_stays_a_thin_orchestration_entrypoint() -> None:
    offenders = []
    relative_path = COMPOSITION_ROOT_MODULE.relative_to(APP_ROOT)
    for line, module in _direct_import_modules(COMPOSITION_ROOT_MODULE):
        if _is_composition_root_allowed_import(module):
            continue
        offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_composition_root_import_detection_catches_top_level_app_wildcard(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text("from app import *\n", encoding="utf-8")

    import_modules = _direct_import_modules(module_path)

    assert import_modules == [(1, "app")]
    assert [
        f"{line}: {module}"
        for line, module in import_modules
        if not _is_composition_root_allowed_import(module)
    ] == ["1: app"]


def test_database_provider_database_import_detection_catches_concrete_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    module_path = app_root / "user_import" / "services" / "summary_service.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text(
        "from app.data_access.provider import Database\n"
        "import app.data_access.provider\n"
        "from app.data_access.provider import Database as ProviderDatabase\n"
        "from app.data_access import provider\n"
        "from app.data_access import provider as data_provider\n"
        "from app.data_access.provider import create_database\n"
        "from app.data_access import repositories\n"
        "import app.data_access\n"
        "from ...data_access.provider import Database\n"
        "from ...data_access.provider import Database as RelativeProviderDatabase\n"
        "from ...data_access import provider\n"
        "from ...data_access import provider as relative_data_provider\n"
        "from ...data_access.provider import create_database\n"
        "from ...data_access import repositories\n",
        encoding="utf-8",
    )

    assert _database_provider_database_import_lines(module_path) == [
        1,
        2,
        3,
        4,
        5,
        9,
        10,
        11,
        12,
    ]


def test_database_provider_import_detection_catches_any_provider_imports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_root = tmp_path / "app"
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)
    module_path = app_root / "user_import" / "services" / "summary_service.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text(
        "from app.data_access.provider import create_database\n"
        "from app.data_access.provider import Database\n"
        "import app.data_access.provider\n"
        "from app.data_access import provider\n"
        "from app.data_access import provider as data_provider\n"
        "from app.data_access import repositories\n"
        "import app.data_access\n"
        "from ...data_access.provider import create_database\n"
        "from ...data_access.provider import Database\n"
        "from ...data_access import provider\n"
        "from ...data_access import provider as relative_data_provider\n"
        "from ...data_access import repositories\n",
        encoding="utf-8",
    )

    assert _database_provider_import_lines(module_path) == [1, 2, 3, 4, 5, 8, 9, 10, 11]


def test_user_import_bound_google_doc_sync_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_bound_google_doc_sync_processor_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_PROCESSOR_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_PROCESSOR_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_post_upgrade_google_doc_rescan_service_does_not_import_concrete_data_access() -> None:
    offenders = []
    for path in (
        USER_IMPORT_POST_UPGRADE_GOOGLE_DOC_RESCAN_SERVICE_PATH,
        USER_IMPORT_POST_UPGRADE_GOOGLE_DOC_RESCAN_QUEUE_SERVICE_PATH,
    ):
        import_lines = sorted(
            set(
                _database_provider_import_lines(path)
                + _concrete_module_import_lines(path, "app.data_access")
                + _concrete_module_import_lines(path, "app.models")
                + _concrete_module_import_lines(path, "sqlalchemy")
                + _legacy_repositories_import_lines(path)
            )
        )
        offenders.extend(
            f"app/{path.relative_to(APP_ROOT).as_posix()}:{line}"
            for line in import_lines
        )

    assert offenders == []


def test_user_import_post_upgrade_google_doc_rescan_facade_delegates_queue_workflow() -> None:
    _, method_names = _class_member_names(
        USER_IMPORT_POST_UPGRADE_GOOGLE_DOC_RESCAN_SERVICE_PATH,
        "UserImportPostUpgradeGoogleDocRescanService",
    )
    queue_workflow_methods = {
        "_queue_missing_post_upgrade_rescans",
        "_create_post_upgrade_rescan_task",
        "_process_post_upgrade_rescan_task",
        "_has_existing_post_upgrade_rescan",
        "_has_successful_post_upgrade_rescan",
    }

    assert method_names.isdisjoint(queue_workflow_methods)


def test_user_import_bound_google_doc_sync_processor_uses_explicit_import_dependencies() -> None:
    offenders = _source_fragment_offenders(
        USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_PROCESSOR_PATH,
        (
            "UserEntitlementResolver",
            "UserImportCandidateFilterService",
            "read_user_import_runtime_settings",
            "DEFAULT_IMPORT_RUNTIME_SETTINGS",
            "log_user_import_pipeline_error",
        ),
    )

    assert offenders == []


def test_user_import_bound_google_doc_sync_processor_delegates_validation_and_progress_helpers() -> None:
    processor_source = USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_PROCESSOR_PATH.read_text(
        encoding="utf-8"
    )
    _, processor_methods = _class_member_names(
        USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_PROCESSOR_PATH,
        "UserImportBoundGoogleDocSyncProcessor",
    )
    _, validation_methods = _class_member_names(
        USER_IMPORT_INTAKE_MANUAL_BIND_VALIDATION_SERVICE_PATH,
        "UserImportManualBindValidationService",
    )
    _, progress_methods = _class_member_names(
        USER_IMPORT_INTAKE_MANUAL_BIND_PROGRESS_SERVICE_PATH,
        "UserImportManualBindProgressService",
    )
    moved_processor_methods = {
        "_validate_parsed_words",
        "_record_validation_usage",
        "_validation_rejected_fragments",
        "_mark_google_doc_progress",
    }

    assert processor_methods.isdisjoint(moved_processor_methods)
    assert {
        "validate_parsed_words",
        "record_usage",
        "rejected_fragments",
    }.issubset(validation_methods)
    assert "mark_google_doc_progress" in progress_methods
    assert "IMPORT_MODE_LOOKUP_ONLY" not in processor_source
    assert "progress_checkpoint_for_scope" not in processor_source
    assert "UserImportValidationOutcome" not in processor_source


def test_user_import_bound_google_doc_sync_service_does_not_import_concrete_intake_service() -> None:
    offenders = _source_fragment_offenders(
        USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_SERVICE_PATH,
        (
            "UserImportIntakeService",
            "app.user_import.services.intake_service",
            "from .intake_service",
            "from app.user_import.services import intake_service",
            "import app.user_import.services.intake_service",
        ),
    )

    assert offenders == []


def test_user_import_bound_google_doc_sync_methods_live_on_processor_not_intake_service() -> None:
    _, intake_methods = _class_member_names(
        USER_IMPORT_INTAKE_SERVICE_PATH,
        "UserImportIntakeService",
    )
    _, processor_methods = _class_member_names(
        USER_IMPORT_BOUND_GOOGLE_DOC_SYNC_PROCESSOR_PATH,
        "UserImportBoundGoogleDocSyncProcessor",
    )
    scheduled_sync_methods = {
        "process_bound_google_doc_sync_row",
        "mark_bound_google_doc_sync_failed",
    }

    assert scheduled_sync_methods.isdisjoint(intake_methods)
    assert scheduled_sync_methods.issubset(processor_methods)


def test_user_import_intake_job_methods_live_on_job_service() -> None:
    _, job_service_methods = _class_member_names(
        USER_IMPORT_INTAKE_JOB_SERVICE_PATH,
        "UserImportIntakeJobService",
    )
    job_methods = {
        "build_user_import_intake_snapshot",
        "get_user_import_intake_snapshot",
        "create_user_import_job_from_words",
        "_normalize_nonempty_strings",
    }

    assert job_methods.issubset(job_service_methods)


def test_user_import_intake_service_does_not_write_job_storage_snapshots() -> None:
    offenders = _source_fragment_offenders(
        USER_IMPORT_INTAKE_SERVICE_PATH,
        (
            "build_import_storage_path",
            "build_import_snapshot",
            "write_json_atomic",
            "app_user_import_storage_dir",
        ),
    )

    assert offenders == []


def test_user_import_intake_job_service_delegates_snapshot_storage_to_provider() -> None:
    init_annotations = _class_init_param_annotation_names(
        USER_IMPORT_INTAKE_JOB_SERVICE_PATH,
        "UserImportIntakeJobService",
    )
    offenders = _source_fragment_offenders(
        USER_IMPORT_INTAKE_JOB_SERVICE_PATH,
        (
            "app_user_import_storage_dir",
            "build_import_storage_path",
            "write_json_atomic",
        ),
    )

    assert init_annotations.get("artifact_storage_provider") == {
        "UserImportArtifactStorageProvider"
    }
    assert offenders == []


def test_user_import_intake_job_service_call_sites_pass_artifact_storage_provider() -> None:
    offenders = []
    for root in (APP_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            import_aliases = _import_alias_map(module, path)
            relative_path = path.relative_to(APP_ROOT.parent)
            for node in ast.walk(module):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _resolve_import_alias_name(
                    _attribute_chain_name(node.func),
                    import_aliases,
                )
                if call_name not in {
                    "UserImportIntakeJobService",
                    "app.user_import.services.intake_job_service.UserImportIntakeJobService",
                }:
                    continue
                keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
                if "artifact_storage_provider" not in keyword_names:
                    offenders.append(f"{relative_path.as_posix()}:{node.lineno}")

    assert offenders == []


def test_user_import_document_service_delegates_artifact_writes_to_provider() -> None:
    init_annotations = _class_init_param_annotation_names(
        USER_IMPORT_DOCUMENT_SERVICE_PATH,
        "UserImportDocumentService",
    )
    offenders = _source_fragment_offenders(
        USER_IMPORT_DOCUMENT_SERVICE_PATH,
        (
            "write_text_atomic",
            "with_name(",
        ),
    )

    assert init_annotations.get("artifact_storage_provider") == {
        "UserImportArtifactStorageProvider"
    }
    assert offenders == []


def test_client_web_import_service_call_sites_pass_artifact_storage_provider() -> None:
    offenders = []
    for root in (APP_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            import_aliases = _import_alias_map(module, path)
            relative_path = path.relative_to(APP_ROOT.parent)
            for node in ast.walk(module):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _resolve_import_alias_name(
                    _attribute_chain_name(node.func),
                    import_aliases,
                )
                if call_name not in {
                    "ClientWebImportService",
                    "app.application.client_web.import_service.ClientWebImportService",
                }:
                    continue
                keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
                if "artifact_storage_provider" not in keyword_names:
                    offenders.append(f"{relative_path.as_posix()}:{node.lineno}")

    assert offenders == []


def test_user_import_artifact_filesystem_writes_stay_behind_storage_provider() -> None:
    forbidden_fragments = (
        "build_import_storage_path",
        "write_json_atomic",
        "write_text_atomic",
    )
    offenders = []
    for path in (
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        USER_IMPORT_INTAKE_JOB_SERVICE_PATH,
        USER_IMPORT_DOCUMENT_SERVICE_PATH,
    ):
        offenders.extend(_source_fragment_offenders(path, forbidden_fragments))

    assert offenders == []


def test_pending_import_enrichment_provider_payload_writes_stay_behind_artifact_storage_provider() -> None:
    offenders = _source_fragment_offenders(
        PENDING_IMPORT_ENRICHMENT_MODULE,
        (
            "app.helpers.user_import_storage",
            "Path",
            "write_json_atomic",
            "build_source_payload_path",
        ),
    )
    init_annotations = _class_init_param_annotation_names(
        USER_IMPORT_COLLECTING_RESOLVER_MODULE,
        "UserImportCollectingResolver",
    )
    source = USER_IMPORT_COLLECTING_RESOLVER_MODULE.read_text(encoding="utf-8")

    assert offenders == []
    assert init_annotations.get("artifact_storage_provider") == {
        "UserImportArtifactStorageProvider"
    }
    assert "artifact_storage_provider=self.artifact_storage_provider" in source


def test_resolve_pending_import_word_depends_on_artifact_storage_provider() -> None:
    module = ast.parse(
        PENDING_IMPORT_ENRICHMENT_MODULE.read_text(encoding="utf-8"),
        filename=str(PENDING_IMPORT_ENRICHMENT_MODULE),
    )
    function_node = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_pending_import_word"
    )
    keyword_param_names = {param.arg for param in function_node.args.kwonlyargs}
    annotations = {
        param.arg: _annotation_names(param.annotation)
        for param in function_node.args.kwonlyargs
    }

    assert "artifact_storage_provider" in keyword_param_names
    assert annotations["artifact_storage_provider"] == {
        "UserImportArtifactStorageProvider"
    }


def test_pending_import_enrichment_does_not_accept_audio_build_inputs() -> None:
    offenders = _source_fragment_offenders(
        PENDING_IMPORT_ENRICHMENT_MODULE,
        (
            "audio_dir",
            "storage_dir",
            "WordAudioProvider",
            "google_tts_language_code",
            "google_tts_voice_name",
        ),
    )

    assert offenders == []


def test_user_import_runtime_service_does_not_own_import_storage_paths() -> None:
    offenders = _source_fragment_offenders(
        USER_IMPORT_RUNTIME_SERVICE_PATH,
        (
            "from pathlib import Path",
            "Path(",
            "app_user_import_storage_dir",
            "app_user_import_audio_dir",
        ),
    )

    assert offenders == []


def test_user_import_intake_service_does_not_own_manual_bind_fragments() -> None:
    offenders = _source_fragment_offenders(
        USER_IMPORT_INTAKE_SERVICE_PATH,
        (
            "parse_google_doc_since_progress",
            "progress_checkpoint_for_scope",
            "UserEntitlementResolver",
            "UserImportCandidateFilterService",
            "read_user_import_runtime_settings",
            "DEFAULT_IMPORT_RUNTIME_SETTINGS",
            "manual google doc bind started",
            "_record_validation_usage",
        ),
    )

    assert offenders == []


def test_user_import_intake_manual_bind_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_INTAKE_MANUAL_BIND_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_INTAKE_MANUAL_BIND_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_intake_manual_bind_helpers_own_moved_responsibilities() -> None:
    manual_bind_source = USER_IMPORT_INTAKE_MANUAL_BIND_SERVICE_PATH.read_text(
        encoding="utf-8"
    )
    _, manual_bind_methods = _class_member_names(
        USER_IMPORT_INTAKE_MANUAL_BIND_SERVICE_PATH,
        "UserImportIntakeManualBindService",
    )
    _, validation_methods = _class_member_names(
        USER_IMPORT_INTAKE_MANUAL_BIND_VALIDATION_SERVICE_PATH,
        "UserImportManualBindValidationService",
    )
    _, progress_methods = _class_member_names(
        USER_IMPORT_INTAKE_MANUAL_BIND_PROGRESS_SERVICE_PATH,
        "UserImportManualBindProgressService",
    )
    _, job_submission_methods = _class_member_names(
        USER_IMPORT_INTAKE_MANUAL_BIND_JOB_SUBMISSION_SERVICE_PATH,
        "UserImportManualBindJobSubmissionService",
    )
    moved_manual_bind_methods = {
        "_validate_parsed_words",
        "_record_validation_usage",
        "_validation_rejected_fragments",
        "_mark_google_doc_progress",
    }

    assert manual_bind_methods.isdisjoint(moved_manual_bind_methods)
    assert {
        "validate_parsed_words",
        "record_usage",
        "rejected_fragments",
    }.issubset(validation_methods)
    assert "mark_google_doc_progress" in progress_methods
    assert {
        "create_validated_import_job",
        "finalize_created_import_job",
    }.issubset(job_submission_methods)
    assert "manual google doc bind started" not in manual_bind_source
    assert "manual google doc bind completed" not in manual_bind_source
    assert "prepare_import_job_items(" not in manual_bind_source
    assert "mark_summary_sent(" not in manual_bind_source


def test_user_import_intake_manual_bind_helpers_do_not_import_concrete_database_provider() -> None:
    offenders = []
    for path in (
        USER_IMPORT_INTAKE_MANUAL_BIND_VALIDATION_SERVICE_PATH,
        USER_IMPORT_INTAKE_MANUAL_BIND_PROGRESS_SERVICE_PATH,
        USER_IMPORT_INTAKE_MANUAL_BIND_JOB_SUBMISSION_SERVICE_PATH,
    ):
        import_lines = sorted(
            set(
                _database_provider_import_lines(path)
                + _concrete_module_import_lines(path, "app.data_access")
                + _concrete_module_import_lines(path, "app.models")
                + _concrete_module_import_lines(path, "sqlalchemy")
                + _legacy_repositories_import_lines(path)
            )
        )
        offenders.extend(
            f"app/{path.relative_to(APP_ROOT).as_posix()}:{line}"
            for line in import_lines
        )

    assert offenders == []


def test_user_import_intake_composition_wires_sync_processor_to_job_service() -> None:
    source = USER_IMPORT_INTAKE_COMPOSITION_PATH.read_text(encoding="utf-8")
    offenders = _source_fragment_offenders(
        USER_IMPORT_INTAKE_COMPOSITION_PATH,
        ("intake_job_service=service.user_import_intake_service",),
    )

    assert "service.user_import_intake_job_service = UserImportIntakeJobService(" in source
    assert "intake_job_service=service.user_import_intake_job_service" in source
    assert offenders == []


def test_user_import_intake_composition_wires_manual_bind_service_to_facade() -> None:
    source = USER_IMPORT_INTAKE_COMPOSITION_PATH.read_text(encoding="utf-8")

    assert "service.user_import_intake_manual_bind_service = UserImportIntakeManualBindService(" in source
    assert "manual_bind_service=service.user_import_intake_manual_bind_service" in source


def test_user_import_preparation_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_PREPARATION_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_PREPARATION_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_preparation_service_uses_composed_access_policy() -> None:
    offenders = _source_fragment_offenders(
        USER_IMPORT_PREPARATION_SERVICE_PATH,
        (
            "UserEntitlementResolver",
            "subscriptions",
            "user_profiles",
            "app_settings",
        ),
    )

    assert offenders == []


def test_user_import_preparation_service_call_sites_pass_access_policy() -> None:
    offenders = []
    for root in (APP_ROOT, TESTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            import_aliases = _import_alias_map(module, path)
            relative_path = path.relative_to(APP_ROOT.parent)
            for node in ast.walk(module):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _resolve_import_alias_name(_attribute_chain_name(node.func), import_aliases)
                if call_name not in {
                    "UserImportPreparationService",
                    "app.user_import.services.preparation_service.UserImportPreparationService",
                }:
                    continue
                if len(node.args) < 2 and not any(keyword.arg == "access_policy" for keyword in node.keywords):
                    offenders.append(f"{relative_path}:{node.lineno}")

    assert offenders == []


def test_user_import_job_task_result_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_JOB_TASK_RESULT_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_JOB_TASK_RESULT_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_job_processing_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_JOB_PROCESSING_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_JOB_PROCESSING_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_document_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_DOCUMENT_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_DOCUMENT_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_intake_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(USER_IMPORT_INTAKE_SERVICE_PATH)
    offenders = [
        f"app/{USER_IMPORT_INTAKE_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_intake_job_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(USER_IMPORT_INTAKE_JOB_SERVICE_PATH)
    offenders = [
        f"app/{USER_IMPORT_INTAKE_JOB_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_notification_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_NOTIFICATION_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_NOTIFICATION_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_runtime_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_RUNTIME_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_RUNTIME_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_summary_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_SUMMARY_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_SUMMARY_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_summary_screen_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_SUMMARY_SCREEN_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_SUMMARY_SCREEN_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_summary_screen_service_is_stateless_renderer() -> None:
    source = USER_IMPORT_SUMMARY_SCREEN_SERVICE_PATH.read_text(encoding="utf-8")

    assert "Protocol" not in source
    assert "DatabasePort" not in source
    assert ".db" not in source
    assert "user_import_jobs" not in source
    assert "dictionary_lookup" not in source
    assert "task_logs" not in source


def test_user_import_summary_service_delegates_screen_rendering() -> None:
    source = USER_IMPORT_SUMMARY_SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    direct_screen_construction_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ScreenModel"
    ]

    assert "ButtonModel" not in source
    assert "app.screen_delivery_policy" not in source
    assert "with_delete_after_hours" not in source
    assert "with_documents_only_delivery" not in source
    assert direct_screen_construction_lines == []


def test_user_import_technical_details_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_TECHNICAL_DETAILS_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_TECHNICAL_DETAILS_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_user_dictionary_build_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        USER_IMPORT_USER_DICTIONARY_BUILD_SERVICE_PATH
    )
    offenders = [
        f"app/{USER_IMPORT_USER_DICTIONARY_BUILD_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_user_import_user_dictionary_build_phase_modules_do_not_import_concrete_database_provider() -> None:
    offenders = []
    for path in USER_IMPORT_USER_DICTIONARY_BUILD_PHASE_MODULE_PATHS:
        import_lines = _database_provider_database_import_lines(path)
        relative_path = path.relative_to(APP_ROOT)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_user_import_user_dictionary_build_phase_modules_use_explicit_ports_not_raw_db() -> None:
    offenders = []
    for path, class_name in USER_IMPORT_USER_DICTIONARY_BUILD_PHASE_MODULE_CLASSES:
        relative_path = path.relative_to(APP_ROOT)
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        target_class = next(
            node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name
        )
        init_method = next(
            node
            for node in target_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        for argument in [
            *init_method.args.posonlyargs,
            *init_method.args.args,
            *init_method.args.kwonlyargs,
        ]:
            if argument.arg == "db":
                offenders.append(
                    f"app/{relative_path.as_posix()}:{argument.lineno}:__init__ accepts db"
                )
        for node in ast.walk(target_class):
            if not isinstance(node, ast.Attribute):
                continue
            chain_name = _attribute_chain_name(node)
            if chain_name == "self.db" or (
                chain_name is not None and chain_name.startswith("self.db.")
            ):
                offenders.append(f"app/{relative_path.as_posix()}:{node.lineno}:{chain_name}")

    assert sorted(set(offenders)) == []


def test_user_import_user_dictionary_build_facade_no_longer_owns_phase_helpers() -> None:
    _, facade_methods = _class_member_names(
        USER_IMPORT_USER_DICTIONARY_BUILD_SERVICE_PATH,
        "UserDictionaryBuildService",
    )
    _, details_methods = _class_member_names(
        USER_IMPORT_USER_DICTIONARY_DETAILS_BUILD_SERVICE_PATH,
        "UserDictionaryDetailsBuildService",
    )
    _, embedding_methods = _class_member_names(
        USER_IMPORT_USER_DICTIONARY_EMBEDDING_BUILD_SERVICE_PATH,
        "UserDictionaryEmbeddingBuildService",
    )
    _, logging_methods = _class_member_names(
        USER_IMPORT_USER_DICTIONARY_BUILD_LOGGING_PATH,
        "UserDictionaryBuildLogger",
    )
    logging_module = ast.parse(
        USER_IMPORT_USER_DICTIONARY_BUILD_LOGGING_PATH.read_text(encoding="utf-8")
    )
    logging_module_functions = {
        statement.name
        for statement in logging_module.body
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    phase_helper_names = {
        "_details_retry_feedback",
        "_details_validation_error",
        "_embedding_provider_setting",
        "_log_pipeline_error",
        "_optional_int",
    }

    assert _source_fragment_offenders(
        USER_IMPORT_USER_DICTIONARY_BUILD_SERVICE_PATH,
        tuple(sorted(phase_helper_names)),
    ) == []
    assert phase_helper_names.isdisjoint(facade_methods)
    assert {"_details_retry_feedback", "_details_validation_error"}.issubset(details_methods)
    assert "_embedding_provider_setting" in embedding_methods
    assert "log_pipeline_error" in logging_methods
    assert "_optional_int" in logging_module_functions


def test_external_provider_pricing_snapshots_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        EXTERNAL_PROVIDER_PRICING_SNAPSHOTS_PATH
    )
    offenders = [
        f"app/{EXTERNAL_PROVIDER_PRICING_SNAPSHOTS_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_pure_provider_reference_modules_are_retired() -> None:
    assert [
        path.relative_to(APP_ROOT).as_posix()
        for path in RETIRED_PROVIDER_REFERENCE_MODULE_PATHS
        if path.exists()
    ] == []


def test_app_code_does_not_import_retired_provider_reference_modules() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for forbidden_module in sorted(RETIRED_PROVIDER_REFERENCE_IMPORT_MODULES):
            import_lines = _concrete_module_import_lines(path, forbidden_module)
            offenders.extend(
                f"app/{relative_path.as_posix()}:{line}: {forbidden_module}"
                for line in import_lines
            )

    assert offenders == []


def test_admin_exercise_text_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        ADMIN_EXERCISE_TEXT_SERVICE_PATH
    )
    offenders = [
        f"app/{ADMIN_EXERCISE_TEXT_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_admin_exercise_text_generation_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        ADMIN_EXERCISE_TEXT_GENERATION_SERVICE
    )
    offenders = [
        f"app/{ADMIN_EXERCISE_TEXT_GENERATION_SERVICE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_admin_exercise_text_tts_service_does_not_import_concrete_database_provider() -> None:
    import_lines = _database_provider_database_import_lines(
        ADMIN_EXERCISE_TEXT_TTS_SERVICE
    )
    offenders = [
        f"app/{ADMIN_EXERCISE_TEXT_TTS_SERVICE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in import_lines
    ]

    assert offenders == []


def test_application_admin_exercise_text_services_do_not_import_exercise_texts_data_access_module() -> None:
    offenders = []
    for path in (
        ADMIN_EXERCISE_TEXT_SERVICE_PATH,
        ADMIN_EXERCISE_TEXT_GENERATION_SERVICE,
        ADMIN_EXERCISE_TEXT_TTS_SERVICE,
    ):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _concrete_module_import_lines(
            path,
            "app.data_access.exercise_texts",
        )
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_data_access_exercise_texts_uses_domain_version_conflict_error() -> None:
    imported_names = _imported_or_qualified_reference_names_from_module(
        DATA_ACCESS_EXERCISE_TEXTS_MODULE,
        DOMAIN_EXERCISE_TEXT_ERRORS_MODULE,
        {EXERCISE_TEXT_VERSION_CONFLICT_ERROR_NAME},
    )
    binding_lines = _top_level_name_binding_lines(
        DATA_ACCESS_EXERCISE_TEXTS_MODULE,
        {EXERCISE_TEXT_VERSION_CONFLICT_ERROR_NAME},
    )
    relative_path = DATA_ACCESS_EXERCISE_TEXTS_MODULE.relative_to(APP_ROOT.parent)
    offenders = []
    if EXERCISE_TEXT_VERSION_CONFLICT_ERROR_NAME not in imported_names:
        offenders.append(
            f"{relative_path.as_posix()}: missing "
            f"{DOMAIN_EXERCISE_TEXT_ERRORS_MODULE}.{EXERCISE_TEXT_VERSION_CONFLICT_ERROR_NAME}"
        )
    offenders.extend(
        f"{relative_path.as_posix()}:{line}: {name}"
        for line, name in binding_lines
    )

    assert offenders == []


def test_application_admin_exercise_text_services_use_domain_version_conflict_error() -> None:
    offenders = []
    for path in (
        ADMIN_EXERCISE_TEXT_SERVICE_PATH,
        ADMIN_EXERCISE_TEXT_GENERATION_SERVICE,
        ADMIN_EXERCISE_TEXT_TTS_SERVICE,
    ):
        imported_names = _imported_or_qualified_reference_names_from_module(
            path,
            DOMAIN_EXERCISE_TEXT_ERRORS_MODULE,
            {EXERCISE_TEXT_VERSION_CONFLICT_ERROR_NAME},
        )
        if EXERCISE_TEXT_VERSION_CONFLICT_ERROR_NAME not in imported_names:
            relative_path = path.relative_to(APP_ROOT.parent)
            offenders.append(
                f"{relative_path.as_posix()}: missing "
                f"{DOMAIN_EXERCISE_TEXT_ERRORS_MODULE}.{EXERCISE_TEXT_VERSION_CONFLICT_ERROR_NAME}"
            )

    assert offenders == []


def test_admin_exercise_text_services_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in ADMIN_EXERCISE_TEXT_APPLICATION_BOUNDARY_MODULES:
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_exercise_text_modules_do_not_import_admin_api() -> None:
    offenders = []
    for path in ADMIN_EXERCISE_TEXT_APPLICATION_BOUNDARY_MODULES:
        relative_path = path.relative_to(APP_ROOT)
        offenders.extend(
            f"app/{relative_path.as_posix()}:{line}: {module}"
            for line, module in _direct_import_modules(path)
            if module == "app.admin_api" or module.startswith("app.admin_api.")
        )

    assert offenders == []


def test_application_admin_exercise_text_modules_do_not_import_external_provider_adapters_or_httpx() -> None:
    offenders = []
    for path in ADMIN_EXERCISE_TEXT_APPLICATION_BOUNDARY_MODULES:
        relative_path = path.relative_to(APP_ROOT)
        import_lines = sorted(
            {
                *_external_provider_import_lines(path),
                *_httpx_transport_usage_lines(path),
            }
        )
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_external_exercise_text_provider_adapter_owns_transport_and_uses_application_ports() -> None:
    direct_imports = {
        module
        for _line, module in _direct_import_modules(EXTERNAL_EXERCISE_TEXT_PROVIDER_ADAPTER)
    }

    assert _httpx_transport_usage_lines(EXTERNAL_EXERCISE_TEXT_PROVIDER_ADAPTER) != []
    assert "app.application.admin.exercise_texts.providers" in direct_imports
    assert any(module.startswith("app.external_providers.") for module in direct_imports)


def test_admin_exercise_text_generation_service_does_not_import_fastapi_directly() -> None:
    offenders = [
        f"app/{ADMIN_EXERCISE_TEXT_GENERATION_SERVICE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _fastapi_import_lines(ADMIN_EXERCISE_TEXT_GENERATION_SERVICE)
    ]

    assert offenders == []


def test_admin_exercise_text_tts_service_does_not_import_fastapi_directly() -> None:
    offenders = [
        f"app/{ADMIN_EXERCISE_TEXT_TTS_SERVICE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _fastapi_import_lines(ADMIN_EXERCISE_TEXT_TTS_SERVICE)
    ]

    assert offenders == []


def test_application_admin_logs_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_LOGS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_logs_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_LOGS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_logs_read_service_does_not_import_admin_pagination_helper_directly() -> None:
    offenders = [
        f"app/{APPLICATION_ADMIN_LOGS_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _admin_pagination_helper_import_lines(
            APPLICATION_ADMIN_LOGS_READ_SERVICE_PATH
        )
    ]

    assert offenders == []


def test_application_admin_ai_usage_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_AI_USAGE_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_billing_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_BILLING_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_ai_usage_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_AI_USAGE_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_ai_usage_read_service_does_not_import_admin_pagination_helper_directly() -> None:
    offenders = [
        f"app/{APPLICATION_ADMIN_AI_USAGE_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _admin_pagination_helper_import_lines(
            APPLICATION_ADMIN_AI_USAGE_READ_SERVICE_PATH
        )
    ]

    assert offenders == []


def test_admin_pagination_http_helper_module_is_retired() -> None:
    assert not RETIRED_ADMIN_PAGINATION_HELPER_MODULE.exists()


def test_application_admin_billing_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_BILLING_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_billing_read_service_does_not_import_billing_data_access_module() -> None:
    offenders = [
        f"app/{APPLICATION_ADMIN_BILLING_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _concrete_module_import_lines(
            APPLICATION_ADMIN_BILLING_READ_SERVICE_PATH,
            "app.data_access.billing",
        )
    ]

    assert offenders == []


def test_application_admin_billing_read_service_uses_domain_billing_vocabulary() -> None:
    imported_names = _imported_or_qualified_reference_names_from_module(
        APPLICATION_ADMIN_BILLING_READ_SERVICE_PATH,
        DOMAIN_BILLING_CONSTANTS_MODULE,
        BILLING_ADMIN_READ_VOCABULARY_CONSTANT_NAMES,
    )

    assert sorted(BILLING_ADMIN_READ_VOCABULARY_CONSTANT_NAMES - imported_names) == []


def test_billing_vocabulary_constants_are_defined_only_in_domain_constants() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path == DOMAIN_BILLING_CONSTANTS_MODULE_PATH:
            continue

        relative_path = path.relative_to(APP_ROOT.parent)
        binding_lines = _top_level_billing_vocabulary_binding_lines(
            path,
            include_literal_duplicates=_is_billing_vocabulary_literal_scan_path(path),
        )
        binding_lines.extend(_inline_billing_terminal_status_literal_duplicate_lines(path))
        offenders.extend(
            (
                f"{relative_path.as_posix()}:{line}: {name} duplicates "
                f"{DOMAIN_BILLING_CONSTANTS_MODULE}.{vocabulary_name}"
            )
            for line, name, vocabulary_name in sorted(set(binding_lines))
        )

    assert offenders == []


def test_data_access_billing_vocabulary_constants_come_from_domain_constants() -> None:
    data_access_billing_imported_vocabulary_names = {"BILLING_TERMINAL_STATUSES"}
    imported_names = _imported_or_qualified_reference_names_from_module(
        DATA_ACCESS_BILLING_MODULE,
        DOMAIN_BILLING_CONSTANTS_MODULE,
        data_access_billing_imported_vocabulary_names,
    )
    binding_lines = _top_level_name_binding_lines(
        DATA_ACCESS_BILLING_MODULE,
        BILLING_VOCABULARY_CONSTANT_NAMES,
    )
    relative_path = DATA_ACCESS_BILLING_MODULE.relative_to(APP_ROOT.parent)
    offenders = [
        f"{relative_path.as_posix()}: missing {DOMAIN_BILLING_CONSTANTS_MODULE}.{name}"
        for name in sorted(data_access_billing_imported_vocabulary_names - imported_names)
    ]
    offenders.extend(
        f"{relative_path.as_posix()}:{line}: {name}"
        for line, name in binding_lines
    )

    assert offenders == []


def test_billing_vocabulary_binding_detection_catches_service_local_duplicate(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "payment_status.py"
    module_path.write_text(
        'MONOBANK_TERMINAL_STATUSES = {"success", "failure", "reversed", "expired"}\n',
        encoding="utf-8",
    )

    assert _top_level_billing_vocabulary_binding_lines(
        module_path,
        include_literal_duplicates=True,
    ) == [(1, "MONOBANK_TERMINAL_STATUSES", "BILLING_TERMINAL_STATUSES")]


def test_billing_vocabulary_binding_detection_allows_domain_import_aliases(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "status_service.py"
    module_path.write_text(
        "from app.domain.billing.constants import "
        "BILLING_TERMINAL_STATUSES as _BILLING_TERMINAL_STATUSES\n"
        "TERMINAL_STATUSES = _BILLING_TERMINAL_STATUSES\n",
        encoding="utf-8",
    )

    assert (
        _top_level_billing_vocabulary_binding_lines(
            module_path,
            include_literal_duplicates=True,
        )
        == []
    )


def test_billing_vocabulary_inline_literal_detection_catches_terminal_status_set(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "status_service.py"
    module_path.write_text(
        "from app.domain.billing.constants import "
        "BILLING_TERMINAL_STATUSES as DOMAIN_TERMINAL_STATUSES\n"
        "def uses_domain_constant(status: str) -> bool:\n"
        "    return status in DOMAIN_TERMINAL_STATUSES\n"
        "def duplicates_terminal_statuses(status: str) -> bool:\n"
        '    return status in {"expired", "failure", "reversed", "success"}\n',
        encoding="utf-8",
    )

    assert _inline_billing_terminal_status_literal_duplicate_lines(module_path) == [
        (5, "inline set literal", "BILLING_TERMINAL_STATUSES")
    ]


def test_application_admin_billing_read_service_does_not_import_admin_pagination_helper_directly() -> None:
    offenders = [
        f"app/{APPLICATION_ADMIN_BILLING_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _admin_pagination_helper_import_lines(
            APPLICATION_ADMIN_BILLING_READ_SERVICE_PATH
        )
    ]

    assert offenders == []


def test_application_admin_ai_usage_modules_do_not_import_admin_api() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_AI_USAGE_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.admin_api" or module.startswith("app.admin_api."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_api_ai_usage_adapter_modules_import_only_allowed_application_ai_usage_modules() -> None:
    allowed_application_ai_usage_imports = {
        "app.application.admin.ai_usage",
        "app.application.admin.ai_usage.action_otp",
        "app.application.admin.ai_usage.errors",
        "app.application.admin.ai_usage.read_service",
    }
    offenders = []
    for module_path in (
        ADMIN_API_AI_USAGE_ROUTER_MODULE,
        ADMIN_API_AI_USAGE_HTTP_ERRORS_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(module_path):
            if not module.startswith("app.application.admin.ai_usage"):
                continue
            if module not in allowed_application_ai_usage_imports:
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_billing_modules_do_not_import_admin_api() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_BILLING_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.admin_api" or module.startswith("app.admin_api."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_api_billing_adapter_modules_import_only_allowed_application_billing_modules() -> None:
    allowed_application_billing_imports = {
        "app.application.admin.billing",
        "app.application.admin.billing.errors",
        "app.application.admin.billing.read_service",
    }
    offenders = []
    for module_path in (
        ADMIN_API_BILLING_ROUTER_MODULE,
        ADMIN_API_BILLING_HTTP_ERRORS_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(module_path):
            if not module.startswith("app.application.admin.billing"):
                continue
            if module not in allowed_application_billing_imports:
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_api_settings_adapter_modules_import_only_allowed_application_settings_modules() -> None:
    offenders = []
    for module_path in (
        ADMIN_API_SETTINGS_ROUTER_MODULE,
        ADMIN_API_SETTINGS_HTTP_ERRORS_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        offenders.extend(
            f"app/{relative_path.as_posix()}:{line}"
            for line in _admin_api_settings_adapter_disallowed_application_settings_import_lines(
                module_path
            )
        )

    assert offenders == []


def test_admin_api_settings_adapter_import_detection_flags_application_settings_decision_modules(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "settings_adapter.py"
    module_path.write_text(
        "from app.application.admin.settings.settings_service import AdminSettingsService\n"
        "import app.application.admin.settings.validators as settings_validators\n"
        "from app.application.admin.settings.action_otp import SettingsActionOtpService\n"
        "from app.application.admin.settings import settings_service\n"
        "from app.application.admin.settings import validators\n"
        "from app.application.admin.settings import action_otp\n"
        "from app.application.admin.settings import errors\n"
        "from app.application.admin.settings.errors import AdminSettingsError\n",
        encoding="utf-8",
    )

    assert _admin_api_settings_adapter_disallowed_application_settings_import_lines(
        module_path
    ) == [1, 2, 3, 4, 5, 6]


def test_admin_api_users_adapter_modules_import_only_allowed_application_user_modules() -> None:
    allowed_application_user_imports = {
        "app.application.admin.users.errors",
    }
    offenders = []
    for module_path in (
        ADMIN_API_USERS_ROUTER_MODULE,
        ADMIN_API_USERS_HTTP_ERRORS_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(module_path):
            if not module.startswith("app.application.admin.users"):
                continue
            if module not in allowed_application_user_imports:
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_dashboard_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DASHBOARD_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_dashboard_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DASHBOARD_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_dashboard_modules_do_not_import_admin_api() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DASHBOARD_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.admin_api" or module.startswith("app.admin_api."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_dashboard_modules_do_not_import_data_access() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DASHBOARD_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.data_access" or module.startswith("app.data_access."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_api_dashboard_adapter_modules_import_only_allowed_application_dashboard_modules() -> None:
    allowed_application_dashboard_imports = {
        "app.application.admin.dashboard",
        "app.application.admin.dashboard.errors",
        "app.application.admin.dashboard.dashboard_service",
    }
    offenders = []
    for module_path in (
        ADMIN_API_DASHBOARD_ROUTER_MODULE,
        ADMIN_API_DASHBOARD_HTTP_ERRORS_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(module_path):
            if not module.startswith("app.application.admin.dashboard"):
                continue
            if module not in allowed_application_dashboard_imports:
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_http_permissions_do_not_import_legacy_validators_directly() -> None:
    relative_path = ADMIN_HTTP_PERMISSIONS_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in _legacy_validators_import_lines(ADMIN_HTTP_PERMISSIONS_MODULE)
    ]

    assert offenders == []


def test_application_admin_user_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_USERS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_user_read_service_does_not_import_admin_pagination_helper_directly() -> None:
    offenders = [
        f"app/{APPLICATION_ADMIN_USERS_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _admin_pagination_helper_import_lines(APPLICATION_ADMIN_USERS_READ_SERVICE_PATH)
    ]

    assert offenders == []


def test_application_admin_settings_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_SETTINGS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_settings_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_SETTINGS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_settings_modules_do_not_import_admin_api() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_SETTINGS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.admin_api" or module.startswith("app.admin_api."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_settings_modules_do_not_import_data_access() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_SETTINGS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.data_access" or module.startswith("app.data_access."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_settings_use_domain_provider_contracts() -> None:
    required_imports_by_path = {
        APPLICATION_ADMIN_SETTINGS_SERVICE_PATH: {
            DOMAIN_PROVIDER_PRICING_MODULE,
            DOMAIN_PROVIDER_SETTINGS_MODULE,
        },
        APPLICATION_ADMIN_SETTINGS_VALIDATORS_PATH: {
            DOMAIN_PROVIDER_PRICING_MODULE,
            DOMAIN_PROVIDER_SETTINGS_MODULE,
        },
    }
    offenders = []
    for path, required_modules in required_imports_by_path.items():
        relative_path = path.relative_to(APP_ROOT)
        direct_imports = {module for _line, module in _direct_import_modules(path)}
        missing_imports = sorted(required_modules - direct_imports)
        offenders.extend(
            f"app/{relative_path.as_posix()}: missing {module}"
            for module in missing_imports
        )

    assert offenders == []


def test_application_admin_dictionary_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_dictionary_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_dictionary_read_service_does_not_import_admin_pagination_helper_directly() -> None:
    offenders = [
        f"app/{APPLICATION_ADMIN_DICTIONARY_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _admin_pagination_helper_import_lines(APPLICATION_ADMIN_DICTIONARY_READ_SERVICE_PATH)
    ]

    assert offenders == []


def test_application_admin_dictionary_modules_do_not_import_admin_api() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.admin_api" or module.startswith("app.admin_api."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_dictionary_modules_do_not_import_data_access() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.data_access" or module.startswith("app.data_access."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_api_dictionary_adapter_modules_import_only_allowed_application_dictionary_modules() -> None:
    allowed_application_dictionary_imports = {
        "app.application.admin.dictionary",
        "app.application.admin.dictionary.errors",
    }
    disallowed_parent_imports = {
        "action_service",
        "archive_entry",
        "delete_entry",
        "dictionary_service",
        "read_service",
        "validators",
        "verify_entries",
    }
    offenders = []
    for module_path in (
        ADMIN_API_DICTIONARY_ROUTER_MODULE,
        ADMIN_API_DICTIONARY_HTTP_ERRORS_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(module_path):
            if not module.startswith("app.application.admin.dictionary"):
                continue
            if module not in allowed_application_dictionary_imports:
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")
                continue
            if module == "app.application.admin.dictionary":
                tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.ImportFrom) or node.lineno != line:
                        continue
                    if any(alias.name == "*" or alias.name in disallowed_parent_imports for alias in node.names):
                        offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")
                        break

    assert offenders == []


def test_application_admin_entity_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_ENTITY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_entity_modules_do_not_import_interface_or_data_access_packages() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_ENTITY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module in {"app.admin_api", "app.data_access"} or module.startswith(
                ("app.admin_api.", "app.data_access.")
            ):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_entity_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_ENTITY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_imports_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_IMPORTS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_imports_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_IMPORTS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_imports_read_service_does_not_import_admin_pagination_helper_directly() -> None:
    offenders = [
        f"app/{APPLICATION_ADMIN_IMPORTS_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _admin_pagination_helper_import_lines(
            APPLICATION_ADMIN_IMPORTS_READ_SERVICE_PATH
        )
    ]

    assert offenders == []


def test_application_admin_imports_modules_do_not_import_admin_api() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_IMPORTS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.admin_api" or module.startswith("app.admin_api."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_imports_modules_do_not_import_data_access() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_IMPORTS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.data_access" or module.startswith("app.data_access."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_logs_modules_do_not_import_admin_api() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_LOGS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.admin_api" or module.startswith("app.admin_api."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_logs_modules_do_not_import_data_access() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_LOGS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module == "app.data_access" or module.startswith("app.data_access."):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_api_imports_adapter_modules_import_only_allowed_application_imports_modules() -> None:
    allowed_application_imports_imports = {
        "app.application.admin.imports",
        "app.application.admin.imports.errors",
        "app.application.admin.imports.read_service",
    }
    offenders = []
    for module_path in (
        ADMIN_API_IMPORTS_ROUTER_MODULE,
        ADMIN_API_IMPORTS_HTTP_ERRORS_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(module_path):
            if not module.startswith("app.application.admin.imports"):
                continue
            if module not in allowed_application_imports_imports:
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_api_logs_adapter_modules_import_only_allowed_application_logs_modules() -> None:
    allowed_application_logs_imports = {
        "app.application.admin.logs",
        "app.application.admin.logs.errors",
        "app.application.admin.logs.read_service",
    }
    offenders = []
    for module_path in (
        ADMIN_API_LOGS_ROUTER_MODULE,
        ADMIN_API_LOGS_HTTP_ERRORS_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(module_path):
            if not module.startswith("app.application.admin.logs"):
                continue
            if module not in allowed_application_logs_imports:
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_read_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_READ_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_read_modules_do_not_import_interface_or_data_access_packages() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_READ_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if module in {"app.admin_api", "app.data_access"} or module.startswith(
                ("app.admin_api.", "app.data_access.")
            ):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_read_modules_do_not_build_audio_responses_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_READ_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _api_audio_response_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_user_dictionary_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_USER_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_user_dictionary_modules_do_not_import_legacy_validators_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_USER_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _legacy_validators_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_user_dictionary_read_service_does_not_import_admin_pagination_helper_directly() -> None:
    offenders = [
        f"app/{APPLICATION_ADMIN_USER_DICTIONARY_READ_SERVICE_PATH.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _admin_pagination_helper_import_lines(APPLICATION_ADMIN_USER_DICTIONARY_READ_SERVICE_PATH)
    ]

    assert offenders == []


def test_application_admin_user_dictionary_modules_do_not_import_admin_api_or_data_access() -> None:
    offenders = []
    forbidden_roots = ("app.admin_api", "app.data_access")
    for path in sorted(APPLICATION_ADMIN_USER_DICTIONARY_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if any(module == root or module.startswith(f"{root}.") for root in forbidden_roots):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_application_admin_user_modules_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_USERS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_user_modules_do_not_import_admin_api_or_data_access() -> None:
    offenders = []
    forbidden_roots = ("app.admin_api", "app.data_access")
    for path in sorted(APPLICATION_ADMIN_USERS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line, module in _direct_import_modules(path):
            if any(module == root or module.startswith(f"{root}.") for root in forbidden_roots):
                offenders.append(f"app/{relative_path.as_posix()}:{line}: {module}")

    assert offenders == []


def test_admin_request_schemas_do_not_import_fastapi_directly() -> None:
    offenders = []
    for path in (ADMIN_API_SCHEMAS_MODULE, ADMIN_SCHEMA_VALIDATORS_MODULE, ADMIN_EXERCISE_TEXT_SCHEMAS_MODULE):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _fastapi_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_security_internal_api_tokens_do_not_import_fastapi_directly() -> None:
    offenders = [
        f"app/{SECURITY_INTERNAL_API_TOKENS_MODULE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _fastapi_import_lines(SECURITY_INTERNAL_API_TOKENS_MODULE)
    ]

    assert offenders == []


def test_json_datetime_serialization_does_not_import_http_frameworks() -> None:
    offenders = [
        f"app/{JSON_DATETIME_SERIALIZATION_MODULE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line in _http_framework_import_lines(JSON_DATETIME_SERIALIZATION_MODULE)
    ]

    assert offenders == []


def test_application_admin_permissions_do_not_import_fastapi_directly() -> None:
    relative_path = APPLICATION_ADMIN_PERMISSIONS_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in _fastapi_import_lines(APPLICATION_ADMIN_PERMISSIONS_MODULE)
    ]

    assert offenders == []


def test_client_web_import_service_application_module_stays_out_of_api_layer() -> None:
    offenders = []
    for module_path in (
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE,
        APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE,
    ):
        relative_path = module_path.relative_to(APP_ROOT)
        offenders.extend(
            f"app/{relative_path.as_posix()}:{line}"
            for line in sorted(
                set(
                    _fastapi_import_lines(module_path)
                    + _interface_api_import_lines(module_path)
                    + _specific_module_import_lines(
                        module_path,
                        {"app.composition.user_import_provider_adapters"},
                    )
                )
            )
        )

    assert offenders == []


def test_client_web_import_statuses_application_module_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_WEB_IMPORT_STATUSES_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_WEB_IMPORT_STATUSES_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_WEB_IMPORT_STATUSES_MODULE)
            )
        )
    ]

    assert offenders == []


def test_client_web_import_sources_application_module_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_WEB_IMPORT_SOURCES_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_WEB_IMPORT_SOURCES_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_WEB_IMPORT_SOURCES_MODULE)
                + _specific_module_import_lines(
                    APPLICATION_CLIENT_WEB_IMPORT_SOURCES_MODULE,
                    {"app.composition.user_import_provider_adapters"},
                )
            )
        )
    ]

    assert offenders == []


def test_client_web_import_events_application_module_stays_out_of_api_layer() -> None:
    relative_path = APPLICATION_CLIENT_WEB_IMPORT_EVENTS_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(APPLICATION_CLIENT_WEB_IMPORT_EVENTS_MODULE)
                + _interface_api_import_lines(APPLICATION_CLIENT_WEB_IMPORT_EVENTS_MODULE)
            )
        )
    ]

    assert offenders == []


def test_client_web_import_events_composition_module_stays_out_of_api_layer() -> None:
    relative_path = COMPOSITION_CLIENT_WEB_IMPORT_EVENTS_MODULE.relative_to(APP_ROOT)
    offenders = [
        f"app/{relative_path.as_posix()}:{line}"
        for line in sorted(
            set(
                _fastapi_import_lines(COMPOSITION_CLIENT_WEB_IMPORT_EVENTS_MODULE)
                + _interface_api_import_lines(COMPOSITION_CLIENT_WEB_IMPORT_EVENTS_MODULE)
            )
        )
    ]

    assert offenders == []


def test_client_web_request_schemas_do_not_import_data_access() -> None:
    relative_path = CLIENT_WEB_SCHEMAS_MODULE.relative_to(APP_ROOT)
    data_access_offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(CLIENT_WEB_SCHEMAS_MODULE)
        if module == "app.data_access" or module.startswith("app.data_access.")
    ]

    assert data_access_offenders == []


def test_fastapi_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from fastapi import HTTPException\n"
        "from fastapi.responses import FileResponse\n"
        "import fastapi\n",
        encoding="utf-8",
    )

    assert _fastapi_import_lines(module_path) == [1, 2, 3]


def test_lower_layers_do_not_import_interface_api_packages() -> None:
    offenders = []
    for path in _iter_lower_layer_paths():
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _interface_api_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_interface_api_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.admin_api.auth.services import admin_auth_service\n"
        "import app.client_api.router\n"
        "from app import admin_api, client_api\n",
        encoding="utf-8",
    )

    assert _interface_api_import_lines(module_path) == [1, 2, 3]


def test_interface_api_import_detection_catches_relative_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_root = tmp_path / "app"
    module_path = app_root / "application" / "scheduled_runtime" / "service.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text(
        "from ...client_api.router import build_client_router\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)

    assert _interface_api_import_lines(module_path) == [1]


def test_user_import_services_do_not_own_http_transport() -> None:
    offenders = []
    for path in sorted(USER_IMPORT_SERVICES_ROOT.rglob("*.py")):
        import_lines = _httpx_transport_usage_lines(path)
        relative_path = path.relative_to(APP_ROOT)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_http_transport_detection_catches_imports_and_direct_references(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "import httpx\n"
        "client = httpx.Client()\n"
        "from httpx import Timeout\n",
        encoding="utf-8",
    )

    assert _httpx_transport_usage_lines(module_path) == [1, 2, 3]


def test_http_transport_imports_are_confined_to_boundary_modules() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        if _is_http_transport_boundary_path(relative_path):
            continue
        import_lines = _httpx_transport_usage_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_billing_services_do_not_construct_monobank_client_directly() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        call_lines = _monobank_client_constructor_call_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in call_lines)

    assert offenders == []


def test_billing_services_do_not_reference_concrete_monobank_client_type() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        reference_lines = _monobank_client_type_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_billing_services_do_not_reference_provider_monobank_invoice_request_dto() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        reference_lines = _monobank_invoice_request_provider_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_billing_services_do_not_reference_provider_monobank_api_error() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        reference_lines = _monobank_api_error_provider_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_billing_services_do_not_reference_provider_monobank_audit_context() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        reference_lines = _monobank_audit_context_provider_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_billing_services_do_not_reference_provider_monobank_audit_helpers() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        reference_lines = _monobank_audit_helper_provider_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_billing_services_do_not_reference_provider_monobank_client_factory() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        reference_lines = _monobank_client_factory_provider_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_billing_services_do_not_define_monobank_client_factory_escape_hatches() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "monobank_client_factory" in line or "require_monobank_client_factory" in line:
                offenders.append(f"app/{relative_path.as_posix()}:{line_number}")

    assert offenders == []


def test_billing_services_do_not_reference_provider_monobank_webhook_signature_verifier() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        reference_lines = _monobank_signature_verifier_provider_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_billing_services_do_not_reference_monobank_provider_package() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        reference_lines = _monobank_provider_package_reference_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in reference_lines)

    assert offenders == []


def test_billing_services_do_not_import_provider_monobank_modules() -> None:
    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _specific_module_import_lines(
            path,
            {"app.billing.providers.monobank"},
        )
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_billing_checkout_service_uses_provider_config_for_monobank_runtime_boundary() -> None:
    source = BILLING_CHECKOUT_SERVICE_PATH.read_text(encoding="utf-8")
    forbidden_fragments = (
        "MONOBANK_MODE_DISABLED",
        "MONOBANK_MODE_TEST",
        "MONOBANK_MODE_PRODUCTION",
        "validate_monobank_mode_token",
        "MONOBANK_PLAN_ICON_PATHS",
        "build_monobank_subscription_description",
        "build_monobank_plan_icon_url",
    )

    assert [fragment for fragment in forbidden_fragments if fragment in source] == []


def test_billing_status_service_uses_provider_runtime_for_credential_boundary() -> None:
    source = BILLING_PAYMENT_STATUS_POLLING_SERVICE_PATH.read_text(encoding="utf-8")
    forbidden_fragments = (
        "validate_monobank_mode_token",
        "_validate_monobank_mode_token",
        "monobank_token_test",
        "monobank_token",
    )

    assert [fragment for fragment in forbidden_fragments if fragment in source] == []


def test_billing_provider_runtime_fragments_are_confined_to_boundary_owner_modules() -> None:
    allowed_modules_by_fragment = {
        "_payment_provider_key": set(),
        "BILLING_PROVIDER_MONOBANK": {
            "provider_runtime.py",
            "checkout_provider_config.py",
            "monobank_client_port.py",
            "checkout_service.py",
        },
        "validate_monobank_mode_token": {
            "provider_runtime.py",
            "checkout_provider_config.py",
        },
        "monobank_token_test": {
            "provider_runtime.py",
        },
        "monobank_token": {
            "provider_runtime.py",
        },
    }

    offenders = []
    for path in sorted(BILLING_SERVICES_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        source_lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(source_lines, 1):
            for fragment, allowed_modules in allowed_modules_by_fragment.items():
                if fragment not in line or path.name in allowed_modules:
                    continue
                offenders.append(
                    f"app/{relative_path.as_posix()}:{line_number} -> {fragment}"
                )

    assert offenders == []


def test_monobank_provider_package_reference_detection_catches_aliases_and_refs(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank import MonobankClient\n"
        "from app.billing.providers.monobank.audit import mask_headers\n"
        "import app.billing.providers.monobank\n"
        "import app.billing.providers.monobank as mono\n"
        "import app.billing.providers.monobank.audit as mono_audit_module\n"
        "from app.billing.providers import monobank as provider_mono\n"
        "from app.billing.providers.monobank import audit as mono_audit\n"
        "qualified_client = app.billing.providers.monobank.client.MonobankClient\n"
        "masked = mono.audit.mask_headers(headers)\n"
        "provider_client = provider_mono.build_monobank_client(provider_mode='test')\n"
        "audit_masked = mono_audit.mask_headers(headers)\n"
        "audit_module_masked = mono_audit_module.mask_headers(headers)\n"
        "direct_client_type = MonobankClient\n"
        "direct_masked = mask_headers(headers)\n"
        "dynamic_provider_path = 'app.billing.providers.monobank.dynamic'\n",
        encoding="utf-8",
    )
    local_module_path = tmp_path / "local_module.py"
    local_module_path.write_text(
        "from app.billing.services.monobank_client_port import MonobankClientPort\n"
        "from app.billing.services.monobank_client_port import MonobankAuditContext\n"
        "class MonobankClient:\n"
        "    pass\n"
        "def mask_headers(headers):\n"
        "    return headers\n"
        "monobank_provider = object()\n"
        "provider_mono = object()\n"
        "client_type: type[MonobankClient]\n"
        "port_type: MonobankClientPort | None\n"
        "audit_type: MonobankAuditContext | None\n"
        "masked = mask_headers(headers)\n"
        "local_provider = monobank_provider.build_monobank_client(provider_mode='test')\n"
        "local_alias = provider_mono.build_monobank_client(provider_mode='test')\n",
        encoding="utf-8",
    )

    assert _monobank_provider_package_reference_lines(module_path) == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
    ]
    assert _monobank_provider_package_reference_lines(local_module_path) == []


def test_monobank_client_constructor_call_detection_ignores_imports_and_annotations(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank import MonobankClient\n"
        "from app.billing.providers.monobank import MonobankClient as Mono\n"
        "from app.billing.providers.monobank.client import MonobankClient as ClientAlias\n"
        "from app.billing.providers.monobank import client as mono_client\n"
        "import app.billing.providers.monobank\n"
        "import app.billing.providers.monobank as mono\n"
        "import app.billing.providers.monobank.client as mono_client_module\n"
        "client_type: type[MonobankClient]\n"
        "mono_type: type[Mono]\n"
        "client_alias_type: type[ClientAlias]\n"
        "module_alias_type: type[mono.MonobankClient]\n"
        "from_import_module_alias_type: type[mono_client.MonobankClient]\n"
        "direct_client = MonobankClient(settings=settings)\n"
        "qualified_client = app.billing.providers.monobank.MonobankClient(settings=settings)\n"
        "qualified_client_module = app.billing.providers.monobank.client.MonobankClient(settings=settings)\n"
        "package_class_alias_client = Mono(settings=settings)\n"
        "client_class_alias_client = ClientAlias(settings=settings)\n"
        "module_alias_client = mono.MonobankClient(settings=settings)\n"
        "client_module_alias_client = mono_client_module.MonobankClient(settings=settings)\n"
        "from_import_module_alias_client = mono_client.MonobankClient(settings=settings)\n",
        encoding="utf-8",
    )

    assert _monobank_client_constructor_call_lines(module_path) == [13, 14, 15, 16, 17, 18, 19, 20]


def test_monobank_client_type_reference_detection_catches_aliases_and_allows_ports(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank import MonobankClient\n"
        "from app.billing.providers.monobank import MonobankClient as Mono\n"
        "from app.billing.providers.monobank.client import MonobankClient as ClientAlias\n"
        "from app.billing.providers.monobank import client as mono_client\n"
        "import app.billing.providers.monobank\n"
        "import app.billing.providers.monobank as mono\n"
        "import app.billing.providers.monobank.client as mono_client_module\n"
        "from app.billing.providers.monobank import MonobankAPIError, MonobankCreateInvoiceRequest\n"
        "from app.billing.providers.monobank import build_monobank_client, verify_monobank_webhook_signature\n"
        "from app.billing.providers.monobank.audit import MonobankAuditContext\n"
        "from app.billing.services.monobank_client_port import MonobankClientPort, MonobankClientFactory\n"
        "client_type: type[MonobankClient]\n"
        "mono_type: type[Mono]\n"
        "client_alias_type: type[ClientAlias]\n"
        "qualified_type: type[app.billing.providers.monobank.MonobankClient]\n"
        "qualified_client_module_type: type[app.billing.providers.monobank.client.MonobankClient]\n"
        "module_alias_type: type[mono.MonobankClient]\n"
        "client_module_alias_type: type[mono_client_module.MonobankClient]\n"
        "from_import_module_alias_type: type[mono_client.MonobankClient]\n"
        "port_type: MonobankClientPort | None\n"
        "factory_type: MonobankClientFactory | None\n"
        "api_error_type: type[MonobankAPIError]\n"
        "request_type: MonobankCreateInvoiceRequest\n"
        "audit_context_type: MonobankAuditContext\n"
        "factory = build_monobank_client\n"
        "verifier = verify_monobank_webhook_signature\n",
        encoding="utf-8",
    )
    local_module_path = tmp_path / "local_module.py"
    local_module_path.write_text(
        "class MonobankClient:\n"
        "    pass\n"
        "class MonobankClientPort:\n"
        "    pass\n"
        "class MonobankClientFactory:\n"
        "    pass\n"
        "client_type: type[MonobankClient]\n"
        "port_type: MonobankClientPort | None\n"
        "factory_type: MonobankClientFactory | None\n",
        encoding="utf-8",
    )

    assert _monobank_client_type_reference_lines(module_path) == [1, 2, 3, 12, 13, 14, 15, 16, 17, 18, 19]
    assert _monobank_client_type_reference_lines(local_module_path) == []


def test_monobank_invoice_request_provider_reference_detection_catches_aliases_and_allows_local_dtos(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank import MonobankCreateInvoiceRequest\n"
        "from app.billing.providers.monobank import MonobankCreateInvoiceRequest as InvoiceReq\n"
        "from app.billing.providers.monobank.client import MonobankCreateInvoiceRequest as ClientReq\n"
        "from app.billing.providers.monobank import client as mono_client\n"
        "import app.billing.providers.monobank\n"
        "import app.billing.providers.monobank as mono\n"
        "import app.billing.providers.monobank.client as mono_client_module\n"
        "from app.billing.providers.monobank import MonobankAPIError, build_monobank_client\n"
        "from app.billing.providers.monobank import verify_monobank_webhook_signature\n"
        "from app.billing.providers.monobank.audit import MonobankAuditContext\n"
        "request_type: MonobankCreateInvoiceRequest\n"
        "alias_request_type: InvoiceReq\n"
        "client_alias_request_type: ClientReq\n"
        "qualified_type: app.billing.providers.monobank.MonobankCreateInvoiceRequest\n"
        "qualified_client_module_type: app.billing.providers.monobank.client.MonobankCreateInvoiceRequest\n"
        "module_alias_type: mono.MonobankCreateInvoiceRequest\n"
        "client_module_alias_type: mono_client_module.MonobankCreateInvoiceRequest\n"
        "from_import_module_alias_type: mono_client.MonobankCreateInvoiceRequest\n"
        "api_error_type: type[MonobankAPIError]\n"
        "factory = build_monobank_client\n"
        "verifier = verify_monobank_webhook_signature\n"
        "audit_context_type: MonobankAuditContext\n",
        encoding="utf-8",
    )
    local_module_path = tmp_path / "local_module.py"
    local_module_path.write_text(
        "from app.billing.services.monobank_client_port import MonobankInvoiceCreateRequest\n"
        "from app.billing.services.monobank_client_port import MonobankInvoiceCreateRequest as InvoiceReq\n"
        "class MonobankCreateInvoiceRequest:\n"
        "    pass\n"
        "class FakeMonobankCreateInvoiceRequest:\n"
        "    pass\n"
        "request_type: MonobankInvoiceCreateRequest\n"
        "alias_request_type: InvoiceReq\n"
        "fake_request_type: MonobankCreateInvoiceRequest\n"
        "fake_local_request = FakeMonobankCreateInvoiceRequest()\n",
        encoding="utf-8",
    )

    assert _monobank_invoice_request_provider_reference_lines(module_path) == [
        1,
        2,
        3,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
    ]
    assert _monobank_invoice_request_provider_reference_lines(local_module_path) == []


def test_monobank_api_error_provider_reference_detection_catches_aliases_and_allows_local_helpers(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank import MonobankAPIError\n"
        "from app.billing.providers.monobank import MonobankAPIError as MonoAPIError\n"
        "from app.billing.providers.monobank.client import MonobankAPIError as ClientAPIError\n"
        "from app.billing.providers.monobank import client as mono_client\n"
        "from app.billing.providers import monobank as provider_mono\n"
        "import app.billing.providers.monobank\n"
        "import app.billing.providers.monobank as mono\n"
        "import app.billing.providers.monobank.client as mono_client_module\n"
        "from app.billing.providers.monobank import build_monobank_client, verify_monobank_webhook_signature\n"
        "from app.billing.providers.monobank.audit import MonobankAuditContext\n"
        "from app.billing.services.monobank_client_port import monobank_provider_api_error_details\n"
        "direct_type: type[MonobankAPIError]\n"
        "alias_type: type[MonoAPIError]\n"
        "client_alias_type: type[ClientAPIError]\n"
        "qualified_type: type[app.billing.providers.monobank.MonobankAPIError]\n"
        "qualified_client_type: type[app.billing.providers.monobank.client.MonobankAPIError]\n"
        "module_alias_type: type[mono.MonobankAPIError]\n"
        "client_module_alias_type: type[mono_client_module.MonobankAPIError]\n"
        "from_import_module_alias_type: type[mono_client.MonobankAPIError]\n"
        "package_module_alias_type: type[provider_mono.MonobankAPIError]\n"
        "factory = build_monobank_client\n"
        "verifier = verify_monobank_webhook_signature\n"
        "audit_context_type: MonobankAuditContext\n"
        "helper = monobank_provider_api_error_details(RuntimeError())\n",
        encoding="utf-8",
    )
    local_module_path = tmp_path / "local_module.py"
    local_module_path.write_text(
        "from app.billing.services.monobank_client_port import MonobankProviderAPIErrorDetails\n"
        "from app.billing.services.monobank_client_port import monobank_provider_api_error_details\n"
        "class MonobankAPIError(Exception):\n"
        "    pass\n"
        "local_type: type[MonobankAPIError]\n"
        "details_type: type[MonobankProviderAPIErrorDetails]\n"
        "helper = monobank_provider_api_error_details(RuntimeError())\n",
        encoding="utf-8",
    )

    assert _monobank_api_error_provider_reference_lines(module_path) == [
        1,
        2,
        3,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
    ]
    assert _monobank_api_error_provider_reference_lines(local_module_path) == []


def test_monobank_audit_context_provider_reference_detection_catches_aliases_and_allows_local_contexts(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank.audit import MonobankAuditContext\n"
        "from app.billing.providers.monobank.audit import MonobankAuditContext as ProviderAuditContext\n"
        "import app.billing.providers.monobank.audit\n"
        "import app.billing.providers.monobank.audit as provider_audit\n"
        "from app.billing.providers.monobank import audit as mono_audit\n"
        "from app.billing.providers import monobank as provider_mono\n"
        "from app.billing.providers.monobank.audit import duration_ms, mask_headers\n"
        "direct_type: type[MonobankAuditContext]\n"
        "alias_type: type[ProviderAuditContext]\n"
        "qualified_type: type[app.billing.providers.monobank.audit.MonobankAuditContext]\n"
        "module_alias_type: type[provider_audit.MonobankAuditContext]\n"
        "from_import_module_alias_type: type[mono_audit.MonobankAuditContext]\n"
        "package_module_alias_type: type[provider_mono.audit.MonobankAuditContext]\n"
        "elapsed = duration_ms(started_at)\n"
        "headers = mask_headers(headers)\n",
        encoding="utf-8",
    )
    local_module_path = tmp_path / "local_module.py"
    local_module_path.write_text(
        "from app.billing.services.monobank_client_port import MonobankAuditContext\n"
        "from app.billing.services.monobank_client_port import MonobankAuditContext as LocalAuditContext\n"
        "class FakeMonobankAuditContext:\n"
        "    pass\n"
        "class MonobankAuditContext:\n"
        "    pass\n"
        "port_type: type[MonobankAuditContext]\n"
        "alias_type: type[LocalAuditContext]\n"
        "fake_type: type[FakeMonobankAuditContext]\n",
        encoding="utf-8",
    )

    assert _monobank_audit_context_provider_reference_lines(module_path) == [
        1,
        2,
        8,
        9,
        10,
        11,
        12,
        13,
    ]
    assert _monobank_audit_context_provider_reference_lines(local_module_path) == []


def test_monobank_audit_helper_provider_reference_detection_catches_aliases_and_allows_local_helpers(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank.audit import duration_ms, mask_headers\n"
        "from app.billing.providers.monobank.audit import duration_ms as provider_duration\n"
        "from app.billing.providers.monobank.audit import mask_headers as provider_mask_headers\n"
        "from app.billing.providers.monobank import audit as mono_audit\n"
        "from app.billing.providers import monobank as provider_mono\n"
        "import app.billing.providers.monobank.audit\n"
        "import app.billing.providers.monobank.audit as provider_audit\n"
        "duration_ref = duration_ms\n"
        "headers_ref = mask_headers\n"
        "duration_alias_ref = provider_duration\n"
        "headers_alias_ref = provider_mask_headers\n"
        "elapsed = duration_ms(started, finished)\n"
        "masked = mask_headers(headers)\n"
        "module_elapsed = mono_audit.duration_ms(started, finished)\n"
        "module_masked = mono_audit.mask_headers(headers)\n"
        "package_elapsed = provider_mono.audit.duration_ms(started, finished)\n"
        "package_masked = provider_mono.audit.mask_headers(headers)\n"
        "qualified_elapsed = app.billing.providers.monobank.audit.duration_ms(started, finished)\n"
        "qualified_masked = app.billing.providers.monobank.audit.mask_headers(headers)\n"
        "audit_module_elapsed = provider_audit.duration_ms(started, finished)\n"
        "audit_module_masked = provider_audit.mask_headers(headers)\n",
        encoding="utf-8",
    )
    local_module_path = tmp_path / "local_module.py"
    local_module_path.write_text(
        "from app.billing.services import webhook_audit as service_audit\n"
        "from app.billing.services.webhook_audit import duration_ms, mask_headers\n"
        "def duration_ms(started, finished):\n"
        "    return 0\n"
        "def mask_headers(headers):\n"
        "    return headers\n"
        "elapsed = duration_ms(started, finished)\n"
        "masked = mask_headers(headers)\n"
        "service_elapsed = service_audit.duration_ms(started, finished)\n"
        "service_masked = service_audit.mask_headers(headers)\n"
        "duration_ms_value = 0\n"
        "mask_headers_value = {'X-Token': 'kept'}\n",
        encoding="utf-8",
    )

    assert _monobank_audit_helper_provider_reference_lines(module_path) == [
        1,
        2,
        3,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
    ]
    assert _monobank_audit_helper_provider_reference_lines(local_module_path) == []


def test_monobank_client_factory_provider_reference_detection_catches_aliases_and_allows_local_values(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank import build_monobank_client\n"
        "from app.billing.providers.monobank import build_monobank_client as provider_factory\n"
        "from app.billing.providers.monobank.factory import build_monobank_client as factory_alias\n"
        "from app.billing.providers.monobank import factory as mono_factory\n"
        "from app.billing.providers import monobank as provider_mono\n"
        "import app.billing.providers.monobank\n"
        "import app.billing.providers.monobank as mono\n"
        "import app.billing.providers.monobank.factory as mono_factory_module\n"
        "factory_ref = build_monobank_client\n"
        "alias_ref = provider_factory\n"
        "factory_alias_ref = factory_alias\n"
        "module_ref = mono.build_monobank_client\n"
        "from_import_module_ref = mono_factory.build_monobank_client\n"
        "package_module_ref = provider_mono.build_monobank_client\n"
        "qualified_ref = app.billing.providers.monobank.build_monobank_client\n"
        "factory_module_ref = mono_factory_module.build_monobank_client\n"
        "direct_client = build_monobank_client(provider_mode='test')\n"
        "qualified_client = app.billing.providers.monobank.build_monobank_client(provider_mode='test')\n"
        "factory_module_client = mono_factory_module.build_monobank_client(provider_mode='test')\n",
        encoding="utf-8",
    )
    local_module_path = tmp_path / "local_module.py"
    local_module_path.write_text(
        "def build_monobank_client(**kwargs):\n"
        "    return kwargs\n"
        "def build_service(monobank_client_factory=None):\n"
        "    self = type('Service', (), {})()\n"
        "    self.monobank_client_factory = monobank_client_factory\n"
        "    return build_monobank_client(provider_mode='test')\n",
        encoding="utf-8",
    )

    assert _monobank_client_factory_provider_reference_lines(module_path) == [
        1,
        2,
        3,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
    ]
    assert _monobank_client_factory_provider_reference_lines(local_module_path) == []


def test_monobank_signature_verifier_provider_reference_detection_catches_aliases_and_allows_local_values(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.billing.providers.monobank import verify_monobank_webhook_signature\n"
        "from app.billing.providers.monobank import verify_monobank_webhook_signature as provider_verifier\n"
        "from app.billing.providers.monobank.signature import verify_monobank_webhook_signature as signature_verifier\n"
        "from app.billing.providers.monobank import signature as mono_signature\n"
        "from app.billing.providers import monobank as provider_mono\n"
        "import app.billing.providers.monobank\n"
        "import app.billing.providers.monobank as mono\n"
        "import app.billing.providers.monobank.signature as signature_module\n"
        "verifier_ref = verify_monobank_webhook_signature\n"
        "alias_ref = provider_verifier\n"
        "signature_alias_ref = signature_verifier\n"
        "module_ref = mono.verify_monobank_webhook_signature\n"
        "signature_module_ref = mono_signature.verify_monobank_webhook_signature\n"
        "package_ref = provider_mono.verify_monobank_webhook_signature\n"
        "package_signature_ref = provider_mono.signature.verify_monobank_webhook_signature\n"
        "qualified_ref = app.billing.providers.monobank.verify_monobank_webhook_signature\n"
        "qualified_signature_ref = app.billing.providers.monobank.signature.verify_monobank_webhook_signature\n"
        "signature_import_ref = signature_module.verify_monobank_webhook_signature\n"
        "direct_result = verify_monobank_webhook_signature(raw_body=b'{}')\n"
        "qualified_result = app.billing.providers.monobank.signature.verify_monobank_webhook_signature(raw_body=b'{}')\n",
        encoding="utf-8",
    )
    local_module_path = tmp_path / "local_module.py"
    local_module_path.write_text(
        "def verify_monobank_webhook_signature(**kwargs):\n"
        "    return bool(kwargs)\n"
        "def build_service(monobank_signature_verifier=None):\n"
        "    self = type('Service', (), {})()\n"
        "    self.monobank_signature_verifier = monobank_signature_verifier\n"
        "    local_verifier = verify_monobank_webhook_signature\n"
        "    return local_verifier(raw_body=b'{}')\n",
        encoding="utf-8",
    )

    assert _monobank_signature_verifier_provider_reference_lines(module_path) == [
        1,
        2,
        3,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
    ]
    assert _monobank_signature_verifier_provider_reference_lines(local_module_path) == []


def test_scripts_do_not_import_external_providers_or_http_transport() -> None:
    offenders = []
    for path in sorted(SCRIPTS_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT.parent)
        external_provider_lines = _external_provider_import_lines(path)
        http_transport_lines = _httpx_transport_usage_lines(path)
        offenders.extend(
            f"{relative_path.as_posix()}:{line}"
            for line in sorted({*external_provider_lines, *http_transport_lines})
        )

    assert offenders == []


def test_user_import_services_do_not_import_external_providers() -> None:
    offenders = []
    for path in sorted(USER_IMPORT_SERVICES_ROOT.rglob("*.py")):
        import_lines = _external_provider_import_lines(path)
        relative_path = path.relative_to(APP_ROOT)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_auth_modules_do_not_import_telegram_gateway() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_AUTH_ROOT.rglob("*.py")):
        import_lines = _telegram_gateway_import_lines(path)
        relative_path = path.relative_to(APP_ROOT)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_module_imported_names_reports_original_names_for_aliased_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text("from x import hash_token_for_lookup as h\n", encoding="utf-8")
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))

    assert "hash_token_for_lookup" in _module_imported_names(tree)


def test_client_api_router_does_not_write_billing_delivery_results_directly() -> None:
    offenders = _source_fragment_offenders(
        CLIENT_API_ROUTER_MODULE,
        (
            "db.billing.mark_",
            "db.billing.get_bot_notification_by_id",
        ),
    )

    assert offenders == []


def test_client_api_router_does_not_construct_runtime_services() -> None:
    offenders = _source_fragment_offenders(
        CLIENT_API_ROUTER_MODULE,
        (
            "BillingBotNotificationService",
            "ClientBotMessageService",
            "ClientReminderDispatchService",
        ),
    )

    assert offenders == []


def test_billing_api_router_does_not_construct_webhook_service() -> None:
    offenders = _source_fragment_offenders(
        BILLING_API_ROUTER_MODULE,
        (
            "BillingWebhookService",
            "monobank_client_factory",
            "monobank_webhook_signature_verifier",
            "queue_post_upgrade_rescan",
        ),
    )

    assert offenders == []


def test_billing_router_runtime_contract_requires_prewired_webhook_service() -> None:
    annotation_names, method_names = _class_member_names(
        BILLING_API_ROUTER_MODULE,
        "BillingRouterRuntime",
    )

    assert "billing_webhook_service" in annotation_names
    assert {
        "db",
        "time_service",
        "user_import_bound_google_doc_sync_service",
    }.isdisjoint(annotation_names)
    assert method_names == set()


def test_client_api_router_does_not_assemble_import_notification_sources() -> None:
    offenders = _source_fragment_offenders(
        CLIENT_API_ROUTER_MODULE,
        (
            "ClientImportNotificationService",
            "ClientImportSource",
            "user_import_scheduled_runtime_service",
            "client_admin_restore_service",
            "billing_notification_runtime_service",
            "dispatch_due_admin_bot_restores",
            "dispatch_due_billing_notifications",
        ),
    )

    assert offenders == []


def test_client_router_runtime_contract_does_not_require_clock_service() -> None:
    annotation_names, _ = _class_member_names(CLIENT_API_ROUTER_MODULE, "ClientRouterRuntime")

    assert "time_service" not in annotation_names


def test_api_router_runtime_contract_requires_client_import_notification_service() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }

    assert "client_import_notification_service" in annotation_names


def test_client_router_runtime_contract_requires_direct_runtime_services() -> None:
    annotation_names, _ = _class_member_names(CLIENT_API_ROUTER_MODULE, "ClientRouterRuntime")

    assert {
        "client_runtime_bootstrap_service",
        "client_runtime_input_service",
        "client_runtime_bot_message_service",
        "client_runtime_reminder_service",
        "client_import_notification_service",
        "subscription_maintenance_runtime_service",
        "billing_notification_service",
    }.issubset(annotation_names)


def test_client_runtime_bootstrap_service_contract_covers_bootstrap_restore_and_error_handling() -> None:
    _, method_names = _class_member_names(CLIENT_API_ROUTER_MODULE, "ClientRuntimeBootstrapService")

    assert {
        "bootstrap",
        "build_main_menu_restore_screen",
        "build_unexpected_error_screen",
        "log_unexpected_error",
    }.issubset(method_names)


def test_client_runtime_input_service_contract_covers_action_and_text_input() -> None:
    _, method_names = _class_member_names(CLIENT_API_ROUTER_MODULE, "ClientRuntimeInputService")

    assert {"handle_action", "handle_text_input"}.issubset(method_names)


def test_client_api_router_uses_local_adapter_error_handling_runtime_boundary() -> None:
    source = CLIENT_API_ROUTER_MODULE.read_text(encoding="utf-8")

    assert "log_unexpected_error(service" not in source
    assert "build_unexpected_error_screen(request.user)" not in source
    assert "client_adapter.log_unexpected_error" in source
    assert "client_adapter.build_unexpected_error_screen" in source


def test_composition_root_does_not_wire_menu_screen_callbacks_through_root_service() -> None:
    source = COMPOSITION_ROOT_MODULE.read_text(encoding="utf-8")

    assert "self.build_menu_screen" not in source


def test_client_router_runtime_contract_does_not_require_root_input_methods() -> None:
    _, method_names = _class_member_names(CLIENT_API_ROUTER_MODULE, "ClientRouterRuntime")

    assert {"handle_action", "handle_text_input"}.isdisjoint(method_names)


def test_api_router_runtime_contract_requires_subscription_maintenance_runtime_service() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }

    assert "subscription_maintenance_runtime_service" in annotation_names


def test_api_router_runtime_contract_requires_billing_notification_service() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }

    assert "billing_notification_service" in annotation_names


def test_api_router_runtime_contract_requires_billing_webhook_service() -> None:
    annotation_names, _ = _class_member_names(API_MODULE, "ApiRouterRuntime")

    assert "billing_webhook_service" in annotation_names


def test_api_router_runtime_contract_requires_client_runtime_bot_message_service() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }

    assert "client_runtime_bot_message_service" in annotation_names


def test_api_router_runtime_contract_requires_client_runtime_reminder_service() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }

    assert "client_runtime_reminder_service" in annotation_names


def test_api_router_runtime_contract_requires_client_runtime_bootstrap_service() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }

    assert "client_runtime_bootstrap_service" in annotation_names


def test_api_router_runtime_contract_requires_client_runtime_input_service() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }

    assert "client_runtime_input_service" in annotation_names


def test_api_router_runtime_contract_uses_client_learning_start_service_not_root_start_learning() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }
    method_names = {
        statement.name
        for statement in runtime_class.body
        if isinstance(statement, ast.FunctionDef)
    }

    assert "client_learning_start_service" in annotation_names
    assert "start_learning" not in method_names


def test_api_router_runtime_contract_does_not_require_root_screen_flow_methods() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    method_names = {
        statement.name
        for statement in runtime_class.body
        if isinstance(statement, ast.FunctionDef)
    }

    assert {
        "bootstrap",
        "handle_action",
        "handle_text_input",
        "build_main_menu_restore_screen",
    }.isdisjoint(method_names)


def test_api_router_runtime_contract_does_not_require_root_import_notification_method() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    method_names = {
        statement.name
        for statement in runtime_class.body
        if isinstance(statement, ast.FunctionDef)
    }

    assert "process_due_user_vocabulary_imports" not in method_names


def test_api_router_runtime_contract_uses_scheduled_runtime_for_user_import_attribute_queue() -> None:
    module = ast.parse(API_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ApiRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }
    method_names = {
        statement.name
        for statement in runtime_class.body
        if isinstance(statement, ast.FunctionDef)
    }

    assert "user_import_scheduled_runtime_service" in annotation_names
    assert "process_user_import_attribute_queue_now" not in method_names


def test_router_and_import_runtime_contracts_use_preparation_service_not_root_prepare_method() -> None:
    runtime_contracts = (
        (API_MODULE, "ApiRouterRuntime"),
        (
            APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE,
            "ClientWebImportProcessingRuntime",
        ),
    )
    missing_preparation_service = []
    root_prepare_methods = []
    for path, class_name in runtime_contracts:
        annotation_names, method_names = _class_member_names(path, class_name)
        relative_path = path.relative_to(APP_ROOT)
        contract_name = f"app/{relative_path.as_posix()}:{class_name}"
        if "user_import_preparation_service" not in annotation_names:
            missing_preparation_service.append(contract_name)
        if "prepare_import_job_items" in method_names:
            root_prepare_methods.append(contract_name)

    assert missing_preparation_service == []
    assert root_prepare_methods == []

    facade_annotation_names, facade_method_names = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportRuntime",
    )
    assert "user_import_preparation_service" not in facade_annotation_names
    assert "prepare_import_job_items" not in facade_method_names


def test_client_router_runtime_adapter_wires_direct_runtime_services() -> None:
    assignments = _class_init_attribute_assignments(
        CLIENT_API_ROUTER_MODULE,
        "_ClientRouterRuntimeAdapter",
    )

    expected_assignments = {
        "bootstrap_service": "runtime.client_runtime_bootstrap_service",
        "input_service": "runtime.client_runtime_input_service",
        "bot_message_service": "runtime.client_runtime_bot_message_service",
        "reminder_dispatch_service": "runtime.client_runtime_reminder_service",
        "import_notification_service": "runtime.client_import_notification_service",
        "subscription_maintenance_runtime_service": (
            "runtime.subscription_maintenance_runtime_service"
        ),
        "billing_notification_service": "runtime.billing_notification_service",
    }

    assert {
        name: assignments.get(name)
        for name in expected_assignments
    } == expected_assignments
    assert {
        name: value
        for name, value in assignments.items()
        if value in {"runtime", "learning_service"}
    } == {}


def test_client_router_runtime_adapter_delegates_client_methods_to_direct_services() -> None:
    method_calls = _class_method_call_names(
        CLIENT_API_ROUTER_MODULE,
        "_ClientRouterRuntimeAdapter",
    )
    expected_calls = {
        "bootstrap": {"self.bootstrap_service.bootstrap"},
        "handle_action": {"self.input_service.handle_action"},
        "handle_text_input": {"self.input_service.handle_text_input"},
        "restore_menu": {"self.bootstrap_service.build_main_menu_restore_screen"},
        "build_unexpected_error_screen": {
            "self.bootstrap_service.build_unexpected_error_screen"
        },
        "log_unexpected_error": {"self.bootstrap_service.log_unexpected_error"},
        "dispatch_due_reminders": {
            "self.reminder_dispatch_service.dispatch_due_reminders"
        },
        "track_bot_message": {"self.bot_message_service.track_bot_message"},
        "lookup_bot_message": {"self.bot_message_service.get_bot_message_log"},
        "list_active_bot_messages": {
            "self.bot_message_service.list_active_bot_messages"
        },
        "dispatch_due_bot_message_cleanup": {
            "self.bot_message_service.dispatch_due_bot_message_cleanup"
        },
        "process_due_import_notifications": {
            "self.import_notification_service.process_due_import_notifications"
        },
        "process_due_subscription_maintenance": {
            "self.subscription_maintenance_runtime_service."
            "process_due_subscription_maintenance"
        },
        "save_bot_message_cleanup_result": {
            "self.bot_message_service.save_bot_message_cleanup_result"
        },
        "save_billing_notification_delivery_result": {
            "self.billing_notification_service.save_bot_notification_delivery_result"
        },
        "save_billing_receipt_delivery_result": {
            "self.billing_notification_service.save_receipt_delivery_result"
        },
        "save_billing_receipt_admin_alert_result": {
            "self.billing_notification_service.save_receipt_admin_alert_result"
        },
    }
    mismatches = [
        f"{method}: {sorted(method_calls.get(method, set()))}"
        for method, expected_method_calls in expected_calls.items()
        if method_calls.get(method, set()) != expected_method_calls
    ]

    assert mismatches == []


def test_client_api_router_does_not_call_client_runtime_methods_through_root_service() -> None:
    root_receivers = (
        "learning_service",
        "runtime",
        "service",
        "self.learning_service",
        "self.runtime",
    )
    root_methods = (
        "bootstrap",
        "handle_action",
        "handle_text_input",
        "build_main_menu_restore_screen",
        "dispatch_due_reminders",
        "track_bot_message",
        "get_bot_message_log",
        "list_active_bot_messages",
        "dispatch_due_bot_message_cleanup",
        "save_bot_message_cleanup_result",
        "process_due_subscription_maintenance",
        "save_bot_notification_delivery_result",
        "save_receipt_delivery_result",
        "save_receipt_admin_alert_result",
        "process_due_user_vocabulary_imports",
        "dispatch_due_admin_bot_restores",
        "dispatch_due_billing_notifications",
    )
    forbidden_call_names = {
        f"{receiver}.{method}"
        for receiver in root_receivers
        for method in root_methods
    }
    offenders = [
        f"app/{CLIENT_API_ROUTER_MODULE.relative_to(APP_ROOT).as_posix()}:{line_number}"
        for line_number, call_name in _module_call_name_lines(CLIENT_API_ROUTER_MODULE)
        if call_name in forbidden_call_names
    ]
    fallback_offenders = _source_fragment_offenders(
        CLIENT_API_ROUTER_MODULE,
        (
            'hasattr(learning_service, "client_runtime_bootstrap_service")',
            'getattr(learning_service, "client_runtime_bootstrap_service"',
            'hasattr(learning_service, "client_runtime_input_service")',
            'getattr(learning_service, "client_runtime_input_service"',
            'hasattr(learning_service, "client_runtime_bot_message_service")',
            'hasattr(learning_service, "client_bot_message_service")',
            'hasattr(learning_service, "client_runtime_reminder_service")',
            'hasattr(learning_service, "client_reminder_dispatch_service")',
            'getattr(learning_service, "client_runtime_reminder_service"',
            'getattr(learning_service, "client_reminder_dispatch_service"',
            'hasattr(learning_service, "billing_notification_service")',
            'hasattr(runtime, "client_runtime_bootstrap_service")',
            'getattr(runtime, "client_runtime_bootstrap_service"',
            'hasattr(runtime, "client_runtime_input_service")',
            'getattr(runtime, "client_runtime_input_service"',
            'hasattr(runtime, "client_runtime_bot_message_service")',
            'hasattr(runtime, "client_runtime_reminder_service")',
            'getattr(runtime, "client_runtime_reminder_service"',
            'hasattr(runtime, "billing_notification_service")',
        ),
    )

    assert offenders == []
    assert fallback_offenders == []


def test_admin_router_does_not_import_telegram_gateway() -> None:
    offenders = []
    for line in _telegram_gateway_import_lines(ADMIN_ROUTER_MODULE):
        relative_path = ADMIN_ROUTER_MODULE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_admin_router_does_not_reach_into_composition_or_provider_boundaries() -> None:
    relative_path = ADMIN_ROUTER_MODULE.relative_to(APP_ROOT)
    forbidden_import_prefixes = (
        "app.composition",
        "app.external_providers",
        "app.telegram_gateway",
    )
    forbidden_references = (
        "build_admin_service_dependencies",
        "build_admin_telegram_gateway",
    )
    offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(ADMIN_ROUTER_MODULE)
        if any(
            module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
            for forbidden_prefix in forbidden_import_prefixes
        )
    ]
    for line_number, line in enumerate(ADMIN_ROUTER_MODULE.read_text(encoding="utf-8").splitlines(), 1):
        if any(reference in line for reference in forbidden_references):
            offenders.append(f"app/{relative_path.as_posix()}:{line_number}")

    assert offenders == []


def test_client_web_router_does_not_import_telegram_gateway() -> None:
    offenders = []
    for line in _telegram_gateway_import_lines(CLIENT_WEB_ROUTER_MODULE):
        relative_path = CLIENT_WEB_ROUTER_MODULE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_client_web_router_does_not_reach_into_composition_or_provider_boundaries() -> None:
    relative_path = CLIENT_WEB_ROUTER_MODULE.relative_to(APP_ROOT)
    forbidden_import_prefixes = (
        "app.composition",
        "app.external_providers",
    )
    forbidden_references = (
        "build_client_web_auth_telegram_gateway",
        "build_web_learning_telegram_gateway",
        "build_word_validation_provider",
        "fetch_google_doc_text_with_provider",
        "build_teacher_student_telegram_gateway",
        "build_google_calendar_meet_provider",
        "build_monobank_client",
    )
    offenders = [
        f"app/{relative_path.as_posix()}:{line}: {module}"
        for line, module in _direct_import_modules(CLIENT_WEB_ROUTER_MODULE)
        if any(
            module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
            for forbidden_prefix in forbidden_import_prefixes
        )
    ]
    for line_number, line in enumerate(CLIENT_WEB_ROUTER_MODULE.read_text(encoding="utf-8").splitlines(), 1):
        if any(reference in line for reference in forbidden_references):
            offenders.append(f"app/{relative_path.as_posix()}:{line_number}")

    assert offenders == []


def test_client_web_router_runtime_contract_uses_prewired_client_web_services() -> None:
    module = ast.parse(CLIENT_WEB_ROUTER_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ClientWebRouterRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }
    method_names = {
        statement.name
        for statement in runtime_class.body
        if isinstance(statement, ast.FunctionDef)
    }

    expected_annotations = {
        "client_web_auth_service",
        "client_web_learning_service",
        "client_web_import_service",
        "client_web_settings_service",
        "client_web_plan_service",
        "client_web_billing_checkout_service",
        "client_web_billing_payment_status_service",
        "client_web_billing_payment_history_service",
        "client_web_teacher_student_service",
        "client_web_import_event_streamer",
    }
    assert expected_annotations.issubset(annotation_names)
    assert {
        "user_import_preparation_service",
        "user_import_scheduled_runtime_service",
        "client_learning_start_service",
    }.isdisjoint(annotation_names)
    assert {
        "start_learning",
        "prepare_import_job_items",
        "process_user_import_attribute_queue_now",
    }.isdisjoint(method_names)


def test_client_web_router_does_not_construct_concrete_client_web_services_directly() -> None:
    forbidden_constructors = {
        "ClientWebAuthService",
        "ClientWebLearningService",
        "ClientWebImportService",
        "ClientWebImportProcessingService",
        "ClientWebSettingsService",
        "ClientWebPlanService",
        "BillingCheckoutService",
        "BillingPaymentStatusService",
        "BillingPaymentHistoryService",
        "ClientWebTeacherStudentService",
    }
    offenders = [
        f"app/{CLIENT_WEB_ROUTER_MODULE.relative_to(APP_ROOT).as_posix()}:{line}"
        for line, call_name in _module_call_name_lines(CLIENT_WEB_ROUTER_MODULE)
        if call_name in forbidden_constructors
    ]

    assert offenders == []


def test_client_web_import_runtime_contract_uses_explicit_application_ports() -> None:
    module = ast.parse(APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE.read_text(encoding="utf-8"))
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ClientWebImportRuntime"
    )
    runtime_annotations = {
        statement.target.id: ast.unparse(statement.annotation)
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }
    expected_annotations = {
        "db": "ClientWebImportDatabasePort",
        "time_service": "ClientWebImportTimeService",
    }

    assert {name: runtime_annotations.get(name) for name in expected_annotations} == expected_annotations
    assert {
        "user_import_preparation_service",
        "user_import_scheduled_runtime_service",
    }.isdisjoint(runtime_annotations)

    init_annotations = _class_init_param_annotation_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportService",
    )
    assert init_annotations.get("results_service") == {
        "ClientWebImportResultsServicePort"
    }
    assert init_annotations.get("processing_service") == {
        "ClientWebImportProcessingServicePort"
    }
    assert init_annotations.get("artifact_storage_provider") == {
        "UserImportArtifactStorageProvider"
    }
    assert {
        "event_publisher",
        "build_validation_provider",
    }.isdisjoint(init_annotations)
    service_class = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "ClientWebImportService"
    )
    init_node = next(
        node
        for node in service_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    kwonly_param_names = {param.arg for param in init_node.args.kwonlyargs}
    assert {
        "results_service",
        "processing_service",
        "artifact_storage_provider",
    }.issubset(kwonly_param_names)


def test_client_web_import_service_does_not_construct_results_service() -> None:
    module = ast.parse(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE.read_text(encoding="utf-8")
    )
    imported_results_service_lines = [
        node.lineno
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom)
        and node.module == "app.application.client_web.import_results_service"
        for alias in node.names
        if alias.name in {"ClientWebImportResultsService", "*"}
    ]
    constructed_results_service_lines = [
        line
        for line, call_name in _module_call_name_lines(
            APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE
        )
        if call_name == "ClientWebImportResultsService"
        or call_name.endswith(".ClientWebImportResultsService")
    ]

    assert imported_results_service_lines == []
    assert constructed_results_service_lines == []


def test_client_web_import_service_does_not_construct_processing_service() -> None:
    module = ast.parse(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE.read_text(encoding="utf-8")
    )
    imported_processing_service_lines = [
        node.lineno
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom)
        and node.module == "app.application.client_web.import_processing_service"
        for alias in node.names
        if alias.name in {"ClientWebImportProcessingService", "*"}
    ]
    constructed_processing_service_lines = [
        line
        for line, call_name in _module_call_name_lines(
            APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE
        )
        if call_name == "ClientWebImportProcessingService"
        or call_name.endswith(".ClientWebImportProcessingService")
    ]

    assert imported_processing_service_lines == []
    assert constructed_processing_service_lines == []


def test_client_web_import_processing_runtime_contract_uses_explicit_application_ports() -> None:
    module = ast.parse(
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE.read_text(
            encoding="utf-8"
        )
    )
    runtime_class = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef)
        and node.name == "ClientWebImportProcessingRuntime"
    )
    runtime_annotations = {
        statement.target.id: ast.unparse(statement.annotation)
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
    }
    expected_annotations = {
        "db": "ClientWebImportProcessingDatabasePort",
        "user_import_preparation_service": (
            "ClientWebImportProcessingPreparationServicePort"
        ),
        "user_import_scheduled_runtime_service": (
            "ClientWebImportProcessingScheduledRuntimeServicePort"
        ),
    }

    assert {
        name: runtime_annotations.get(name)
        for name in expected_annotations
    } == expected_annotations


def test_client_web_import_results_runtime_contract_uses_explicit_application_ports() -> None:
    module = ast.parse(
        APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE.read_text(encoding="utf-8")
    )
    runtime_class = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef)
        and node.name == "ClientWebImportResultsRuntime"
    )
    runtime_annotations = {
        statement.target.id: ast.unparse(statement.annotation)
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
    }
    expected_annotations = {
        "db": "ClientWebImportResultsDatabasePort",
        "user_import_preparation_service": (
            "ClientWebImportResultsPreparationServicePort"
        ),
    }

    assert {
        name: runtime_annotations.get(name)
        for name in expected_annotations
    } == expected_annotations


def test_client_web_import_application_ports_cover_runtime_dependencies() -> None:
    _, facade_user_import_jobs_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportUserImportJobsPort",
    )
    _, facade_google_docs_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportGoogleDocsPort",
    )
    facade_database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportDatabasePort",
    )
    _, facade_app_settings_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportAppSettingsPort",
    )
    _, processing_user_import_jobs_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE,
        "ClientWebImportProcessingUserImportJobsPort",
    )
    _, processing_google_docs_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE,
        "ClientWebImportProcessingGoogleDocsPort",
    )
    processing_database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE,
        "ClientWebImportProcessingDatabasePort",
    )
    _, processing_app_settings_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE,
        "ClientWebImportProcessingAppSettingsPort",
    )
    results_database_base_names = _class_base_names(
        APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE,
        "ClientWebImportResultsDatabasePort",
    )
    results_database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE,
        "ClientWebImportResultsDatabasePort",
    )

    assert facade_user_import_jobs_methods == {"create_job", "get_job_for_user"}
    assert facade_google_docs_methods == {"get_progress", "clear_binding"}
    assert facade_database_annotations == {
        "user_import_jobs",
        "user_import_google_docs",
        "app_settings",
    }
    assert "get_value" in facade_app_settings_methods
    assert processing_user_import_jobs_methods == {
        "mark_processing",
        "complete",
        "append_items",
        "get_job_for_user",
    }
    assert processing_google_docs_methods == {
        "set_binding",
        "mark_sync_success",
        "mark_progress",
    }
    assert processing_database_annotations == {
        "user_import_jobs",
        "user_import_google_docs",
        "app_settings",
    }
    assert "get_value" in processing_app_settings_methods
    assert {"user_import_jobs"} == results_database_annotations
    assert "ClientWebImportDatabasePort" not in results_database_base_names


def test_client_web_import_processing_service_uses_composed_import_collaborators() -> None:
    offenders = _source_fragment_offenders(
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE,
        (
            "UserImportValidationService(",
            "UserImportCandidateFilterService(",
            "UserEntitlementResolver(",
            'hasattr(self.db, "error_logs")',
            'getattr(self.db, "error_logs"',
        ),
    )

    assert offenders == []


def test_client_web_import_results_service_uses_composed_import_mode() -> None:
    offenders = _source_fragment_offenders(
        APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE,
        (
            "UserEntitlementResolver",
            "PlanLimitSettingsValidationError",
            "read_user_uuid",
            "app_settings",
            "subscriptions",
            "user_profiles",
        ),
    )

    assert offenders == []


def test_client_web_import_processing_service_call_sites_pass_explicit_collaborators() -> None:
    required_keywords = {
        "validation_service",
        "import_mode_for_user",
        "candidate_filter",
        "error_logger",
    }
    offenders = []
    for root in (APP_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relative_path = path.relative_to(APP_ROOT.parent)
            for node in ast.walk(module):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _attribute_chain_name(node.func)
                if call_name not in {
                    "ClientWebImportProcessingService",
                    "app.application.client_web.import_processing_service.ClientWebImportProcessingService",
                }:
                    continue
                keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
                missing_keywords = required_keywords - keyword_names
                if "build_validation_provider" in keyword_names or missing_keywords:
                    offenders.append(
                        f"{relative_path.as_posix()}:{node.lineno}:"
                        f"missing={sorted(missing_keywords)}"
                    )

    assert offenders == []


def test_client_web_import_results_service_call_sites_pass_import_mode_for_user() -> None:
    offenders = []
    for root in (APP_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            import_aliases = _import_alias_map(module, path)
            relative_path = path.relative_to(APP_ROOT.parent)
            for node in ast.walk(module):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _resolve_import_alias_name(_attribute_chain_name(node.func), import_aliases)
                if call_name not in {
                    "ClientWebImportResultsService",
                    "app.application.client_web.import_results_service.ClientWebImportResultsService",
                }:
                    continue
                keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
                if "import_mode_for_user" not in keyword_names:
                    offenders.append(f"{relative_path.as_posix()}:{node.lineno}")

    assert offenders == []


def test_client_web_import_result_query_job_methods_stay_in_results_port() -> None:
    submit_user_import_jobs_base_names = _class_base_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportUserImportJobsPort",
    )
    _, submit_user_import_jobs_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportUserImportJobsPort",
    )
    _, results_user_import_jobs_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE,
        "ClientWebImportResultsUserImportJobsPort",
    )

    assert submit_user_import_jobs_methods.isdisjoint(
        CLIENT_WEB_IMPORT_RESULT_QUERY_JOB_METHODS
    )
    assert "ClientWebImportResultsUserImportJobsPort" not in (
        submit_user_import_jobs_base_names
    )
    assert not {
        base_name
        for base_name in submit_user_import_jobs_base_names
        if base_name.startswith("ClientWebImportResults") and base_name.endswith("Port")
    }
    assert CLIENT_WEB_IMPORT_RESULT_QUERY_JOB_METHODS.issubset(
        results_user_import_jobs_methods
    )


def test_client_web_import_facade_does_not_call_result_query_job_methods() -> None:
    module = ast.parse(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE.read_text(encoding="utf-8")
    )
    service_class = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "ClientWebImportService"
    )
    offenders = []
    for node in ast.walk(service_class):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in CLIENT_WEB_IMPORT_RESULT_QUERY_JOB_METHODS:
            continue
        if _attribute_chain_name(node.func.value) == "self.db.user_import_jobs":
            offenders.append(
                f"app/{APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE.relative_to(APP_ROOT).as_posix()}:"
                f"{node.lineno}:self.db.user_import_jobs.{node.func.attr}"
            )

    assert offenders == []


def test_client_web_import_results_service_calls_list_unfinished_items_directly() -> None:
    module = ast.parse(
        APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE.read_text(
            encoding="utf-8"
        )
    )
    fallback_lines = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        call_name = _attribute_chain_name(node.func)
        if call_name not in {"hasattr", "getattr"} or len(node.args) < 2:
            continue
        target_name = _attribute_chain_name(node.args[0])
        method_name_node = node.args[1]
        method_name = (
            method_name_node.value
            if isinstance(method_name_node, ast.Constant)
            and isinstance(method_name_node.value, str)
            else None
        )
        if (
            target_name == "self.db.user_import_jobs"
            and method_name == "list_unfinished_items"
        ):
            fallback_lines.append(node.lineno)

    assert fallback_lines == []


def test_client_web_import_result_business_helpers_stay_in_results_service() -> None:
    _, import_service_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportService",
    )
    _, results_service_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_RESULTS_SERVICE_MODULE,
        "ClientWebImportResultsService",
    )
    moved_business_helpers = {
        "_repair_lookup_only_pending_job",
        "_list_unfinished_items",
        "_serialize_item",
        "_serialize_job",
    }

    assert import_service_methods.isdisjoint(moved_business_helpers)
    assert CLIENT_WEB_IMPORT_RESULTS_SERVICE_METHODS.issubset(results_service_methods)


def test_client_web_import_processing_methods_stay_in_processing_service() -> None:
    import_service_source = APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE.read_text(
        encoding="utf-8"
    )
    _, import_service_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE,
        "ClientWebImportService",
    )
    _, processing_service_methods = _class_member_names(
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE,
        "ClientWebImportProcessingService",
    )
    moved_processing_methods = {
        "process_submitted_import_job",
        "_append_and_prepare_items",
        "_mark_google_doc_progress",
        "_items_from_validation_outcome",
        "_candidate_batches",
        "_import_mode_for_user",
        "_publish_import_event",
    }

    assert import_service_methods.isdisjoint(moved_processing_methods)
    assert moved_processing_methods.issubset(processing_service_methods)
    assert "self.validation_service" not in import_service_source


def test_client_web_import_runtime_contract_uses_scheduled_runtime_for_user_import_attribute_queue() -> None:
    module = ast.parse(
        APPLICATION_CLIENT_WEB_IMPORT_PROCESSING_SERVICE_MODULE.read_text(
            encoding="utf-8"
        )
    )
    runtime_class = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef)
        and node.name == "ClientWebImportProcessingRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }
    method_names = {
        statement.name
        for statement in runtime_class.body
        if isinstance(statement, ast.FunctionDef)
    }

    assert "user_import_scheduled_runtime_service" in annotation_names
    assert "process_user_import_attribute_queue_now" not in method_names


def test_production_code_does_not_call_root_user_import_attribute_queue_method() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        call_lines = _root_user_import_attribute_queue_call_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in call_lines)

    assert offenders == []


def test_import_preparation_wiring_uses_composed_service_not_root_pass_through() -> None:
    forbidden_fragments_by_path = {
        COMPOSITION_ROOT_MODULE: ("self.prepare_import_job_items",),
        APPLICATION_CLIENT_WEB_IMPORT_SERVICE_MODULE: ("learning_service.prepare_import_job_items",),
    }
    offenders = []
    for path, forbidden_fragments in forbidden_fragments_by_path.items():
        relative_path = path.relative_to(APP_ROOT)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(fragment in line for fragment in forbidden_fragments):
                offenders.append(f"app/{relative_path.as_posix()}:{line_number}")

    assert offenders == []


def test_client_web_learning_runtime_contract_uses_client_learning_start_service_not_root_start_learning() -> None:
    module = ast.parse(
        APPLICATION_CLIENT_WEB_LEARNING_SERVICE_MODULE.read_text(encoding="utf-8")
    )
    runtime_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "ClientWebLearningRuntime"
    )
    annotation_names = {
        statement.target.id
        for statement in runtime_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }
    method_names = {
        statement.name
        for statement in runtime_class.body
        if isinstance(statement, ast.FunctionDef)
    }

    assert "client_learning_start_service" in annotation_names
    assert "start_learning" not in method_names


def test_client_web_learning_words_dependencies_stay_in_words_database_port() -> None:
    learning_database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_LEARNING_SERVICE_MODULE,
        "ClientWebLearningDatabasePort",
    )
    words_database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_LEARNING_WORDS_SERVICE_MODULE,
        "ClientWebLearningWordsDatabasePort",
    )

    assert learning_database_annotations.isdisjoint(CLIENT_WEB_LEARNING_WORDS_DATABASE_DEPENDENCIES)
    assert CLIENT_WEB_LEARNING_WORDS_DATABASE_DEPENDENCIES.issubset(words_database_annotations)


def test_client_web_learning_words_service_uses_composed_access_resolver() -> None:
    offenders = _source_fragment_offenders(
        APPLICATION_CLIENT_WEB_LEARNING_WORDS_SERVICE_MODULE,
        (
            "UserEntitlementResolver",
            "PlanLimitSettingsValidationError",
            "app_settings",
            "user_profiles",
            "subscriptions",
        ),
    )

    assert offenders == []


def test_client_web_learning_service_call_sites_pass_words_service() -> None:
    offenders = []
    for root in (APP_ROOT, SCRIPTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            import_aliases = _import_alias_map(module, path)
            relative_path = path.relative_to(APP_ROOT.parent)
            for node in ast.walk(module):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _resolve_import_alias_name(_attribute_chain_name(node.func), import_aliases)
                if call_name not in {
                    "ClientWebLearningService",
                    "app.application.client_web.learning_service.ClientWebLearningService",
                }:
                    continue
                keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
                if "words_service" not in keyword_names:
                    offenders.append(f"{relative_path.as_posix()}:{node.lineno}")

    assert offenders == []


def test_client_web_learning_session_dependencies_stay_in_session_database_port() -> None:
    learning_database_base_names = _class_base_names(
        APPLICATION_CLIENT_WEB_LEARNING_SERVICE_MODULE,
        "ClientWebLearningDatabasePort",
    )
    learning_database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_LEARNING_SERVICE_MODULE,
        "ClientWebLearningDatabasePort",
    )
    session_database_annotations, _ = _class_member_names(
        APPLICATION_CLIENT_WEB_LEARNING_SESSION_SERVICE_MODULE,
        "ClientWebLearningSessionDatabasePort",
    )

    assert (
        "ClientWebLearningSessionDatabasePort"
        not in learning_database_base_names
    )
    assert learning_database_annotations.isdisjoint(
        CLIENT_WEB_LEARNING_SESSION_DATABASE_DEPENDENCIES
    )
    assert CLIENT_WEB_LEARNING_SESSION_DATABASE_DEPENDENCIES.issubset(
        session_database_annotations
    )


def test_client_web_learning_words_facade_does_not_access_words_database_dependencies_directly() -> None:
    offenders = _self_db_dependency_accesses(
        APPLICATION_CLIENT_WEB_LEARNING_SERVICE_MODULE,
        "ClientWebLearningService",
        CLIENT_WEB_LEARNING_WORDS_DATABASE_DEPENDENCIES,
    )

    assert offenders == []


def test_client_web_learning_session_facade_does_not_access_session_database_dependencies_directly() -> None:
    offenders = _self_db_dependency_accesses(
        APPLICATION_CLIENT_WEB_LEARNING_SERVICE_MODULE,
        "ClientWebLearningService",
        CLIENT_WEB_LEARNING_SESSION_DATABASE_DEPENDENCIES,
    )

    assert offenders == []


def test_telegram_gateway_imports_are_confined_to_boundary_modules() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        if relative_path in TELEGRAM_GATEWAY_IMPORT_BOUNDARY_FILES:
            continue
        import_lines = _telegram_gateway_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_application_admin_settings_modules_do_not_import_external_providers() -> None:
    offenders = []
    for path in sorted(APPLICATION_ADMIN_SETTINGS_ROOT.rglob("*.py")):
        import_lines = _external_provider_import_lines(path)
        relative_path = path.relative_to(APP_ROOT)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_admin_exercise_text_generation_service_does_not_import_external_providers() -> None:
    offenders = []
    for line in _external_provider_import_lines(ADMIN_EXERCISE_TEXT_GENERATION_SERVICE):
        relative_path = ADMIN_EXERCISE_TEXT_GENERATION_SERVICE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_admin_exercise_text_tts_service_does_not_import_external_providers() -> None:
    offenders = []
    for line in _external_provider_import_lines(ADMIN_EXERCISE_TEXT_TTS_SERVICE):
        relative_path = ADMIN_EXERCISE_TEXT_TTS_SERVICE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_embedding_smoke_does_not_import_external_providers() -> None:
    offenders = []
    for line in _external_provider_import_lines(EMBEDDING_SMOKE_MODULE):
        relative_path = EMBEDDING_SMOKE_MODULE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_telegram_transient_helper_does_not_import_telegram_gateway() -> None:
    offenders = []
    for line in _telegram_gateway_import_lines(TELEGRAM_TRANSIENT_HELPER_MODULE):
        relative_path = TELEGRAM_TRANSIENT_HELPER_MODULE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_composition_root_does_not_import_external_providers() -> None:
    offenders = []
    for line in _external_provider_import_lines(COMPOSITION_ROOT_MODULE):
        relative_path = COMPOSITION_ROOT_MODULE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_embedding_worker_does_not_import_external_providers() -> None:
    offenders = []
    for line in _external_provider_import_lines(EMBEDDING_WORKER_MODULE):
        relative_path = EMBEDDING_WORKER_MODULE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_user_imports_legacy_facade_does_not_import_external_providers() -> None:
    offenders = []
    for line in _external_provider_import_lines(USER_IMPORTS_MODULE):
        relative_path = USER_IMPORTS_MODULE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_user_import_providers_is_not_external_provider_import_boundary_file() -> None:
    assert USER_IMPORT_PROVIDERS_MODULE.relative_to(APP_ROOT) not in EXTERNAL_PROVIDER_IMPORT_BOUNDARY_FILES


def test_user_import_providers_does_not_import_external_providers() -> None:
    offenders = []
    for line in _external_provider_import_lines(USER_IMPORT_PROVIDERS_MODULE):
        relative_path = USER_IMPORT_PROVIDERS_MODULE.relative_to(APP_ROOT)
        offenders.append(f"app/{relative_path.as_posix()}:{line}")

    assert offenders == []


def test_user_import_package_does_not_import_external_providers_or_own_http_transport() -> None:
    offenders = []
    for path in sorted(USER_IMPORT_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        import_lines = _external_provider_import_lines(path)
        http_transport_lines = _httpx_transport_usage_lines(path)
        offenders.extend(
            f"app/{relative_path.as_posix()}:{line}"
            for line in sorted({*import_lines, *http_transport_lines})
        )

    assert offenders == []


def test_user_import_provider_adapters_composition_module_is_external_provider_boundary_file() -> None:
    relative_path = USER_IMPORT_PROVIDER_ADAPTERS_COMPOSITION_MODULE.relative_to(APP_ROOT)

    assert relative_path in EXTERNAL_PROVIDER_IMPORT_BOUNDARY_FILES
    assert relative_path in HTTP_TRANSPORT_BOUNDARY_FILES
    assert _external_provider_import_lines(USER_IMPORT_PROVIDER_ADAPTERS_COMPOSITION_MODULE) != []
    assert _httpx_transport_usage_lines(USER_IMPORT_PROVIDER_ADAPTERS_COMPOSITION_MODULE) != []


def test_provider_setting_literal_source_of_truth_lives_in_domain_provider_settings() -> None:
    domain_values = _domain_provider_setting_literal_values()

    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path == DOMAIN_PROVIDER_SETTINGS_MODULE_PATH:
            continue
        relative_path = path.relative_to(APP_ROOT.parent)
        offenders.extend(
            f"{relative_path.as_posix()}:{line}: duplicate "
            f"{DOMAIN_PROVIDER_SETTINGS_MODULE}.{name} binding"
            for line, name in _top_level_name_binding_lines(
                path,
                set(DOMAIN_PROVIDER_SETTING_LITERAL_NAMES),
            )
        )
        for name, value in domain_values.items():
            offenders.extend(
                (
                    f"{relative_path.as_posix()}:{line}: duplicate "
                    f"{DOMAIN_PROVIDER_SETTINGS_MODULE}.{name} literal"
                )
                for line in _string_literal_value_lines(path, value)
            )

    assert offenders == []


def test_external_provider_imports_are_confined_to_boundary_modules() -> None:
    offenders = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        relative_path = path.relative_to(APP_ROOT)
        if relative_path.parts[0] == "external_providers":
            continue
        if relative_path in EXTERNAL_PROVIDER_IMPORT_BOUNDARY_FILES:
            continue
        import_lines = _external_provider_import_lines(path)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_client_web_student_services_do_not_own_http_transport() -> None:
    offenders = []
    for path in APPLICATION_CLIENT_WEB_TEACHER_STUDENTS_MODULES:
        import_lines = _httpx_transport_usage_lines(path)
        relative_path = path.relative_to(APP_ROOT)
        offenders.extend(f"app/{relative_path.as_posix()}:{line}" for line in import_lines)

    assert offenders == []


def test_external_provider_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.external_providers.user_import_openai import DEFAULT_OPENAI_API_URL\n"
        "import app.external_providers.user_import_deepl\n",
        encoding="utf-8",
    )

    assert _external_provider_import_lines(module_path) == [1, 2]


def test_string_literal_value_detection_catches_duplicate_provider_setting_literals(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.domain.provider_settings import DEFAULT_OPENAI_API_URL\n"
        "from app.domain.provider_settings import WORD_AUDIO_TASK_KEY as WORD_AUDIO_TASK_KEY\n"
        "fallback_api_url = 'https://api.openai.com/v1/responses'\n"
        "config = {'task_key': 'user_import.word_audio'}\n"
        "generation_config = {'task_key': 'exercise_texts.content_generation'}\n"
        "tts_provider_config = {'task_key': 'exercise_texts.tts'}\n"
        "task_log_type = 'exercise_texts.tts_generation'\n",
        encoding="utf-8",
    )

    assert _string_literal_value_lines(
        module_path, "https://api.openai.com/v1/responses"
    ) == [3]
    assert _string_literal_value_lines(module_path, "user_import.word_audio") == [4]
    assert _string_literal_value_lines(
        module_path, "exercise_texts.content_generation"
    ) == [5]
    assert _string_literal_value_lines(module_path, "exercise_texts.tts") == [6]


def test_external_provider_import_detection_catches_relative_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_root = tmp_path / "app"
    module_path = app_root / "user_import" / "providers.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text(
        "from ..external_providers.user_import_embeddings import X\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(__import__(__name__, fromlist=["APP_ROOT"]), "APP_ROOT", app_root)

    assert _external_provider_import_lines(module_path) == [1]


def test_telegram_gateway_import_detection_catches_imports(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "from app.telegram_gateway import TelegramGateway\n"
        "import app.telegram_gateway\n",
        encoding="utf-8",
    )

    assert _telegram_gateway_import_lines(module_path) == [1, 2]


def test_class_member_names_detects_sync_and_async_methods(tmp_path: Path) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "class Service:\n"
        "    value: int\n"
        "    def sync_method(self) -> None:\n"
        "        pass\n"
        "    async def async_method(self) -> None:\n"
        "        pass\n",
        encoding="utf-8",
    )

    annotation_names, method_names = _class_member_names(module_path, "Service")

    assert annotation_names == {"value"}
    assert method_names == {"sync_method", "async_method"}


def test_self_db_dependency_accesses_detects_direct_getattr_and_local_aliases(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "module.py"
    module_path.write_text(
        "class Service:\n"
        "    def direct_attribute(self):\n"
        "        return self.db.billing\n"
        "\n"
        "    def direct_getattr(self):\n"
        "        return getattr(self.db, 'subscriptions')\n"
        "\n"
        "    def alias_attribute(self):\n"
        "        db = self.db\n"
        "        return db.user_profiles\n"
        "\n"
        "    def alias_getattr(self):\n"
        "        database = self.db\n"
        "        return getattr(database, 'billing')\n"
        "\n"
        "    def branch_local_alias(self, flag, other):\n"
        "        if flag:\n"
        "            db = self.db\n"
        "        else:\n"
        "            db = other\n"
        "        return db.billing\n",
        encoding="utf-8",
    )

    offenders = _self_db_dependency_accesses(
        module_path,
        "Service",
        frozenset({"user_profiles", "subscriptions", "billing"}),
    )

    assert set(offenders) == {
        "3:self.db.billing",
        "6:getattr(self.db, 'subscriptions')",
        "10:db.user_profiles",
        "14:getattr(database, 'billing')",
        "21:db.billing",
    }


def _class_base_names(path: Path, class_name: str) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    target_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )

    return {
        base_name
        for base in target_class.bases
        if (base_name := _base_name(base)) is not None
    }


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return None


def _class_member_names(path: Path, class_name: str) -> tuple[set[str], set[str]]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    target_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    annotation_names = {
        statement.target.id
        for statement in target_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }
    method_names = {
        statement.name
        for statement in target_class.body
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    return annotation_names, method_names


def _self_db_dependency_accesses(
    path: Path,
    class_name: str,
    dependency_names: frozenset[str],
) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    target_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    offenders = set()
    for statement in target_class.body:
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
            visitor = _SelfDbDependencyAccessVisitor(dependency_names)
            visitor.visit(statement)
            offenders.update(visitor.offenders)
    return sorted(set(offenders))


class _SelfDbDependencyAccessVisitor(ast.NodeVisitor):
    def __init__(self, dependency_names: frozenset[str]) -> None:
        self._dependency_names = dependency_names
        self._self_db_aliases: set[str] = set()
        self._function_self_db_aliases: set[str] = set()
        self.offenders: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        owner_name = _self_db_dependency_owner_name(
            node.value,
            self._self_db_aliases,
        )
        if owner_name is not None and node.attr in self._dependency_names:
            self.offenders.add(f"{node.lineno}:{owner_name}.{node.attr}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        dependency_name = (
            node.args[1].value
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            )
            else None
        )
        owner_name = (
            _self_db_dependency_owner_name(node.args[0], self._self_db_aliases)
            if dependency_name in self._dependency_names
            else None
        )
        if owner_name is not None:
            self.offenders.add(
                f"{node.lineno}:getattr({owner_name}, {dependency_name!r})"
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        self._update_assignment_aliases(node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
            self._update_assignment_aliases([node.target], node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        self._self_db_aliases.difference_update(
            _simple_name_targets([node.target]) - self._function_self_db_aliases
        )

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        previous_aliases = self._self_db_aliases.copy()
        previous_function_aliases = self._function_self_db_aliases.copy()
        self._function_self_db_aliases = _function_self_db_assignment_aliases(node)
        self._self_db_aliases.update(self._function_self_db_aliases)
        self.generic_visit(node)
        self._self_db_aliases = previous_aliases
        self._function_self_db_aliases = previous_function_aliases

    def _update_assignment_aliases(
        self,
        targets: list[ast.expr],
        value: ast.expr,
    ) -> None:
        target_names = _simple_name_targets(targets)
        if _is_self_db_node(value):
            self._self_db_aliases.update(target_names)
        else:
            self._self_db_aliases.difference_update(
                target_names - self._function_self_db_aliases
            )


def _function_self_db_assignment_aliases(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    visitor = _SelfDbAssignmentAliasVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return visitor.aliases


class _SelfDbAssignmentAliasVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.aliases: set[str] = set()

    def visit_FunctionDef(self, _node: ast.FunctionDef) -> None:
        pass

    def visit_AsyncFunctionDef(self, _node: ast.AsyncFunctionDef) -> None:
        pass

    def visit_ClassDef(self, _node: ast.ClassDef) -> None:
        pass

    def visit_Assign(self, node: ast.Assign) -> None:
        if _is_self_db_node(node.value):
            self.aliases.update(_simple_name_targets(node.targets))

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None and _is_self_db_node(node.value):
            self.aliases.update(_simple_name_targets([node.target]))


def _simple_name_targets(targets: list[ast.expr]) -> set[str]:
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _self_db_dependency_owner_name(
    node: ast.AST,
    self_db_aliases: set[str],
) -> str | None:
    if _is_self_db_node(node):
        return "self.db"
    if isinstance(node, ast.Name) and node.id in self_db_aliases:
        return node.id
    return None


def _is_self_db_node(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "db"
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _user_dictionary_status_assignment_lines(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        else:
            continue
        offenders.extend(
            (node.lineno, name)
            for target in targets
            for name in _assignment_target_names(target)
            if name in USER_DICTIONARY_STATUS_CONSTANT_NAMES
        )
    return sorted(set(offenders))


def _assignment_target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Tuple | ast.List):
        names = []
        for element in target.elts:
            names.extend(_assignment_target_names(element))
        return names
    return []


def _top_level_name_binding_lines(
    path: Path,
    names: set[str],
) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name in names:
                offenders.append((node.lineno, node.name))
            continue
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        else:
            continue
        offenders.extend(
            (node.lineno, name)
            for target in targets
            for name in _assignment_target_names(target)
            if name in names
        )
    return sorted(set(offenders))


def _top_level_billing_vocabulary_binding_lines(
    path: Path,
    *,
    include_literal_duplicates: bool,
) -> list[tuple[int, str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name in BILLING_VOCABULARY_CONSTANT_NAMES:
                offenders.append((node.lineno, node.name, node.name))
            continue
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
            value = None
        else:
            continue

        target_names = [
            name
            for target in targets
            for name in _assignment_target_names(target)
        ]
        for name in target_names:
            if name in BILLING_VOCABULARY_CONSTANT_NAMES:
                offenders.append((node.lineno, name, name))

        if not include_literal_duplicates or value is None:
            continue
        vocabulary_name = _billing_vocabulary_literal_name(value)
        if vocabulary_name is None:
            continue
        offenders.extend((node.lineno, name, vocabulary_name) for name in target_names)
    return sorted(set(offenders))


def _billing_vocabulary_literal_name(value: ast.AST) -> str | None:
    literal_values = _literal_string_collection_values(value)
    if literal_values is None:
        return None
    return BILLING_VOCABULARY_LITERAL_VALUES.get(literal_values)


def _inline_billing_terminal_status_literal_duplicate_lines(
    path: Path,
) -> list[tuple[int, str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    top_level_literal_sets = _top_level_billing_vocabulary_literal_sets(tree)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Set) or node in top_level_literal_sets:
            continue
        if _billing_vocabulary_literal_name(node) != "BILLING_TERMINAL_STATUSES":
            continue
        offenders.append(
            (node.lineno, "inline set literal", "BILLING_TERMINAL_STATUSES")
        )
    return sorted(set(offenders))


def _top_level_billing_vocabulary_literal_sets(tree: ast.Module) -> set[ast.Set]:
    literal_sets = set()
    for node in tree.body:
        value = _assignment_value(node)
        if value is None or _billing_vocabulary_literal_name(value) is None:
            continue
        literal_sets.update(
            child for child in ast.walk(value) if isinstance(child, ast.Set)
        )
    return literal_sets


def _assignment_value(node: ast.AST) -> ast.AST | None:
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    return None


def _domain_provider_setting_literal_values() -> dict[str, str]:
    tree = ast.parse(
        DOMAIN_PROVIDER_SETTINGS_MODULE_PATH.read_text(encoding="utf-8"),
        filename=str(DOMAIN_PROVIDER_SETTINGS_MODULE_PATH),
    )
    values_by_name: dict[str, list[ast.AST]] = {
        name: [] for name in DOMAIN_PROVIDER_SETTING_LITERAL_NAMES
    }
    for node in tree.body:
        value = _assignment_value(node)
        if value is None:
            continue
        target_names = []
        if isinstance(node, ast.Assign):
            for target in node.targets:
                target_names.extend(_assignment_target_names(target))
        elif isinstance(node, ast.AnnAssign):
            target_names.extend(_assignment_target_names(node.target))
        for name in target_names:
            if name in values_by_name:
                values_by_name[name].append(value)

    literal_values = {}
    for name, values in values_by_name.items():
        assert len(values) == 1
        value = values[0]
        assert isinstance(value, ast.Constant)
        assert isinstance(value.value, str)
        literal_values[name] = value.value
    return literal_values


def _string_literal_value_lines(path: Path, value: str) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return sorted(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value == value
        }
    )


def _literal_string_collection_values(value: ast.AST) -> frozenset[str] | None:
    if isinstance(value, ast.Call):
        if (
            not isinstance(value.func, ast.Name)
            or value.func.id not in {"frozenset", "set"}
            or len(value.args) != 1
            or value.keywords
        ):
            return None
        return _literal_string_collection_values(value.args[0])

    if not isinstance(value, ast.Set | ast.List | ast.Tuple):
        return None

    values = []
    for element in value.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        values.append(element.value)
    return frozenset(values)


def _is_billing_vocabulary_literal_scan_path(path: Path) -> bool:
    return path in BILLING_VOCABULARY_LITERAL_SCAN_FILES or any(
        path.is_relative_to(root) for root in BILLING_VOCABULARY_LITERAL_SCAN_ROOTS
    )


def _data_access_user_dictionary_status_import_lines(path: Path) -> list[int]:
    return _data_access_user_dictionary_constant_import_lines(
        path,
        DATA_ACCESS_USER_DICTIONARY_STATUS_MODULE_NAMES,
        USER_DICTIONARY_STATUS_CONSTANT_NAMES,
    )


def _data_access_user_dictionary_assignment_source_import_lines(path: Path) -> list[int]:
    return _data_access_user_dictionary_constant_import_lines(
        path,
        DATA_ACCESS_USER_DICTIONARY_ASSIGNMENT_SOURCE_MODULE_NAMES,
        USER_DICTIONARY_ASSIGNMENT_SOURCE_CONSTANT_NAMES,
    )


def _inline_user_word_assignment_status_literal_lines(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            expressions = [node.left, *node.comparators]
            if not any(
                _is_user_word_assignment_status_reference(expression, import_aliases)
                for expression in expressions
            ):
                continue
            for expression in expressions:
                offenders.extend(_literal_string_value_lines(expression))
            continue

        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in {
            "in_",
            "not_in",
            "notin_",
        }:
            continue
        if not _is_user_word_assignment_status_reference(node.func.value, import_aliases):
            continue
        for argument in node.args:
            offenders.extend(_literal_string_value_lines(argument))
    return sorted(set(offenders))


def _is_user_word_assignment_status_reference(
    node: ast.AST,
    import_aliases: dict[str, str],
) -> bool:
    reference_name = _resolve_import_alias_name(_attribute_chain_name(node), import_aliases)
    return reference_name in {
        "UserWordAssignment.status",
        "app.models.UserWordAssignment.status",
        "app.models.dictionary.UserWordAssignment.status",
    }


def _literal_string_value_lines(node: ast.AST) -> list[tuple[int, str]]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [(node.lineno, node.value)]
    if isinstance(node, ast.List | ast.Set | ast.Tuple):
        values = []
        for element in node.elts:
            values.extend(_literal_string_value_lines(element))
        return values
    return []


def _data_access_user_dictionary_constant_import_lines(
    path: Path,
    module_names: frozenset[str],
    constant_names: set[str],
) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in module_names and any(
                alias.name == "*" or alias.name in constant_names
                for alias in node.names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = (
                _attribute_chain_name(node)
                if isinstance(node, ast.Attribute)
                else node.id
            )
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if _is_data_access_user_dictionary_constant_reference(
                resolved_reference_name,
                module_names,
                constant_names,
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _is_data_access_user_dictionary_constant_reference(
    name: str | None,
    module_names: frozenset[str],
    constant_names: set[str],
) -> bool:
    if name is None:
        return False
    for module_name in module_names:
        prefix = f"{module_name}."
        if name.startswith(prefix) and name.removeprefix(prefix) in constant_names:
            return True
    return False


def _source_fragment_offenders(path: Path, fragments: tuple[str, ...]) -> list[str]:
    relative_path = path.relative_to(APP_ROOT)
    offenders = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if any(fragment in line for fragment in fragments):
            offenders.append(f"app/{relative_path.as_posix()}:{line_number}")
    return offenders


def _class_init_attribute_assignments(
    path: Path,
    class_name: str,
) -> dict[str, str | None]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    target_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    init_method = next(
        node
        for node in target_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assignments = {}
    for node in ast.walk(init_method):
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        for target in targets:
            target_name = _attribute_chain_name(target)
            if target_name is None or not target_name.startswith("self."):
                continue
            assignments[target_name.removeprefix("self.")] = _attribute_chain_name(value)
    return assignments


def _class_method_call_names(path: Path, class_name: str) -> dict[str, set[str]]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    target_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method_calls = {}
    for statement in target_class.body:
        if not isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        call_names = {
            call_name
            for node in ast.walk(statement)
            if isinstance(node, ast.Call)
            if (call_name := _attribute_chain_name(node.func)) is not None
        }
        method_calls[statement.name] = call_names
    return method_calls


def _module_call_name_lines(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    call_name_lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _attribute_chain_name(node.func)
        if call_name is not None:
            call_name_lines.append((node.lineno, call_name))
    return sorted(set(call_name_lines))


def _readme_concrete_app_path_references(markdown: str) -> list[str]:
    references = []
    seen = set()
    for match in re.finditer(r"(?<!`)`([^`\n]+)`(?!`)", markdown):
        reference = match.group(1).strip()
        if not reference.startswith("app/") or any(
            marker in reference for marker in "*?[]"
        ):
            continue
        if reference in seen:
            continue
        references.append(reference)
        seen.add(reference)
    return references


def _is_raw_sql_allowed_path(path: Path) -> bool:
    return path in RAW_SQL_ALLOWED_FILES or any(
        path.is_relative_to(root) for root in RAW_SQL_ALLOWED_ROOTS
    )


def _raw_sql_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in RAW_SQL_TEXT_IMPORT_MODULES and any(
                alias.name in {"text", "*"} for alias in node.names
            ):
                lines.append(node.lineno)
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "exec_driver_sql":
            lines.append(node.lineno)
            continue
        raw_sql_callable_name = _attribute_chain_name(node.func)
        resolved_callable_name = _resolve_import_alias_name(
            raw_sql_callable_name,
            import_aliases,
        )
        if resolved_callable_name in RAW_SQL_FORBIDDEN_CALLABLE_NAMES:
            lines.append(node.lineno)
    return sorted(set(lines))


def _iter_lower_layer_paths() -> list[Path]:
    paths = []
    seen = set()
    for root in LOWER_LAYER_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if path not in seen:
                paths.append(path)
                seen.add(path)
    for path in LOWER_LAYER_FILES:
        if path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


def _learning_service_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.learning_service" or module.startswith("app.learning_service."):
                lines.append(node.lineno)
            if module == "app":
                for alias in node.names:
                    if alias.name == "learning_service":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.learning_service" or alias.name.startswith("app.learning_service."):
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _legacy_repositories_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.repositories" or (
                module is not None and module.startswith("app.repositories.")
            ):
                lines.append(node.lineno)
            if module == "app":
                for alias in node.names:
                    if alias.name == "repositories":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.repositories" or alias.name.startswith("app.repositories."):
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _module_all_names(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        return list(value)
    return []


def _module_imported_names(tree: ast.Module) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom | ast.Import):
            continue
        names.update(alias.name for alias in node.names)
    return names


def _user_imports_facade_scan_paths() -> list[Path]:
    paths = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT):
        paths.extend(sorted(root.rglob("*.py")))
    paths.extend(_word_base_user_imports_facade_scan_paths())
    return paths


def _legacy_provider_exports_facade_scan_paths() -> list[Path]:
    paths = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        paths.extend(sorted(root.rglob("*.py")))
    return [path for path in paths if path != LEGACY_PROVIDER_EXPORTS_MODULE]


def _admin_service_facade_scan_paths() -> list[Path]:
    paths = []
    for root in (APP_ROOT, TESTS_ROOT, SCRIPTS_ROOT, WORD_BASE_ROOT):
        paths.extend(sorted(root.rglob("*.py")))
    return [path for path in paths if path != ADMIN_SERVICE_MODULE]


def _word_base_user_imports_facade_scan_paths() -> list[Path]:
    ignored_local_drafts_root = WORD_BASE_ROOT / "reading_listening"
    return [
        path
        for path in sorted(WORD_BASE_ROOT.rglob("*.py"))
        if not path.is_relative_to(ignored_local_drafts_root)
    ]


def _user_import_package_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.user_import":
                lines.append(node.lineno)
            if module == "app":
                for alias in node.names:
                    if alias.name == "user_import":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.user_import":
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _bot_runtime_package_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.bot_runtime":
                lines.append(node.lineno)
            if module == "app":
                for alias in node.names:
                    if alias.name == "bot_runtime":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.bot_runtime":
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _minimal_package_facade_shape_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    all_count = 0
    for node in tree.body:
        if _is_module_docstring_node(node):
            continue
        if isinstance(node, ast.Assign):
            targets = [target for target in node.targets if isinstance(target, ast.Name)]
            if len(targets) != 1 or targets[0].id != "__all__":
                violations.append(f"{path}:{node.lineno}: unexpected Assign")
                continue
            all_count += 1
            if all_count > 1:
                violations.append(f"{path}:{node.lineno}: duplicate __all__ assignment")
                continue
            try:
                names = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                violations.append(f"{path}:{node.lineno}: non-literal __all__ assignment")
                continue
            if not isinstance(names, tuple | list) or any(names):
                violations.append(f"{path}:{node.lineno}: non-empty __all__ assignment")
            continue
        violations.append(f"{path}:{node.lineno}: unexpected {type(node).__name__}")
    return violations


def _marker_only_package_facade_shape_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    marker_target_prefixes = {
        "RETIRED_APPLICATION_MODULE": "app.application.",
        "RETIRED_COMPOSITION_MODULE": "app.composition.",
    }
    for node in tree.body:
        if _is_module_docstring_node(node):
            continue
        if isinstance(node, ast.Assign):
            targets = [target for target in node.targets if isinstance(target, ast.Name)]
            if len(targets) != 1 or targets[0].id not in marker_target_prefixes:
                violations.append(f"{path}:{node.lineno}: unexpected Assign")
                continue
            marker_name = targets[0].id
            try:
                target_module = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                violations.append(f"{path}:{node.lineno}: non-literal retired target marker")
                continue
            if not isinstance(target_module, str) or not target_module.startswith(
                marker_target_prefixes[marker_name]
            ):
                violations.append(f"{path}:{node.lineno}: invalid retired target marker")
            continue
        violations.append(f"{path}:{node.lineno}: unexpected {type(node).__name__}")
    return violations


def _explicit_reexport_wrapper_shape_violations(
    path: Path,
    target_module: str,
) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    imported_names = []
    import_count = 0
    all_count = 0
    all_names: list[str] | None = None
    for node in tree.body:
        if _is_module_docstring_node(node):
            continue
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__" and all(
                alias.name == "annotations" and alias.asname is None for alias in node.names
            ):
                continue
            import_count += 1
            module = _resolve_import_from_module(path, node)
            if module != target_module:
                violations.append(f"{path}:{node.lineno}: unexpected re-export source")
            for alias in node.names:
                if alias.name == "*":
                    violations.append(f"{path}:{node.lineno}: wildcard re-export")
                    continue
                if alias.asname is not None:
                    violations.append(f"{path}:{node.lineno}: aliased re-export")
                imported_names.append(alias.name)
            continue
        if isinstance(node, ast.Assign):
            targets = [target for target in node.targets if isinstance(target, ast.Name)]
            if len(targets) != 1 or targets[0].id != "__all__":
                violations.append(f"{path}:{node.lineno}: unexpected Assign")
                continue
            all_count += 1
            if all_count > 1:
                violations.append(f"{path}:{node.lineno}: duplicate __all__ assignment")
                continue
            try:
                names = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                violations.append(f"{path}:{node.lineno}: non-literal __all__ assignment")
                continue
            if not isinstance(names, tuple | list) or not all(
                isinstance(name, str) for name in names
            ):
                violations.append(f"{path}:{node.lineno}: invalid __all__ assignment")
                continue
            all_names = list(names)
            continue
        violations.append(f"{path}:{node.lineno}: unexpected {type(node).__name__}")

    if import_count != 1:
        violations.append(f"{path}: expected exactly one re-export import")
    if all_count != 1:
        violations.append(f"{path}: expected exactly one __all__ assignment")
    if len(imported_names) != len(set(imported_names)):
        violations.append(f"{path}: duplicate imported re-export names")
    if all_names is not None and len(all_names) != len(set(all_names)):
        violations.append(f"{path}: duplicate __all__ names")
    if all_names is not None and set(imported_names) != set(all_names):
        missing = sorted(set(imported_names) - set(all_names))
        extra = sorted(set(all_names) - set(imported_names))
        violations.append(f"{path}: __all__ mismatch missing={missing} extra={extra}")
    return violations


def _controlled_model_export_hub_shape_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    imported_names = []
    all_count = 0
    all_names: list[str] | None = None
    for node in tree.body:
        if _is_module_docstring_node(node):
            continue
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if not _is_models_submodule_export_source(module):
                violations.append(f"{path}:{node.lineno}: unexpected model export source")
            for alias in node.names:
                if alias.name == "*":
                    violations.append(f"{path}:{node.lineno}: wildcard model export")
                    continue
                if alias.asname is not None:
                    violations.append(f"{path}:{node.lineno}: aliased model export")
                imported_names.append(alias.name)
            continue
        if isinstance(node, ast.Assign):
            targets = [target for target in node.targets if isinstance(target, ast.Name)]
            if len(targets) != 1 or targets[0].id != "__all__":
                violations.append(f"{path}:{node.lineno}: unexpected Assign")
                continue
            all_count += 1
            if all_count > 1:
                violations.append(f"{path}:{node.lineno}: duplicate __all__ assignment")
                continue
            try:
                names = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                violations.append(f"{path}:{node.lineno}: non-literal __all__ assignment")
                continue
            if not isinstance(names, tuple | list) or not all(
                isinstance(name, str) for name in names
            ):
                violations.append(f"{path}:{node.lineno}: invalid __all__ assignment")
                continue
            all_names = list(names)
            continue
        violations.append(f"{path}:{node.lineno}: unexpected {type(node).__name__}")

    if all_count != 1:
        violations.append(f"{path}: expected exactly one __all__ assignment")
    if len(imported_names) != len(set(imported_names)):
        violations.append(f"{path}: duplicate imported model export names")
    if all_names is not None and len(all_names) != len(set(all_names)):
        violations.append(f"{path}: duplicate __all__ names")
    if all_names is not None and set(imported_names) != set(all_names):
        missing = sorted(set(imported_names) - set(all_names))
        extra = sorted(set(all_names) - set(imported_names))
        violations.append(f"{path}: __all__ mismatch missing={missing} extra={extra}")
    if all_names is not None and "Base" not in all_names:
        violations.append(f"{path}: expected Base export")
    return violations


def _is_models_submodule_export_source(module: str | None) -> bool:
    if module is None or not module.startswith("app.models."):
        return False
    submodule = module.removeprefix("app.models.")
    return bool(submodule) and "." not in submodule


def _api_package_facade_import_lines(path: Path) -> list[int]:
    return sorted(
        set(
            _package_facade_import_lines(path, "app.admin_api")
            + _package_facade_import_lines(path, "app.client_api")
        )
    )


def _package_facade_import_lines(
    path: Path,
    package_name: str,
    *,
    allowed_import_from_names: set[str] | frozenset[str] = frozenset(),
) -> list[int]:
    parent_module, _, package_basename = package_name.rpartition(".")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == package_name:
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == package_name:
                if allowed_import_from_names and all(
                    alias.name in allowed_import_from_names for alias in node.names
                ):
                    continue
                lines.append(node.lineno)
                continue
            if module == parent_module:
                for alias in node.names:
                    if alias.name == package_basename:
                        lines.append(node.lineno)
                        break
    return sorted(set(lines))









def _retired_admin_import_facade_helper_validator_import_lines(path: Path) -> list[int]:
    return sorted(
        set(
            _package_facade_import_lines(
                path,
                ADMIN_API_IMPORTS_PACKAGE_NAME,
                allowed_import_from_names=ADMIN_API_IMPORTS_ALLOWED_PACKAGE_IMPORT_NAMES,
            )
            + _concrete_module_import_lines(
                path,
                RETIRED_ADMIN_IMPORT_HELPERS_PACKAGE_NAME,
            )
            + _concrete_module_import_lines(
                path,
                RETIRED_ADMIN_IMPORT_VALIDATORS_PACKAGE_NAME,
            )
        )
    )


def _retired_admin_billing_facade_import_lines(path: Path) -> list[int]:
    return _package_facade_import_lines(
        path,
        ADMIN_API_BILLING_PACKAGE_NAME,
        allowed_import_from_names=ADMIN_API_BILLING_ALLOWED_PACKAGE_IMPORT_NAMES,
    )


def _retired_admin_ai_usage_facade_action_otp_import_lines(path: Path) -> list[int]:
    return sorted(
        set(
            _package_facade_import_lines(
                path,
                ADMIN_API_AI_USAGE_PACKAGE_NAME,
                allowed_import_from_names=ADMIN_API_AI_USAGE_ALLOWED_PACKAGE_IMPORT_NAMES,
            )
            + _concrete_module_import_lines(
                path,
                f"{ADMIN_API_AI_USAGE_PACKAGE_NAME}.action_otp",
            )
        )
    )


def _retired_admin_settings_facade_action_otp_import_lines(path: Path) -> list[int]:
    return sorted(
        set(
            _package_facade_import_lines(
                path,
                ADMIN_API_SETTINGS_PACKAGE_NAME,
                allowed_import_from_names=ADMIN_API_SETTINGS_ALLOWED_PACKAGE_IMPORT_NAMES,
            )
            + _concrete_module_import_lines(
                path,
                f"{ADMIN_API_SETTINGS_PACKAGE_NAME}.action_otp",
            )
        )
    )


def _admin_bootstrap_api_service_module_import_lines(path: Path) -> list[int]:
    forbidden_module = "app.admin_api.bootstrap.services.bootstrap_service"
    parent_module = "app.admin_api.bootstrap.services"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == forbidden_module or alias.name.startswith(f"{forbidden_module}."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == forbidden_module or (
                module is not None and module.startswith(f"{forbidden_module}.")
            ):
                lines.append(node.lineno)
                continue
            if module == parent_module:
                for alias in node.names:
                    if alias.name in {"*", "bootstrap_service"}:
                        lines.append(node.lineno)
                        break
    return sorted(set(lines))











def _monobank_provider_package_facade_import_lines(path: Path) -> list[int]:
    return _package_facade_import_lines(path, MONOBANK_PROVIDER_PACKAGE)


def _user_import_services_package_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.user_import.services":
                lines.append(node.lineno)
            if module == "app.user_import":
                for alias in node.names:
                    if alias.name == "services":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.user_import.services":
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _user_imports_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.user_imports" or module.startswith("app.user_imports."):
                lines.append(node.lineno)
            if module == "app":
                for alias in node.names:
                    if alias.name == "user_imports":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.user_imports" or alias.name.startswith("app.user_imports."):
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _legacy_provider_exports_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.user_import.legacy_provider_exports" or (
                module is not None
                and module.startswith("app.user_import.legacy_provider_exports.")
            ):
                lines.append(node.lineno)
            if module == "app.user_import":
                for alias in node.names:
                    if alias.name == "legacy_provider_exports":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.user_import.legacy_provider_exports" or alias.name.startswith(
                    "app.user_import.legacy_provider_exports."
                ):
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _is_module_docstring_node(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _admin_service_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.admin_service" or module.startswith("app.admin_service."):
                lines.append(node.lineno)
            if module == "app":
                for alias in node.names:
                    if alias.name == "admin_service":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.admin_service" or alias.name.startswith("app.admin_service."):
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _legacy_audio_response_helper_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.helpers.audio_response" or module.startswith(
                "app.helpers.audio_response."
            ):
                lines.append(node.lineno)
            if module == "app":
                for alias in node.names:
                    if alias.name == "helpers.audio_response" or alias.name.startswith(
                        "helpers.audio_response."
                    ):
                        lines.append(node.lineno)
                        break
            if module == "app.helpers":
                for alias in node.names:
                    if alias.name == "audio_response":
                        lines.append(node.lineno)
                        break
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.helpers.audio_response" or alias.name.startswith(
                    "app.helpers.audio_response."
                ):
                    lines.append(node.lineno)
                    break
    return sorted(set(lines))


def _direct_audio_file_mutation_call_lines(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _attribute_chain_name(node.func) if isinstance(node.func, ast.Attribute) else None
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        resolved_call_name = _resolve_import_alias_name(call_name, import_aliases)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in AUDIO_STORAGE_DIRECT_MUTATION_ATTR_NAMES
        ):
            lines.append((node.lineno, node.func.attr))
            continue
        if call_name in AUDIO_STORAGE_DIRECT_MUTATION_CALL_NAMES or (
            resolved_call_name in AUDIO_STORAGE_DIRECT_MUTATION_CALL_NAMES
        ):
            lines.append((node.lineno, resolved_call_name or call_name or "<unknown>"))
    return sorted(set(lines))


def _build_audio_response_calls_without_non_null_storage_provider(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _attribute_chain_name(node.func) if isinstance(node.func, ast.Attribute) else None
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        resolved_call_name = _resolve_import_alias_name(call_name, import_aliases)
        if call_name != "build_audio_response" and resolved_call_name != (
            "app.api_helpers.audio_response.build_audio_response"
        ):
            continue
        storage_provider_keyword = next(
            (keyword for keyword in node.keywords if keyword.arg == "storage_provider"),
            None,
        )
        if storage_provider_keyword is not None and not _contains_none_literal(
            storage_provider_keyword.value
        ):
            continue
        lines.append(node.lineno)
    return sorted(set(lines))


def _contains_none_literal(node: ast.AST) -> bool:
    return any(isinstance(child, ast.Constant) and child.value is None for child in ast.walk(node))


def _resolve_import_from_module(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    try:
        relative_path = path.resolve().relative_to(APP_ROOT.parent.resolve()).with_suffix("")
    except ValueError:
        return node.module

    package_parts = list(relative_path.parent.parts)
    base_parts = package_parts[: max(0, len(package_parts) - node.level + 1)]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)



def _specific_module_import_lines(path: Path, forbidden_modules: set[str]) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _matches_forbidden_module(alias.name, forbidden_modules):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if _matches_forbidden_module(node.module, forbidden_modules):
                lines.append(node.lineno)
    return sorted(set(lines))


def _concrete_module_import_lines(path: Path, forbidden_module: str) -> list[int]:
    parent_module, _, module_basename = forbidden_module.rpartition(".")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == forbidden_module or alias.name.startswith(f"{forbidden_module}."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == forbidden_module or (
                module is not None and module.startswith(f"{forbidden_module}.")
            ):
                lines.append(node.lineno)
                continue
            if module == parent_module:
                for alias in node.names:
                    if alias.name in {"*", module_basename}:
                        lines.append(node.lineno)
                        break
    return sorted(set(lines))


def _database_provider_database_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == DATABASE_PROVIDER_MODULE:
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == DATABASE_PROVIDER_MODULE and any(
                alias.name == "Database" for alias in node.names
            ):
                lines.append(node.lineno)
            if module == "app.data_access" and any(
                alias.name == "provider" for alias in node.names
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _database_provider_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == DATABASE_PROVIDER_MODULE:
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == DATABASE_PROVIDER_MODULE:
                lines.append(node.lineno)
            if module == "app.data_access" and any(
                alias.name == "provider" for alias in node.names
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _database_provider_public_non_property_method_lines(
    path: Path,
) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    database_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Database"
        ),
        None,
    )
    if database_class is None:
        return []

    return [
        (node.lineno, node.name)
        for node in database_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _is_database_provider_public_method_name(node.name)
        and not _has_property_decorator(node)
    ]


def _class_public_method_names(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    class_node = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if class_node is None:
        raise AssertionError(f"{path}: class {class_name} not found")

    return {
        node.name
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def _forbidden_call_name_lines(path: Path, forbidden_names: set[str]) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        qualified_name = _qualified_ast_name(node.func)
        if qualified_name in forbidden_names:
            lines.append(node.lineno)
    return sorted(set(lines))


def _module_reference_name_lines(path: Path, forbidden_names: set[str]) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in forbidden_names or (alias.asname and alias.asname in forbidden_names):
                    lines.append(node.lineno)
            continue
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if (
                reference_name in forbidden_names
                or (resolved_reference_name or "").split(".")[-1] in forbidden_names
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _class_init_param_annotation_names(path: Path, class_name: str) -> dict[str, set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    class_node = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if class_node is None:
        raise AssertionError(f"{path}: class {class_name} not found")

    init_node = next(
        (
            node
            for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "__init__"
        ),
        None,
    )
    if init_node is None:
        raise AssertionError(f"{path}: class {class_name}.__init__ not found")

    params = [
        *init_node.args.posonlyargs,
        *init_node.args.args,
        *init_node.args.kwonlyargs,
    ]
    if init_node.args.vararg is not None:
        params.append(init_node.args.vararg)
    if init_node.args.kwarg is not None:
        params.append(init_node.args.kwarg)

    return {
        param.arg: _annotation_names(param.annotation)
        for param in params
        if param.arg != "self"
    }


def _annotation_names(annotation: ast.AST | None) -> set[str]:
    if annotation is None:
        return set()
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            annotation = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return set()

    names = set()
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name):
            names.add(node.id)
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
            qualified_name = _qualified_ast_name(node)
            if qualified_name is not None:
                names.add(qualified_name)
    return names


def _qualified_ast_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        value_name = _qualified_ast_name(node.value)
        if value_name is None:
            return None
        return f"{value_name}.{node.attr}"
    return None


def _is_database_provider_public_method_name(name: str) -> bool:
    return name == "__init__" or not name.startswith("_")


def _has_property_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(decorator, ast.Name) and decorator.id == "property"
        for decorator in node.decorator_list
    )


def _direct_import_modules(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend((node.lineno, alias.name) for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module is None:
                continue
            if module == "app":
                modules.extend(
                    (node.lineno, "app" if alias.name == "*" else f"app.{alias.name}")
                    for alias in node.names
                )
            else:
                modules.append((node.lineno, module))
    return sorted(set(modules))


def _imported_or_qualified_reference_names_from_module(
    path: Path,
    module_name: str,
    names: set[str],
) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    imported_names = set()
    module_prefix = f"{module_name}."
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == module_name:
                imported_names.update(
                    alias.name for alias in node.names if alias.name in names
                )
            continue
        if not isinstance(node, ast.Name | ast.Attribute):
            continue
        reference_name = (
            _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
        )
        resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
        if resolved_reference_name is None or not resolved_reference_name.startswith(
            module_prefix
        ):
            continue
        imported_name = resolved_reference_name.removeprefix(module_prefix).split(".", 1)[0]
        if imported_name in names:
            imported_names.add(imported_name)
    return imported_names


def _filesystem_audio_storage_provider_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in FILESYSTEM_AUDIO_STORAGE_PROVIDER_MODULE_NAMES and any(
                alias.name in FILESYSTEM_AUDIO_STORAGE_PROVIDER_NAMES | {"*"}
                for alias in node.names
            ):
                lines.append(node.lineno)
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if any(
                provider_name in node.value
                for provider_name in FILESYSTEM_AUDIO_STORAGE_PROVIDER_NAMES
            ):
                lines.append(node.lineno)
            continue
        if not isinstance(node, ast.Name | ast.Attribute):
            continue
        reference_name = (
            _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
        )
        resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
        if (
            reference_name in FILESYSTEM_AUDIO_STORAGE_PROVIDER_NAMES
            or resolved_reference_name in FILESYSTEM_AUDIO_STORAGE_PROVIDER_REFERENCES
        ):
            lines.append(node.lineno)
    return sorted(set(lines))


def _resolve_local_path_attribute_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return sorted(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "resolve_local_path"
        }
    )


def _same_public_name_imported_names_from_module(
    path: Path,
    module_name: str,
    names: set[str],
) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_names = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        module = _resolve_import_from_module(path, node)
        if module != module_name:
            continue
        imported_names.update(
            alias.name
            for alias in node.names
            if alias.name in names and alias.asname in {None, alias.name}
        )
    return imported_names


def _admin_api_settings_adapter_disallowed_application_settings_import_lines(
    path: Path,
) -> list[int]:
    allowed_modules = {
        "app.application.admin.settings",
        "app.application.admin.settings.errors",
    }
    disallowed_parent_imports = {
        "action_otp",
        "provider_reference",
        "settings_service",
        "validators",
    }
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith("app.application.admin.settings"):
                    continue
                if alias.name not in allowed_modules:
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module is None or not module.startswith("app.application.admin.settings"):
                continue
            if module not in allowed_modules:
                lines.append(node.lineno)
                continue
            if module == "app.application.admin.settings":
                for alias in node.names:
                    if alias.name == "*" or alias.name in disallowed_parent_imports:
                        lines.append(node.lineno)
                        break
    return sorted(set(lines))


def _is_composition_root_allowed_import(module: str) -> bool:
    if module == "app":
        return False
    if not module.startswith("app."):
        return True
    if module in COMPOSITION_ROOT_ALLOWED_APP_IMPORTS:
        return True
    return module == "app.composition" or module.startswith("app.composition.")


def _is_client_api_import(module: str) -> bool:
    return module == "app.client_api" or module.startswith("app.client_api.")


def _runtime_state_database_facade_method_call_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    forbidden_names = {"get_app_runtime_state", "set_app_runtime_state"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in forbidden_names:
                lines.append(node.lineno)
    return sorted(set(lines))


def _database_log_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _matches_forbidden_module(alias.name, REMOVED_DATABASE_LOG_FACADE_MODULES):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module is not None and _matches_forbidden_module(module, REMOVED_DATABASE_LOG_FACADE_MODULES):
                lines.append(node.lineno)
                continue
            if module == "app.db_facades":
                for alias in node.names:
                    if f"{module}.{alias.name}" in REMOVED_DATABASE_LOG_FACADE_MODULES:
                        lines.append(node.lineno)
                        break
    return sorted(set(lines))


def _database_log_facade_method_call_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in REMOVED_DATABASE_LOG_FACADE_METHOD_NAMES:
                lines.append(node.lineno)
    return sorted(set(lines))


def _bot_message_database_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _matches_forbidden_module(alias.name, REMOVED_BOT_MESSAGE_DATABASE_FACADE_MODULES):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module is not None and _matches_forbidden_module(module, REMOVED_BOT_MESSAGE_DATABASE_FACADE_MODULES):
                lines.append(node.lineno)
                continue
            if module == "app.db_facades":
                for alias in node.names:
                    if alias.name in REMOVED_BOT_MESSAGE_DATABASE_FACADE_NAMES:
                        lines.append(node.lineno)
                        break
    return sorted(set(lines))


def _bot_message_database_facade_method_call_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in REMOVED_BOT_MESSAGE_DATABASE_FACADE_METHOD_NAMES:
            continue
        receiver_name = _attribute_chain_name(node.func.value)
        if receiver_name in {"db", "self.db"}:
            lines.append(node.lineno)
    return sorted(set(lines))


def _db_facade_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.db_facades" or alias.name.startswith("app.db_facades."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module == "app.db_facades" or (module is not None and module.startswith("app.db_facades.")):
                lines.append(node.lineno)
                continue
            if module == "app":
                for alias in node.names:
                    if alias.name == "db_facades" or alias.name.startswith("db_facades."):
                        lines.append(node.lineno)
                        break
    return sorted(set(lines))


def _admin_auth_database_facade_method_call_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in REMOVED_ADMIN_AUTH_DATABASE_FACADE_METHOD_NAMES:
            continue
        receiver_name = _attribute_chain_name(node.func.value)
        if receiver_name in {"db", "self.db"}:
            lines.append(node.lineno)
    return sorted(set(lines))


def _matches_forbidden_module(module: str, forbidden_modules: set[str]) -> bool:
    return any(
        module == forbidden or module.startswith(f"{forbidden}.")
        for forbidden in forbidden_modules
    )


def _fastapi_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "fastapi" or alias.name.startswith("fastapi."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "fastapi" or node.module.startswith("fastapi."):
                lines.append(node.lineno)
    return sorted(set(lines))


def _http_framework_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"fastapi", "starlette"} or alias.name.startswith(("fastapi.", "starlette.")):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module in {"fastapi", "starlette"} or node.module.startswith(("fastapi.", "starlette.")):
                lines.append(node.lineno)
    return sorted(set(lines))


def _interface_api_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    forbidden_package_names = {"admin_api", "client_api"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_interface_api_module(alias.name):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module is None:
                continue
            if _is_interface_api_module(module):
                lines.append(node.lineno)
            if module == "app":
                for alias in node.names:
                    if alias.name in forbidden_package_names:
                        lines.append(node.lineno)
                        break
    return sorted(set(lines))


def _is_interface_api_module(module_name: str) -> bool:
    return module_name in {"app.admin_api", "app.client_api"} or module_name.startswith(
        ("app.admin_api.", "app.client_api.")
    )


def _httpx_transport_usage_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "httpx" or alias.name.startswith("httpx."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "httpx" or node.module.startswith("httpx."):
                lines.append(node.lineno)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "httpx":
            lines.append(node.lineno)
    return sorted(set(lines))


def _root_user_import_attribute_queue_call_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "process_user_import_attribute_queue_now":
            continue
        if path == USER_IMPORT_SCHEDULED_RUNTIME_SERVICE_MODULE:
            continue
        if _attribute_chain_contains(node.func.value, "user_import_scheduled_runtime_service"):
            continue
        lines.append(node.lineno)
    return sorted(set(lines))


def _monobank_provider_package_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(_is_monobank_provider_package_name(alias.name) for alias in node.names):
                lines.append(node.lineno)
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            imported_names = [
                f"{module}.{alias.name}"
                for alias in node.names
                if module is not None and alias.name != "*"
            ]
            if _is_monobank_provider_package_name(module) or any(
                _is_monobank_provider_package_name(name) for name in imported_names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if _is_monobank_provider_package_name(
                reference_name
            ) or _is_monobank_provider_package_name(resolved_reference_name):
                lines.append(node.lineno)
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and MONOBANK_PROVIDER_PACKAGE in node.value
        ):
            lines.append(node.lineno)
    return sorted(set(lines))


def _monobank_client_constructor_call_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        constructor_name = _attribute_chain_name(node.func)
        resolved_constructor_name = _resolve_import_alias_name(constructor_name, import_aliases)
        if (
            constructor_name in MONOBANK_CLIENT_CONSTRUCTOR_NAMES
            or resolved_constructor_name in MONOBANK_CLIENT_CONSTRUCTOR_NAMES
        ):
            lines.append(node.lineno)
    return sorted(set(lines))


def _monobank_client_type_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in MONOBANK_CLIENT_PROVIDER_MODULES and any(
                alias.name in {"MonobankClient", "*"} for alias in node.names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if (
                reference_name in MONOBANK_CLIENT_PROVIDER_TYPE_NAMES
                or resolved_reference_name in MONOBANK_CLIENT_PROVIDER_TYPE_NAMES
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _monobank_invoice_request_provider_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in MONOBANK_CLIENT_PROVIDER_MODULES and any(
                alias.name in {"MonobankCreateInvoiceRequest", "*"} for alias in node.names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if (
                reference_name in MONOBANK_INVOICE_REQUEST_PROVIDER_TYPE_NAMES
                or resolved_reference_name in MONOBANK_INVOICE_REQUEST_PROVIDER_TYPE_NAMES
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _monobank_api_error_provider_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in MONOBANK_CLIENT_PROVIDER_MODULES and any(
                alias.name in {"MonobankAPIError", "*"} for alias in node.names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if (
                reference_name in MONOBANK_API_ERROR_PROVIDER_TYPE_NAMES
                or resolved_reference_name in MONOBANK_API_ERROR_PROVIDER_TYPE_NAMES
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _monobank_audit_context_provider_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in MONOBANK_AUDIT_CONTEXT_PROVIDER_MODULES and any(
                alias.name in {"MonobankAuditContext", "*"} for alias in node.names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if (
                reference_name in MONOBANK_AUDIT_CONTEXT_PROVIDER_TYPE_NAMES
                or resolved_reference_name in MONOBANK_AUDIT_CONTEXT_PROVIDER_TYPE_NAMES
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _monobank_audit_helper_provider_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in MONOBANK_AUDIT_HELPER_PROVIDER_MODULES and any(
                alias.name in {*MONOBANK_AUDIT_HELPER_NAMES, "*"} for alias in node.names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if resolved_reference_name in MONOBANK_AUDIT_HELPER_PROVIDER_NAMES:
                lines.append(node.lineno)
    return sorted(set(lines))


MONOBANK_PROVIDER_PACKAGE = "app.billing.providers.monobank"

MONOBANK_CLIENT_CONSTRUCTOR_NAMES = {
    "MonobankClient",
    "app.billing.providers.monobank.MonobankClient",
    "app.billing.providers.monobank.client.MonobankClient",
}

MONOBANK_CLIENT_PROVIDER_TYPE_NAMES = {
    "app.billing.providers.monobank.MonobankClient",
    "app.billing.providers.monobank.client.MonobankClient",
}

MONOBANK_CLIENT_PROVIDER_MODULES = {
    "app.billing.providers.monobank",
    "app.billing.providers.monobank.client",
}

MONOBANK_INVOICE_REQUEST_PROVIDER_TYPE_NAMES = {
    "app.billing.providers.monobank.MonobankCreateInvoiceRequest",
    "app.billing.providers.monobank.client.MonobankCreateInvoiceRequest",
}

MONOBANK_API_ERROR_PROVIDER_TYPE_NAMES = {
    "app.billing.providers.monobank.MonobankAPIError",
    "app.billing.providers.monobank.client.MonobankAPIError",
}

MONOBANK_AUDIT_CONTEXT_PROVIDER_TYPE_NAMES = {
    "app.billing.providers.monobank.audit.MonobankAuditContext",
}

MONOBANK_AUDIT_CONTEXT_PROVIDER_MODULES = {
    "app.billing.providers.monobank.audit",
}

MONOBANK_AUDIT_HELPER_NAMES = {
    "duration_ms",
    "mask_headers",
}

MONOBANK_AUDIT_HELPER_PROVIDER_NAMES = {
    "app.billing.providers.monobank.audit.duration_ms",
    "app.billing.providers.monobank.audit.mask_headers",
}

MONOBANK_AUDIT_HELPER_PROVIDER_MODULES = {
    "app.billing.providers.monobank.audit",
}

MONOBANK_CLIENT_FACTORY_PROVIDER_NAMES = {
    "app.billing.providers.monobank.build_monobank_client",
    "app.billing.providers.monobank.factory.build_monobank_client",
}

MONOBANK_CLIENT_FACTORY_PROVIDER_MODULES = {
    "app.billing.providers.monobank",
    "app.billing.providers.monobank.factory",
}

MONOBANK_SIGNATURE_VERIFIER_PROVIDER_NAMES = {
    "app.billing.providers.monobank.verify_monobank_webhook_signature",
    "app.billing.providers.monobank.signature.verify_monobank_webhook_signature",
}

MONOBANK_SIGNATURE_VERIFIER_PROVIDER_MODULES = {
    "app.billing.providers.monobank",
    "app.billing.providers.monobank.signature",
}


def _is_monobank_provider_package_name(name: str | None) -> bool:
    if name is None:
        return False
    return name == MONOBANK_PROVIDER_PACKAGE or name.startswith(f"{MONOBANK_PROVIDER_PACKAGE}.")


def _monobank_client_factory_provider_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in MONOBANK_CLIENT_FACTORY_PROVIDER_MODULES and any(
                alias.name in {"build_monobank_client", "*"} for alias in node.names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if resolved_reference_name in MONOBANK_CLIENT_FACTORY_PROVIDER_NAMES:
                lines.append(node.lineno)
    return sorted(set(lines))


def _monobank_signature_verifier_provider_reference_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    import_aliases = _import_alias_map(tree, path)
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module in MONOBANK_SIGNATURE_VERIFIER_PROVIDER_MODULES and any(
                alias.name in {"verify_monobank_webhook_signature", "*"} for alias in node.names
            ):
                lines.append(node.lineno)
        if isinstance(node, ast.Name | ast.Attribute):
            reference_name = _attribute_chain_name(node) if isinstance(node, ast.Attribute) else node.id
            resolved_reference_name = _resolve_import_alias_name(reference_name, import_aliases)
            if resolved_reference_name in MONOBANK_SIGNATURE_VERIFIER_PROVIDER_NAMES:
                lines.append(node.lineno)
    return sorted(set(lines))


def _import_alias_map(tree: ast.AST, path: Path) -> dict[str, str]:
    import_aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname is not None:
                    import_aliases[alias.asname] = alias.name
                    continue
                root_name = alias.name.split(".", maxsplit=1)[0]
                import_aliases.setdefault(root_name, root_name)
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if module is None:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                import_aliases[alias.asname or alias.name] = f"{module}.{alias.name}"
    return import_aliases


def _resolve_import_alias_name(name: str | None, import_aliases: dict[str, str]) -> str | None:
    if name is None:
        return None
    root_name, separator, rest = name.partition(".")
    imported_name = import_aliases.get(root_name)
    if imported_name is None:
        return name
    if separator:
        return f"{imported_name}.{rest}"
    return imported_name


def _attribute_chain_name(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _attribute_chain_contains(node: ast.AST, attr_name: str) -> bool:
    while isinstance(node, ast.Attribute):
        if node.attr == attr_name:
            return True
        node = node.value
    return False


def _is_http_transport_boundary_path(relative_path: Path) -> bool:
    if relative_path in HTTP_TRANSPORT_BOUNDARY_FILES:
        return True
    return any(boundary_dir in relative_path.parents for boundary_dir in HTTP_TRANSPORT_BOUNDARY_DIRS)


def _is_external_provider_module(module: str | None) -> bool:
    return module == "app.external_providers" or (
        module is not None and module.startswith("app.external_providers.")
    )


def _external_provider_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_external_provider_module(alias.name):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from_module(path, node)
            if _is_external_provider_module(module):
                lines.append(node.lineno)
                continue
            if module == "app" and any(
                alias.name == "external_providers" for alias in node.names
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _api_audio_response_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.api_helpers.audio_response" or alias.name.startswith(
                    "app.api_helpers.audio_response."
                ):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "app.api_helpers.audio_response" or node.module.startswith(
                "app.api_helpers.audio_response."
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _api_helper_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.api_helpers" or alias.name.startswith("app.api_helpers."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "app.api_helpers" or node.module.startswith("app.api_helpers."):
                lines.append(node.lineno)
    return sorted(set(lines))


def _legacy_validators_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.validators" or alias.name.startswith("app.validators."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "app.validators" or node.module.startswith("app.validators."):
                lines.append(node.lineno)
    return sorted(set(lines))


def _legacy_request_validator_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.validators.request" or alias.name.startswith("app.validators.request."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "app.validators.request" or node.module.startswith("app.validators.request."):
                lines.append(node.lineno)
            if node.module == "app.validators" and any(
                alias.name == "request" or alias.name.startswith("request.") for alias in node.names
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def _admin_pagination_helper_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.admin_api.helpers.pagination":
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module == "app.admin_api.helpers.pagination":
            lines.append(node.lineno)
    return sorted(set(lines))


def _telegram_gateway_import_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.telegram_gateway" or alias.name.startswith("app.telegram_gateway."):
                    lines.append(node.lineno)
                    break
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "app.telegram_gateway" or node.module.startswith("app.telegram_gateway."):
                lines.append(node.lineno)
    return sorted(set(lines))
