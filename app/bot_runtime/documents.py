from __future__ import annotations

from pathlib import Path

from app.contracts import ButtonModel, ScreenModel
from app.screen_delivery_policy import read_screen_delivery_policy


def read_auxiliary_message_text(screen: ScreenModel) -> str | None:
    return read_screen_delivery_policy(screen).auxiliary_message_text


def read_intro_message_text(screen: ScreenModel) -> str | None:
    return read_screen_delivery_policy(screen).intro_message_text


def read_auxiliary_message_buttons(screen: ScreenModel) -> list[ButtonModel]:
    return read_screen_delivery_policy(screen).auxiliary_message_buttons


def read_delete_after_hours(screen: ScreenModel) -> int | None:
    return read_screen_delivery_policy(screen).delete_after_hours


def read_screen_documents(screen: ScreenModel) -> list[dict[str, str | None]]:
    documents: list[dict[str, str | None]] = []
    for document in screen.documents:
        path = str(document.path).strip()
        filename = str(document.filename).strip()
        if not path or not filename:
            continue
        documents.append(
            {
                "path": path,
                "filename": filename,
                "caption": document.caption,
            }
        )
    return documents


def resolve_document_path(document_path: str) -> Path:
    path = Path(document_path)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()
