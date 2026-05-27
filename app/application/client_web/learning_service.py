from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, cast

from app.application.client_learning.content import (
    QuizPayload,
)
from app.application.client_learning.content import (
    build_quiz_payload as _build_quiz_payload,
)
from app.application.client_learning.display import (
    build_card_progress_bar as _build_card_progress_bar,
)
from app.application.client_learning.display import (
    build_quiz_progress_bar as _build_quiz_progress_bar,
)
from app.application.client_web.learning_session_service import (
    WEB_LEARNING_CLAIM_SCREEN_ID,
    ClientWebLearningSessionDatabasePort,
    ClientWebLearningSessionService,
    ClientWebLearningTelegramGateway,
    NoOpClientWebLearningTelegramGateway,
    _strip_summary_title,
)
from app.contracts import ScreenModel

__all__ = [
    "ClientWebLearningDatabasePort",
    "ClientWebLearningRuntime",
    "ClientWebLearningService",
    "ClientWebLearningStartService",
    "ClientWebLearningTelegramGateway",
    "ClientWebLearningTimeService",
    "QuizPayload",
    "WEB_LEARNING_CLAIM_SCREEN_ID",
    "_build_card_progress_bar",
    "_build_quiz_payload",
    "_build_quiz_progress_bar",
    "_strip_summary_title",
]


class ClientWebLearningTimeService(Protocol):
    def now(self) -> datetime: ...


class ClientWebLearningStartService(Protocol):
    def start_learning(self, telegram_user_id: int, locale: str) -> ScreenModel: ...


class ClientWebLearningWordsServicePort(Protocol):
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
    ) -> dict[str, Any]: ...

    def word_filters(self, user: dict[str, Any]) -> dict[str, Any]: ...

    def dictionary_search(
        self,
        user: dict[str, Any],
        *,
        query: str,
        page: int,
        page_size: int,
        level: str = "",
    ) -> dict[str, Any]: ...

    def prioritize_word(self, user: dict[str, Any], *, word_source: str, word_id: int) -> dict[str, Any]: ...

    def learn_dictionary_word(self, user: dict[str, Any], *, word_source: str, word_id: int) -> dict[str, Any]: ...

    def dictionary_search_audio_path(
        self,
        user: dict[str, Any],
        *,
        word_source: str,
        word_id: int,
    ) -> str | None: ...


class ClientWebLearningDatabasePort(Protocol):
    pass


class ClientWebLearningRuntime(Protocol):
    db: ClientWebLearningDatabasePort
    time_service: ClientWebLearningTimeService
    client_learning_card_action_service: Any
    client_learning_quiz_action_service: Any
    client_learning_ready_action_service: Any
    client_learning_session_completion_service: Any
    client_learning_start_service: ClientWebLearningStartService
    client_learning_summary_service: Any


class _FallbackClientWebLearningRuntime:
    def __init__(self, db: Any) -> None:
        self.db = db


class ClientWebLearningService:
    def __init__(
        self,
        learning_service: ClientWebLearningRuntime,
        telegram_gateway: ClientWebLearningTelegramGateway,
        *,
        words_service: ClientWebLearningWordsServicePort,
    ) -> None:
        self.learning_service = learning_service
        self.db: ClientWebLearningDatabasePort = learning_service.db
        self.telegram_gateway = telegram_gateway
        self._learning_words_service = words_service
        self._learning_session_service = self._build_session_service()

    def state(self, user: dict[str, Any]) -> dict[str, Any]:
        return self._session_service().state(user)

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
        return self._words_service().words(
            user,
            mode=mode,
            page=page,
            page_size=page_size,
            word=word,
            topic=topic,
            level=level,
        )

    def word_filters(self, user: dict[str, Any]) -> dict[str, Any]:
        return self._words_service().word_filters(user)

    def dictionary_search(
        self,
        user: dict[str, Any],
        *,
        query: str,
        page: int,
        page_size: int,
        level: str = "",
    ) -> dict[str, Any]:
        return self._words_service().dictionary_search(
            user,
            query=query,
            page=page,
            page_size=page_size,
            level=level,
        )

    def prioritize_word(self, user: dict[str, Any], *, word_source: str, word_id: int) -> dict[str, Any]:
        return self._words_service().prioritize_word(user, word_source=word_source, word_id=word_id)

    def learn_dictionary_word(self, user: dict[str, Any], *, word_source: str, word_id: int) -> dict[str, Any]:
        return self._words_service().learn_dictionary_word(user, word_source=word_source, word_id=word_id)

    def start(self, user: dict[str, Any]) -> dict[str, Any]:
        return self._session_service().start(user)

    def continue_session(self, user: dict[str, Any]) -> dict[str, Any]:
        return self._session_service().continue_session(user)

    def answer(self, user: dict[str, Any], *, session_word_id: int, option_index: int) -> dict[str, Any]:
        return self._session_service().answer(user, session_word_id=session_word_id, option_index=option_index)

    def card_action(self, user: dict[str, Any], *, session_word_id: int, action: str) -> dict[str, Any]:
        return self._session_service().card_action(user, session_word_id=session_word_id, action=action)

    def ready_action(self, user: dict[str, Any], *, expected_stage: str, decision: str) -> dict[str, Any]:
        return self._session_service().ready_action(user, expected_stage=expected_stage, decision=decision)

    def finish(self, user: dict[str, Any]) -> dict[str, Any]:
        return self._session_service().finish(user)

    def audio_path(self, user: dict[str, Any], *, session_word_id: int) -> str | None:
        return self._session_service().audio_path(user, session_word_id=session_word_id)

    def dictionary_search_audio_path(self, user: dict[str, Any], *, word_source: str, word_id: int) -> str | None:
        return self._words_service().dictionary_search_audio_path(
            user,
            word_source=word_source,
            word_id=word_id,
        )

    def _words_service(self) -> ClientWebLearningWordsServicePort:
        words_service = getattr(self, "_learning_words_service", None)
        if words_service is None:
            raise RuntimeError("Client web learning words service is not configured")
        return words_service

    def _session_service(self) -> ClientWebLearningSessionService:
        session_service = getattr(self, "_learning_session_service", None)
        if session_service is None:
            session_service = self._build_session_service()
            self._learning_session_service = session_service
        return session_service

    def _build_session_service(self) -> ClientWebLearningSessionService:
        learning_service = getattr(
            self,
            "learning_service",
            _FallbackClientWebLearningRuntime(getattr(self, "db", None)),
        )
        db = getattr(self, "db", getattr(learning_service, "db", None))
        return ClientWebLearningSessionService(
            learning_service,
            cast(ClientWebLearningSessionDatabasePort, db),
            self._telegram_gateway(),
        )

    def _telegram_gateway(self) -> ClientWebLearningTelegramGateway:
        gateway = getattr(self, "telegram_gateway", None)
        if gateway is None:
            gateway = NoOpClientWebLearningTelegramGateway()
            self.telegram_gateway = gateway
        return gateway


    def _session_state(self, session: dict[str, Any] | None, user: dict[str, Any]) -> dict[str, Any] | None:
        return self._session_service()._session_state(session, user)

    def _exercise(self, session: dict[str, Any], locale: str, *, telegram_user_id: int) -> dict[str, Any] | None:
        return self._session_service()._exercise(session, locale, telegram_user_id=telegram_user_id)

    def _summary_exercise(self, session_id: int, locale: str, *, telegram_user_id: int) -> dict[str, Any]:
        return self._session_service()._summary_exercise(
            session_id,
            locale,
            telegram_user_id=telegram_user_id,
        )

    def _has_teacher_link(self, telegram_user_id: int) -> bool:
        return self._session_service()._has_teacher_link(telegram_user_id)

    def _feedback_options(self, screen: Any) -> list[str]:
        return self._session_service()._feedback_options(screen)

    def _notify_telegram_web_claim(self, user: dict[str, Any], session: dict[str, Any] | None) -> None:
        self._session_service()._notify_telegram_web_claim(user, session)

    def _clear_active_telegram_screens(self, *, telegram_user_id: int, chat_id: int, current_time: datetime) -> None:
        self._session_service()._clear_active_telegram_screens(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            current_time=current_time,
        )

    def _track_telegram_claim_message(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        message_id: int,
        current_time: datetime,
    ) -> None:
        self._session_service()._track_telegram_claim_message(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            message_id=message_id,
            current_time=current_time,
        )
