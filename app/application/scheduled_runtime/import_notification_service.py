from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class ClientImportSource(Protocol):
    def process_due_user_vocabulary_imports(self) -> list[Any]: ...


@runtime_checkable
class ClientAdminRestoreSource(Protocol):
    def dispatch_due_admin_bot_restores(self) -> list[Any]: ...


@runtime_checkable
class ClientBillingNotificationSource(Protocol):
    def dispatch_due_billing_notifications(self) -> list[Any]: ...


class ClientImportNotificationService:
    def __init__(
        self,
        import_source: ClientImportSource,
        *,
        admin_restore_source: ClientAdminRestoreSource | None = None,
        billing_notification_source: ClientBillingNotificationSource | None = None,
    ) -> None:
        self.import_source = import_source
        self.admin_restore_source = admin_restore_source
        self.billing_notification_source = billing_notification_source

    def process_due_import_notifications(self) -> list[Any]:
        admin_restores = []
        admin_restore_source = self.admin_restore_source
        if admin_restore_source is None and isinstance(self.import_source, ClientAdminRestoreSource):
            admin_restore_source = self.import_source
        if admin_restore_source is not None:
            admin_restores = admin_restore_source.dispatch_due_admin_bot_restores()
        billing_notifications = []
        billing_notification_source = self.billing_notification_source
        if billing_notification_source is None and isinstance(
            self.import_source, ClientBillingNotificationSource
        ):
            billing_notification_source = self.import_source
        if billing_notification_source is not None:
            billing_notifications = billing_notification_source.dispatch_due_billing_notifications()
        return [
            *self.import_source.process_due_user_vocabulary_imports(),
            *admin_restores,
            *billing_notifications,
        ]
