from __future__ import annotations

from typing import Any, Protocol

from app.plurals import format_word_count

LEVEL_ORDER = ("A1", "A2", "B1", "B2", "C1", "C2")
DEFAULT_LANGUAGE_LEVEL_TITLE = "A1"
WORDS_PER_SESSION_OPTIONS = (5, 10, 15, 20, 30, 40)


class LanguageLevelReader(Protocol):
    def list_language_levels(self) -> list[dict[str, Any]]:
        ...


class LearningSyllabusReader(Protocol):
    def list_grouped_by_level(self) -> list[dict[str, Any]]:
        ...


class GrammarTopicReader(Protocol):
    def list_active(self) -> list[dict[str, Any]]:
        ...


def format_count_text(locale: str, count: Any) -> str:
    try:
        normalized_count = int(count)
    except (TypeError, ValueError):
        return str(count)
    return format_word_count(locale, normalized_count)


class AppReference:
    def __init__(
        self,
        language_levels: LanguageLevelReader,
        learning_syllabus: LearningSyllabusReader | None = None,
        grammar_topics: GrammarTopicReader | None = None,
    ) -> None:
        self.language_level_reader = language_levels
        self.learning_syllabus_reader = learning_syllabus
        self.grammar_topic_reader = grammar_topics

    def level_order(self) -> tuple[str, ...]:
        return LEVEL_ORDER

    def words_per_session_options(self) -> tuple[int, ...]:
        return WORDS_PER_SESSION_OPTIONS

    def language_levels(self) -> list[dict[str, Any]]:
        return self.language_level_reader.list_language_levels()

    def get_level_by_title(self, level_title: str) -> dict[str, Any] | None:
        return next((level for level in self.language_levels() if level["title"] == level_title), None)

    def get_level_by_id(self, level_id: int) -> dict[str, Any] | None:
        return next((level for level in self.language_levels() if level["id"] == level_id), None)

    def available_level_titles(self) -> set[str]:
        return {level["title"] for level in self.language_levels()}

    def learning_syllabus(self) -> list[dict[str, Any]]:
        if self.learning_syllabus_reader is None:
            return []
        return self.learning_syllabus_reader.list_grouped_by_level()

    def grammar_topics(self) -> list[dict[str, Any]]:
        if self.grammar_topic_reader is None:
            return []
        return self.grammar_topic_reader.list_active()
