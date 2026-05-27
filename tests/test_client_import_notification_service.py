from __future__ import annotations

from app.application.scheduled_runtime.import_notification_service import (
    ClientImportNotificationService,
)


class ImportSource:
    def process_due_user_vocabulary_imports(self):
        return [{"kind": "import"}]


class ImportSourceWithAdminRestore(ImportSource):
    def dispatch_due_admin_bot_restores(self):
        return [{"kind": "restore"}]


class AdminRestoreSource:
    def dispatch_due_admin_bot_restores(self):
        return [{"kind": "restore"}]


class BillingNotificationSource:
    def dispatch_due_billing_notifications(self):
        return [{"kind": "billing"}]


def test_import_notification_service_combines_import_and_admin_restore_notifications() -> None:
    service = ClientImportNotificationService(ImportSourceWithAdminRestore())

    assert service.process_due_import_notifications() == [{"kind": "import"}, {"kind": "restore"}]


def test_import_notification_service_combines_separate_notification_sources() -> None:
    service = ClientImportNotificationService(
        ImportSource(),
        admin_restore_source=AdminRestoreSource(),
        billing_notification_source=BillingNotificationSource(),
    )

    assert service.process_due_import_notifications() == [
        {"kind": "import"},
        {"kind": "restore"},
        {"kind": "billing"},
    ]


def test_import_notification_service_allows_sources_without_admin_restore_hook() -> None:
    service = ClientImportNotificationService(ImportSource())

    assert service.process_due_import_notifications() == [{"kind": "import"}]
