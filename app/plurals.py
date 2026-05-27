from __future__ import annotations

from dataclasses import dataclass

DEFAULT_PLURAL_LOCALE = "uk"
SUPPORTED_PLURAL_LOCALES = frozenset({"uk", "ru", "pl"})


@dataclass(frozen=True)
class PluralForms:
    one: str
    few: str
    many: str


EXERCISE_ERROR_FORMS = {
    "uk": PluralForms(one="помилка", few="помилки", many="помилок"),
    "ru": PluralForms(one="ошибка", few="ошибки", many="ошибок"),
    "pl": PluralForms(one="błąd", few="błędy", many="błędów"),
}
WORD_FORMS = {
    "uk": PluralForms(one="слово", few="слова", many="слів"),
    "ru": PluralForms(one="слово", few="слова", many="слов"),
    "pl": PluralForms(one="słowo", few="słowa", many="słów"),
}
IMPORT_ITEM_FORMS = {
    "uk": PluralForms(one="елемент", few="елементи", many="елементів"),
    "ru": PluralForms(one="элемент", few="элемента", many="элементов"),
    "pl": PluralForms(one="element", few="elementy", many="elementów"),
}


def resolve_plural_locale(locale: str | None) -> str:
    if locale is None:
        return DEFAULT_PLURAL_LOCALE
    normalized = locale.strip().lower().replace("_", "-")
    if not normalized:
        return DEFAULT_PLURAL_LOCALE
    base_locale = normalized.split("-", 1)[0]
    if base_locale in SUPPORTED_PLURAL_LOCALES:
        return base_locale
    return DEFAULT_PLURAL_LOCALE


def select_plural_form(locale: str | None, count: int, forms: PluralForms) -> str:
    normalized_locale = resolve_plural_locale(locale)
    absolute_count = abs(int(count))
    last_two_digits = absolute_count % 100
    last_digit = absolute_count % 10

    if normalized_locale == "pl":
        if absolute_count == 1:
            return forms.one
        if last_digit in {2, 3, 4} and last_two_digits not in {12, 13, 14}:
            return forms.few
        return forms.many

    if last_digit == 1 and last_two_digits != 11:
        return forms.one
    if last_digit in {2, 3, 4} and last_two_digits not in {12, 13, 14}:
        return forms.few
    return forms.many


def format_counted_noun(locale: str | None, count: int, forms: PluralForms) -> str:
    return f"{count} {select_plural_form(locale, count, forms)}"


def format_exercise_error_count(locale: str | None, count: int) -> str:
    forms = EXERCISE_ERROR_FORMS[resolve_plural_locale(locale)]
    return format_counted_noun(locale, count, forms)


def format_word_count(locale: str | None, count: int) -> str:
    forms = WORD_FORMS[resolve_plural_locale(locale)]
    return format_counted_noun(locale, count, forms)


def format_import_item_count(locale: str | None, count: int) -> str:
    forms = IMPORT_ITEM_FORMS[resolve_plural_locale(locale)]
    return format_counted_noun(locale, count, forms)
