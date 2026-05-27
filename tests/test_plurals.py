from __future__ import annotations

from app.plurals import (
    PluralForms,
    format_exercise_error_count,
    format_import_item_count,
    format_word_count,
    resolve_plural_locale,
    select_plural_form,
)


def test_resolve_plural_locale_normalizes_supported_language_codes() -> None:
    assert resolve_plural_locale("uk-UA") == "uk"
    assert resolve_plural_locale("ru_RU") == "ru"
    assert resolve_plural_locale("pl-PL") == "pl"


def test_resolve_plural_locale_falls_back_to_uk_for_unsupported_language() -> None:
    assert resolve_plural_locale("en-US") == "uk"


def test_select_plural_form_supports_ukrainian_and_russian_rules() -> None:
    forms = PluralForms(one="one", few="few", many="many")

    assert select_plural_form("uk", 1, forms) == "one"
    assert select_plural_form("uk", 2, forms) == "few"
    assert select_plural_form("uk", 5, forms) == "many"
    assert select_plural_form("ru", 21, forms) == "one"
    assert select_plural_form("ru", 24, forms) == "few"
    assert select_plural_form("ru", 11, forms) == "many"


def test_select_plural_form_supports_polish_rules() -> None:
    forms = PluralForms(one="one", few="few", many="many")

    assert select_plural_form("pl", 1, forms) == "one"
    assert select_plural_form("pl", 2, forms) == "few"
    assert select_plural_form("pl", 12, forms) == "many"
    assert select_plural_form("pl", 25, forms) == "many"


def test_format_exercise_error_count_uses_locale_specific_forms() -> None:
    assert format_exercise_error_count("uk", 2) == "2 помилки"
    assert format_exercise_error_count("ru", 5) == "5 ошибок"
    assert format_exercise_error_count("pl", 1) == "1 błąd"


def test_format_word_count_uses_locale_specific_forms() -> None:
    assert format_word_count("uk", 1) == "1 слово"
    assert format_word_count("uk", 2) == "2 слова"
    assert format_word_count("ru", 5) == "5 слов"
    assert format_word_count("pl", 3) == "3 słowa"


def test_format_import_item_count_uses_generic_item_forms() -> None:
    assert format_import_item_count("uk", 1) == "1 елемент"
    assert format_import_item_count("uk", 3) == "3 елементи"
    assert format_import_item_count("ru", 5) == "5 элементов"
    assert format_import_item_count("pl", 2) == "2 elementy"
