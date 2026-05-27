from __future__ import annotations

from typing import Any

from app.application.client_learning.resume import (
    can_resume_from_telegram_menu,
    get_menu_resume_button_text,
)
from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.screen_delivery_policy import with_screen_delivery_policy


def build_main_menu_screen(
    *,
    locale: str,
    active_session: dict[str, Any] | None,
    notice: str | None = None,
    clear_chat: bool = False,
    force_resend: bool = False,
) -> ScreenModel:
    lines = [translate(locale, "menu_learning_hint")]
    if notice:
        lines.insert(0, notice)

    buttons = [
        ButtonModel(action="m:s", text=translate(locale, "menu_start_learning")),
    ]
    if can_resume_from_telegram_menu(active_session):
        buttons.insert(
            1,
            ButtonModel(
                action="m:r",
                text=get_menu_resume_button_text(locale, active_session),
            ),
        )
    screen = ScreenModel(
        screen_id="menu",
        text="\n\n".join(lines),
        buttons=buttons,
        keyboard_type="inline",
        clear_chat=clear_chat,
        metadata={
            "buttons_per_row": 1,
        },
    )
    return with_screen_delivery_policy(
        screen,
        force_resend=force_resend,
        auxiliary_after_active=True,
        auxiliary_message_text=translate(locale, "menu_settings_hint"),
        auxiliary_message_buttons=[
            ButtonModel(action="m:settings", text=translate(locale, "menu_settings_button"))
        ],
    )
