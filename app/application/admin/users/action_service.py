from __future__ import annotations

from typing import Protocol

from app.application.admin.users.archive_user import ArchiveUserDatabasePort, archive_user
from app.application.admin.users.delete_user import DeleteUserDatabasePort, delete_user
from app.application.admin.users.reset_password import (
    ResetUserPasswordDatabasePort,
    reset_user_password,
)
from app.application.admin.users.set_learning_role import (
    SetUserLearningRoleDatabasePort,
    set_user_learning_role,
)
from app.application.admin.users.set_role import SetUserRoleDatabasePort, set_user_role
from app.application.admin.users.set_subscription import (
    SetUserSubscriptionDatabasePort,
    set_user_subscription,
)
from app.application.admin.users.set_subscription_trial import (
    SetUserSubscriptionTrialDatabasePort,
    set_user_subscription_trial,
)
from app.time_utils import TimeService


class AdminUserActionDatabasePort(
    ArchiveUserDatabasePort,
    DeleteUserDatabasePort,
    ResetUserPasswordDatabasePort,
    SetUserLearningRoleDatabasePort,
    SetUserRoleDatabasePort,
    SetUserSubscriptionDatabasePort,
    SetUserSubscriptionTrialDatabasePort,
    Protocol,
):
    pass


class AdminUserActionService:
    def __init__(self, db: AdminUserActionDatabasePort, time_service: TimeService) -> None:
        self.db = db
        self.time_service = time_service

    def set_role(self, *, actor: dict, target_user_id: str, role: str) -> dict:
        return set_user_role(self.db, self.time_service, actor=actor, target_user_id=target_user_id, role=role)

    def set_learning_role(self, *, actor: dict, target_user_id: str, learning_role: str) -> dict:
        return set_user_learning_role(
            self.db,
            self.time_service,
            actor=actor,
            target_user_id=target_user_id,
            learning_role=learning_role,
        )

    def set_subscription(self, *, actor: dict, target_user_id: str, plan_key: str) -> dict:
        return set_user_subscription(
            self.db,
            self.time_service,
            actor=actor,
            target_user_id=target_user_id,
            plan_key=plan_key,
        )

    def set_subscription_trial(self, *, actor: dict, target_user_id: str, is_trial_enabled: bool) -> dict:
        return set_user_subscription_trial(
            self.db,
            self.time_service,
            actor=actor,
            target_user_id=target_user_id,
            is_trial_enabled=is_trial_enabled,
        )

    def archive(self, *, actor: dict, user_id: str) -> dict[str, str]:
        return archive_user(self.db, self.time_service, actor=actor, user_id=user_id)

    def delete(self, *, actor: dict, user_id: str) -> dict[str, str]:
        return delete_user(self.db, actor=actor, user_id=user_id)

    def reset_password(self, *, actor: dict, user_id: str) -> dict:
        return reset_user_password(self.db, self.time_service, actor=actor, user_id=user_id)
