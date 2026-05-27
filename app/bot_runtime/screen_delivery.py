from __future__ import annotations

from telegram import Update
from telegram.ext import Application, ContextTypes

from app.bot_api_client import BotApiClient
from app.bot_runtime.auxiliary_delivery import sync_auxiliary_screen_message
from app.bot_runtime.delivery import (
    ensure_reply_keyboard_removed,
    send_new_screen_message,
    try_edit_active_screen,
)
from app.bot_runtime.document_delivery import send_screen_documents
from app.bot_runtime.message_tracking import (
    clear_messages,
    is_sticky_import_report_screen_id,
    list_chat_tracked_messages,
    resolve_callback_active_screen_message,
    save_cleanup_deleted_result,
    sweep_chat_tracked_messages,
    track_sent_bot_message,
)
from app.bot_runtime.rendering import build_keyboard, build_screen_text
from app.bot_runtime.state import (
    ActiveScreenMessage,
    build_message_log_refs,
    get_active_screen_message,
    get_auxiliary_screen_message,
    read_int,
    save_active_screen_message,
)
from app.contracts import ScreenModel
from app.screen_delivery_policy import read_screen_delivery_policy

PUSH_NOTIFICATION_SCREEN_PREFIXES = ("reminder:",)


def resolve_primary_disable_notification(screen: ScreenModel, requested_disable_notification: bool) -> bool:
    if requested_disable_notification:
        return True
    return not screen.screen_id.startswith(PUSH_NOTIFICATION_SCREEN_PREFIXES)


async def render_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    screen: ScreenModel,
) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    application = getattr(context, "application", context)
    fallback_active_message = await resolve_callback_active_screen_message(
        update,
        context.user_data,
        application.bot_data.get("api_client"),
        getattr(update.effective_user, "id", None),
        chat.id,
    )
    await send_screen_to_chat(
        application,
        chat.id,
        screen,
        user_data=context.user_data,
        telegram_user_id=getattr(update.effective_user, "id", None),
        fallback_active_message=fallback_active_message,
    )


async def send_screen_to_chat(
    application: Application,
    chat_id: int,
    screen: ScreenModel,
    user_data: dict | None = None,
    telegram_user_id: int | None = None,
    disable_notification: bool = True,
    fallback_active_message: ActiveScreenMessage | None = None,
) -> None:
    api_client: BotApiClient | None = application.bot_data.get("api_client")
    policy = read_screen_delivery_policy(screen)
    primary_disable_notification = resolve_primary_disable_notification(screen, disable_notification)
    secondary_disable_notification = True
    await ensure_reply_keyboard_removed(application, chat_id, user_data)
    if policy.documents_only:
        active_message = fallback_active_message or get_active_screen_message(user_data)
        await sweep_chat_tracked_messages(
            application=application,
            api_client=api_client,
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            keep_messages=[active_message, get_auxiliary_screen_message(user_data)],
            user_data=user_data,
        )
        await send_screen_documents(
            application=application,
            chat_id=chat_id,
            screen=screen,
            user_data=user_data,
            telegram_user_id=telegram_user_id,
            disable_notification=secondary_disable_notification,
        )
        return
    if policy.delete_current_message_only:
        active_message = fallback_active_message or get_active_screen_message(user_data)
        cached_active_message = get_active_screen_message(user_data)
        messages_to_delete = [active_message] if active_message is not None else []
        if (
            policy.delete_cached_active_screen
            and cached_active_message is not None
            and cached_active_message.message_id not in {message.message_id for message in messages_to_delete}
        ):
            messages_to_delete.append(cached_active_message)
        if messages_to_delete:
            await clear_messages(
                chat_id,
                application,
                [message.message_id for message in messages_to_delete],
                build_message_log_refs(messages_to_delete),
            )
            if (
                user_data is not None
                and read_int(user_data.get("active_screen_message_id"))
                in {message.message_id for message in messages_to_delete}
            ):
                user_data["bot_message_ids"] = []
                user_data["bot_message_log_refs"] = []
                user_data["active_screen_message_id"] = None
                user_data["active_screen_message_log_id"] = None
                user_data["active_screen_has_audio"] = False
                user_data["active_screen_screen_id"] = None
        return
    keyboard = build_keyboard(screen)
    screen_text = build_screen_text(screen)
    intro_text = policy.intro_message_text
    auxiliary_text = policy.auxiliary_message_text
    auxiliary_buttons = policy.auxiliary_message_buttons
    auxiliary_after_active = policy.auxiliary_after_active
    auxiliary_message = get_auxiliary_screen_message(user_data)
    previous_message_ids = list((user_data or {}).get("bot_message_ids", []))
    previous_message_log_refs = list((user_data or {}).get("bot_message_log_refs", []))
    tracked_active_message = get_active_screen_message(user_data)
    active_message = fallback_active_message or tracked_active_message
    if policy.delete_cached_active_screen and tracked_active_message is not None:
        cleanup_message_ids = set(previous_message_ids)
        active_message_id = active_message.message_id if active_message is not None else None
        if tracked_active_message.message_id != active_message_id and tracked_active_message.message_id not in cleanup_message_ids:
            previous_message_ids.append(tracked_active_message.message_id)
            if tracked_active_message.message_log_id is not None:
                previous_message_log_refs.append(
                    {
                        "message_id": tracked_active_message.message_id,
                        "message_log_id": tracked_active_message.message_log_id,
                    }
                )
    if (
        active_message is None
        and policy.prefer_edit_active
        and api_client is not None
        and telegram_user_id is not None
    ):
        tracked_messages = await list_chat_tracked_messages(api_client, telegram_user_id, chat_id)
        active_message = max(
            tracked_messages,
            key=lambda message: (message.message_id, message.message_log_id or -1),
            default=None,
        )
    preserve_active_message_as_sticky = (
        active_message is not None
        and is_sticky_import_report_screen_id(active_message.screen_id)
        and not is_sticky_import_report_screen_id(screen.screen_id)
        and fallback_active_message is None
    )
    should_force_resend = policy.force_resend or (
        auxiliary_text is not None and auxiliary_message is None and active_message is not None
        and not auxiliary_after_active
    )
    if (
        fallback_active_message is not None
        and is_sticky_import_report_screen_id(fallback_active_message.screen_id)
        and not is_sticky_import_report_screen_id(screen.screen_id)
    ):
        should_force_resend = True
    if preserve_active_message_as_sticky:
        active_message = None
        previous_message_ids = [message_id for message_id in previous_message_ids if message_id != tracked_active_message.message_id]
        previous_message_log_refs = [
            item
            for item in previous_message_log_refs
            if item.get("message_id") != tracked_active_message.message_id
        ]

    if not auxiliary_after_active:
        await sync_auxiliary_screen_message(
            application=application,
            api_client=api_client,
            chat_id=chat_id,
            user_data=user_data,
            telegram_user_id=telegram_user_id,
            auxiliary_text=auxiliary_text,
            auxiliary_buttons=auxiliary_buttons,
            disable_notification=secondary_disable_notification,
        )
        auxiliary_message = get_auxiliary_screen_message(user_data)
    elif should_force_resend and auxiliary_message is not None:
        await sync_auxiliary_screen_message(
            application=application,
            api_client=api_client,
            chat_id=chat_id,
            user_data=user_data,
            telegram_user_id=telegram_user_id,
            auxiliary_text=None,
            auxiliary_buttons=None,
            disable_notification=secondary_disable_notification,
        )
        auxiliary_message = None

    intro_message: ActiveScreenMessage | None = None
    if intro_text is not None:
        sent_intro_message = await application.bot.send_message(
            chat_id=chat_id,
            text=intro_text,
            parse_mode=screen.parse_mode,
            disable_notification=secondary_disable_notification,
        )
        tracked_intro_row = await track_sent_bot_message(
            api_client=api_client,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            screen_id=f"{screen.screen_id}:intro",
            message_id=sent_intro_message.message_id,
            delete_after_hours=policy.delete_after_hours,
        )
        intro_message = ActiveScreenMessage(
            message_id=sent_intro_message.message_id,
            message_log_id=getattr(tracked_intro_row, "id", None),
            has_audio=False,
            screen_id=f"{screen.screen_id}:intro",
        )

    if should_force_resend and active_message is not None:
        await clear_messages(
            chat_id,
            application,
            [active_message.message_id],
            build_message_log_refs([active_message]),
        )
        previous_message_ids = [message_id for message_id in previous_message_ids if message_id != active_message.message_id]
        previous_message_log_refs = [
            item for item in previous_message_log_refs if item.get("message_id") != active_message.message_id
        ]
        active_message = None

    if active_message is not None:
        edited = await try_edit_active_screen(
            application=application,
            chat_id=chat_id,
            active_message=active_message,
            screen=screen,
            keyboard=keyboard,
            screen_text=screen_text,
        )
        if edited:
            if policy.prefer_edit_active:
                if api_client is not None and active_message.message_log_id is not None:
                    await save_cleanup_deleted_result(api_client, active_message.message_log_id)
                tracked_row = await track_sent_bot_message(
                    api_client=api_client,
                    telegram_user_id=telegram_user_id,
                    chat_id=chat_id,
                    screen_id=screen.screen_id,
                    message_id=active_message.message_id,
                    delete_after_hours=policy.delete_after_hours,
                )
                active_message.message_log_id = getattr(tracked_row, "id", None)
            should_reset_tracked_history = False
            if (
                fallback_active_message is not None
                and tracked_active_message is not None
                and tracked_active_message.message_id != fallback_active_message.message_id
                and previous_message_ids
            ):
                cleanup_message_ids = [
                    message_id for message_id in previous_message_ids if message_id != fallback_active_message.message_id
                ]
                cleanup_message_log_refs = [
                    item
                    for item in previous_message_log_refs
                    if item.get("message_id") != fallback_active_message.message_id
                ]
                if cleanup_message_ids:
                    await clear_messages(
                        chat_id,
                        application,
                        cleanup_message_ids,
                        cleanup_message_log_refs,
                    )
                should_reset_tracked_history = True
            if user_data is not None:
                if should_reset_tracked_history:
                    user_data["bot_message_ids"] = []
                    user_data["bot_message_log_refs"] = []
                if intro_message is not None:
                    user_data.setdefault("bot_message_ids", []).append(intro_message.message_id)
                    user_data.setdefault("bot_message_log_refs", []).extend(build_message_log_refs([intro_message]))
                save_active_screen_message(user_data, active_message)
            if auxiliary_after_active:
                await sync_auxiliary_screen_message(
                    application=application,
                    api_client=api_client,
                    chat_id=chat_id,
                    user_data=user_data,
                    telegram_user_id=telegram_user_id,
                    auxiliary_text=auxiliary_text,
                    auxiliary_buttons=auxiliary_buttons,
                    disable_notification=secondary_disable_notification,
                )
                auxiliary_message = get_auxiliary_screen_message(user_data)
            await sweep_chat_tracked_messages(
                application=application,
                api_client=api_client,
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                keep_messages=[active_message, auxiliary_message, intro_message],
                user_data=user_data,
            )
            await send_screen_documents(
                application=application,
                chat_id=chat_id,
                screen=screen,
                user_data=user_data,
                telegram_user_id=telegram_user_id,
                disable_notification=secondary_disable_notification,
            )
            return

    sent_message = await send_new_screen_message(
        application=application,
        chat_id=chat_id,
        screen=screen,
        keyboard=keyboard,
        screen_text=screen_text,
        disable_notification=primary_disable_notification,
    )
    tracked_row = await track_sent_bot_message(
        api_client=api_client,
        telegram_user_id=telegram_user_id,
        chat_id=chat_id,
        screen_id=screen.screen_id,
        message_id=sent_message.message_id,
        delete_after_hours=policy.delete_after_hours,
    )
    current_message = ActiveScreenMessage(
        message_id=sent_message.message_id,
        message_log_id=getattr(tracked_row, "id", None),
        has_audio=bool(screen.audio_path),
        screen_id=screen.screen_id,
    )

    if previous_message_ids:
        await clear_messages(
            chat_id,
            application,
            previous_message_ids,
            previous_message_log_refs,
        )

    if user_data is not None:
        user_data["bot_message_ids"] = [intro_message.message_id] if intro_message is not None else []
        user_data["bot_message_log_refs"] = build_message_log_refs([intro_message]) if intro_message is not None else []
        save_active_screen_message(user_data, current_message)
    if auxiliary_after_active:
        await sync_auxiliary_screen_message(
            application=application,
            api_client=api_client,
            chat_id=chat_id,
            user_data=user_data,
            telegram_user_id=telegram_user_id,
            auxiliary_text=auxiliary_text,
            auxiliary_buttons=auxiliary_buttons,
            disable_notification=secondary_disable_notification,
        )
        auxiliary_message = get_auxiliary_screen_message(user_data)
    await sweep_chat_tracked_messages(
        application=application,
        api_client=api_client,
        chat_id=chat_id,
        telegram_user_id=telegram_user_id,
        keep_messages=[current_message, auxiliary_message, intro_message],
        user_data=user_data,
    )
    await send_screen_documents(
        application=application,
        chat_id=chat_id,
        screen=screen,
        user_data=user_data,
        telegram_user_id=telegram_user_id,
        disable_notification=secondary_disable_notification,
    )
