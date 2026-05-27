from __future__ import annotations

from contextlib import contextmanager

from app.data_access.learning_syllabus import (
    LearningSyllabusRepository,
    learning_syllabus_domain_to_dict,
    learning_syllabus_item_to_dict,
    normalize_learning_syllabus_domain_code,
)
from app.models import LanguageLevel, LearningSyllabusDomain, LearningSyllabusItem


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, scalars_rows=None) -> None:
        self.scalars_rows = list(scalars_rows or [])

    def scalars(self, statement):
        rows = self.scalars_rows.pop(0) if self.scalars_rows else []
        return FakeScalarsResult(rows)


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_domain(**overrides) -> LearningSyllabusDomain:
    values = {"id": 1, "code": "grammar", "title": "Grammar", "sort_order": 10}
    values.update(overrides)
    return LearningSyllabusDomain(**values)


def make_item(**overrides) -> LearningSyllabusItem:
    level = overrides.pop("level", LanguageLevel(id=1, title="A1", description="Survival English"))
    domain = overrides.pop("domain", make_domain())
    values = {
        "id": 101,
        "level_id": level.id,
        "domain_id": domain.id,
        "code": "a1_grammar_present_simple",
        "title": "Present Simple",
        "normalized_title": "present simple",
        "sort_order": 80,
        "is_active": True,
        "metadata_json": {"source": "test"},
    }
    values.update(overrides)
    row = LearningSyllabusItem(**values)
    row.level = level
    row.domain = domain
    return row


def test_learning_syllabus_serializers_preserve_reference_shape() -> None:
    domain = make_domain()
    item = make_item(domain=domain)

    assert learning_syllabus_domain_to_dict(domain) == {
        "id": 1,
        "code": "grammar",
        "title": "Grammar",
        "sort_order": 10,
    }
    assert learning_syllabus_item_to_dict(item) == {
        "id": 101,
        "code": "a1_grammar_present_simple",
        "title": "Present Simple",
        "normalized_title": "present simple",
        "sort_order": 80,
        "is_active": True,
        "metadata_json": {"source": "test"},
    }


def test_learning_syllabus_repository_lists_domains_and_items() -> None:
    domain = make_domain()
    item = make_item(domain=domain)
    repository = LearningSyllabusRepository(FakeSessionManager(FakeSession(scalars_rows=[[domain], [item]])))

    assert repository.list_domains() == [
        {"id": 1, "code": "grammar", "title": "Grammar", "sort_order": 10},
    ]
    assert repository.list_items(level_title="a1", domain_code="Grammar")[0] == {
        "id": 101,
        "code": "a1_grammar_present_simple",
        "title": "Present Simple",
        "normalized_title": "present simple",
        "sort_order": 80,
        "is_active": True,
        "metadata_json": {"source": "test"},
        "level": {"id": 1, "title": "A1", "description": "Survival English"},
        "domain": {"id": 1, "code": "grammar", "title": "Grammar", "sort_order": 10},
    }


def test_learning_syllabus_domain_filter_accepts_readable_titles() -> None:
    assert normalize_learning_syllabus_domain_code("Vocabulary Themes") == "vocabulary_theme"
    assert normalize_learning_syllabus_domain_code("functional-skills") == "functional_skill"


def test_learning_syllabus_repository_groups_items_by_level_and_domain() -> None:
    level = LanguageLevel(id=1, title="A1", description="Survival English")
    grammar = make_domain(id=1, code="grammar", title="Grammar", sort_order=10)
    vocabulary = make_domain(id=2, code="vocabulary_theme", title="Vocabulary Themes", sort_order=20)
    repository = LearningSyllabusRepository(
        FakeSessionManager(
            FakeSession(
                scalars_rows=[
                    [level],
                    [
                        make_item(id=101, level=level, domain=grammar),
                        make_item(
                            id=102,
                            level=level,
                            domain=vocabulary,
                            code="a1_vocabulary_family",
                            title="Family",
                            normalized_title="family",
                            sort_order=20,
                        ),
                    ],
                ]
            )
        )
    )

    payload = repository.list_grouped_by_level()

    assert payload[0]["level"] == {"id": 1, "title": "A1", "description": "Survival English"}
    assert [domain["code"] for domain in payload[0]["domains"]] == ["grammar", "vocabulary_theme"]
    assert payload[0]["domains"][0]["items"][0]["code"] == "a1_grammar_present_simple"
    assert payload[0]["domains"][1]["items"][0]["code"] == "a1_vocabulary_family"
