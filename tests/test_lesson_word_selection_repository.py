from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from sqlalchemy.dialects import postgresql

from app.config import Settings
from app.data_access.lesson_word_selection import (
    LessonWordSelectionRepository,
    build_lesson_bucket_quotas,
    build_lesson_entry_type_quotas,
)
from app.models import User

USER_UUID = UUID("11111111-1111-4111-8111-111111111111")


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeSession:
    def __init__(
        self,
        *,
        row_by_key: dict[Any, Any] | None = None,
        execute_rows: list[list[Any]] | None = None,
        scalar_values: list[Any] | None = None,
        scalars_rows: list[list[Any]] | None = None,
    ) -> None:
        self.row_by_key = row_by_key or {}
        self.execute_rows = list(execute_rows or [])
        self.scalar_values = list(scalar_values or [])
        self.scalars_rows = list(scalars_rows or [])
        self.executed_statements: list[Any] = []
        self.added: list[Any] = []

    def get(self, model, primary_key):
        return self.row_by_key.get((model, primary_key))

    def execute(self, statement):
        self.executed_statements.append(statement)
        return FakeResult(self.execute_rows.pop(0) if self.execute_rows else [])

    def scalar(self, statement):
        return self.scalar_values.pop(0) if self.scalar_values else None

    def scalars(self, statement):
        return FakeResult(self.scalars_rows.pop(0) if self.scalars_rows else [])

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        pass


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


class FakeStatement:
    def __init__(self) -> None:
        self.limit_value: int | None = None

    def limit(self, value: int):
        self.limit_value = value
        return self


class SelectionRepositoryStub(LessonWordSelectionRepository):
    def __init__(self, session_manager: FakeSessionManager, settings: Settings, fetch_results: list[list[dict[str, Any]]]):
        super().__init__(session_manager, settings)
        self.fetch_results = list(fetch_results)
        self.fetch_limits: list[int] = []

    def _fetch_word_candidates(self, session, stmt, limit: int) -> list[dict[str, Any]]:
        self.fetch_limits.append(limit)
        return self.fetch_results.pop(0) if self.fetch_results else []

    def _fetch_user_word_candidates(self, session, stmt, limit: int) -> list[dict[str, Any]]:
        self.fetch_limits.append(limit)
        return self.fetch_results.pop(0) if self.fetch_results else []


def build_settings() -> Settings:
    return Settings(
        bot_token="token",
        db_host="localhost",
        db_port=5432,
        db_name="cronolex",
        db_user="user",
        db_password="password",
        app_env="test",
        app_timezone="Europe/Kyiv",
        app_host="127.0.0.1",
        app_port=8000,
        app_api_base_url="http://127.0.0.1:8000",
        app_bot_enabled=False,
        app_bot_reminder_poll_minutes=5,
        app_bot_message_cleanup_poll_minutes=60,
        app_bot_message_retention_days=30,
        app_db_pool_min_size=4,
        app_db_pool_max_size=20,
        app_api_workers=2,
        app_word_cooldown_days=2,
        app_review_mix_percent=30,
    )


def make_entry(entry_id: int, word: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=entry_id,
        word=word,
        transcription=f"/{word}/",
        audio_path=f"audio/{word}.mp3",
        examples_json=[],
        level_id=1,
        embedding=None,
        translation_uk=f"{word}-uk",
        translation_ru=f"{word}-ru",
        translation_pl=f"{word}-pl",
        entry_type="word",
        is_archived=False,
    )


def test_fetch_word_candidates_maps_metadata_priority_and_review(monkeypatch) -> None:
    entry = make_entry(101, "priority")
    stmt = FakeStatement()
    session = FakeSession(execute_rows=[[(entry, 7, 1)]])
    repository = LessonWordSelectionRepository(FakeSessionManager(session), build_settings())

    monkeypatch.setattr(
        "app.data_access.lesson_word_selection.load_dictionary_entry_metadata",
        lambda db_session, entry_ids: {101: {"parts_of_speech": ["noun"], "categories": ["work"]}},
    )

    payload = repository._fetch_word_candidates(session, stmt, 3)

    assert stmt.limit_value == 3
    assert payload == [
        {
            "id": 101,
            "word": "priority",
            "part_of_speech": "noun",
            "parts_of_speech": ["noun"],
            "categories": ["work"],
            "phonetic_us": "/priority/",
            "audio_path": "audio/priority.mp3",
            "examples_json": [],
            "level_id": 1,
            "level_title": None,
            "has_embedding": False,
            "translation_uk": "priority-uk",
            "translation_ru": "priority-ru",
            "translation_pl": "priority-pl",
            "entry_type": "word",
            "is_archived": False,
            "is_teacher_verified": False,
            "teacher_verified_by_user_uuid": None,
            "teacher_verified_at": None,
            "review_priority": 7,
            "is_priority": True,
            "priority_rank": 1,
            "priority_state": "none",
            "last_seen_at": None,
            "next_review_at": None,
            "learning_state": "learning",
            "word_source": "core",
            "word_id": 101,
        }
    ]


def test_select_lesson_words_keeps_priority_words_ahead_of_regular_words() -> None:
    active_level_run = SimpleNamespace(id=1)
    session = FakeSession(row_by_key={(User, 1): User(uuid=USER_UUID, telegram_user_id=1)}, scalar_values=[active_level_run])
    repository = SelectionRepositoryStub(
        FakeSessionManager(session),
        build_settings(),
        [
            [
                {
                    "id": 101,
                    "word": "older priority",
                    "word_source": "user",
                    "word_id": 101,
                    "translation_uk": "старіший пріоритет",
                    "is_priority": True,
                    "priority_rank": 1_777_000_000,
                },
            ],
            [
                {
                    "id": 103,
                    "word": "newer priority",
                    "word_source": "core",
                    "word_id": 103,
                    "translation_uk": "новіший пріоритет",
                    "is_priority": True,
                    "priority_rank": 1_778_000_000,
                },
            ],
            [{"id": 102, "word": "regular", "translation_uk": "звичайне", "is_priority": False}],
        ],
    )

    payload = repository.select_lesson_words(telegram_user_id=1, level_id=1, words_limit=3)

    assert [row["word"] for row in payload] == ["newer priority", "regular"]
    assert "older priority" not in [row["word"] for row in payload]


def test_select_lesson_words_fills_remaining_review_candidates() -> None:
    repository = SelectionRepositoryStub(
        FakeSessionManager(
            FakeSession(row_by_key={(User, 1): User(uuid=USER_UUID, telegram_user_id=1)}, scalar_values=[SimpleNamespace(id=1)])
        ),
        build_settings(),
        [
            [],
            [],
            [],
            [{"id": 101, "word": "review", "is_priority": False}],
            [],
            [],
            [],
            [{"id": 102, "word": "fresh", "is_priority": False}],
            [{"id": 103, "word": "remaining", "is_priority": False}],
        ],
    )

    payload = repository.select_lesson_words(telegram_user_id=1, level_id=1, words_limit=4)

    assert [row["word"] for row in payload] == ["review", "fresh", "remaining"]


def test_build_lesson_entry_type_quotas_uses_ten_percent_with_minimum_one() -> None:
    assert build_lesson_entry_type_quotas(2) == {}
    assert build_lesson_entry_type_quotas(10) == {"idiom": 1, "phrase_pattern": 1, "phrasal_verb": 1}
    assert build_lesson_entry_type_quotas(15) == {"idiom": 2, "phrase_pattern": 2, "phrasal_verb": 2}


def test_build_lesson_bucket_quotas_limits_priority_share() -> None:
    assert build_lesson_bucket_quotas(30) == {"due": 12, "priority": 7, "needs_work": 6, "fresh": 5}
    assert build_lesson_bucket_quotas(3) == {"due": 1, "priority": 1, "needs_work": 0, "fresh": 1}


def test_select_lesson_words_does_not_let_priority_fill_whole_session_when_fresh_exists() -> None:
    priority_words = [
        {
            "id": 1_000 + index,
            "word": f"priority {index}",
            "word_source": "core",
            "word_id": 1_000 + index,
            "translation_uk": "пріоритет",
            "is_priority": True,
            "priority_rank": 1_777_000_000 + index,
        }
        for index in range(30)
    ]
    first_fresh_words = [
        {"id": 2_000 + index, "word": f"fresh {index}", "translation_uk": "нове", "is_priority": False}
        for index in range(5)
    ]
    backfill_fresh_words = [
        {"id": 3_000 + index, "word": f"backfill {index}", "translation_uk": "добір", "is_priority": False}
        for index in range(18)
    ]
    repository = SelectionRepositoryStub(
        FakeSessionManager(
            FakeSession(row_by_key={(User, 1): User(uuid=USER_UUID, telegram_user_id=1)}, scalar_values=[SimpleNamespace(id=1)])
        ),
        build_settings(),
        [
            [],
            [],
            priority_words,
            [],
            [],
            [],
            [],
            [],
            [],
            first_fresh_words,
            [],
            [],
            [],
            [],
            [],
            backfill_fresh_words,
        ],
    )

    payload = repository.select_lesson_words(telegram_user_id=1, level_id=1, words_limit=30)

    assert len(payload) == 30
    assert sum(1 for word in payload if word.get("is_priority")) == 7
    assert sum(1 for word in payload if not word.get("is_priority")) == 23


def test_select_lesson_words_caps_large_pending_priority_batches() -> None:
    priority_words = [
        {
            "id": 10_000 + index,
            "word": f"priority {index}",
            "word_source": "core",
            "word_id": 10_000 + index,
            "translation_uk": "пріоритет",
            "is_priority": True,
            "priority_rank": 1_777_000_000 + index,
        }
        for index in range(160)
    ]
    repository = SelectionRepositoryStub(
        FakeSessionManager(
            FakeSession(
                row_by_key={(User, 1): User(uuid=USER_UUID, telegram_user_id=1)},
                scalar_values=[SimpleNamespace(id=1)],
            )
        ),
        build_settings(),
        _priority_only_fetch_results(priority_words),
    )

    payload = repository.select_lesson_words(telegram_user_id=1, level_id=1, words_limit=30)

    assert len(payload) == 7
    assert all(word.get("is_priority") for word in payload)


def test_regular_assignment_selection_excludes_pending_priority_state() -> None:
    session = FakeSession()
    repository = LessonWordSelectionRepository(FakeSessionManager(session), build_settings())
    current_time = datetime(2026, 5, 11, 12, 0, 0)

    repository._extend_with_due_assignments(
        session,
        [],
        set(),
        USER_UUID,
        1,
        7,
        current_time=current_time,
        cooldown_boundary=current_time,
    )
    repository._extend_with_user_assignments(
        session,
        [],
        set(),
        USER_UUID,
        7,
        current_time=current_time,
        cooldown_boundary=current_time,
    )

    compiled_sql = "\n".join(
        str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        for statement in session.executed_statements
    )
    assert compiled_sql.count("user_word_assignment.priority_state != 'pending'") >= 3


def test_select_lesson_words_rotates_large_priority_batches_with_fresh_backfill() -> None:
    priority_words = [
        {
            "id": 10_000 + index,
            "word": f"priority {index}",
            "word_source": "core",
            "word_id": 10_000 + index,
            "translation_uk": "пріоритет",
            "is_priority": True,
            "priority_rank": 1_777_000_000 + index,
        }
        for index in range(160)
    ]
    fresh_words = [
        {
            "id": 20_000 + index,
            "word": f"fresh {index}",
            "word_source": "core",
            "word_id": 20_000 + index,
            "translation_uk": "нове",
            "is_priority": False,
        }
        for index in range(160)
    ]
    selected_batches = []
    for offset in (0, 30, 60):
        repository = SelectionRepositoryStub(
            FakeSessionManager(
                FakeSession(
                    row_by_key={(User, 1): User(uuid=USER_UUID, telegram_user_id=1)},
                    scalar_values=[SimpleNamespace(id=1)],
                )
            ),
            build_settings(),
            _priority_with_fresh_fetch_results(
                priority_words[offset : offset + 7],
                fresh_words[offset : offset + 23],
            ),
        )

        selected_batches.append(
            [
                word["word_id"]
                for word in repository.select_lesson_words(telegram_user_id=1, level_id=1, words_limit=30)
            ]
        )

    assert all(len(batch) == 30 for batch in selected_batches)
    assert all(sum(1 for word_id in batch if word_id < 20_000) == 7 for batch in selected_batches)
    assert len({tuple(batch) for batch in selected_batches}) == 3
    assert set(selected_batches[0]).isdisjoint(selected_batches[1])
    assert set(selected_batches[1]).isdisjoint(selected_batches[2])


def test_pending_priority_selection_filters_out_introduced_priority_state() -> None:
    session = FakeSession()
    repository = LessonWordSelectionRepository(FakeSessionManager(session), build_settings())

    repository._extend_with_pending_priority_assignments(session, [], set(), USER_UUID, 7)

    compiled_sql = "\n".join(
        str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        for statement in session.executed_statements
    )
    assert "user_word_assignment.priority_state = 'pending'" in compiled_sql
    assert "user_word_assignment.priority_rank > 0" in compiled_sql


def test_select_lesson_words_prefills_entry_type_quotas_when_available() -> None:
    repository = SelectionRepositoryStub(
        FakeSessionManager(
            FakeSession(row_by_key={(User, 1): User(uuid=USER_UUID, telegram_user_id=1)}, scalar_values=[SimpleNamespace(id=1)])
        ),
        build_settings(),
        [
            [],
            [],
            [],
            [],
            [{"id": 101, "word": "review idiom", "entry_type": "idiom", "is_priority": False}],
            [{"id": 102, "word": "make smb do smth", "entry_type": "phrase_pattern", "is_priority": False}],
            [{"id": 103, "word": "carry on", "entry_type": "phrasal_verb", "is_priority": False}],
            [
                {"id": 104, "word": "regular", "entry_type": "word", "is_priority": False},
            ],
            [],
        ],
    )

    payload = repository.select_lesson_words(telegram_user_id=1, level_id=1, words_limit=10)

    assert [row["entry_type"] for row in payload[:4]] == ["idiom", "phrase_pattern", "phrasal_verb", "word"]


def test_select_next_lesson_word_returns_first_candidate() -> None:
    session = FakeSession(row_by_key={(User, 1): User(uuid=USER_UUID, telegram_user_id=1)}, scalar_values=[SimpleNamespace(id=10)])
    repository = SelectionRepositoryStub(
        FakeSessionManager(session),
        build_settings(),
        [[], [], [{"id": 201, "word": "next", "is_priority": False}]],
    )

    payload = repository.select_next_lesson_word(telegram_user_id=1, level_id=1, excluded_word_ids=[101])

    assert payload == {"id": 201, "word": "next", "is_priority": False}
    assert repository.fetch_limits == [1, 1, 1, 1]


def test_select_next_lesson_word_returns_none_without_candidates() -> None:
    repository = SelectionRepositoryStub(
        FakeSessionManager(FakeSession(row_by_key={(User, 1): User(uuid=USER_UUID, telegram_user_id=1)})),
        build_settings(),
        [[]],
    )

    payload = repository.select_next_lesson_word(telegram_user_id=1, level_id=1, excluded_word_ids=[])

    assert payload is None


def test_create_core_assignments_uses_conflict_safe_bulk_insert() -> None:
    session = FakeSession()
    repository = LessonWordSelectionRepository(FakeSessionManager(session), build_settings())

    repository._create_core_assignments(
        session,
        USER_UUID,
        [{"id": 301, "word": "repeat"}],
        current_time=datetime(2026, 5, 4, 12, 0, 0),
    )

    assert session.added == []
    assert len(session.executed_statements) == 1
    compiled = str(session.executed_statements[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT" in compiled
    assert "DO NOTHING" in compiled


def test_select_followup_words_maps_mixed_session_candidates(monkeypatch) -> None:
    entry = make_entry(301, "repeat")
    user_entry = SimpleNamespace(
        id=88,
        word="carry on",
        part_of_speech="phrasal verb",
        transcription="/carry on/",
        audio_path="word_base/user/phrasal_verb/carry-on.mp3",
        examples_json=["Carry on."],
        level_id=1,
        level=None,
        embedding=None,
        translation_uk="продовжувати",
        translation_ru="продолжать",
        translation_pl="kontynuowac",
        entry_type="phrasal_verb",
        status="ready_for_rotation",
    )
    session_words = [
        SimpleNamespace(word_source="core", word_id=301, card_status="next", item_order=1),
        SimpleNamespace(word_source="user", word_id=88, card_status="next", item_order=2),
    ]
    assignment_rows = [
        SimpleNamespace(word_source="core", word_id=301, review_priority=4),
        SimpleNamespace(word_source="user", word_id=88, review_priority=7),
    ]
    session = FakeSession(
        scalar_values=[SimpleNamespace(id=5, user_uuid=USER_UUID)],
        scalars_rows=[
            session_words,
            [entry],
            [user_entry],
            assignment_rows,
        ],
    )
    repository = LessonWordSelectionRepository(FakeSessionManager(session), build_settings())

    monkeypatch.setattr(
        "app.data_access.lesson_selection_payloads.load_dictionary_entry_metadata",
        lambda db_session, entry_ids: {301: {"parts_of_speech": ["verb"], "categories": ["daily"]}},
    )

    payload = repository.select_followup_words(source_session_id=5)

    assert payload[0]["word"] == "repeat"
    assert payload[0]["part_of_speech"] == "verb"
    assert payload[0]["categories"] == ["daily"]
    assert payload[0]["review_priority"] == 4
    assert payload[1]["word"] == "carry on"
    assert payload[1]["word_source"] == "user"
    assert payload[1]["review_priority"] == 7


def _priority_only_fetch_results(priority_words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [
        [],
        [],
        priority_words[:7],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        priority_words[7:],
        [],
    ]


def _priority_with_fresh_fetch_results(
    priority_words: list[dict[str, Any]],
    fresh_words: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    return [
        [],
        [],
        priority_words,
        [],
        [],
        [],
        [],
        [],
        [],
        fresh_words[:5],
        [],
        [],
        [],
        [],
        [],
        fresh_words[5:],
    ]
