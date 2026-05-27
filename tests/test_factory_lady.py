from __future__ import annotations

from tests.factory_lady import FactoryLady


def test_factory_lady_creates_word_with_nested_translation_override() -> None:
    factory = FactoryLady()

    word = factory.create_word(
        word="abandon",
        translation_uk={"text": "покидати"},
    )

    assert word["word"] == "abandon"
    assert word["translation_uk"]["text"] == "покидати"


def test_factory_lady_generates_unique_users() -> None:
    factory = FactoryLady()

    first = factory.create_user()
    second = factory.create_user()

    assert first["telegram_user_id"] != second["telegram_user_id"]
