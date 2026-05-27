from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError

import app.application.client_learning.content as shared_content_helpers
import app.application.client_learning.display as shared_display_helpers
import app.application.client_web.learning_service as application_learning_service
from app.application.client_web.learning_errors import (
    ClientWebLearningConflictError,
    ClientWebLearningNotFoundError,
    ClientWebLearningPaymentRequiredError,
    ClientWebLearningValidationError,
)
from app.application.client_web.learning_service import (
    WEB_LEARNING_CLAIM_SCREEN_ID,
    ClientWebLearningService,
)
from app.application.client_web.learning_words_service import (
    ClientWebLearningWordsAccess,
    ClientWebLearningWordsService,
)
from app.contracts import ButtonModel, ScreenModel
from app.subscriptions.plans import FREE_ENTITLEMENTS, PREMIUM_ENTITLEMENTS


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.deleted_messages: list[dict] = []

    def send_message(self, **kwargs):
        self.messages.append(kwargs)
        return 555

    def delete_message(self, **kwargs):
        self.deleted_messages.append(kwargs)
        return True


class FakeTimeService:
    def __init__(self) -> None:
        self.current_time = datetime(2026, 4, 28, 15, 30, 0)

    def now(self) -> datetime:
        return self.current_time


class FakeLearningService:
    def __init__(self) -> None:
        self.time_service = FakeTimeService()
        self.client_learning_start_service = FakeStartService()
        self.client_learning_ready_action_service = FakeReadyActionService()
        self.client_learning_card_action_service = FakeCardActionService()
        self.client_learning_quiz_action_service = FakeQuizActionService()
        self.client_learning_summary_service = FakeSummaryService()
        self.client_learning_session_completion_service = FakeSessionCompletionService()


def test_constructor_accepts_runtime_port_fake() -> None:
    db = SimpleNamespace(settings=SimpleNamespace(bot_token="test-token"))
    runtime = SimpleNamespace(
        db=db,
        time_service=FakeTimeService(),
        client_learning_ready_action_service=FakeReadyActionService(),
        client_learning_card_action_service=FakeCardActionService(),
        client_learning_quiz_action_service=FakeQuizActionService(),
        client_learning_summary_service=FakeSummaryService(),
        client_learning_session_completion_service=FakeSessionCompletionService(),
        client_learning_start_service=FakeStartService(),
    )

    gateway = FakeTelegramGateway()
    words_service = FakeLearningWordsService()
    service = ClientWebLearningService(runtime, gateway, words_service=words_service)

    assert service.learning_service is runtime
    assert service.db is db
    assert service.telegram_gateway is gateway


def make_learning_words_service(
    db: Any,
    *,
    time_service: FakeTimeService | None = None,
) -> ClientWebLearningWordsService:
    return ClientWebLearningWordsService(
        db,
        time_service or FakeTimeService(),
        access_resolver=lambda _telegram_user_id, *, current_time: ClientWebLearningWordsAccess(
            user_uuid="user-uuid",
            allowed_core_levels=None,
            include_user_words=True,
        ),
    )


class FakeLearningWordsService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    def words(self, user: dict[str, Any], **kwargs: Any) -> dict[str, str]:
        self.calls.append(("words", user, kwargs))
        return {"result": "words"}

    def word_filters(self, user: dict[str, Any]) -> dict[str, str]:
        self.calls.append(("word_filters", user, {}))
        return {"result": "word_filters"}

    def dictionary_search(self, user: dict[str, Any], **kwargs: Any) -> dict[str, str]:
        self.calls.append(("dictionary_search", user, kwargs))
        return {"result": "dictionary_search"}

    def prioritize_word(self, user: dict[str, Any], **kwargs: Any) -> dict[str, str]:
        self.calls.append(("prioritize_word", user, kwargs))
        return {"result": "prioritize_word"}

    def learn_dictionary_word(self, user: dict[str, Any], **kwargs: Any) -> dict[str, str]:
        self.calls.append(("learn_dictionary_word", user, kwargs))
        return {"result": "learn_dictionary_word"}

    def dictionary_search_audio_path(self, user: dict[str, Any], **kwargs: Any) -> str:
        self.calls.append(("dictionary_search_audio_path", user, kwargs))
        return "runtime/audio/core-17.mp3"


def test_client_web_learning_service_delegates_words_public_methods() -> None:
    words_service = FakeLearningWordsService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service._learning_words_service = words_service
    user = {"telegram_user_id": 42}

    assert service.words(
        user,
        mode="learning",
        page=1,
        page_size=20,
        word="pass",
        topic=["emotion"],
        level="A1",
    ) == {"result": "words"}
    assert service.word_filters(user) == {"result": "word_filters"}
    assert service.dictionary_search(
        user,
        query="intent",
        page=2,
        page_size=10,
        level="A2",
    ) == {"result": "dictionary_search"}
    assert service.prioritize_word(user, word_source="user", word_id=88) == {
        "result": "prioritize_word"
    }
    assert service.learn_dictionary_word(user, word_source="core", word_id=17) == {
        "result": "learn_dictionary_word"
    }
    assert (
        service.dictionary_search_audio_path(user, word_source="core", word_id=17)
        == "runtime/audio/core-17.mp3"
    )
    assert words_service.calls == [
        (
            "words",
            user,
            {
                "mode": "learning",
                "page": 1,
                "page_size": 20,
                "word": "pass",
                "topic": ["emotion"],
                "level": "A1",
            },
        ),
        ("word_filters", user, {}),
        (
            "dictionary_search",
            user,
            {"query": "intent", "page": 2, "page_size": 10, "level": "A2"},
        ),
        ("prioritize_word", user, {"word_source": "user", "word_id": 88}),
        ("learn_dictionary_word", user, {"word_source": "core", "word_id": 17}),
        (
            "dictionary_search_audio_path",
            user,
            {"word_source": "core", "word_id": 17},
        ),
    ]


class FakeStartService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def start_learning(self, telegram_user_id: int, locale: str) -> ScreenModel:
        self.calls.append({"telegram_user_id": telegram_user_id, "locale": locale})
        return ScreenModel(
            screen_id=f"start:{telegram_user_id}",
            text=locale,
        )


class FakeSessionCompletionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete_session(self, telegram_user_id: int, session: dict[str, Any]) -> None:
        self.calls.append({"telegram_user_id": telegram_user_id, "session_id": session["id"]})
        session["status"] = "completed"
        session["current_stage"] = "summary"
        session["stage_queue_json"] = []
        session["stage_position"] = 0


class FakeReadyActionService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def handle_action(
        self,
        telegram_user_id: int,
        session: dict,
        locale: str,
        expected_stage: str,
        decision: str,
    ) -> ScreenModel:
        self.calls.append(
            {
                "telegram_user_id": telegram_user_id,
                "session": session,
                "locale": locale,
                "expected_stage": expected_stage,
                "decision": decision,
            }
        )
        return ScreenModel(screen_id="quiz_en_uk", text="next")


class FakeQuizActionService:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.complete_after_answer = False

    def handle_answer(
        self,
        session: dict,
        locale: str,
        session_word_id: int,
        option_index: int,
        *,
        max_options: int | None = None,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        if self.complete_after_answer:
            session["status"] = "completed"
            session["current_stage"] = "completed"
        self.calls.append(
            {
                "session": session,
                "locale": locale,
                "session_word_id": session_word_id,
                "option_index": option_index,
                "max_options": max_options,
                "telegram_user_id": telegram_user_id,
            }
        )
        return ScreenModel(
            screen_id="quiz_en_uk:11:feedback",
            text="feedback",
            buttons=[
                ButtonModel(action="noop", text="задоволення"),
                ButtonModel(action="noop", text="пристрасть ✅"),
                ButtonModel(action="noop", text="гордість"),
                ButtonModel(action="noop", text="палкий"),
                ButtonModel(action="m:menu", text="Повернутися в меню"),
            ],
            metadata={"auto_advance_after_ms": 1500},
        )


class FakeCardActionService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def handle_action(
        self,
        session: dict,
        locale: str,
        session_word_id: int,
        action: str,
        *,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        self.calls.append(
            {
                "session": session,
                "locale": locale,
                "session_word_id": session_word_id,
                "action": action,
                "telegram_user_id": telegram_user_id,
            }
        )
        return ScreenModel(screen_id="card", text="card")


class FakeSummaryService:
    def build_summary_screen(
        self,
        session_id: int,
        locale: str,
        *,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        assert session_id == 77
        assert locale == "uk"
        assert telegram_user_id == 42
        return ScreenModel(
            screen_id="summary:77",
            text=(
                "<i>Підсумок заняття</i>\n"
                "Супер, тренування завершено.\n"
                "Було допущено 2 помилки у 1 слово.\n"
                "Ми обовʼязково повторимо їх пізніше."
            ),
        )


def test_feedback_options_keep_original_button_order_without_menu_button() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    screen = ScreenModel(
        screen_id="quiz_en_uk:11:feedback",
        text="feedback",
        buttons=[
            ButtonModel(action="noop", text="first"),
            ButtonModel(action="noop", text="second ❌"),
            ButtonModel(action="noop", text="third ✅"),
            ButtonModel(action="noop", text="fourth"),
            ButtonModel(action="m:menu", text="Повернутися в меню"),
        ],
    )

    assert service._feedback_options(screen) == [
        "first",
        "second ❌",
        "third ✅",
        "fourth",
    ]


@pytest.mark.parametrize("stage", ["quiz_en_uk", "quiz_uk_en", "quiz_gap"])
def test_private_quiz_payload_matches_shared_helper_for_copied_subset(stage: str) -> None:
    session_word = {
        "session_word_id": 41,
        "word": "motion",
        "translation_uk": "рух, рух, переміщення",
        "translation_ru": "",
        "translation_pl": "ruch",
        "examples_json": [
            "  ",
            "The <fast> motion surprised everyone.",
            "A fallback line.",
        ],
    }
    distractors = [
        {
            "word": "movement",
            "translation_uk": "рух",
            "translation_ru": "движение",
            "translation_pl": "ruch",
        },
        {
            "word": "shift",
            "translation_uk": "зсув, зсув",
            "translation_ru": "сдвиг",
            "translation_pl": "zmiana",
        },
        {
            "word": "gesture",
            "translation_uk": "жест",
            "translation_ru": "жест",
            "translation_pl": "gest",
        },
    ]

    application_payload = application_learning_service._build_quiz_payload(
        stage=stage,
        session_word=session_word,
        distractors=distractors,
        locale="de",
        max_options=4,
    )
    shared_payload = shared_content_helpers.build_quiz_payload(
        stage=stage,
        session_word=session_word,
        distractors=distractors,
        locale="de",
        max_options=4,
    )

    assert application_payload.__dict__ == shared_payload.__dict__


@pytest.mark.parametrize(
    ("current_position", "total_count", "total_slots"),
    [
        (1, 0, None),
        (22, 25, None),
    ],
)
def test_private_card_progress_bar_matches_shared_helper(
    current_position: int,
    total_count: int,
    total_slots: int | None,
) -> None:
    assert application_learning_service._build_card_progress_bar(
        current_position,
        total_count,
        total_slots=total_slots,
    ) == shared_display_helpers.build_card_progress_bar(
        current_position,
        total_count,
        total_slots=total_slots,
    )


@pytest.mark.parametrize(
    ("queue", "position", "session_words_by_id", "exercise_type"),
    [
        ([], 0, {}, "en_uk"),
        (
            [1, 2, 3, 2],
            1,
            {
                1: {"en_uk_attempts": 1, "en_uk_correct": True},
                2: {"en_uk_attempts": 1, "en_uk_correct": False},
                3: {"en_uk_attempts": 2, "en_uk_correct": False},
            },
            "en_uk",
        ),
    ],
)
def test_private_quiz_progress_bar_matches_shared_helper(
    queue: list[int],
    position: int,
    session_words_by_id: dict[int, dict[str, Any]],
    exercise_type: str,
) -> None:
    assert application_learning_service._build_quiz_progress_bar(
        queue,
        position,
        session_words_by_id,
        exercise_type,
    ) == shared_display_helpers.build_quiz_progress_bar(
        queue,
        position,
        session_words_by_id,
        exercise_type,
    )


class FakeDb:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(app_bot_message_retention_days=30)
        self.restores: list[dict] = []
        self.cleanup_results: list[dict] = []
        self.created_bot_messages: list[dict] = []
        self.active_bot_messages = [
            {
                "id": 901,
                "telegram_user_id": 42,
                "chat_id": 100,
                "message_id": 501,
                "screen_id": "menu",
            },
            {
                "id": 902,
                "telegram_user_id": 42,
                "chat_id": 100,
                "message_id": 502,
                "screen_id": "ready_en_uk",
            },
        ]
        self.bot_message_logs = FakeBotMessageLogRepository(self)
        self.admin_auth = FakeAdminAuthRepository(self)


class FakeAdminAuthRepository:
    def __init__(self, db: FakeDb) -> None:
        self.db = db

    def schedule_bot_restore(self, **kwargs):
        self.db.restores.append(kwargs)


class FakeBotMessageLogRepository:
    def __init__(self, db: FakeDb) -> None:
        self.db = db

    def list_active(self, telegram_user_id: int, chat_id: int):
        assert telegram_user_id == 42
        assert chat_id == 100
        return self.db.active_bot_messages

    def save_cleanup_result(self, message_log_id: int, **kwargs):
        self.db.cleanup_results.append({"message_log_id": message_log_id, **kwargs})

    def create(self, telegram_user_id, chat_id, message_id, screen_id, delete_after, current_time):
        self.db.created_bot_messages.append(
            {
                "telegram_user_id": telegram_user_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "screen_id": screen_id,
                "delete_after": delete_after,
                "current_time": current_time,
            }
        )
        return {"id": 903}


class FakeLearningSessions:
    def __init__(self) -> None:
        self.claims: list[tuple[int, str]] = []
        self.active_session = {
            "id": 77,
            "status": "active",
            "current_stage": "ready_en_uk",
            "stage_position": 0,
            "active_interface": "client_web",
            "interface_revision": 1,
        }

    def get_active_session(self, telegram_user_id: int):
        assert telegram_user_id == 42
        return self.active_session if self.active_session.get("status") == "active" else None

    def get_resumable_session(self, telegram_user_id: int):
        assert telegram_user_id == 42
        return self.active_session

    def claim_active_session(self, telegram_user_id: int, active_interface: str):
        assert telegram_user_id == 42
        self.claims.append((telegram_user_id, active_interface))
        self.active_session["active_interface"] = active_interface
        return self.active_session

    def claim_resumable_session(self, telegram_user_id: int, active_interface: str):
        assert telegram_user_id == 42
        self.claims.append((telegram_user_id, active_interface))
        self.active_session["active_interface"] = active_interface
        return self.active_session

    def update_session_state(
        self,
        session_id: int,
        current_stage: str,
        stage_queue: list[int],
        stage_position: int,
    ) -> None:
        assert session_id == 77
        self.active_session.update(
            {
                "current_stage": current_stage,
                "stage_queue_json": stage_queue,
                "stage_position": stage_position,
            }
        )

    def complete_session(self, session_id: int) -> None:
        assert session_id == 77
        self.active_session["status"] = "completed"

    def finish_completed_summary(self, session_id: int) -> None:
        assert session_id == 77
        if self.active_session["status"] == "completed":
            self.active_session["current_stage"] = "finished"

    def get_session_word(self, session_word_id: int):
        if session_word_id == 11:
            return {
                "session_id": 77,
                "session_word_id": 11,
                "word_id": 101,
                "level_id": 1,
                "word": "passion",
                "translation_uk": "пристрасть",
                "translations_json": ["пристрасть"],
                "examples_json": ["Music & art is his greatest passion."],
                "audio_path": "runtime/audio/frightening.mp3",
                "en_uk_attempts": 0,
                "en_uk_correct": False,
                "uk_en_attempts": 0,
                "uk_en_correct": False,
                "gap_attempts": 0,
                "gap_correct": False,
            }
        return None

    def get_session_words(self, session_id: int):
        assert session_id == 77
        return [
            {
                "session_word_id": 11,
                "word": "frightening",
                "translation_uk": "страшний, що лякає",
                "phonetic_us": "/ˈfraɪtnɪŋ/",
                "examples_json": ["It was a very frightening experience."],
                "categories": ["quality"],
                "audio_path": "runtime/audio/frightening.mp3",
            },
            {
                "session_word_id": 12,
                "word": "abrupt",
                "translation_uk": "раптовий",
                "phonetic_us": "/əˈbrʌpt/",
                "examples_json": [],
                "categories": [],
                "audio_path": "",
            },
        ]


class FakeExerciseDb:
    def __init__(self) -> None:
        self.learning_sessions = FakeLearningSessions()
        self.learning_progress = FakeLearningProgress()
        self.learning_word_priority = FakeLearningWordPriority()
        self.learning_levels = FakeLearningLevels()
        self.user_import_items = FakeUserImportItems()
        self.similar_words = FakeSimilarWords()
        self.teacher_student_links = FakeTeacherStudentLinks()
        self.dictionary_lookup = FakeDictionaryLookup()


class FakeLearningWordPriority:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result: dict[str, Any] | None = {"word_source": "user", "word_id": 88, "priority_rank": 1777390200}

    def prioritize_word(self, telegram_user_id: int, **kwargs: Any) -> dict[str, Any] | None:
        self.calls.append({"telegram_user_id": telegram_user_id, **kwargs})
        return self.result


class FakeSimilarWords:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def find_similar_words(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return [
            {"word": "joy", "translation_uk": "задоволення", "translations_json": ["задоволення"]},
            {"word": "pride", "translation_uk": "гордість", "translations_json": ["гордість"]},
            {"word": "enthusiasm", "translation_uk": "ентузіазм", "translations_json": ["ентузіазм"]},
            {"word": "warm", "translation_uk": "палкий", "translations_json": ["палкий"]},
        ]


class FakeTeacherStudentLinks:
    def has_active_teacher(self, telegram_user_id: int) -> bool:
        assert telegram_user_id == 42
        return False


class FakeLearningLevels:
    def list_levels(self):
        return [{"title": "A1"}, {"title": "A2"}]


class FakeDictionaryLookup:
    def list_categories(self):
        return [
            {"code": "emotion", "title": "Emotion"},
            {"code": "planning", "title": "Planning"},
        ]


class FakeLearningProgress:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def list_user_words(self, telegram_user_id: int, **kwargs):
        self.calls.append({"telegram_user_id": telegram_user_id, **kwargs})
        return {
            "items": [
                {
                    "id": 101,
                    "word": "passion",
                    "topic": "business, quality",
                    "level": "A1",
                    "translation": "пристрасть",
                    "translation_uk": "пристрасть",
                    "translation_ru": "страсть",
                    "translation_pl": "pasja",
                    "learning_state": "needs_work",
                },
                {
                    "id": 102,
                    "word": "logic",
                    "topic": "communication",
                    "level": "A1",
                    "translation": "логіка",
                    "translation_uk": "логіка",
                    "translation_ru": "логика",
                    "translation_pl": "logika",
                    "learning_state": "learning",
                },
            ],
            "total": 2,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "pages": 1,
        }


class FakeUserImportItems:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.learning_state = "imported"

    def list_learning_words(self, telegram_user_id: int, **kwargs):
        self.calls.append({"telegram_user_id": telegram_user_id, **kwargs})
        return {
            "items": [
                {
                    "id": 201,
                    "word": "intention",
                    "topic": "travel",
                    "level": "A1",
                    "translation": "намір",
                    "translation_uk": "намір",
                    "translation_ru": "намерение",
                    "translation_pl": "zamiar",
                    "learning_state": self.learning_state,
                    "import_job_id": 9,
                },
            ],
            "total": 1,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "pages": 1,
        }


class FakeDictionarySearchRepository:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, Any]] = []
        self.learn_calls: list[dict[str, Any]] = []

    def search_words(self, **kwargs):
        self.search_calls.append(kwargs)
        return {
            "items": [
                {
                    "word_source": "core",
                    "word_id": 17,
                    "word": "intention",
                    "transcription": "/in-ten-shun/",
                    "level": "A1",
                    "translation": "намір",
                    "translation_uk": "намір",
                    "translation_ru": "намерение",
                    "translation_pl": "zamiar",
                    "has_audio": True,
                },
            ],
            "total": 1,
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "pages": 1,
        }

    def create_priority_assignment(self, **kwargs):
        self.learn_calls.append(kwargs)
        return {"word_source": kwargs["word_source"], "word_id": kwargs["word_id"]}


class FakeDictionarySearchDb:
    def __init__(self, entitlements=FREE_ENTITLEMENTS) -> None:
        self.entitlements = entitlements
        self.dictionary_search = FakeDictionarySearchRepository()
        self.learning_levels = SimpleNamespace(
            list_levels=lambda: [{"title": "A1"}, {"title": "A2"}, {"title": "B1"}]
        )


class FakeDictionarySearchAccessResolver:
    def __init__(self, db: FakeDictionarySearchDb) -> None:
        self.db = db
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        telegram_user_id: int,
        *,
        current_time: datetime,
    ) -> ClientWebLearningWordsAccess:
        assert telegram_user_id == 42
        assert current_time == datetime(2026, 4, 28, 15, 30, 0)
        self.calls.append(
            {"telegram_user_id": telegram_user_id, "current_time": current_time}
        )
        allowed_core_levels = (
            set(self.db.entitlements.level_titles)
            if self.db.entitlements.level_titles is not None
            else None
        )
        return ClientWebLearningWordsAccess(
            user_uuid="user-uuid",
            allowed_core_levels=allowed_core_levels,
            include_user_words=self.db.entitlements.level_titles is None,
        )


def make_dictionary_search_service(
    db: FakeDictionarySearchDb,
) -> tuple[ClientWebLearningWordsService, FakeDictionarySearchAccessResolver]:
    access_resolver = FakeDictionarySearchAccessResolver(db)
    return ClientWebLearningWordsService(
        db,
        FakeTimeService(),
        access_resolver=access_resolver,
    ), access_resolver


def test_dictionary_search_free_plan_limits_core_levels_and_localizes() -> None:
    db = FakeDictionarySearchDb(FREE_ENTITLEMENTS)
    service, access_resolver = make_dictionary_search_service(db)

    response = service.dictionary_search(
        {"telegram_user_id": 42, "interface_locale": "ru"},
        query=" intention ",
        page=1,
        page_size=50,
        level="A1",
    )

    assert db.dictionary_search.search_calls == [
        {
            "user_uuid": "user-uuid",
            "query": "intention",
            "page": 1,
            "page_size": 50,
            "level": "A1",
            "allowed_core_levels": {"A1", "A2"},
            "include_user_words": False,
        }
    ]
    assert len(access_resolver.calls) == 1
    assert response["items"][0]["translation"] == "намерение"
    assert response["items"][0]["audio_url"] == "/api/v1/client-web/learning/dictionary-search/core/17/audio"


def test_dictionary_search_free_plan_rejects_locked_level() -> None:
    db = FakeDictionarySearchDb(FREE_ENTITLEMENTS)
    service, _access_resolver = make_dictionary_search_service(db)

    with pytest.raises(ClientWebLearningPaymentRequiredError) as error:
        service.dictionary_search(
            {"telegram_user_id": 42, "interface_locale": "uk"},
            query="intention",
            page=1,
            page_size=50,
            level="B1",
        )

    assert error.value.detail == "This word level is not available on your plan"
    assert db.dictionary_search.search_calls == []


def test_dictionary_search_premium_includes_user_words_and_all_levels() -> None:
    db = FakeDictionarySearchDb(PREMIUM_ENTITLEMENTS)
    service, _access_resolver = make_dictionary_search_service(db)

    service.dictionary_search(
        {"telegram_user_id": 42, "interface_locale": "uk"},
        query="intention",
        page=2,
        page_size=50,
        level="B1",
    )

    assert db.dictionary_search.search_calls[0]["allowed_core_levels"] is None
    assert db.dictionary_search.search_calls[0]["include_user_words"] is True


def test_learn_dictionary_word_uses_priority_assignment_with_plan_access() -> None:
    db = FakeDictionarySearchDb(PREMIUM_ENTITLEMENTS)
    service, _access_resolver = make_dictionary_search_service(db)

    response = service.learn_dictionary_word(
        {"telegram_user_id": 42},
        word_source="user",
        word_id=88,
    )

    assert response == {"word_source": "user", "word_id": 88}
    assert db.dictionary_search.learn_calls == [
        {
            "user_uuid": "user-uuid",
            "word_source": "user",
            "word_id": 88,
            "current_time": datetime(2026, 4, 28, 15, 30, 0),
            "allowed_core_levels": None,
            "include_user_words": True,
        }
    ]


def test_facade_constructor_wires_dictionary_search_to_words_service() -> None:
    db = FakeDictionarySearchDb(PREMIUM_ENTITLEMENTS)
    runtime = FakeLearningService()
    runtime.db = db
    words_service, _access_resolver = make_dictionary_search_service(db)
    service = ClientWebLearningService(
        runtime,
        FakeTelegramGateway(),
        words_service=words_service,
    )
    words_service = service._learning_words_service

    response = service.dictionary_search(
        {"telegram_user_id": 42, "interface_locale": "ru"},
        query=" intention ",
        page=3,
        page_size=25,
        level="B1",
    )
    learned = service.learn_dictionary_word(
        {"telegram_user_id": 42},
        word_source="user",
        word_id=88,
    )

    assert service._words_service() is words_service
    assert response["items"][0]["translation"] == "намерение"
    assert learned == {"word_source": "user", "word_id": 88}
    assert db.dictionary_search.search_calls == [
        {
            "user_uuid": "user-uuid",
            "query": "intention",
            "page": 3,
            "page_size": 25,
            "level": "B1",
            "allowed_core_levels": None,
            "include_user_words": True,
        }
    ]
    assert db.dictionary_search.learn_calls == [
        {
            "user_uuid": "user-uuid",
            "word_source": "user",
            "word_id": 88,
            "current_time": datetime(2026, 4, 28, 15, 30, 0),
            "allowed_core_levels": None,
            "include_user_words": True,
        }
    ]


def test_web_learning_claim_notification_offers_telegram_resume_and_menu_restore() -> None:
    gateway = FakeTelegramGateway()
    db = FakeDb()
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.telegram_gateway = gateway
    service.db = db
    service.learning_service = learning_service

    service._notify_telegram_web_claim(
        {"telegram_user_id": 42, "chat_id": 100, "interface_locale": "uk"},
        {"id": 77, "active_interface": "client_web"},
    )

    assert gateway.messages[0]["text"] == (
        "Заняття відкрито у вебінтерфейсі. У Telegram можна продовжити його в будь-який момент."
    )
    assert gateway.messages[0]["reply_markup"] == {
        "inline_keyboard": [
            [{"text": "⏯️ Продовжити поточне заняття", "callback_data": "m:r"}],
            [{"text": "Повернутися в меню", "callback_data": "m:menu"}],
        ]
    }
    assert gateway.deleted_messages == [
        {"chat_id": 100, "message_id": 501, "ignore_errors": True},
        {"chat_id": 100, "message_id": 502, "ignore_errors": True},
    ]
    assert db.cleanup_results == [
        {
            "message_log_id": 901,
            "is_deleted": True,
            "current_time": datetime(2026, 4, 28, 15, 30, 0),
        },
        {
            "message_log_id": 902,
            "is_deleted": True,
            "current_time": datetime(2026, 4, 28, 15, 30, 0),
        },
    ]
    assert db.created_bot_messages == [
        {
            "telegram_user_id": 42,
            "chat_id": 100,
            "message_id": 555,
            "screen_id": WEB_LEARNING_CLAIM_SCREEN_ID,
            "delete_after": datetime(2026, 4, 28, 15, 35, 0),
            "current_time": datetime(2026, 4, 28, 15, 30, 0),
        }
    ]
    assert db.restores == [
        {
            "telegram_user_id": 42,
            "chat_id": 100,
            "previous_screen_id": None,
            "scheduled_for": datetime(2026, 4, 28, 15, 35, 0),
            "current_time": datetime(2026, 4, 28, 15, 30, 0),
        }
    ]


def test_card_exercise_uses_shared_session_word_details_and_progress() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()

    exercise = service._exercise(
        {
            "id": 77,
            "current_stage": "card",
            "stage_position": 0,
        },
        "uk",
        telegram_user_id=42,
    )

    assert exercise == {
        "type": "card",
        "session_word_id": 11,
        "word": "frightening",
        "translation": "страшний, що лякає",
        "translation_uk": "страшний, що лякає",
        "transcription": "/ˈfraɪtnɪŋ/",
        "examples": ["It was a very frightening experience."],
        "categories": ["quality"],
        "audio_url": "/api/v1/client-web/learning/session-words/11/audio",
        "position": 1,
        "total": 2,
        "progress_bar": "[⋯⋯⋯⋯⋯⋯⋯⋯⋯●○⋯⋯⋯⋯⋯⋯⋯⋯⋯]",
        "can_go_back": False,
        "can_go_forward": True,
        "next_action": "next",
    }


def test_ready_exercise_uses_shared_ready_stage_text() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()

    exercise = service._exercise(
        {
            "id": 77,
            "current_stage": "ready_en_uk",
            "stage_position": 0,
        },
        "uk",
        telegram_user_id=42,
    )

    assert exercise == {
        "type": "ready",
        "stage": "ready_en_uk",
        "title": "Знайомство зі словами завершено.\n\nПереходимо до практики.",
        "prompt": "Готові продовжувати?",
    }


def test_quiz_exercise_uses_four_options_and_stage_title() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()

    exercise = service._exercise(
        {
            "id": 77,
            "current_stage": "quiz_en_uk",
            "telegram_user_id": 42,
            "stage_queue_json": [11],
            "stage_position": 0,
        },
        "uk",
        telegram_user_id=42,
    )

    assert exercise["type"] == "quiz"
    assert exercise["stage"] == "quiz_en_uk"
    assert exercise["title"] == "Вправа 1/3 - оберіть правильний український переклад"
    assert exercise["prompt"] == "passion"
    assert len(exercise["options"]) == 4
    assert "пристрасть" in exercise["options"]


def test_gap_quiz_exercise_returns_plain_web_prompt_without_telegram_html() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.db.learning_sessions.active_session["current_stage"] = "quiz_gap"
    service.db.learning_sessions.active_session["stage_queue_json"] = [11]

    exercise = service._exercise(
        {
            "id": 77,
            "current_stage": "quiz_gap",
            "stage_queue_json": [11],
            "stage_position": 0,
        },
        "uk",
        telegram_user_id=42,
    )

    assert exercise["prompt"] == "Music & art is his greatest _____."
    assert "<b>" not in exercise["prompt"]
    assert "</b>" not in exercise["prompt"]


def test_quiz_exercise_advances_empty_non_final_queue_to_ready_stage() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()

    session = {
        "id": 77,
        "status": "active",
        "current_stage": "quiz_en_uk",
        "stage_queue_json": [11],
        "stage_position": 1,
        "active_interface": "client_web",
        "interface_revision": 1,
    }

    state = service._session_state(session, {"telegram_user_id": 42, "interface_locale": "uk"})

    assert state["current_stage"] == "ready_uk_en"
    assert state["stage_position"] == 0
    assert state["exercise"] == {
        "type": "ready",
        "stage": "ready_uk_en",
        "title": "Вправа 2 із 3. Оберіть правильне англійське слово.",
        "prompt": "Готові продовжувати?",
    }


def test_final_quiz_exercise_with_empty_queue_returns_summary() -> None:
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service

    session = {
        "id": 77,
        "status": "active",
        "current_stage": "quiz_gap",
        "stage_queue_json": [11],
        "stage_position": 1,
        "active_interface": "client_web",
        "interface_revision": 1,
    }

    state = service._session_state(session, {"telegram_user_id": 42, "interface_locale": "uk"})

    assert state["status"] == "completed"
    assert state["current_stage"] == "summary"
    assert state["stage_position"] == 0
    assert state["exercise"]["type"] == "summary"
    assert state["exercise"]["finish_label"] == "Завершити тренування"
    assert learning_service.client_learning_session_completion_service.calls == [
        {"telegram_user_id": 42, "session_id": 77}
    ]


def test_completed_session_returns_localized_web_summary_exercise() -> None:
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service

    exercise = service._exercise(
        {
            "id": 77,
            "status": "completed",
            "current_stage": "completed",
            "stage_queue_json": [],
            "stage_position": 0,
        },
        "uk",
        telegram_user_id=42,
    )

    assert exercise == {
        "type": "summary",
        "title": "Підсумок заняття",
        "prompt": (
            "Супер, тренування завершено.\n"
            "Було допущено 2 помилки у 1 слово.\n"
            "Ми обовʼязково повторимо їх пізніше."
        ),
        "finish_label": "Завершити тренування",
    }


def test_state_returns_completed_session_summary_as_resumable() -> None:
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service
    service.db.learning_sessions.active_session.update(
        {
            "status": "completed",
            "current_stage": "completed",
            "active_interface": "client_web",
        }
    )

    response = service.state({"telegram_user_id": 42, "interface_locale": "uk"})

    assert response["has_teacher_link"] is False
    assert response["active_session"]["status"] == "completed"
    assert response["active_session"]["exercise"]["type"] == "summary"
    assert response["active_session"]["exercise"]["finish_label"] == "Завершити тренування"


def test_words_returns_learning_progress_rows_with_status_labels() -> None:
    db = FakeExerciseDb()
    service = make_learning_words_service(db)

    response = service.words(
        {"telegram_user_id": 42},
        mode="learning",
        page=1,
        page_size=20,
        word="pass",
        topic=["emotion"],
        level="A1",
    )

    assert response["items"][0]["status"] == "Потребує доопрацювання"
    assert response["items"][0]["topic"] == "Бізнес, Якість"
    assert response["items"][0]["topic_codes"] == ["business", "quality"]
    assert response["items"][1]["status"] == "В процесі"
    assert response["items"][1]["topic"] == "Спілкування"
    assert response["items"][1]["topic_codes"] == ["communication"]
    assert db.learning_progress.calls == [
        {
            "telegram_user_id": 42,
            "mode": "learning",
            "page": 1,
            "page_size": 20,
            "word": "pass",
            "topic": ["emotion"],
            "level": "A1",
        }
    ]


def test_words_uses_user_interface_locale_for_rows() -> None:
    service = make_learning_words_service(FakeExerciseDb())

    response = service.words(
        {"telegram_user_id": 42, "interface_locale": "ru"},
        mode="learning",
        page=1,
        page_size=20,
    )

    assert response["items"][0]["translation"] == "страсть"
    assert response["items"][0]["status"] == "Требует доработки"
    assert response["items"][0]["topic"] == "Бизнес, Качество"
    assert response["items"][1]["translation"] == "логика"
    assert response["items"][1]["status"] == "В процессе"
    assert response["items"][1]["topic"] == "Общение"


def test_words_returns_imported_rows_with_status_labels() -> None:
    db = FakeExerciseDb()
    service = make_learning_words_service(db)

    response = service.words(
        {"telegram_user_id": 42},
        mode="imported_rotation",
        page=1,
        page_size=20,
        word="intent",
        topic=["planning"],
        level="A1",
    )

    assert response["items"][0]["status"] == "Імпортоване"
    assert response["items"][0]["topic"] == "Подорожі"
    assert response["items"][0]["topic_codes"] == ["travel"]
    assert db.user_import_items.calls == [
        {
            "telegram_user_id": 42,
            "mode": "imported_rotation",
            "page": 1,
            "page_size": 20,
            "word": "intent",
            "topic": ["planning"],
            "level": "A1",
        }
    ]
    assert db.learning_progress.calls == []


def test_words_returns_imported_pending_rows_with_user_dictionary_status_labels() -> None:
    db = FakeExerciseDb()
    service = make_learning_words_service(db)
    db.user_import_items.learning_state = "queued_for_details"

    response = service.words(
        {"telegram_user_id": 42, "interface_locale": "ru"},
        mode="imported_pending",
        page=1,
        page_size=20,
    )

    assert response["items"][0]["status"] == "Ожидает деталей"
    assert db.user_import_items.calls[0]["mode"] == "imported_pending"


def test_words_rejects_unsupported_mode_and_level() -> None:
    service = make_learning_words_service(FakeExerciseDb())

    with pytest.raises(ClientWebLearningValidationError) as mode_error:
        service.words({"telegram_user_id": 42}, mode="imported", page=1, page_size=20)

    with pytest.raises(ClientWebLearningValidationError) as level_error:
        service.words({"telegram_user_id": 42}, mode="learning", page=1, page_size=20, level="Z9")

    assert mode_error.value.detail == "Unsupported learning word mode"
    assert level_error.value.detail == "Unsupported language level"


def test_words_rejects_unsupported_topic() -> None:
    service = make_learning_words_service(FakeExerciseDb())

    with pytest.raises(ClientWebLearningValidationError) as topic_error:
        service.words({"telegram_user_id": 42}, mode="learning", page=1, page_size=20, topic=["unknown"])

    assert topic_error.value.detail == "Unsupported learning word topic"


def test_word_filters_returns_localized_topics_and_levels() -> None:
    service = make_learning_words_service(FakeExerciseDb())

    response = service.word_filters({"telegram_user_id": 42, "interface_locale": "uk"})

    assert response["levels"] == [{"value": "A1", "label": "A1"}, {"value": "A2", "label": "A2"}]
    assert response["topics"] == [
        {"value": "emotion", "label": "Emotion"},
        {"value": "planning", "label": "Planning"},
    ]


def test_word_filters_falls_back_to_reference_topics_when_database_categories_are_empty() -> None:
    db = FakeExerciseDb()
    service = make_learning_words_service(db)
    db.dictionary_lookup = type("EmptyDictionaryLookup", (), {"list_categories": lambda self: []})()

    response = service.word_filters({"telegram_user_id": 42, "interface_locale": "uk"})

    values = {item["value"]: item["label"] for item in response["topics"]}
    assert values["business"] == "Бізнес"
    assert values["travel"] == "Подорожі"
    assert values["it"] == "ІТ"


def test_word_filters_falls_back_to_reference_topics_when_database_categories_fail() -> None:
    db = FakeExerciseDb()
    service = make_learning_words_service(db)

    class BrokenDictionaryLookup:
        def list_categories(self):
            raise SQLAlchemyError("dictionary categories are unavailable")

    db.dictionary_lookup = BrokenDictionaryLookup()

    response = service.word_filters({"telegram_user_id": 42, "interface_locale": "uk"})

    values = {item["value"]: item["label"] for item in response["topics"]}
    assert response["levels"] == [{"value": "A1", "label": "A1"}, {"value": "A2", "label": "A2"}]
    assert values["business"] == "Бізнес"


def test_prioritize_word_passes_user_payload_and_current_time() -> None:
    db = FakeExerciseDb()
    time_service = FakeTimeService()
    service = make_learning_words_service(db, time_service=time_service)

    response = service.prioritize_word({"telegram_user_id": 42}, word_source="user", word_id=88)

    assert response == {"word_source": "user", "word_id": 88, "priority_rank": 1777390200}
    assert db.learning_word_priority.calls == [
        {
            "telegram_user_id": 42,
            "word_source": "user",
            "word_id": 88,
            "current_time": time_service.current_time,
        }
    ]


def test_prioritize_word_returns_404_when_word_is_missing() -> None:
    db = FakeExerciseDb()
    service = make_learning_words_service(db)
    db.learning_word_priority.result = None

    with pytest.raises(ClientWebLearningNotFoundError) as error:
        service.prioritize_word({"telegram_user_id": 42}, word_source="core", word_id=404)

    assert error.value.detail == "Learning word was not found"


def test_answer_uses_web_quiz_options_and_returns_feedback_without_menu_button() -> None:
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service
    service.db.learning_sessions.active_session.update(
        {
            "current_stage": "quiz_en_uk",
            "stage_queue_json": [11],
            "stage_position": 0,
        }
    )

    response = service.answer(
        {"telegram_user_id": 42, "interface_locale": "uk"},
        session_word_id=11,
        option_index=1,
    )

    assert response["feedback_options"] == [
        "задоволення",
        "пристрасть ✅",
        "гордість",
        "палкий",
    ]
    assert response["screen"]["metadata"]["auto_advance_after_ms"] == 1500
    assert learning_service.client_learning_quiz_action_service.calls == [
        {
            "session": service.db.learning_sessions.active_session,
            "locale": "uk",
            "session_word_id": 11,
            "option_index": 1,
            "max_options": 4,
            "telegram_user_id": 42,
        }
    ]


def test_card_action_passes_user_context_when_session_has_only_uuid_identity() -> None:
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service
    assert "telegram_user_id" not in service.db.learning_sessions.active_session

    response = service.card_action(
        {"telegram_user_id": 42, "interface_locale": "uk"},
        session_word_id=11,
        action="next",
    )

    assert response["screen"]["screen_id"] == "card"
    assert learning_service.client_learning_card_action_service.calls == [
        {
            "session": service.db.learning_sessions.active_session,
            "locale": "uk",
            "session_word_id": 11,
            "action": "next",
            "telegram_user_id": 42,
        }
    ]


def test_answer_returns_completed_summary_when_last_web_answer_finishes_session() -> None:
    learning_service = FakeLearningService()
    learning_service.client_learning_quiz_action_service.complete_after_answer = True
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service
    service.db.learning_sessions.active_session.update(
        {
            "current_stage": "quiz_gap",
            "stage_queue_json": [11],
            "stage_position": 0,
            "active_interface": "client_web",
        }
    )

    response = service.answer(
        {"telegram_user_id": 42, "interface_locale": "uk"},
        session_word_id=11,
        option_index=1,
    )

    assert response["active_session"]["status"] == "completed"
    assert response["active_session"]["current_stage"] == "completed"
    assert response["active_session"]["exercise"]["type"] == "summary"
    assert response["active_session"]["exercise"]["finish_label"] == "Завершити тренування"


def test_ready_action_uses_shared_learning_service_and_returns_refreshed_session() -> None:
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service

    response = service.ready_action(
        {"telegram_user_id": 42, "interface_locale": "uk"},
        expected_stage="ready_en_uk",
        decision="yes",
    )

    assert response["screen"] == {
        "screen_id": "quiz_en_uk",
        "text": "next",
        "buttons": [],
        "documents": [],
        "keyboard_type": "inline",
        "clear_chat": False,
        "audio_path": None,
        "parse_mode": "HTML",
        "notice_text": None,
        "metadata": {},
    }
    assert response["active_session"]["exercise"] == {
        "type": "ready",
        "stage": "ready_en_uk",
        "title": "Знайомство зі словами завершено.\n\nПереходимо до практики.",
        "prompt": "Готові продовжувати?",
    }
    assert learning_service.client_learning_ready_action_service.calls == [
        {
            "telegram_user_id": 42,
            "session": service.db.learning_sessions.active_session,
            "locale": "uk",
            "expected_stage": "ready_en_uk",
            "decision": "yes",
        }
    ]


def test_start_uses_client_learning_start_service_and_claims_web_session() -> None:
    gateway = FakeTelegramGateway()
    db = FakeDb()
    db.learning_sessions = FakeLearningSessions()
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.telegram_gateway = gateway
    service.db = db
    service.learning_service = learning_service

    response = service.start({"telegram_user_id": 42, "chat_id": 100, "interface_locale": "uk"})

    assert response["screen"]["screen_id"] == "start:42"
    assert response["active_session"]["is_owned_by_web"] is True
    assert db.learning_sessions.claims == [(42, "client_web")]
    assert learning_service.client_learning_start_service.calls == [
        {"telegram_user_id": 42, "locale": "uk"}
    ]


def test_continue_session_advances_ready_stage_without_second_confirmation() -> None:
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service

    response = service.continue_session(
        {"telegram_user_id": 42, "interface_locale": "uk"},
    )

    assert response["active_session"]["exercise"] == {
        "type": "ready",
        "stage": "ready_en_uk",
        "title": "Знайомство зі словами завершено.\n\nПереходимо до практики.",
        "prompt": "Готові продовжувати?",
    }
    assert service.db.learning_sessions.claims == [(42, "client_web")]
    assert learning_service.client_learning_ready_action_service.calls == [
        {
            "telegram_user_id": 42,
            "session": service.db.learning_sessions.active_session,
            "locale": "uk",
            "expected_stage": "ready_en_uk",
            "decision": "yes",
        }
    ]


def test_continue_session_opens_completed_summary_instead_of_starting_new_session() -> None:
    learning_service = FakeLearningService()
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.learning_service = learning_service
    service.db.learning_sessions.active_session.update(
        {
            "status": "completed",
            "current_stage": "completed",
            "active_interface": "telegram_user",
        }
    )

    response = service.continue_session(
        {"telegram_user_id": 42, "interface_locale": "uk", "chat_id": 100},
    )

    assert response["active_session"]["status"] == "completed"
    assert response["active_session"]["is_owned_by_web"] is True
    assert response["active_session"]["exercise"]["type"] == "summary"
    assert service.db.learning_sessions.claims == [(42, "client_web")]


def test_finish_completed_summary_closes_resumable_web_session() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.db.learning_sessions.active_session.update(
        {
            "status": "completed",
            "current_stage": "completed",
            "active_interface": "client_web",
        }
    )

    response = service.finish({"telegram_user_id": 42, "interface_locale": "uk"})

    assert response == {"active_session": None}
    assert service.db.learning_sessions.active_session["current_stage"] == "finished"


def test_finish_rejects_summary_owned_by_other_interface() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.db.learning_sessions.active_session.update(
        {
            "status": "completed",
            "current_stage": "completed",
            "active_interface": "telegram_user",
        }
    )

    with pytest.raises(ClientWebLearningConflictError) as error:
        service.finish({"telegram_user_id": 42, "interface_locale": "uk"})

    assert error.value.detail == "Training session is active in another interface"


def test_audio_path_requires_current_session_word() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()

    response = service.audio_path({"telegram_user_id": 42}, session_word_id=11)

    assert response == "runtime/audio/frightening.mp3"


def test_web_quiz_uses_combined_similar_lookup_for_user_dictionary_word() -> None:
    service = ClientWebLearningService.__new__(ClientWebLearningService)
    service.db = FakeExerciseDb()
    service.db.learning_sessions.active_session.update(
        {
            "current_stage": "quiz_en_uk",
            "telegram_user_id": 42,
            "stage_queue_json": [11],
            "stage_position": 0,
            "active_interface": "client_web",
        }
    )
    original_get_session_word = service.db.learning_sessions.get_session_word

    def get_session_word(session_word_id: int):
        row = original_get_session_word(session_word_id)
        if row is not None:
            row["word_source"] = "user"
            row["word_id"] = 88
        return row

    service.db.learning_sessions.get_session_word = get_session_word

    payload = service._exercise(service.db.learning_sessions.active_session, "uk", telegram_user_id=42)

    assert payload["type"] == "quiz"
    assert service.db.similar_words.calls == [
        {
            "args": (88, 1),
            "kwargs": {"excluded_word_ids": [88], "limit": 8, "word_source": "user", "telegram_user_id": 42},
        }
    ]
