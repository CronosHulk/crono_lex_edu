from __future__ import annotations

from collections.abc import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from app.bot_api_client import BotApiClient
from app.bot_runtime.auto_advance import cancel_auto_advance_task, cancel_reminder_auto_return_task
from app.bot_runtime.user_context import build_user_context
from app.contracts import ScreenModel, TelegramUserContext

RenderScreen = Callable[[Update, ContextTypes.DEFAULT_TYPE, ScreenModel], Awaitable[None]]
ScheduleAutoAdvance = Callable[[ContextTypes.DEFAULT_TYPE, TelegramUserContext, int | None, ScreenModel], None]


async def start_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    render_screen_func: RenderScreen,
) -> None:
    if update.message is None:
        return
    cancel_user_runtime_tasks(update, context)
    api_client: BotApiClient = context.application.bot_data["api_client"]
    user = build_user_context(update)
    response = await api_client.bootstrap(user, update.message.text)
    await render_screen_func(update, context, response.screen)


async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    render_screen_func: RenderScreen,
) -> None:
    cancel_user_runtime_tasks(update, context)
    api_client: BotApiClient = context.application.bot_data["api_client"]
    user = build_user_context(update)
    response = await api_client.action(user, "m:menu")
    await render_screen_func(update, context, response.screen)


async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    render_screen_func: RenderScreen,
) -> None:
    if update.message is None or not update.message.text:
        return
    cancel_user_runtime_tasks(update, context)
    api_client: BotApiClient = context.application.bot_data["api_client"]
    user = build_user_context(update)
    response = await api_client.text(user, update.message.text)
    await render_screen_func(update, context, response.screen)


async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    render_screen_func: RenderScreen,
    schedule_auto_advance_func: ScheduleAutoAdvance,
) -> None:
    query = update.callback_query
    if query is None:
        return
    cancel_user_runtime_tasks(update, context)
    await query.answer()
    if (query.data or "") == "noop":
        return
    api_client: BotApiClient = context.application.bot_data["api_client"]
    user = build_user_context(update)
    response = await api_client.action(user, query.data or "m:menu")
    await render_screen_func(update, context, response.screen)
    schedule_auto_advance_func(
        context,
        user,
        update.effective_chat.id if update.effective_chat is not None else None,
        response.screen,
    )


def cancel_user_runtime_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel_auto_advance_task(context.user_data)
    telegram_user_id = getattr(update.effective_user, "id", None)
    chat_id = getattr(update.effective_chat, "id", None)
    if telegram_user_id is None:
        return
    cancel_reminder_auto_return_task(
        context.application.bot_data,
        int(telegram_user_id),
        int(chat_id) if chat_id is not None else None,
    )
