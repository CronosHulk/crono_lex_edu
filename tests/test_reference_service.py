from __future__ import annotations

from app.reference.labels import (
    format_category_labels,
    format_part_of_speech_labels,
    translate_category_label,
    translate_part_of_speech_label,
)
from app.reference.learning_flow import (
    FINAL_QUIZ_STAGE,
    NEXT_READY_STAGE,
    QUIZ_PROMPT_PROGRESS_STAGES,
    QUIZ_STAGE_META_I18N_KEYS,
    QUIZ_STAGE_TO_EXERCISE,
    QUIZ_STAGES,
    READY_STAGE_INTRO_I18N_KEYS,
    READY_STAGE_TO_QUIZ_STAGE,
    READY_STAGES,
)
from app.reference.scheduling import (
    HOURS_BY_PERIOD,
    WEEKDAY_CODES,
    format_hour_label,
    format_weekday_labels,
    weekday_name,
)
from app.reference.service import (
    LEVEL_ORDER,
    WORDS_PER_SESSION_OPTIONS,
    AppReference,
    format_count_text,
)


class FakeLanguageLevelReader:
    def __init__(self) -> None:
        self.levels = [
            {"id": 1, "title": "A1"},
            {"id": 2, "title": "A2"},
        ]

    def list_language_levels(self):
        return list(self.levels)


class FakeLearningSyllabusReader:
    def list_grouped_by_level(self):
        return [{"level": {"title": "A1"}, "domains": [{"code": "grammar", "items": []}]}]


class FakeGrammarTopicReader:
    def list_active(self):
        return [{"code": "a1_grammar_present_simple", "title": "Present Simple", "level": "A1", "min_level": "A1"}]


def test_reference_exposes_static_learning_options() -> None:
    reference = AppReference(FakeLanguageLevelReader())

    assert reference.level_order() == LEVEL_ORDER
    assert reference.words_per_session_options() == WORDS_PER_SESSION_OPTIONS
    assert reference.words_per_session_options() == (5, 10, 15, 20, 30, 40)


def test_reference_reads_language_levels_from_db() -> None:
    reference = AppReference(FakeLanguageLevelReader())

    assert reference.language_levels() == [{"id": 1, "title": "A1"}, {"id": 2, "title": "A2"}]
    assert reference.get_level_by_title("A2") == {"id": 2, "title": "A2"}
    assert reference.get_level_by_id(1) == {"id": 1, "title": "A1"}
    assert reference.get_level_by_title("B1") is None
    assert reference.get_level_by_id(999) is None


def test_reference_reads_learning_syllabus_when_provider_is_configured() -> None:
    empty_reference = AppReference(FakeLanguageLevelReader())
    reference = AppReference(FakeLanguageLevelReader(), FakeLearningSyllabusReader())

    assert empty_reference.learning_syllabus() == []
    assert reference.learning_syllabus() == [{"level": {"title": "A1"}, "domains": [{"code": "grammar", "items": []}]}]


def test_reference_reads_grammar_topics_when_provider_is_configured() -> None:
    empty_reference = AppReference(FakeLanguageLevelReader())
    reference = AppReference(FakeLanguageLevelReader(), grammar_topics=FakeGrammarTopicReader())

    assert empty_reference.grammar_topics() == []
    assert reference.grammar_topics() == [
        {"code": "a1_grammar_present_simple", "title": "Present Simple", "level": "A1", "min_level": "A1"}
    ]


def test_reference_formats_word_counts() -> None:
    assert format_count_text("uk", 10) == "10 слів"
    assert format_count_text("uk", "not-a-number") == "not-a-number"


def test_reference_translates_part_of_speech_labels() -> None:
    assert translate_part_of_speech_label("uk", " phrasal   verb ") == "фразове дієслово"
    assert translate_part_of_speech_label("uk", "rare-pos") == "rare-pos"
    assert translate_part_of_speech_label("uk", None) is None


def test_reference_formats_part_of_speech_labels_without_duplicates() -> None:
    assert format_part_of_speech_labels("uk", ["verb", "verb", "noun"]) == "дієслово, іменник"
    assert format_part_of_speech_labels("uk", []) == ""
    assert format_part_of_speech_labels("uk", None) == ""


def test_reference_translates_category_labels() -> None:
    assert translate_category_label("uk", " general ") == "загальне"
    assert translate_category_label("uk", "rare-category") == "rare-category"
    assert translate_category_label("uk", None) is None


def test_reference_formats_category_labels_like_existing_card_formatter() -> None:
    assert format_category_labels("uk", ["actions", "common", "actions"]) == "Дії, Поширене, Дії"
    assert format_category_labels("uk", []) == ""
    assert format_category_labels("uk", None) == ""


def test_reference_exposes_reminder_schedule_options() -> None:
    assert list(HOURS_BY_PERIOD) == ["morning", "day", "evening"]
    assert HOURS_BY_PERIOD["morning"] == (8, 9, 10, 11)
    assert HOURS_BY_PERIOD["day"] == (12, 13, 14, 15, 16, 17)
    assert HOURS_BY_PERIOD["evening"] == (19, 20, 21, 22)
    assert WEEKDAY_CODES == (0, 1, 2, 3, 4, 5, 6)


def test_reference_formats_reminder_schedule_labels() -> None:
    assert format_hour_label(8) == "08:00"
    assert weekday_name(0) == "monday"
    assert format_weekday_labels("uk", [4, 0, 0]) == "Пн, Пт"
    assert format_weekday_labels("uk", []) == "не налаштовано"


def test_reference_exposes_learning_flow_stages() -> None:
    assert READY_STAGES == ("ready_en_uk", "ready_uk_en", "ready_gap")
    assert QUIZ_STAGES == ("quiz_en_uk", "quiz_uk_en", "quiz_gap")
    assert READY_STAGE_TO_QUIZ_STAGE == {
        "ready_en_uk": "quiz_en_uk",
        "ready_uk_en": "quiz_uk_en",
        "ready_gap": "quiz_gap",
    }
    assert QUIZ_STAGE_TO_EXERCISE == {
        "quiz_en_uk": "en_uk",
        "quiz_uk_en": "uk_en",
        "quiz_gap": "gap",
    }
    assert NEXT_READY_STAGE == {
        "quiz_en_uk": "ready_uk_en",
        "quiz_uk_en": "ready_gap",
    }
    assert READY_STAGE_INTRO_I18N_KEYS == {
        "ready_en_uk": "practice_intro",
        "ready_uk_en": "quiz_uk_en_title",
        "ready_gap": "quiz_gap_title",
    }
    assert QUIZ_STAGE_META_I18N_KEYS == {
        "quiz_en_uk": "quiz_en_uk_meta",
        "quiz_uk_en": "quiz_uk_en_meta",
        "quiz_gap": "quiz_gap_meta",
    }
    assert QUIZ_PROMPT_PROGRESS_STAGES == ("quiz_en_uk", "quiz_uk_en")
    assert FINAL_QUIZ_STAGE == "quiz_gap"
