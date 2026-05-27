from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.acl.processor import AclPermissionReader
from app.application.admin.permissions import (
    AdminPermissionDeniedError,
    require_admin_access_allowed,
)
from app.application.admin.settings.errors import (
    AdminSettingsAccessDeniedError,
    AdminSettingsValidationError,
)
from app.application.admin.settings.validators import (
    normalize_provider_settings_payload,
    normalize_settings_payload,
)
from app.billing.runtime_settings import (
    BILLING_MONOBANK_MODE_SETTINGS_KEY,
    BILLING_RUNTIME_SETTINGS_KEY,
    BillingRuntimeSettingsValidationError,
    normalize_billing_runtime_settings,
    normalize_monobank_mode_settings,
    read_billing_runtime_settings,
    validate_monobank_mode_token,
)
from app.domain.billing.constants import BILLING_PROVIDER_MONOBANK
from app.domain.provider_pricing import list_provider_model_options
from app.domain.provider_settings import (
    DEFAULT_OPENAI_API_URL,
    DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
    DEFAULT_USER_IMPORT_OPENAI_MODEL,
    WORD_AUDIO_TASK_KEY,
    WORD_DETAILS_TASK_KEY,
    WORD_EMBEDDINGS_TASK_KEY,
    WORD_VALIDATION_TASK_KEY,
    list_provider_tasks,
    resolve_provider_task_setting,
)
from app.marketing.runtime_settings import (
    ANALYTICS_SETTINGS_KEY,
    AnalyticsSettingsValidationError,
    read_analytics_settings,
)
from app.storage.audio import AudioStorageProvider
from app.subscriptions.plan_limits import (
    PLAN_LIMITS_SETTINGS_KEY,
    PlanLimitSettingsValidationError,
    read_plan_limit_settings,
)
from app.subscriptions.runtime_settings import (
    SUBSCRIPTION_RUNTIME_SETTINGS_KEY,
    SubscriptionSettingsValidationError,
    read_subscription_runtime_settings,
)
from app.support.runtime_settings import (
    SUPPORT_SETTINGS_KEY,
    SupportSettingsValidationError,
    normalize_support_settings,
    read_support_settings,
)
from app.time_utils import TimeService
from app.user_import.runtime_settings import (
    USER_IMPORT_RUNTIME_SETTINGS_KEY,
    UserImportRuntimeSettingsValidationError,
    read_user_import_runtime_settings,
)


class AdminSettingsActionOtpVerifierPort(Protocol):
    def verify_action_otp(
        self,
        *,
        user: dict[str, Any],
        action_key: str,
        challenge_id: int,
        otp: str,
    ) -> None: ...


class AdminSettingsSettingsPort(Protocol):
    monobank_token_test: str
    monobank_token: str
    app_user_import_audio_dir: str
    app_user_import_openai_model: str
    app_user_import_openai_api_url: str
    app_user_import_word_audio_provider: str
    app_user_import_google_tts_language_code: str
    app_user_import_google_tts_voice_name: str
    app_user_import_embeddings_model: str
    app_user_import_embeddings_device: str
    app_user_import_word_details_provider: str


class AdminSettingsAppSettingsPort(Protocol):
    def get_value(self, key: str) -> Any | None: ...

    def upsert_value(self, key: str, value_json: dict[str, Any], current_time: datetime) -> dict[str, Any]: ...


class AdminSettingsUserLearningSettingsPort(Protocol):
    def get_current_app_version(self) -> str | None: ...

    def set_current_app_version(self, version: str, *, current_time: datetime) -> str: ...


class AdminSettingsUserProfilesPort(Protocol):
    def set_interface_locale(self, telegram_user_id: int, interface_locale: str) -> None: ...


class AdminSettingsAdminUsersPort(Protocol):
    def get_by_id(self, user_id: int) -> dict[str, Any] | None: ...


class AdminSettingsExternalProviderSettingsPort(Protocol):
    def get_map(self) -> dict[str, dict[str, Any]]: ...

    def upsert(
        self,
        *,
        task_key: str,
        provider_key: str,
        is_enabled: bool,
        config_json: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any]: ...


class AdminSettingsUserImportJobsPort(Protocol):
    def delete_all_import_data(
        self,
        *,
        audio_storage_provider: AudioStorageProvider,
        user_audio_roots: list[Path | str] | None = None,
    ) -> dict[str, int]: ...


class AdminSettingsDatabasePort(Protocol):
    acl_permissions: AclPermissionReader
    settings: AdminSettingsSettingsPort
    app_settings: AdminSettingsAppSettingsPort
    user_learning_settings: AdminSettingsUserLearningSettingsPort
    user_profiles: AdminSettingsUserProfilesPort
    admin_users: AdminSettingsAdminUsersPort
    external_provider_settings: AdminSettingsExternalProviderSettingsPort
    user_import_jobs: AdminSettingsUserImportJobsPort


class AdminSettingsService:
    def __init__(
        self,
        db: AdminSettingsDatabasePort,
        time_service: TimeService,
        *,
        audio_storage_provider: AudioStorageProvider,
        action_otp_verifier: AdminSettingsActionOtpVerifierPort | None = None,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.audio_storage_provider = audio_storage_provider
        self.action_otp_verifier = action_otp_verifier

    def get_settings(self, *, user: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(user, action="settings/view")
        return self._build_settings_payload(user=user)

    def _build_settings_payload(self, *, user: dict[str, Any]) -> dict[str, Any]:
        try:
            support_settings = read_support_settings(self.db)
            analytics_settings = read_analytics_settings(self.db)
            subscription_settings = read_subscription_runtime_settings(self.db)
            plan_limits = read_plan_limit_settings(self.db)
            import_settings = read_user_import_runtime_settings(self.db)
            billing_settings = read_billing_runtime_settings(self.db)
        except (
            AnalyticsSettingsValidationError,
            BillingRuntimeSettingsValidationError,
            PlanLimitSettingsValidationError,
            SubscriptionSettingsValidationError,
            SupportSettingsValidationError,
            UserImportRuntimeSettingsValidationError,
        ) as error:
            raise AdminSettingsValidationError(str(error)) from error

        return {
            "user": user,
            "settings": {
                "interface_locale": user.get("interface_locale") or "uk",
                "app_version": self.db.user_learning_settings.get_current_app_version() or "0.0.5",
                "billing_settings": billing_settings,
                "provider_tasks": self._list_provider_settings()["tasks"],
                "import_settings": import_settings,
                "subscription_settings": subscription_settings,
                "plan_limits": plan_limits,
                "support_settings": support_settings,
                "analytics_settings": analytics_settings,
            },
        }

    def update_settings(self, *, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(user, action="settings/view")
        if payload.get("app_version") is not None:
            self._require_admin_access(user, action="acl/manage")
        billing_settings = payload.get("billing_settings")
        if (
            isinstance(billing_settings, dict)
            and (
                "billing_provider" in billing_settings
                or "monobank_mode" in billing_settings
            )
        ):
            raise AdminSettingsValidationError(
                "Use OTP-protected billing provider settings endpoint"
            )
        normalized = normalize_settings_payload(payload)
        telegram_user_id = int(user["telegram_user_id"])
        current_time = self.time_service.now()
        if "interface_locale" in normalized:
            self.db.user_profiles.set_interface_locale(telegram_user_id, normalized["interface_locale"])
        if "app_version" in normalized:
            self.db.user_learning_settings.set_current_app_version(
                normalized["app_version"],
                current_time=current_time,
            )
        if "billing_settings" in normalized:
            billing_settings_payload = payload.get("billing_settings")
            normalized_billing_updates = {
                key: value
                for key, value in normalized["billing_settings"].items()
                if isinstance(billing_settings_payload, dict) and key in billing_settings_payload
            }
            current_billing_settings = read_billing_runtime_settings(self.db)
            self.db.app_settings.upsert_value(
                BILLING_RUNTIME_SETTINGS_KEY,
                {**current_billing_settings, **normalized_billing_updates},
                current_time=current_time,
            )
        if "import_settings" in normalized:
            self.db.app_settings.upsert_value(
                USER_IMPORT_RUNTIME_SETTINGS_KEY,
                normalized["import_settings"],
                current_time=current_time,
            )
        if "subscription_settings" in normalized:
            self.db.app_settings.upsert_value(
                SUBSCRIPTION_RUNTIME_SETTINGS_KEY,
                normalized["subscription_settings"],
                current_time=current_time,
            )
        if "plan_limits" in normalized:
            self.db.app_settings.upsert_value(
                PLAN_LIMITS_SETTINGS_KEY,
                normalized["plan_limits"],
                current_time=current_time,
            )
        if "support_settings" in normalized:
            try:
                support_settings = normalize_support_settings(
                    {**read_support_settings(self.db), **normalized["support_settings"]},
                )
            except SupportSettingsValidationError as error:
                raise AdminSettingsValidationError(str(error)) from error
            self.db.app_settings.upsert_value(
                SUPPORT_SETTINGS_KEY,
                support_settings,
                current_time=current_time,
            )
        if "analytics_settings" in normalized:
            self.db.app_settings.upsert_value(
                ANALYTICS_SETTINGS_KEY,
                normalized["analytics_settings"],
                current_time=current_time,
            )
        fresh_user = self.db.admin_users.get_by_id(telegram_user_id) or user
        return self._build_settings_payload(user=fresh_user)

    def authorize_update_billing_monobank_mode(self, *, user: dict[str, Any], monobank_mode: str) -> None:
        self._require_admin_access(user, action="acl/manage")
        try:
            validate_monobank_mode_token(self.db.settings, monobank_mode)
        except BillingRuntimeSettingsValidationError as error:
            raise AdminSettingsValidationError(str(error)) from error

    def update_billing_monobank_mode(self, *, user: dict[str, Any], monobank_mode: str) -> dict[str, Any]:
        current_time = self.time_service.now()
        try:
            next_settings = normalize_monobank_mode_settings({"monobank_mode": monobank_mode})
        except BillingRuntimeSettingsValidationError as error:
            raise AdminSettingsValidationError(str(error)) from error
        self.db.app_settings.upsert_value(
            BILLING_MONOBANK_MODE_SETTINGS_KEY,
            next_settings,
            current_time=current_time,
        )
        return self._build_settings_payload(user=user)

    def update_billing_monobank_mode_with_otp(
        self,
        *,
        user: dict[str, Any],
        monobank_mode: str,
        challenge_id: int,
        otp: str,
        action_key: str = "billing_monobank_mode",
    ) -> dict[str, Any]:
        if self.action_otp_verifier is None:
            raise RuntimeError("Action OTP verifier is required for Monobank mode update")
        self.authorize_update_billing_monobank_mode(user=user, monobank_mode=monobank_mode)
        self.action_otp_verifier.verify_action_otp(
            user=user,
            action_key=action_key,
            challenge_id=challenge_id,
            otp=otp,
        )
        return self.update_billing_monobank_mode(user=user, monobank_mode=monobank_mode)

    def update_billing_provider_settings_with_otp(
        self,
        *,
        user: dict[str, Any],
        payload: dict[str, Any],
        action_key: str = "billing_provider_settings",
    ) -> dict[str, Any]:
        self._require_admin_access(user, action="acl/manage")
        billing_provider = payload.get("billing_provider")
        monobank_mode = payload.get("monobank_mode")
        if billing_provider is None and monobank_mode is None:
            raise AdminSettingsValidationError("Either billing_provider or monobank_mode is required")

        challenge_id = payload.get("challenge_id")
        otp = payload.get("otp")
        if challenge_id is None or otp is None:
            raise AdminSettingsValidationError("billing_provider or monobank_mode requires challenge_id and otp")
        if self.action_otp_verifier is None:
            raise RuntimeError("Action OTP verifier is required for billing provider settings update")

        current_billing_settings = read_billing_runtime_settings(self.db)
        next_billing_provider = current_billing_settings.get("billing_provider")
        next_monobank_mode = current_billing_settings.get("monobank_mode")

        if billing_provider is not None:
            try:
                normalized_billing_provider_settings = normalize_billing_runtime_settings(
                    {"billing_provider": billing_provider},
                    partial=True,
                )
            except BillingRuntimeSettingsValidationError as error:
                raise AdminSettingsValidationError(str(error)) from error
            next_billing_provider = normalized_billing_provider_settings["billing_provider"]

        if monobank_mode is not None:
            self.authorize_update_billing_monobank_mode(user=user, monobank_mode=monobank_mode)

        self.action_otp_verifier.verify_action_otp(
            user=user,
            action_key=action_key,
            challenge_id=challenge_id,
            otp=otp,
        )

        if monobank_mode is not None:
            try:
                normalized_monobank_mode_settings = normalize_monobank_mode_settings(
                    {"monobank_mode": monobank_mode},
                )
            except BillingRuntimeSettingsValidationError as error:
                raise AdminSettingsValidationError(str(error)) from error

            next_monobank_mode = normalized_monobank_mode_settings["monobank_mode"]
        else:
            normalized_monobank_mode_settings = None

        if next_billing_provider == BILLING_PROVIDER_MONOBANK:
            try:
                validate_monobank_mode_token(self.db.settings, next_monobank_mode)
            except BillingRuntimeSettingsValidationError as error:
                raise AdminSettingsValidationError(str(error)) from error

        current_time = self.time_service.now()

        if billing_provider is not None:
            self.db.app_settings.upsert_value(
                BILLING_RUNTIME_SETTINGS_KEY,
                {
                    **current_billing_settings,
                    "billing_provider": next_billing_provider,
                },
                current_time=current_time,
            )

        if monobank_mode is not None:
            self.db.app_settings.upsert_value(
                BILLING_MONOBANK_MODE_SETTINGS_KEY,
                normalized_monobank_mode_settings,
                current_time=current_time,
            )

        return self._build_settings_payload(user=user)

    def list_provider_settings(self, *, user: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(user, action="settings/view")
        return self._list_provider_settings()

    def _list_provider_settings(self) -> dict[str, Any]:
        repository = getattr(self.db, "external_provider_settings", None)
        configured = repository.get_map() if repository is not None else {}
        tasks: list[dict[str, Any]] = []
        for task in list_provider_tasks():
            fallback_provider_key, fallback_config = self._fallback_provider_config(task.task_key)
            resolved = resolve_provider_task_setting(
                task,
                configured=configured.get(task.task_key),
                fallback_provider_key=fallback_provider_key,
                fallback_config=fallback_config,
            )
            tasks.append(
                {
                    "task_key": task.task_key,
                    "title": task.title,
                    "description": task.description,
                    "provider_key": resolved.provider_key,
                    "is_enabled": resolved.is_enabled,
                    "config": resolved.config,
                    "config_options": self._config_options(resolved.provider_key),
                    "config_options_by_provider": {
                        provider_key: self._config_options(provider_key) for provider_key in task.allowed_provider_keys
                    },
                    "allowed_provider_keys": list(task.allowed_provider_keys),
                }
            )
        return {"tasks": tasks}

    def update_provider_settings(self, *, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        self._require_admin_access(user, action="acl/manage")
        normalized_tasks = normalize_provider_settings_payload(payload)
        current_time = self.time_service.now()
        for task in normalized_tasks:
            self.db.external_provider_settings.upsert(
                task_key=task["task_key"],
                provider_key=task["provider_key"],
                is_enabled=task["is_enabled"],
                config_json=task["config_json"],
                current_time=current_time,
            )
        return self._list_provider_settings()

    def authorize_delete_all_import_data(self, *, user: dict[str, Any]) -> None:
        self._require_admin_access(user, action="acl/manage")

    def delete_all_import_data(self) -> dict[str, Any]:
        user_audio_root = Path(str(getattr(self.db.settings, "app_user_import_audio_dir", "word_base/user")))
        return {
            "status": "ok",
            **self.db.user_import_jobs.delete_all_import_data(
                audio_storage_provider=self.audio_storage_provider,
                user_audio_roots=[user_audio_root],
            ),
        }

    def delete_all_import_data_with_otp(self, *, user: dict[str, Any], challenge_id: int, otp: str) -> dict[str, Any]:
        if self.action_otp_verifier is None:
            raise RuntimeError("Action OTP verifier is required for import data cleanup")
        self.authorize_delete_all_import_data(user=user)
        self.action_otp_verifier.verify_action_otp(
            user=user,
            action_key="delete_import_data",
            challenge_id=challenge_id,
            otp=otp,
        )
        return self.delete_all_import_data()

    def _fallback_provider_config(self, task_key: str) -> tuple[str | None, dict[str, Any]]:
        if task_key in {WORD_DETAILS_TASK_KEY, WORD_VALIDATION_TASK_KEY}:
            return (
                self._fallback_openai_provider_key(task_key),
                {
                    "model": str(getattr(self.db.settings, "app_user_import_openai_model", DEFAULT_USER_IMPORT_OPENAI_MODEL)),
                    "api_url": str(getattr(self.db.settings, "app_user_import_openai_api_url", DEFAULT_OPENAI_API_URL)),
                },
            )
        if task_key == WORD_AUDIO_TASK_KEY:
            return (
                str(getattr(self.db.settings, "app_user_import_word_audio_provider", "google_tts")),
                {
                    "language_code": str(getattr(self.db.settings, "app_user_import_google_tts_language_code", "en-US")),
                    "voice_name": str(getattr(self.db.settings, "app_user_import_google_tts_voice_name", "en-US-Neural2-F")),
                },
            )
        if task_key == WORD_EMBEDDINGS_TASK_KEY:
            return (
                "local_sentence_transformers",
                {
                    "model": str(getattr(self.db.settings, "app_user_import_embeddings_model", "")),
                    "device": str(getattr(self.db.settings, "app_user_import_embeddings_device", "cpu")),
                },
            )
        return (None, {})

    def _fallback_openai_provider_key(self, task_key: str) -> str:
        if task_key == WORD_VALIDATION_TASK_KEY:
            return "disabled"
        return str(getattr(self.db.settings, "app_user_import_word_details_provider", "openai"))

    def _config_options(self, provider_key: str) -> dict[str, list[str]]:
        if provider_key == "openai":
            return {"model": list_provider_model_options("openai")}
        if provider_key == "local_sentence_transformers":
            return {
                "model": [
                    str(
                        getattr(
                            self.db.settings,
                            "app_user_import_embeddings_model",
                            DEFAULT_USER_IMPORT_EMBEDDINGS_MODEL,
                        )
                    )
                ],
                "device": ["cpu", "cuda"],
            }
        return {}

    def _require_admin_access(self, user: dict[str, Any], *, action: str, detail: str = "Access denied") -> None:
        try:
            require_admin_access_allowed(self.db, user, action=action, detail=detail)
        except AdminPermissionDeniedError as error:
            raise AdminSettingsAccessDeniedError(error.detail) from error
