from __future__ import annotations

from typing import Any, Protocol

from app.acl.processor import AclPermissionReader, AclProcessor
from app.application.admin.permissions import require_acl_access_allowed
from app.user_import.providers import describe_user_import_providers

APP_VERSION = "0.0.5"


class AdminBootstrapVersionReader(Protocol):
    def get_current_app_version(self) -> str | None: ...


class AdminBootstrapService:
    def __init__(
        self,
        settings: Any,
        version_reader: AdminBootstrapVersionReader,
        acl_permissions: AclPermissionReader,
    ) -> None:
        self.settings = settings
        self.version_reader = version_reader
        self.acl_processor = AclProcessor(acl_permissions)

    def bootstrap(self, user: dict[str, Any]) -> dict[str, Any]:
        require_acl_access_allowed(
            self.acl_processor,
            user,
            action="bootstrap/view",
            environment="web_admin",
        )
        acl_capabilities = self.acl_processor.capabilities_for(user, environment="web_admin")
        return {
            "version": self.version_reader.get_current_app_version() or APP_VERSION,
            "locales": [
                {"code": "uk", "title": "Українська"},
                {"code": "ru", "title": "Русский"},
                {"code": "pl", "title": "Polski"},
            ],
            "user": user,
            "acl": {
                "environment": "web_admin",
                "capabilities": acl_capabilities or [],
            },
            "navigation": [
                {"id": "dashboard", "title": "Dashboard", "icon": "grid", "children": []},
                {
                    "id": "dictionary",
                    "title": "Dictionary",
                    "icon": "book",
                    "children": [
                        {"id": "dictionary", "title": "Base"},
                        {"id": "user_dictionary", "title": "User Words"},
                    ],
                },
                {"id": "users", "title": "Users", "icon": "users", "children": []},
                {
                    "id": "logs",
                    "title": "Logs",
                    "icon": "list",
                    "children": [
                        {"id": "task_logs", "title": "Task Logs"},
                        {"id": "ai_usage", "title": "AI Usage"},
                        {"id": "error_log", "title": "Error Log"},
                    ],
                },
                {"id": "settings", "title": "Settings", "icon": "settings", "children": []},
            ],
            "settings": {
                "user_import_providers": describe_user_import_providers(self.settings),
            },
        }
