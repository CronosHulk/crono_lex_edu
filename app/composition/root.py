from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from app.application.dispatch_lock import DispatchLock
from app.composition.admin import configure_admin_runtime
from app.composition.billing import (
    configure_billing_notification_runtime,
    configure_billing_reconciliation_runtime,
    configure_billing_webhook_runtime,
    configure_subscription_runtime,
)
from app.composition.client_admin_restore import configure_client_admin_restore_runtime
from app.composition.client_bot_messages import configure_client_bot_message_runtime
from app.composition.client_import_entry import configure_client_import_entry_runtime
from app.composition.client_learning_actions import configure_client_learning_action_runtime
from app.composition.client_learning_core_flow import configure_client_learning_core_flow_runtime
from app.composition.client_learning_interactions import (
    configure_client_learning_interaction_runtime,
)
from app.composition.client_learning_menu import configure_client_learning_menu_runtime
from app.composition.client_reminders import configure_client_reminder_runtime
from app.composition.client_runtime_input import configure_client_runtime_input_runtime
from app.composition.client_text_actions import configure_client_text_action_runtime
from app.composition.client_web import configure_client_web_runtime
from app.composition.default_helpers import default_helper_resolver
from app.composition.reference_runtime import configure_reference_runtime
from app.composition.user_import_build_pipeline import (
    configure_user_import_build_pipeline_runtime,
)
from app.composition.user_import_intake import configure_user_import_intake_runtime
from app.composition.user_import_runtime import configure_user_import_runtime
from app.composition.user_import_summary_read import (
    configure_user_import_summary_read_runtime,
)
from app.config import Settings
from app.data_access.provider import Database


def __getattr__(name: str) -> Any:
    try:
        return default_helper_resolver(name)
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None


def build_database(settings: Settings) -> Database:
    return Database(settings)


def build_learning_runtime(
    db: Database,
    time_service: Any,
    *,
    quiz_queue_randomizer: Callable[[list[int]], list[int]] | None = None,
) -> SimpleNamespace:
    runtime = SimpleNamespace(
        db=db,
        time_service=time_service,
        dispatch_lock=DispatchLock(),
    )
    configure_learning_service(
        runtime,
        db,
        quiz_queue_randomizer=quiz_queue_randomizer,
    )
    return runtime


def configure_learning_service(
    service: Any,
    db: Database,
    *,
    helper_resolver: Callable[[str], Any] | None = None,
    quiz_queue_randomizer: Callable[[list[int]], list[int]] | None = None,
) -> None:
    self = service
    resolve_helper = helper_resolver or default_helper_resolver
    configure_admin_runtime(self, db)
    configure_reference_runtime(self, db)
    configure_subscription_runtime(self, db)
    configure_billing_notification_runtime(self, db)
    configure_client_bot_message_runtime(self, db)
    configure_client_import_entry_runtime(self, db)
    configure_client_reminder_runtime(self, db)
    configure_client_admin_restore_runtime(self, db)
    configure_client_text_action_runtime(self, db)
    configure_client_learning_action_runtime(self, db)
    configure_client_learning_menu_runtime(self, db)
    configure_client_learning_core_flow_runtime(self, db)
    configure_client_learning_interaction_runtime(
        self,
        db,
        quiz_queue_randomizer=quiz_queue_randomizer,
    )
    configure_user_import_build_pipeline_runtime(self, db, resolve_helper)
    configure_user_import_intake_runtime(self, db, resolve_helper)
    configure_user_import_runtime(self, db, resolve_helper)
    configure_billing_webhook_runtime(
        self,
        db,
        post_upgrade_rescan=self.user_import_bound_google_doc_sync_service.queue_post_upgrade_rescan,
    )
    configure_client_web_runtime(self, db)
    configure_billing_reconciliation_runtime(
        self,
        db,
        post_upgrade_rescan=self.user_import_bound_google_doc_sync_service.queue_post_upgrade_rescan,
    )
    configure_user_import_summary_read_runtime(self, db)
    configure_client_runtime_input_runtime(self, db)
