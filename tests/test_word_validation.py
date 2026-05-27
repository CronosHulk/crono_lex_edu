from __future__ import annotations

from app.word_validation import (
    GeneratedWordDetails,
    GeneratedWordValidationRules,
    usage_form_for_word,
    validate_ascii_word_form,
    validate_generated_word_details,
)


def test_usage_form_for_word_strips_to_prefix_for_verbs_only() -> None:
    assert usage_form_for_word("to look after", "phrasal verb") == "look after"
    assert usage_form_for_word("toxic", "adjective") == "toxic"


def test_validate_ascii_word_form_rejects_non_ascii() -> None:
    try:
        validate_ascii_word_form("ennuyé", field_name="word", source_ref="ennuy__adjective")
    except ValueError as error:
        assert "non-ascii word" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")


def test_validate_generated_word_details_normalizes_and_validates_gap_ready_examples() -> None:
    validated = validate_generated_word_details(
        GeneratedWordDetails(
            source_ref="to-look-after__phrasal-verb",
            word="to look after",
            usage_form="look after",
            examples=[
                "She looks after her younger brother every weekend.  ",
                "Good nurses look after patients with great patience.",
                "Neighbors look after the house during winter trips.",
            ],
            part_of_speech="phrasal verb",
            phonetic_us="/lʊk ˈæf.tɚ/",
            translation_uk="доглядати",
            translation_ru="присматривать",
            translation_pl="opiekować się",
        ),
        rules=GeneratedWordValidationRules(
            expected_example_count=3,
            min_example_words=6,
            max_example_words=14,
            require_part_of_speech=True,
            require_phonetic_us=True,
            require_translations=True,
        ),
    )

    assert validated.examples[0] == "She looks after her younger brother every weekend."
    assert validated.usage_form == "look after"
    assert validated.translation_uk == "доглядати"


def test_validate_generated_word_details_rejects_examples_without_gap_support() -> None:
    try:
        validate_generated_word_details(
            GeneratedWordDetails(
                source_ref="pace__noun",
                word="pace",
                usage_form="pace",
                examples=[
                    "This sentence mentions nothing relevant at all.",
                    "Another unrelated sentence appears right here now.",
                ],
            ),
            rules=GeneratedWordValidationRules(expected_example_count=2, min_example_words=6, max_example_words=12),
        )
    except ValueError as error:
        assert "gap builder could not blank usage form" in str(error)
    else:  # pragma: no cover
        raise AssertionError("ValueError was expected")
