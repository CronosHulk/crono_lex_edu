from __future__ import annotations

import json

from word_base.fix_normolized_clean_words_translations_openai import (
    OpenAITranslationClient,
    base_word_without_to,
    build_prompt,
    build_sibling_context,
    validate_translations_row,
)


def test_base_word_without_to_strips_infinitive_prefix() -> None:
    assert base_word_without_to("to trace") == "trace"
    assert base_word_without_to("trace") == "trace"


def test_build_sibling_context_groups_entries_by_base_word() -> None:
    entries = [
        {"source_ref": "trace__noun", "word": "trace", "parts_of_speech": ["noun"], "translation_uk": "слід", "translation_ru": "след", "translation_pl": "ślad", "examples": ["There was a trace of smoke in the hall."]},
        {"source_ref": "to-trace__verb", "word": "to trace", "parts_of_speech": ["verb"], "translation_uk": "відстежувати", "translation_ru": "отслеживать", "translation_pl": "śledzić", "examples": ["Police traced the phone signal quickly."]},
    ]

    context = build_sibling_context(entries)

    assert "trace" in context
    assert [item["source_ref"] for item in context["trace"]] == ["trace__noun", "to-trace__verb"]


def test_build_prompt_includes_sibling_entries_for_disambiguation() -> None:
    batch = [
        {
            "source_ref": "trace__noun",
            "word": "trace",
            "parts_of_speech": ["noun"],
            "level_code": "B2",
            "translation_uk": "відстежувати, слід",
            "translation_ru": "отслеживать, след",
            "translation_pl": "śledzić, ślad",
            "examples": ["There was a trace of smoke in the hall."],
        }
    ]
    sibling_context = {
        "trace": [
            {
                "source_ref": "trace__noun",
                "word": "trace",
                "part_of_speech": "noun",
                "translation_uk": "слід",
                "translation_ru": "след",
                "translation_pl": "ślad",
                "example": "There was a trace of smoke in the hall.",
            },
            {
                "source_ref": "to-trace__verb",
                "word": "to trace",
                "part_of_speech": "verb",
                "translation_uk": "відстежувати",
                "translation_ru": "отслеживать",
                "translation_pl": "śledzić",
                "example": "Police traced the phone signal quickly.",
            },
        ]
    }

    prompt = json.loads(build_prompt(batch, sibling_context=sibling_context, target_langs=["UK", "RU", "PL"]))

    assert prompt["items"][0]["base_word_without_to"] == "trace"
    assert prompt["items"][0]["sibling_entries"] == [
        {
            "source_ref": "to-trace__verb",
            "word": "to trace",
            "part_of_speech": "verb",
            "translation_uk": "відстежувати",
            "translation_ru": "отслеживать",
            "translation_pl": "śledzić",
            "example": "Police traced the phone signal quickly.",
        }
    ]


def test_openai_translation_client_extract_items_parses_output_text_payload() -> None:
    client = OpenAITranslationClient(api_key="test", model="gpt-5.4-mini", api_url="https://api.openai.com/v1/responses")

    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "items": [
                                    {
                                        "source_ref": "trace__noun",
                                        "translation_uk": "слід",
                                        "translation_ru": "след",
                                        "translation_pl": "ślad",
                                    }
                                ]
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            }
        ]
    }

    assert client._extract_items(payload) == {
        "trace__noun": {
            "translation_uk": "слід",
            "translation_ru": "след",
            "translation_pl": "ślad",
        }
    }


def test_validate_translations_row_trims_and_validates_fields() -> None:
    assert validate_translations_row(
        "trace__noun",
        {
            "translation_uk": " слід ",
            "translation_ru": " след ",
            "translation_pl": " ślad ",
        },
    ) == {
        "translation_uk": "слід",
        "translation_ru": "след",
        "translation_pl": "ślad",
    }
