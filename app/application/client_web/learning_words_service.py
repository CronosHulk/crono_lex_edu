from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.exc import SQLAlchemyError

from app.application.client_web.learning_errors import (
    ClientWebLearningNotFoundError,
    ClientWebLearningPaymentRequiredError,
    ClientWebLearningValidationError,
)
from app.helpers.locale import resolve_user_locale
from app.reference.labels import (
    CATEGORY_LABELS,
    format_category_labels,
    translate_category_label,
)
from app.validation.request_values import normalize_filter_values

WEB_LEARNING_WORD_MODES = {"learning", "learned", "imported_rotation", "imported_pending"}
WEB_LEARNING_WORD_STATUSES = {
    "uk": {
        "learning": "В процесі",
        "needs_work": "Потребує доопрацювання",
        "learned": "Вивчене",
        "found_existing": "Знайдене у словнику",
        "imported": "Імпортоване",
        "pending": "Очікує обробки",
        "waiting_for_user_dictionary_entry": "Очікує словниковий запис",
        "queued_for_details": "Очікує деталей",
        "queued_for_audio": "Очікує аудіо",
        "queued_for_embedding": "Очікує embedding",
        "details_failed": "Помилка деталей",
        "audio_failed": "Помилка аудіо",
        "collecting": "Збирається",
        "approved": "Схвалене",
        "ready_for_embedding": "Очікує embedding",
        "ready_for_publish": "Очікує публікації",
        "awaiting_audio": "Очікує аудіо",
    },
    "ru": {
        "learning": "В процессе",
        "needs_work": "Требует доработки",
        "learned": "Выучено",
        "found_existing": "Найдено в словаре",
        "imported": "Импортировано",
        "pending": "Ожидает обработки",
        "waiting_for_user_dictionary_entry": "Ожидает словарную запись",
        "queued_for_details": "Ожидает деталей",
        "queued_for_audio": "Ожидает аудио",
        "queued_for_embedding": "Ожидает embedding",
        "details_failed": "Ошибка деталей",
        "audio_failed": "Ошибка аудио",
        "collecting": "Собирается",
        "approved": "Одобрено",
        "ready_for_embedding": "Ожидает embedding",
        "ready_for_publish": "Ожидает публикации",
        "awaiting_audio": "Ожидает аудио",
    },
    "pl": {
        "learning": "W trakcie",
        "needs_work": "Wymaga dopracowania",
        "learned": "Nauczone",
        "found_existing": "Znalezione w slowniku",
        "imported": "Zaimportowane",
        "pending": "Oczekuje na przetworzenie",
        "waiting_for_user_dictionary_entry": "Oczekuje na wpis slownikowy",
        "queued_for_details": "Oczekuje na szczegoly",
        "queued_for_audio": "Oczekuje na audio",
        "queued_for_embedding": "Oczekuje na embedding",
        "details_failed": "Blad szczegolow",
        "audio_failed": "Blad audio",
        "collecting": "Zbierane",
        "approved": "Zatwierdzone",
        "ready_for_embedding": "Oczekuje na embedding",
        "ready_for_publish": "Oczekuje na publikacje",
        "awaiting_audio": "Oczekuje na audio",
    },
}


class ClientWebLearningWordsTimeService(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class ClientWebLearningWordsAccess:
    user_uuid: str
    allowed_core_levels: set[str] | None
    include_user_words: bool


class ClientWebLearningWordsAccessResolver(Protocol):
    def __call__(
        self,
        telegram_user_id: int,
        *,
        current_time: datetime,
    ) -> ClientWebLearningWordsAccess: ...


class ClientWebLearningWordsDatabasePort(Protocol):
    dictionary_lookup: Any
    learning_levels: Any
    user_import_items: Any
    learning_progress: Any
    dictionary_search: Any
    learning_word_priority: Any


class ClientWebLearningWordsService:
    def __init__(
        self,
        db: ClientWebLearningWordsDatabasePort,
        time_service: ClientWebLearningWordsTimeService,
        *,
        access_resolver: ClientWebLearningWordsAccessResolver,
    ) -> None:
        self.db = db
        self.time_service = time_service
        self.access_resolver = access_resolver

    def words(
        self,
        user: dict[str, Any],
        *,
        mode: str,
        page: int,
        page_size: int,
        word: str = "",
        topic: str | list[str] = "",
        level: str = "",
    ) -> dict[str, Any]:
        if mode not in WEB_LEARNING_WORD_MODES:
            raise ClientWebLearningValidationError("Unsupported learning word mode")
        locale = resolve_user_locale(user)
        topic_values = normalize_filter_values(topic)
        if topic_values:
            known_topics = _known_topic_codes(self.db.dictionary_lookup.list_categories())
            if any(value not in known_topics for value in topic_values):
                raise ClientWebLearningValidationError("Unsupported learning word topic")
        if level and level not in {item["title"] for item in self.db.learning_levels.list_levels()}:
            raise ClientWebLearningValidationError("Unsupported language level")
        if mode in {"imported_rotation", "imported_pending"}:
            result = self.db.user_import_items.list_learning_words(
                int(user["telegram_user_id"]),
                mode=mode,
                page=page,
                page_size=page_size,
                word=word,
                topic=topic_values,
                level=level,
            )
        else:
            result = self.db.learning_progress.list_user_words(
                int(user["telegram_user_id"]),
                mode=mode,
                page=page,
                page_size=page_size,
                word=word,
                topic=topic_values,
                level=level,
            )
        return {
            **result,
            "items": [
                {
                    **item,
                    "topic_codes": _topic_codes(item.get("topic")),
                    "topic": _localized_topic_labels(locale, item.get("topic")),
                    "translation": localized_learning_translation(locale, item),
                    "status": _localized_word_status(locale, item.get("learning_state")),
                }
                for item in result["items"]
            ],
        }

    def word_filters(self, user: dict[str, Any]) -> dict[str, Any]:
        locale = resolve_user_locale(user)
        try:
            categories = self.db.dictionary_lookup.list_categories()
        except SQLAlchemyError:
            categories = []
        return {
            "levels": [
                {"value": item["title"], "label": item["title"]}
                for item in self.db.learning_levels.list_levels()
            ],
            "topics": _category_filter_options(locale, categories),
        }

    def dictionary_search(
        self,
        user: dict[str, Any],
        *,
        query: str,
        page: int,
        page_size: int,
        level: str = "",
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        if len(normalized_query) < 3:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "pages": 0,
                "min_query_length": 3,
            }
        self._validate_level_filter(level)
        access = self._dictionary_search_access(user)
        if (
            level
            and access.allowed_core_levels is not None
            and level not in access.allowed_core_levels
        ):
            raise ClientWebLearningPaymentRequiredError("This word level is not available on your plan")
        locale = resolve_user_locale(user)
        result = self.db.dictionary_search.search_words(
            user_uuid=access.user_uuid,
            query=normalized_query,
            page=page,
            page_size=page_size,
            level=level,
            allowed_core_levels=access.allowed_core_levels,
            include_user_words=access.include_user_words,
        )
        return {
            **result,
            "min_query_length": 3,
            "items": [
                {
                    **item,
                    "translation": localized_learning_translation(locale, item),
                    "audio_url": (
                        f"/api/v1/client-web/learning/dictionary-search/"
                        f"{item['word_source']}/{item['word_id']}/audio"
                    )
                    if item.get("has_audio")
                    else None,
                }
                for item in result["items"]
            ],
        }

    def prioritize_word(self, user: dict[str, Any], *, word_source: str, word_id: int) -> dict[str, Any]:
        result = self.db.learning_word_priority.prioritize_word(
            int(user["telegram_user_id"]),
            word_source=word_source,
            word_id=word_id,
            current_time=self.time_service.now(),
        )
        if result is None:
            raise ClientWebLearningNotFoundError("Learning word was not found")
        return result

    def learn_dictionary_word(self, user: dict[str, Any], *, word_source: str, word_id: int) -> dict[str, Any]:
        access = self._dictionary_search_access(user)
        result = self.db.dictionary_search.create_priority_assignment(
            user_uuid=access.user_uuid,
            word_source=word_source,
            word_id=word_id,
            current_time=self.time_service.now(),
            allowed_core_levels=access.allowed_core_levels,
            include_user_words=access.include_user_words,
        )
        if result is None:
            raise ClientWebLearningNotFoundError("Dictionary word was not found")
        return result

    def dictionary_search_audio_path(
        self,
        user: dict[str, Any],
        *,
        word_source: str,
        word_id: int,
    ) -> str | None:
        access = self._dictionary_search_access(user)
        return self.db.dictionary_search.audio_path_for_word(
            user_uuid=access.user_uuid,
            word_source=word_source,
            word_id=word_id,
            allowed_core_levels=access.allowed_core_levels,
            include_user_words=access.include_user_words,
        )

    def _dictionary_search_access(self, user: dict[str, Any]) -> ClientWebLearningWordsAccess:
        return self.access_resolver(
            int(user["telegram_user_id"]),
            current_time=self.time_service.now(),
        )

    def _validate_level_filter(self, level: str) -> None:
        if level and level not in {item["title"] for item in self.db.learning_levels.list_levels()}:
            raise ClientWebLearningValidationError("Unsupported language level")


def _category_filter_label(locale: str, item: dict[str, Any]) -> str:
    code = str(item.get("code") or "")
    translated = translate_category_label(locale, code)
    if translated and translated != code:
        return translated
    return str(item.get("title") or code)


def _category_filter_options(locale: str, categories: list[dict[str, Any]]) -> list[dict[str, str]]:
    if categories:
        return [
            {
                "value": str(item["code"]),
                "label": _category_filter_label(locale, item),
            }
            for item in categories
        ]
    fallback_labels = CATEGORY_LABELS.get(locale) or CATEGORY_LABELS.get("uk", {})
    return [{"value": code, "label": label[:1].upper() + label[1:]} for code, label in sorted(fallback_labels.items())]


def _known_topic_codes(categories: list[dict[str, Any]]) -> set[str]:
    if categories:
        return {str(item["code"]) for item in categories}
    fallback_labels = CATEGORY_LABELS.get("uk", {})
    return set(fallback_labels)


def _topic_codes(topic: Any) -> list[str]:
    return [item.strip() for item in str(topic or "").split(",") if item.strip()]


def _localized_topic_labels(locale: str, topic: Any) -> str:
    return format_category_labels(locale, _topic_codes(topic))


def localized_learning_translation(locale: str, item: dict[str, Any]) -> str:
    locale_key = f"translation_{locale}"
    return str(item.get(locale_key) or item.get("translation_uk") or item.get("translation") or "")


def _localized_word_status(locale: str, learning_state: Any) -> str:
    state = str(learning_state or "")
    labels = WEB_LEARNING_WORD_STATUSES.get(locale) or WEB_LEARNING_WORD_STATUSES["uk"]
    return labels.get(state) or WEB_LEARNING_WORD_STATUSES["uk"].get(state) or state
