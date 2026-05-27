from __future__ import annotations

from typing import Any

from app.data_access.grammar_topics import GrammarTopicRepository
from app.data_access.learning_levels import LearningLevelRepository
from app.reference.service import AppReference


def configure_reference_runtime(service: Any, db: Any) -> None:
    learning_levels_repo = getattr(db, "learning_levels", None) or LearningLevelRepository(db)
    grammar_topics_repo = getattr(db, "grammar_topics", None) or GrammarTopicRepository(db)
    service.reference = AppReference(
        learning_levels_repo,
        grammar_topics=grammar_topics_repo,
    )

