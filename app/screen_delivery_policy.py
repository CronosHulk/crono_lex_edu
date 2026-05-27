from __future__ import annotations

from dataclasses import dataclass

from app.contracts import ButtonModel, ScreenModel


@dataclass(frozen=True)
class ScreenDeliveryPolicy:
    force_resend: bool
    clear_chat: bool
    delete_current_message_only: bool
    delete_cached_active_screen: bool
    prefer_edit_active: bool
    documents_only: bool
    auxiliary_after_active: bool
    auxiliary_message_text: str | None
    auxiliary_message_buttons: list[ButtonModel]
    intro_message_text: str | None
    delete_after_hours: int | None
    auto_advance_after_ms: int | None
    auto_return_after_ms: int | None
    next_action: str | None


def read_screen_delivery_policy(screen: ScreenModel) -> ScreenDeliveryPolicy:
    metadata = screen.metadata
    force_resend = bool(metadata.get("force_resend")) or screen.clear_chat
    return ScreenDeliveryPolicy(
        force_resend=force_resend,
        clear_chat=screen.clear_chat,
        delete_current_message_only=bool(metadata.get("delete_current_message_only")),
        delete_cached_active_screen=bool(metadata.get("delete_cached_active_screen")),
        prefer_edit_active=bool(metadata.get("prefer_edit_active")),
        documents_only=bool(metadata.get("documents_only")),
        auxiliary_after_active=bool(metadata.get("auxiliary_after_active")),
        auxiliary_message_text=_read_non_blank_text(metadata.get("auxiliary_message_text")),
        auxiliary_message_buttons=_read_buttons(metadata.get("auxiliary_message_buttons")),
        intro_message_text=_read_non_blank_text(metadata.get("intro_message_text")),
        delete_after_hours=_read_non_negative_int(metadata.get("delete_after_hours")),
        auto_advance_after_ms=_read_positive_int(metadata.get("auto_advance_after_ms")),
        auto_return_after_ms=_read_positive_int(metadata.get("auto_return_after_ms")),
        next_action=_read_non_blank_text(metadata.get("next_action")),
    )


def with_screen_delivery_policy(
    screen: ScreenModel,
    *,
    force_resend: bool | None = None,
    delete_current_message_only: bool | None = None,
    delete_cached_active_screen: bool | None = None,
    prefer_edit_active: bool | None = None,
    documents_only: bool | None = None,
    auxiliary_after_active: bool | None = None,
    auxiliary_message_text: str | None = None,
    auxiliary_message_buttons: list[ButtonModel] | None = None,
    intro_message_text: str | None = None,
    delete_after_hours: int | None = None,
    auto_advance_after_ms: int | None = None,
    auto_return_after_ms: int | None = None,
    next_action: str | None = None,
) -> ScreenModel:
    metadata = dict(screen.metadata)
    _set_if_not_none(metadata, "force_resend", force_resend)
    _set_if_not_none(metadata, "delete_current_message_only", delete_current_message_only)
    _set_if_not_none(metadata, "delete_cached_active_screen", delete_cached_active_screen)
    _set_if_not_none(metadata, "prefer_edit_active", prefer_edit_active)
    _set_if_not_none(metadata, "documents_only", documents_only)
    _set_if_not_none(metadata, "auxiliary_after_active", auxiliary_after_active)
    _set_if_not_none(metadata, "auxiliary_message_text", auxiliary_message_text)
    if auxiliary_message_buttons is not None:
        metadata["auxiliary_message_buttons"] = [
            button.model_dump() if isinstance(button, ButtonModel) else button
            for button in auxiliary_message_buttons
        ]
    _set_if_not_none(metadata, "intro_message_text", intro_message_text)
    _set_if_not_none(metadata, "delete_after_hours", delete_after_hours)
    _set_if_not_none(metadata, "auto_advance_after_ms", auto_advance_after_ms)
    _set_if_not_none(metadata, "auto_return_after_ms", auto_return_after_ms)
    _set_if_not_none(metadata, "next_action", next_action)
    return screen.model_copy(update={"metadata": metadata})


def with_close_to_menu_delivery(screen: ScreenModel) -> ScreenModel:
    return with_screen_delivery_policy(
        screen,
        force_resend=True,
        delete_cached_active_screen=True,
    )


def with_menu_restore_delivery(screen: ScreenModel) -> ScreenModel:
    metadata = dict(screen.metadata)
    metadata["prefer_edit_active"] = True
    metadata["auxiliary_after_active"] = False
    return screen.model_copy(update={"metadata": metadata})


def with_delete_after_hours(screen: ScreenModel, hours: int) -> ScreenModel:
    return with_screen_delivery_policy(screen, delete_after_hours=hours)


def with_documents_only_delivery(screen: ScreenModel) -> ScreenModel:
    return with_screen_delivery_policy(screen, documents_only=True)


def _read_non_blank_text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _read_non_negative_int(value: object) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def _read_positive_int(value: object) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _read_buttons(value: object) -> list[ButtonModel]:
    if not isinstance(value, list):
        return []
    buttons: list[ButtonModel] = []
    for raw_button in value:
        if isinstance(raw_button, ButtonModel):
            buttons.append(raw_button)
            continue
        if not isinstance(raw_button, dict):
            continue
        try:
            buttons.append(ButtonModel.model_validate(raw_button))
        except ValueError:
            continue
    return buttons


def _set_if_not_none(metadata: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        metadata[key] = value
