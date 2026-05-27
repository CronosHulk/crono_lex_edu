from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ButtonModel(BaseModel):
    action: str
    text: str
    url: str | None = None


class DocumentAttachmentModel(BaseModel):
    path: str
    filename: str
    caption: str | None = None


class ScreenModel(BaseModel):
    screen_id: str
    text: str
    buttons: list[ButtonModel] = Field(default_factory=list)
    documents: list[DocumentAttachmentModel] = Field(default_factory=list)
    keyboard_type: str = "inline"
    clear_chat: bool = False
    audio_path: str | None = None
    parse_mode: str = "HTML"
    notice_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApiRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TelegramUserContext(ApiRequestModel):
    telegram_user_id: int = Field(gt=0)
    is_bot: bool | None = None
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, max_length=64)
    language_code: str | None = Field(default=None, max_length=16)
    is_premium: bool | None = None
    chat_id: int | None = None
    chat_type: str | None = Field(default=None, max_length=32)
    chat_username: str | None = Field(default=None, max_length=64)
    chat_title: str | None = Field(default=None, max_length=255)
    raw_telegram_json: str = Field(max_length=10_000)


class ActionRequest(ApiRequestModel):
    user: TelegramUserContext
    action: str = Field(min_length=1, max_length=256)


class BootstrapRequest(ApiRequestModel):
    user: TelegramUserContext
    message_text: str | None = Field(default=None, max_length=4_000)


class TextRequest(ApiRequestModel):
    user: TelegramUserContext
    text: str = Field(min_length=1, max_length=4_000)


class MenuRestoreRequest(ApiRequestModel):
    telegram_user_id: int = Field(gt=0)


class ActionResponse(BaseModel):
    screen: ScreenModel


class ReminderScreenModel(BaseModel):
    telegram_user_id: int
    chat_id: int
    screen: ScreenModel


class ReminderDispatchResponse(BaseModel):
    reminders: list[ReminderScreenModel] = Field(default_factory=list)


class ImportDispatchNotificationModel(BaseModel):
    telegram_user_id: int
    chat_id: int
    screen: ScreenModel
    disable_notification: bool = True
    delivery_kind: str | None = Field(default=None, max_length=64)
    delivery_id: int | None = Field(default=None, gt=0)


class ImportDispatchResponse(BaseModel):
    notifications: list[ImportDispatchNotificationModel] = Field(default_factory=list)


class SubscriptionMaintenanceResponse(BaseModel):
    summary: dict[str, Any] = Field(default_factory=dict)


class BotMessageTrackRequest(ApiRequestModel):
    telegram_user_id: int = Field(gt=0)
    chat_id: int
    message_id: int = Field(gt=0)
    screen_id: str = Field(min_length=1, max_length=120)
    delete_after_hours: int | None = Field(default=None, ge=1, le=168)


class BotMessageTrackResponse(BaseModel):
    id: int
    telegram_user_id: int
    chat_id: int
    message_id: int
    screen_id: str


class BotMessageLookupRequest(ApiRequestModel):
    telegram_user_id: int = Field(gt=0)
    chat_id: int
    message_id: int = Field(gt=0)


class BotMessageListRequest(ApiRequestModel):
    telegram_user_id: int = Field(gt=0)
    chat_id: int


class BotMessageCleanupModel(BaseModel):
    id: int
    telegram_user_id: int
    chat_id: int
    message_id: int
    screen_id: str


class BotMessageCleanupDispatchResponse(BaseModel):
    messages: list[BotMessageCleanupModel] = Field(default_factory=list)


class BotMessageListResponse(BaseModel):
    messages: list[BotMessageCleanupModel] = Field(default_factory=list)


class BotMessageCleanupResultRequest(ApiRequestModel):
    is_deleted: bool
    error_text: str | None = Field(default=None, max_length=1_000)


class BillingNotificationDeliveryResultRequest(ApiRequestModel):
    is_sent: bool
    error_text: str | None = Field(default=None, max_length=1_000)
