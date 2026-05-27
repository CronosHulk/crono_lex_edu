from __future__ import annotations

from sqlalchemy import select

from app.models import AclGroup, AclPermission
from app.orm import SessionManager


class AclPermissionRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def get_effective_rule(self, *, group_title: str, action: str, environment: str) -> str | None:
        with self.session_manager.session() as session:
            group_rows = session.execute(select(AclGroup.id, AclGroup.parent_group_id, AclGroup.title)).all()
            ordered_group_ids = _ancestor_group_ids(group_rows, group_title)
            if not ordered_group_ids:
                return None
            rows = session.execute(
                select(AclPermission.group_id, AclPermission.rule)
                .where(
                    AclPermission.group_id.in_(ordered_group_ids),
                    AclPermission.action == action,
                    AclPermission.environment == environment,
                )
            ).all()
            rules_by_group_id = {int(group_id): rule for group_id, rule in rows}
            for group_id in ordered_group_ids:
                if group_id in rules_by_group_id:
                    return str(rules_by_group_id[group_id])
            return None

    def list_group_capabilities(self, *, group_title: str, environment: str) -> list[str]:
        with self.session_manager.session() as session:
            group_rows = session.execute(select(AclGroup.id, AclGroup.parent_group_id, AclGroup.title)).all()
            ordered_group_ids = _ancestor_group_ids(group_rows, group_title)
            if not ordered_group_ids:
                return []
            rows = session.execute(
                select(AclPermission.group_id, AclPermission.action, AclPermission.rule)
                .where(
                    AclPermission.group_id.in_(ordered_group_ids),
                    AclPermission.environment == environment,
                )
                .order_by(AclPermission.action.asc())
            ).all()
        group_rank = {group_id: index for index, group_id in enumerate(ordered_group_ids)}
        effective: dict[str, tuple[int, str]] = {}
        for group_id, action, rule in rows:
            rank = group_rank.get(int(group_id))
            if rank is None:
                continue
            current = effective.get(str(action))
            if current is None or rank < current[0]:
                effective[str(action)] = (rank, str(rule))
        return sorted(action for action, (_, rule) in effective.items() if rule == "enabled")


def _ancestor_group_ids(group_rows, group_title: str) -> list[int]:
    groups_by_title = {str(title): {"id": int(group_id), "parent_group_id": parent_group_id} for group_id, parent_group_id, title in group_rows}
    group = groups_by_title.get(group_title)
    if group is None:
        return []
    groups_by_id = {row["id"]: row for row in groups_by_title.values()}
    ordered = [group["id"]]
    parent_group_id = group.get("parent_group_id")
    visited = set(ordered)
    while parent_group_id is not None:
        parent_id = int(parent_group_id)
        if parent_id in visited:
            break
        ordered.append(parent_id)
        visited.add(parent_id)
        parent = groups_by_id.get(parent_id)
        if parent is None:
            break
        parent_group_id = parent.get("parent_group_id")
    return ordered
