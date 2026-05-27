from __future__ import annotations

from contextlib import contextmanager

from app.data_access.grammar_topics import GrammarTopicRepository, grammar_topic_to_dict
from app.models import GrammarTopic


class FakeScalarsResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, *, scalars_rows=None, scalar_row=None) -> None:
        self.scalars_rows = list(scalars_rows or [])
        self.scalar_row = scalar_row

    def scalars(self, statement):
        rows = self.scalars_rows.pop(0) if self.scalars_rows else []
        return FakeScalarsResult(rows)

    def scalar(self, statement):
        return self.scalar_row


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_topic(**overrides) -> GrammarTopic:
    values = {
        "id": 1,
        "code": "a1_grammar_present_simple",
        "title": "Present Simple",
        "level": "A1",
        "min_level": "A1",
        "description": "Basic present tense.",
        "is_active": True,
    }
    values.update(overrides)
    return GrammarTopic(**values)


def test_grammar_topic_serializer_preserves_reference_shape() -> None:
    assert grammar_topic_to_dict(make_topic()) == {
        "id": 1,
        "code": "a1_grammar_present_simple",
        "title": "Present Simple",
        "level": "A1",
        "min_level": "A1",
        "description": "Basic present tense.",
        "is_active": True,
    }


def test_grammar_topic_repository_lists_active_topics() -> None:
    topic = make_topic()
    repository = GrammarTopicRepository(FakeSessionManager(FakeSession(scalars_rows=[[topic]])))

    assert repository.list_active() == [grammar_topic_to_dict(topic)]


def test_grammar_topic_repository_gets_active_topic_by_code() -> None:
    topic = make_topic(code="b2_grammar_third_conditional", level="B2", min_level="B2")
    repository = GrammarTopicRepository(FakeSessionManager(FakeSession(scalar_row=topic)))

    assert repository.get_active_by_code(" b2_grammar_third_conditional ") == grammar_topic_to_dict(topic)


def test_grammar_topic_repository_ignores_blank_code() -> None:
    repository = GrammarTopicRepository(FakeSessionManager(FakeSession(scalar_row=make_topic())))

    assert repository.get_active_by_code("   ") is None
