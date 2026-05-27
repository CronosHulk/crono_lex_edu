from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Any


class UserImportScheduledRuntimeService:
    def __init__(
        self,
        user_import_runtime_service: Any,
        *,
        dispatch_lock: Callable[[str], AbstractContextManager[bool]],
    ) -> None:
        self.user_import_runtime_service = user_import_runtime_service
        self.dispatch_lock = dispatch_lock

    def process_due_user_vocabulary_imports(self) -> list[Any]:
        with self.dispatch_lock("user_imports") as acquired:
            if not acquired:
                return []
            return self.user_import_runtime_service.process_due_user_vocabulary_imports()

    def process_due_post_upgrade_rescans(self) -> list[Any]:
        with self.dispatch_lock("post_upgrade_rescans") as acquired:
            if not acquired:
                return []
            return self.user_import_runtime_service.process_due_post_upgrade_rescans()

    def process_due_bound_google_doc_syncs(self) -> list[Any]:
        with self.dispatch_lock("bound_google_doc_syncs") as acquired:
            if not acquired:
                return []
            return self.user_import_runtime_service.process_due_bound_google_doc_syncs()

    def process_due_import_scheduler_tick(self) -> list[Any]:
        with self.dispatch_lock("import_scheduler") as acquired:
            if not acquired:
                return []
            return self.user_import_runtime_service.process_due_import_scheduler_tick()

    def process_user_import_attribute_queue_now(
        self, telegram_user_id: int, current_time: datetime
    ) -> None:
        with self.dispatch_lock(f"user_import_attribute_build:{telegram_user_id}") as acquired:
            if not acquired:
                return
            self.user_import_runtime_service.process_user_import_attribute_queue_now(current_time)
