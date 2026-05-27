from __future__ import annotations

from app.acl.processor import AclProcessor, is_valid_acl_action


class FakeAclPermissionReader:
    def __init__(self, rules: dict[tuple[str, str, str], str] | None = None, capabilities: list[str] | None = None) -> None:
        self.rules = rules or {}
        self.capabilities = capabilities or []

    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        return self.rules.get((group_title, action, environment))

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        return list(self.capabilities)


def test_can_access_allows_enabled_service_action() -> None:
    processor = AclProcessor(
        FakeAclPermissionReader({("admin", "dictionary/add_word", "web_admin"): "enabled"})
    )

    decision = processor.can_access(
        {"acl_group_title": "admin"},
        action=" dictionary/add_word ",
        environment="web_admin",
    )

    assert decision.is_allowed is True


def test_can_access_rejects_dot_or_non_atomic_action() -> None:
    processor = AclProcessor(
        FakeAclPermissionReader({("admin", "dictionary.add_word", "web_admin"): "enabled"})
    )

    decision = processor.can_access(
        {"acl_group_title": "admin"},
        action="dictionary.add_word",
        environment="web_admin",
    )

    assert decision.is_allowed is False
    assert decision.reason == "Action must use service/action format"


def test_can_access_rejects_disabled_permission() -> None:
    processor = AclProcessor(
        FakeAclPermissionReader({("admin", "users/delete", "web_admin"): "disabled"})
    )

    decision = processor.can_access(
        {"acl_group_title": "admin"},
        action="users/delete",
        environment="web_admin",
    )

    assert decision.is_allowed is False
    assert decision.reason == "Access disabled"


def test_capabilities_for_returns_empty_without_acl_group() -> None:
    processor = AclProcessor(FakeAclPermissionReader(capabilities=["dictionary/list_words"]))

    assert processor.capabilities_for({}, environment="web_admin") == []


def test_acl_action_format_requires_service_slash_action() -> None:
    assert is_valid_acl_action("dictionary/add_word") is True
    assert is_valid_acl_action("dictionary/add_idiom") is True
    assert is_valid_acl_action("dictionary.add_word") is False
    assert is_valid_acl_action("dictionary") is False
    assert is_valid_acl_action("Dictionary/add_word") is False
