from app.contracts import ButtonModel, ScreenModel
from app.screen_delivery_policy import (
    read_screen_delivery_policy,
    with_close_to_menu_delivery,
    with_menu_restore_delivery,
    with_screen_delivery_policy,
)


def test_read_screen_delivery_policy_normalizes_delivery_metadata() -> None:
    screen = ScreenModel(
        screen_id="menu",
        text="Menu",
        clear_chat=True,
        metadata={
            "force_resend": False,
            "auxiliary_after_active": True,
            "auxiliary_message_text": " Hint ",
            "auxiliary_message_buttons": [
                ButtonModel(action="m:settings", text="Settings").model_dump(),
                {"action": "bad"},
                "skip",
            ],
            "intro_message_text": "Intro",
            "delete_after_hours": 24,
            "auto_advance_after_ms": 1500,
            "auto_return_after_ms": 5000,
            "next_action": "m:menu",
        },
    )

    policy = read_screen_delivery_policy(screen)

    assert policy.force_resend is True
    assert policy.clear_chat is True
    assert policy.auxiliary_after_active is True
    assert policy.auxiliary_message_text == " Hint "
    assert [button.action for button in policy.auxiliary_message_buttons] == ["m:settings"]
    assert policy.intro_message_text == "Intro"
    assert policy.delete_after_hours == 24
    assert policy.auto_advance_after_ms == 1500
    assert policy.auto_return_after_ms == 5000
    assert policy.next_action == "m:menu"


def test_delivery_policy_builders_keep_runtime_flags_in_one_metadata_block() -> None:
    screen = with_screen_delivery_policy(
        ScreenModel(screen_id="s", text="t"),
        force_resend=True,
        auxiliary_message_buttons=[ButtonModel(action="m:menu", text="Menu")],
        next_action="m:menu",
    )

    assert screen.metadata["force_resend"] is True
    assert screen.metadata["auxiliary_message_buttons"] == [{"action": "m:menu", "text": "Menu", "url": None}]
    assert screen.metadata["next_action"] == "m:menu"


def test_close_to_menu_and_restore_delivery_have_dedicated_helpers() -> None:
    close_screen = with_close_to_menu_delivery(ScreenModel(screen_id="menu", text="Menu"))
    restore_screen = with_menu_restore_delivery(
        ScreenModel(
            screen_id="menu",
            text="Menu",
            metadata={
                "auxiliary_after_active": True,
                "auxiliary_message_text": "hint",
                "auxiliary_message_buttons": [{"action": "m:settings", "text": "Settings"}],
            },
        )
    )

    assert close_screen.metadata == {"force_resend": True, "delete_cached_active_screen": True}
    assert restore_screen.metadata == {
        "auxiliary_after_active": False,
        "auxiliary_message_text": "hint",
        "auxiliary_message_buttons": [{"action": "m:settings", "text": "Settings"}],
        "prefer_edit_active": True,
    }
