from __future__ import annotations

from typing import Any

from app.contracts import ButtonModel, ScreenModel
from app.i18n import translate
from app.reference.learning_flow import READY_STAGE_INTRO_I18N_KEYS


def build_ready_screen(
    session: dict[str, Any],
    locale: str,
    *,
    paused: bool = False,
    notice: str | None = None,
) -> ScreenModel:
    stage = session["current_stage"]
    intro_text = translate(locale, READY_STAGE_INTRO_I18N_KEYS[stage])
    lines = [translate(locale, "ready_pause") if paused else intro_text, translate(locale, "ready_prompt")]
    return ScreenModel(
        screen_id=stage,
        text="\n\n".join(lines),
        buttons=[
            ButtonModel(action=f"s:{session['id']}:ready:{stage}:yes", text=translate(locale, "ready_yes")),
            ButtonModel(action=f"s:{session['id']}:ready:{stage}:no", text=translate(locale, "ready_no")),
        ],
        keyboard_type="inline",
        clear_chat=bool(session.get("metadata", {}).get("clear_previous_card")),
        notice_text=notice,
    )
