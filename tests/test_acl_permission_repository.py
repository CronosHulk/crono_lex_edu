from __future__ import annotations

from contextlib import contextmanager

from app.data_access.acl_permissions import AclPermissionRepository


class FakeResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, execute_rows) -> None:
        self.execute_rows = list(execute_rows)

    def execute(self, statement):
        return FakeResult(self.execute_rows.pop(0) if self.execute_rows else [])


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def test_get_effective_rule_uses_child_group_override_before_parent() -> None:
    repository = AclPermissionRepository(
        FakeSessionManager(
            FakeSession(
                [
                    [(1, None, "student"), (2, 1, "admin"), (3, 2, "super_admin")],
                    [(2, "disabled"), (3, "enabled")],
                ]
            )
        )
    )

    rule = repository.get_effective_rule(
        group_title="super_admin",
        action="users/delete",
        environment="web_admin",
    )

    assert rule == "enabled"


def test_get_effective_rule_falls_back_to_parent_group() -> None:
    repository = AclPermissionRepository(
        FakeSessionManager(
            FakeSession(
                [
                    [(1, None, "student"), (2, 1, "admin")],
                    [(1, "enabled")],
                ]
            )
        )
    )

    rule = repository.get_effective_rule(
        group_title="admin",
        action="learning/view",
        environment="client_web",
    )

    assert rule == "enabled"


def test_list_group_capabilities_returns_effective_enabled_actions_only() -> None:
    repository = AclPermissionRepository(
        FakeSessionManager(
            FakeSession(
                [
                    [(1, None, "student"), (2, 1, "admin"), (3, 2, "super_admin")],
                    [
                        (1, "learning/view", "enabled"),
                        (2, "users/delete", "disabled"),
                        (2, "dictionary/list_words", "enabled"),
                        (3, "users/delete", "enabled"),
                        (3, "imports/run_now", "enabled"),
                    ],
                ]
            )
        )
    )

    capabilities = repository.list_group_capabilities(group_title="super_admin", environment="web_admin")

    assert capabilities == [
        "dictionary/list_words",
        "imports/run_now",
        "learning/view",
        "users/delete",
    ]


def test_list_group_capabilities_keeps_child_disabled_override() -> None:
    repository = AclPermissionRepository(
        FakeSessionManager(
            FakeSession(
                [
                    [(1, None, "student"), (2, 1, "admin")],
                    [
                        (1, "imports/create", "enabled"),
                        (2, "imports/create", "disabled"),
                    ],
                ]
            )
        )
    )

    assert repository.list_group_capabilities(group_title="admin", environment="telegram_user") == []
