from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import LanguageLevel, LearningSyllabusDomain, LearningSyllabusItem
from app.orm import SessionManager

DOMAIN_CODE_ALIASES = {
    "grammar": "grammar",
    "vocabulary_theme": "vocabulary_theme",
    "vocabulary_themes": "vocabulary_theme",
    "functional_skill": "functional_skill",
    "functional_skills": "functional_skill",
}


def learning_syllabus_item_to_dict(row: LearningSyllabusItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "title": row.title,
        "normalized_title": row.normalized_title,
        "sort_order": row.sort_order,
        "is_active": row.is_active,
        "metadata_json": row.metadata_json or {},
    }


def learning_syllabus_domain_to_dict(row: LearningSyllabusDomain) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "title": row.title,
        "sort_order": row.sort_order,
    }


class LearningSyllabusRepository:
    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

    def list_domains(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            rows = session.scalars(select(LearningSyllabusDomain).order_by(LearningSyllabusDomain.sort_order.asc())).all()
            return [learning_syllabus_domain_to_dict(row) for row in rows]

    def list_items(self, *, level_title: str | None = None, domain_code: str | None = None) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            statement = (
                select(LearningSyllabusItem)
                .join(LanguageLevel)
                .join(LearningSyllabusDomain)
                .options(selectinload(LearningSyllabusItem.level), selectinload(LearningSyllabusItem.domain))
                .where(LearningSyllabusItem.is_active.is_(True))
            )
            if level_title:
                statement = statement.where(LanguageLevel.title == level_title.strip().upper())
            if domain_code:
                statement = statement.where(LearningSyllabusDomain.code == normalize_learning_syllabus_domain_code(domain_code))
            rows = session.scalars(
                statement.order_by(
                    LanguageLevel.id.asc(),
                    LearningSyllabusDomain.sort_order.asc(),
                    LearningSyllabusItem.sort_order.asc(),
                )
            ).all()
            return [_learning_syllabus_item_with_refs_to_dict(row) for row in rows]

    def list_grouped_by_level(self) -> list[dict[str, Any]]:
        with self.session_manager.session() as session:
            levels = session.scalars(select(LanguageLevel).order_by(LanguageLevel.id.asc())).all()
            items = session.scalars(
                select(LearningSyllabusItem)
                .join(LanguageLevel)
                .join(LearningSyllabusDomain)
                .options(selectinload(LearningSyllabusItem.level), selectinload(LearningSyllabusItem.domain))
                .where(LearningSyllabusItem.is_active.is_(True))
                .order_by(
                    LanguageLevel.id.asc(),
                    LearningSyllabusDomain.sort_order.asc(),
                    LearningSyllabusItem.sort_order.asc(),
                )
            ).all()

        items_by_level_domain: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        domains_by_level: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
        for item in items:
            domain_payload = learning_syllabus_domain_to_dict(item.domain)
            domains_by_level[item.level_id][item.domain.code] = domain_payload
            items_by_level_domain[item.level_id][item.domain.code].append(learning_syllabus_item_to_dict(item))

        result: list[dict[str, Any]] = []
        for level in levels:
            domain_payloads = []
            for domain in sorted(domains_by_level[level.id].values(), key=lambda value: value["sort_order"]):
                domain_payloads.append(
                    {
                        **domain,
                        "items": items_by_level_domain[level.id][domain["code"]],
                    }
                )
            result.append(
                {
                    "level": {"id": level.id, "title": level.title, "description": level.description},
                    "domains": domain_payloads,
                }
            )
        return result


def _learning_syllabus_item_with_refs_to_dict(row: LearningSyllabusItem) -> dict[str, Any]:
    return {
        **learning_syllabus_item_to_dict(row),
        "level": {"id": row.level.id, "title": row.level.title, "description": row.level.description},
        "domain": learning_syllabus_domain_to_dict(row.domain),
    }


def normalize_learning_syllabus_domain_code(value: str) -> str:
    code = "_".join(str(value or "").strip().lower().replace("-", "_").split())
    return DOMAIN_CODE_ALIASES.get(code, code)
