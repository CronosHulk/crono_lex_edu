from __future__ import annotations

from pathlib import Path

from app.bot_runtime.documents import (
    read_auxiliary_message_buttons,
    read_auxiliary_message_text,
    read_delete_after_hours,
    read_intro_message_text,
    read_screen_documents,
    resolve_document_path,
)
from app.contracts import DocumentAttachmentModel, ScreenModel


def test_read_auxiliary_message_text_accepts_only_non_blank_strings() -> None:
    assert read_auxiliary_message_text(ScreenModel(screen_id="s", text="t", metadata={"auxiliary_message_text": "hint"})) == "hint"
    assert read_auxiliary_message_text(ScreenModel(screen_id="s", text="t", metadata={"auxiliary_message_text": "  "})) is None
    assert read_auxiliary_message_text(ScreenModel(screen_id="s", text="t", metadata={"auxiliary_message_text": 123})) is None


def test_read_intro_message_text_accepts_only_non_blank_strings() -> None:
    assert read_intro_message_text(ScreenModel(screen_id="s", text="t", metadata={"intro_message_text": "hello"})) == "hello"
    assert read_intro_message_text(ScreenModel(screen_id="s", text="t", metadata={"intro_message_text": "  "})) is None
    assert read_intro_message_text(ScreenModel(screen_id="s", text="t", metadata={"intro_message_text": 123})) is None


def test_read_auxiliary_message_buttons_accepts_valid_button_payloads() -> None:
    buttons = read_auxiliary_message_buttons(
        ScreenModel(
            screen_id="s",
            text="t",
            metadata={
                "auxiliary_message_buttons": [
                    {"action": "m:settings", "text": "Settings"},
                    {"action": "broken"},
                    "not-a-button",
                ]
            },
        )
    )

    assert len(buttons) == 1
    assert buttons[0].action == "m:settings"
    assert buttons[0].text == "Settings"


def test_read_delete_after_hours_accepts_non_negative_ints() -> None:
    assert read_delete_after_hours(ScreenModel(screen_id="s", text="t", metadata={"delete_after_hours": 0})) == 0
    assert read_delete_after_hours(ScreenModel(screen_id="s", text="t", metadata={"delete_after_hours": 12})) == 12
    assert read_delete_after_hours(ScreenModel(screen_id="s", text="t", metadata={"delete_after_hours": -1})) is None
    assert read_delete_after_hours(ScreenModel(screen_id="s", text="t", metadata={"delete_after_hours": "12"})) is None


def test_read_screen_documents_filters_empty_documents_and_trims_values() -> None:
    payload = read_screen_documents(
        ScreenModel(
            screen_id="s",
            text="t",
            documents=[
                DocumentAttachmentModel(path=" runtime/report.txt ", filename=" report.txt ", caption="Report"),
                DocumentAttachmentModel(path=" ", filename="empty-path.txt"),
                DocumentAttachmentModel(path="runtime/no-filename.txt", filename=" "),
            ],
        )
    )

    assert payload == [{"path": "runtime/report.txt", "filename": "report.txt", "caption": "Report"}]


def test_resolve_document_path_keeps_absolute_and_resolves_relative(tmp_path: Path, monkeypatch) -> None:
    absolute_path = tmp_path / "report.txt"
    monkeypatch.chdir(tmp_path)

    assert resolve_document_path(str(absolute_path)) == absolute_path
    assert resolve_document_path("relative/report.txt") == (tmp_path / "relative/report.txt").resolve()
