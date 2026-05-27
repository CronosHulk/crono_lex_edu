from __future__ import annotations

from app.application.client_learning.content import (
    build_deterministic_options,
    build_fill_in_gap_example,
    build_marks,
    build_quiz_button_row_widths,
    build_quiz_error_count,
    build_quiz_payload,
    build_quiz_progress_counts,
    build_quiz_progress_title,
    resolve_translation_for_locale,
    select_translation_variant,
    split_translation_variants,
)
from app.application.client_learning.display import (
    build_card_auxiliary_text,
    build_card_caption,
    build_card_progress_bar,
    build_centered_progress_bar,
    build_centered_quiz_prompt_text,
    build_progress_bar_markup,
    build_quiz_auxiliary_text,
    build_quiz_progress_bar,
    build_quiz_prompt_text,
    build_quote_block,
    build_section_title,
    normalize_phonetic,
    pick_single_example,
    prepend_progress_bar_to_prompt_text,
)
from app.reference.labels import translate_part_of_speech_label


def test_build_quote_block_wraps_examples() -> None:
    result = build_quote_block(["Example one.", "Example two."])

    assert "<blockquote>" in result
    assert "Example one." in result
    assert "Example two." in result


def test_build_quote_block_returns_empty_without_examples() -> None:
    assert build_quote_block(["", "  "]) == ""


def test_build_fill_in_gap_example_replaces_target_word() -> None:
    result = build_fill_in_gap_example("learn", ["We learn every day."])

    assert "_____" in result
    assert "learn" not in result.lower()


def test_build_fill_in_gap_example_replaces_inflected_target_word() -> None:
    result = build_fill_in_gap_example("pace", ["She kept pacing across the narrow room."])

    assert result == "She kept _____ across the narrow room."


def test_build_fill_in_gap_example_accepts_to_prefixed_input_and_silent_e_past() -> None:
    result = build_fill_in_gap_example("to pause", ["She paused briefly before answering the question."])

    assert result == "She _____ briefly before answering the question."


def test_build_fill_in_gap_example_accepts_to_prefixed_phrasal_verb_input() -> None:
    result = build_fill_in_gap_example("to check in", ["Please check in before the morning meeting starts."])

    assert result == "Please _____ before the morning meeting starts."


def test_build_fill_in_gap_example_handles_separable_phrasal_verb() -> None:
    result = build_fill_in_gap_example("to let in on", ["Please let me in on the final plan."])

    assert result == "Please _____ the final plan."


def test_build_fill_in_gap_example_handles_object_placeholders() -> None:
    assert build_fill_in_gap_example("play with smb", ["I play with Tom after school."]) == "I _____ after school."
    assert build_fill_in_gap_example("play with somebody", ["I played with Tom after school."]) == (
        "I _____ after school."
    )
    assert build_fill_in_gap_example("ask smb to do smth", ["She asked Tom to bring tea after lunch."]) == (
        "She _____ after lunch."
    )


def test_build_fill_in_gap_example_keeps_sentence_when_no_match_is_found() -> None:
    result = build_fill_in_gap_example("pace", ["This sentence mentions nothing relevant."])

    assert result == "This sentence mentions nothing relevant."


def test_build_fill_in_gap_example_ignores_blank_examples_and_falls_back_to_gap() -> None:
    assert build_fill_in_gap_example("learn", ["  ", "We study daily."]) == "We study daily."
    assert build_fill_in_gap_example("learn", ["  "]) == "_____"


def test_build_fill_in_gap_example_replaces_irregular_plural_forms() -> None:
    assert build_fill_in_gap_example("criterion", ["We use several criteria to evaluate the projects."]) == (
        "We use several _____ to evaluate the projects."
    )
    assert build_fill_in_gap_example("calf", ["The boots were tight around her calves."]) == (
        "The boots were tight around her _____."
    )
    assert build_fill_in_gap_example("shelf", ["We need to put up some new shelves."]) == (
        "We need to put up some new _____."
    )
    assert build_fill_in_gap_example("gentleman", ["Ladies and gentlemen, welcome to the show."]) == (
        "Ladies and _____, welcome to the show."
    )


def test_build_marks_uses_checks_and_crosses() -> None:
    assert build_marks(2, 4) == "✓✓✗✗"


def test_build_deterministic_options_keeps_correct_answer_and_is_stable() -> None:
    first = build_deterministic_options("seed", "correct", ["a", "b", "c", "d"])
    second = build_deterministic_options("seed", "correct", ["a", "b", "c", "d"])

    assert first == second
    assert "correct" in first
    assert len(first) == 4


def test_build_deterministic_options_supports_three_answers() -> None:
    result = build_deterministic_options("seed", "correct", ["a", "b", "c", "d"], max_options=3)

    assert "correct" in result
    assert len(result) == 3


def test_build_deterministic_options_deduplicates_distractors() -> None:
    result = build_deterministic_options("seed", "correct", ["a", "a", "correct", "b"], max_options=3)

    assert len(result) == 3
    assert sorted(result) == ["a", "b", "correct"]


def test_build_quiz_progress_metadata_helpers() -> None:
    assert build_quiz_progress_title("uk", 2, 5) == "Слово 2 із 5"
    assert build_quiz_progress_counts([], 0) == (1, 1, 0, 0)
    assert build_quiz_progress_counts([11, 12, 11], 2) == (1, 2, 1, 1)
    assert build_quiz_button_row_widths(3) == [1, 1, 1, 1]
    assert build_quiz_button_row_widths(4) == [2, 2, 1]
    assert build_quiz_error_count({"gap_attempts": -1}, "gap") == 0
    assert build_quiz_error_count({"gap_attempts": 2}, "gap", current_attempts=1) == 1


def test_build_centered_progress_bar_centers_short_sequences() -> None:
    assert build_centered_progress_bar(["●", "○", "○"], total_slots=7) == "[⋯⋯●○○⋯⋯]"


def test_build_centered_progress_bar_wraps_long_sequences_to_twenty_slot_rows() -> None:
    assert build_centered_progress_bar(["○"] * 30, total_slots=30) == (
        "[○○○○○○○○○○○○○○○○○○○○]\n"
        "[⋯⋯⋯⋯⋯○○○○○○○○○○⋯⋯⋯⋯⋯]"
    )
    assert build_centered_progress_bar(["○"] * 40, total_slots=40) == (
        "[○○○○○○○○○○○○○○○○○○○○]\n"
        "[○○○○○○○○○○○○○○○○○○○○]"
    )


def test_build_card_progress_bar_marks_current_position() -> None:
    assert build_card_progress_bar(2, 4, total_slots=7) == "[⋯✓●○○⋯⋯]"


def test_build_card_progress_bar_uses_word_count_as_total_slots() -> None:
    assert build_card_progress_bar(21, 30) == (
        "[✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓]\n"
        "[⋯⋯⋯⋯⋯●○○○○○○○○○⋯⋯⋯⋯⋯]"
    )


def test_build_quiz_progress_bar_marks_current_and_errors() -> None:
    session_words_by_id = {
        11: {"en_uk_attempts": 1, "en_uk_correct": True},
        12: {"en_uk_attempts": 1, "en_uk_correct": False},
        13: {"en_uk_attempts": 0, "en_uk_correct": False},
    }

    assert build_quiz_progress_bar([11, 12, 13, 12], 3, session_words_by_id, "en_uk", total_slots=7) == "[⋯⋯✓●○⋯⋯]"


def test_build_quiz_progress_bar_handles_empty_and_error_states() -> None:
    session_words_by_id = {
        11: {"en_uk_attempts": 1, "en_uk_correct": True},
        12: {"en_uk_attempts": 1, "en_uk_correct": False},
        13: {"en_uk_attempts": 0, "en_uk_correct": False},
    }

    assert build_quiz_progress_bar([], 0, {}, "en_uk", total_slots=5) == "[⋯⋯●⋯⋯]"
    assert build_quiz_progress_bar([11, 12, 13], 2, session_words_by_id, "en_uk", total_slots=5) == "[⋯✓✗●⋯]"


def test_build_progress_bar_markup_uses_nonbreaking_spaces() -> None:
    assert build_progress_bar_markup("[  ●○○  ]") == "[\u00A0\u00A0●○○\u00A0\u00A0]"


def test_build_centered_quiz_prompt_text_centers_short_values() -> None:
    result = build_centered_quiz_prompt_text("pick out")

    assert result.startswith("\u2060\n\n\n<b>")
    assert result.endswith("</b>\n\n\n\u2060")
    assert "pick out" in result
    assert "\u2060" in result
    assert "\u2007" in result


def test_build_centered_quiz_prompt_text_keeps_long_values_as_is() -> None:
    result = build_centered_quiz_prompt_text("Choose the right answer before time runs out.")

    assert result.startswith("\u2060\n\n\n<b>")
    assert result.endswith("</b>\n\n\n\u2060")
    assert "Choose the right answer before time runs out." in result
    assert "\u2007" not in result


def test_build_quiz_prompt_text_uses_joiner_for_blank_prompt() -> None:
    result = build_quiz_prompt_text("   ")

    assert result.startswith("\u2060\n\n\n<b>\u2060</b>")


def test_build_quiz_prompt_text_keeps_word_left_aligned_and_appends_progress() -> None:
    result = build_quiz_prompt_text("pick out", progress_bar="[  ●○○  ]")

    assert result.startswith("[\u00A0\u00A0●○○\u00A0\u00A0]\n\n\n<b>pick out</b>")
    assert result.endswith("</b>\n\n\n\u2060")
    assert "\u2007" not in result


def test_prepend_progress_bar_to_prompt_text_adds_progress_header() -> None:
    result = prepend_progress_bar_to_prompt_text("<b>prompt</b>", progress_bar="[  ●  ]")

    assert result == "[\u00A0\u00A0●\u00A0\u00A0]\n\n\n<b>prompt</b>"


def test_build_section_title_escapes_title() -> None:
    assert build_section_title("A < B") == "<i>A &lt; B</i>\n────────────"


def test_build_card_auxiliary_text_keeps_progress_below_hint() -> None:
    result = build_card_auxiliary_text("uk", selected_words_count=20, progress_bar="[  ●○○  ]")

    assert result.startswith("Підказка:")
    assert "Вибрано" not in result
    assert "\n\n\n[\u00A0\u00A0●○○\u00A0\u00A0]" in result


def test_build_quiz_auxiliary_text_keeps_progress_below_hint_without_error_counter() -> None:
    result = build_quiz_auxiliary_text(
        "uk",
        stage_title="Вправа 1/3 - оберіть правильний український переклад",
        progress_bar="[  ●○○  ]",
        current_position=4,
        total_count=20,
        total_errors=2,
        repeat_progress_current=1,
        repeat_progress_total=2,
    )

    assert result.startswith("Підказка:")
    assert "[\u00A0\u00A0●○○\u00A0\u00A0]" not in result
    assert "Слово " not in result
    assert "Помил" not in result


def test_build_card_caption_truncates_examples_to_safe_length() -> None:
    caption = build_card_caption(
        locale="uk",
        word="abandon",
        parts_of_speech=["verb", "phrasal verb"],
        phonetic="əˈbændən",
        translation="відмовитися",
        examples=[
            "The baby had been abandoned by its mother.",
            "People often simply abandon their pets when they go abroad.",
            "We have been abandoned to our fate, said one resident.",
            "The study showed a deep fear among the elderly of being abandoned to the care of strangers.",
        ],
        categories=["actions", "common"],
        progress_bar="[  ●○○  ]",
    )

    assert len(caption) <= 900
    assert "<b>abandon</b>" in caption
    assert "<b>abandon</b> <i>(дієслово, фразове дієслово)</i>" in caption
    assert "[əˈbændən]" in caption
    assert "відмовитися\n\n<blockquote>" in caption
    assert "Категорії: Дії, Поширене" in caption
    assert "[\u00A0\u00A0●○○\u00A0\u00A0]" in caption
    assert caption.count("<blockquote>") == 1


def test_build_card_caption_handles_without_examples_or_tail() -> None:
    caption = build_card_caption(
        locale="uk",
        word="plain",
        parts_of_speech=[],
        phonetic="",
        translation="простий",
        examples=[],
    )

    assert caption == "<b>plain</b>\n[]\nпростий"


def test_build_card_caption_drops_long_example_without_tail() -> None:
    caption = build_card_caption(
        locale="uk",
        word="plain",
        parts_of_speech=[],
        phonetic="",
        translation="простий",
        examples=["Very long. " * 200],
    )

    assert caption == "<b>plain</b>\n[]\nпростий"


def test_pick_single_example_returns_one_stable_example() -> None:
    first = pick_single_example("seed", ["one", "two", "three"])
    second = pick_single_example("seed", ["one", "two", "three"])

    assert first == second
    assert len(first) == 1


def test_pick_single_example_returns_empty_without_examples() -> None:
    assert pick_single_example("seed", ["", "  "]) == []


def test_normalize_phonetic_strips_wrapping_slashes() -> None:
    assert normalize_phonetic("/test/") == "test"
    assert normalize_phonetic(None) == "—"
    assert normalize_phonetic(" plain ") == "plain"


def test_build_centered_progress_bar_handles_empty_and_full_sequences() -> None:
    assert build_centered_progress_bar([], total_slots=3) == "[⋯○⋯]"
    assert build_centered_progress_bar(["✓", "●", "○", "✗"], total_slots=3) == "[✓●○]"


def test_translate_part_of_speech_label_falls_back_for_unknown_value() -> None:
    assert translate_part_of_speech_label("uk", "rare-pos") == "rare-pos"


def test_split_translation_variants_splits_and_deduplicates() -> None:
    assert split_translation_variants("через, по той бік, через") == ["через", "по той бік"]
    assert split_translation_variants(None) == []


def test_resolve_translation_for_locale_uses_locale_field_with_uk_fallback() -> None:
    payload = {
        "translation_uk": "через, по той бік",
        "translation_ru": "через, по ту сторону",
        "translation_pl": "przez, po drugiej stronie",
    }

    assert resolve_translation_for_locale("ru", payload) == "через, по ту сторону"
    assert resolve_translation_for_locale("pl", payload) == "przez, po drugiej stronie"
    assert resolve_translation_for_locale("de", payload) == "через, по той бік"
    assert resolve_translation_for_locale("", {"translation_uk": "  "}) == ""


def test_select_translation_variant_is_stable_for_seed() -> None:
    payload = {"translation_uk": "через, по той бік", "translation_ru": None, "translation_pl": None}

    first = select_translation_variant("uk", payload, seed="seed")
    second = select_translation_variant("uk", payload, seed="seed")

    assert first == second
    assert first in {"через", "по той бік"}


def test_select_translation_variant_returns_empty_without_translation() -> None:
    assert select_translation_variant("uk", {}, seed="seed") == ""


def test_build_quiz_payload_builds_en_uk_translation_options() -> None:
    session_word = {
        "session_word_id": 42,
        "word": "across",
        "translation_uk": "через, по той бік",
        "translation_ru": None,
        "translation_pl": None,
        "examples_json": [],
    }
    distractors = [
        {"word": "around", "translation_uk": "навколо", "translation_ru": None, "translation_pl": None},
        {"word": "inside", "translation_uk": "всередині", "translation_ru": None, "translation_pl": None},
    ]

    payload = build_quiz_payload(stage="quiz_en_uk", session_word=session_word, distractors=distractors, locale="uk")

    assert payload.exercise_type == "en_uk"
    assert payload.prompt_text == "across"
    assert payload.correct_answer in {"через", "по той бік"}
    assert payload.correct_answer in payload.options
    assert len(payload.options) == 3


def test_build_quiz_payload_skips_distractors_with_overlapping_translations() -> None:
    session_word = {
        "session_word_id": 45,
        "word": "warehouse",
        "translation_uk": "склад, сховище",
        "translation_ru": None,
        "translation_pl": None,
        "examples_json": [],
    }
    distractors = [
        {"word": "storage", "translation_uk": "склад", "translation_ru": None, "translation_pl": None},
        {"word": "office", "translation_uk": "офіс", "translation_ru": None, "translation_pl": None},
        {"word": "harbor", "translation_uk": "гавань", "translation_ru": None, "translation_pl": None},
    ]

    payload = build_quiz_payload(stage="quiz_en_uk", session_word=session_word, distractors=distractors, locale="uk")

    assert "склад" not in [option for option in payload.options if option != payload.correct_answer]
    assert "офіс" in payload.options
    assert "гавань" in payload.options


def test_build_quiz_payload_builds_uk_en_word_options() -> None:
    session_word = {
        "session_word_id": 43,
        "word": "across",
        "translation_uk": "через",
        "translation_ru": None,
        "translation_pl": None,
        "examples_json": [],
    }
    distractors = [
        {"word": "around", "translation_uk": "навколо"},
        {"word": "inside", "translation_uk": "всередині"},
    ]

    payload = build_quiz_payload(stage="quiz_uk_en", session_word=session_word, distractors=distractors, locale="uk")

    assert payload.exercise_type == "uk_en"
    assert payload.prompt_text == "через"
    assert payload.correct_answer == "across"
    assert payload.options == build_deterministic_options(
        "quiz_uk_en:43",
        "across",
        ["around", "inside"],
        max_options=3,
    )


def test_build_quiz_payload_skips_word_distractors_with_overlapping_translations() -> None:
    session_word = {
        "session_word_id": 46,
        "word": "warehouse",
        "translation_uk": "склад",
        "translation_ru": None,
        "translation_pl": None,
        "examples_json": [],
    }
    distractors = [
        {"word": "storage", "translation_uk": "склад"},
        {"word": "office", "translation_uk": "офіс"},
        {"word": "harbor", "translation_uk": "гавань"},
    ]

    payload = build_quiz_payload(stage="quiz_uk_en", session_word=session_word, distractors=distractors, locale="uk")

    assert "storage" not in payload.options
    assert "office" in payload.options
    assert "harbor" in payload.options


def test_build_quiz_payload_builds_gap_prompt() -> None:
    session_word = {
        "session_word_id": 44,
        "word": "learn",
        "translation_uk": "вчити",
        "translation_ru": None,
        "translation_pl": None,
        "examples_json": ["We learn every day."],
    }
    distractors = [{"word": "teach"}, {"word": "read"}, {"word": "write"}]

    payload = build_quiz_payload(stage="quiz_gap", session_word=session_word, distractors=distractors, locale="uk")

    assert payload.exercise_type == "gap"
    assert "_____" in payload.prompt_text
    assert payload.correct_answer == "learn"
    assert payload.correct_answer in payload.options
