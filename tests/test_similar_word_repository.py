from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from app.data_access.similar_words import SimilarWordRepository
from app.models import DictionaryEntry, User, UserDictionaryEntry


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self):
        return self

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeSession:
    def __init__(
        self,
        *,
        source: DictionaryEntry | UserDictionaryEntry | None,
        vector_rows: list[DictionaryEntry] | None = None,
        user_vector_rows: list[UserDictionaryEntry] | None = None,
        fallback_rows: list[DictionaryEntry] | None = None,
        user_fallback_rows: list[UserDictionaryEntry] | None = None,
        random_rows: list[DictionaryEntry] | None = None,
        user_random_rows: list[UserDictionaryEntry] | None = None,
        user_uuid: str | None = None,
        source_part_of_speech: str | None = "noun",
    ) -> None:
        self.source = source
        self.vector_rows = list(vector_rows or [])
        self.user_vector_rows = list(user_vector_rows or [])
        self.fallback_rows = list(fallback_rows or [])
        self.user_fallback_rows = list(user_fallback_rows or [])
        self.random_rows = list(random_rows or [])
        self.user_random_rows = list(user_random_rows or [])
        self.user_uuid = user_uuid
        self.source_part_of_speech = source_part_of_speech
        self.execute_calls = 0
        self.scalars_calls = 0
        self.scalar_calls = 0

    def get(self, model, primary_key):
        if model is User and self.user_uuid is not None:
            return User(uuid=self.user_uuid, telegram_user_id=primary_key)
        if model is User:
            return None
        return self.source

    def execute(self, statement):
        self.execute_calls += 1
        if self.execute_calls == 1:
            return FakeResult(self.vector_rows)
        return FakeResult(self.user_vector_rows)

    def scalars(self, statement):
        self.scalars_calls += 1
        if self.scalars_calls == 1:
            return FakeResult(self.fallback_rows)
        if self.user_uuid is not None and self.scalars_calls == 2:
            return FakeResult(self.user_fallback_rows)
        random_call = 3 if self.user_uuid is not None else 2
        if self.scalars_calls == random_call:
            return FakeResult(self.random_rows)
        return FakeResult(self.user_random_rows)

    def scalar(self, statement):
        self.scalar_calls += 1
        return self.source_part_of_speech


class FakeSessionManager:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    @contextmanager
    def session(self):
        yield self._session


def make_entry(entry_id: int, word: str, *, embedding=None) -> DictionaryEntry:
    return DictionaryEntry(
        id=entry_id,
        source_namespace="core",
        source_ref=f"core:{word}",
        entry_key=f"{word}__entry",
        word=word,
        normalized_word=word,
        level_id=2,
        transcription=f"/{word}/",
        translation_uk=f"{word}-uk",
        translation_ru=f"{word}-ru",
        translation_pl=f"{word}-pl",
        audio_path=f"audio/{word}.mp3",
        examples_json=[f"{word} example"],
        embedding=embedding,
        entry_type="word",
        is_archived=False,
    )


def make_user_entry(entry_id: int, word: str, *, embedding=None) -> UserDictionaryEntry:
    return UserDictionaryEntry(
        id=entry_id,
        word=word,
        normalized_word=word,
        entry_key=f"{word}__user__entry",
        entry_type="word",
        part_of_speech="noun",
        level_id=2,
        transcription=f"/{word}/",
        translation_uk=f"{word}-uk",
        translation_ru=f"{word}-ru",
        translation_pl=f"{word}-pl",
        examples_json=[f"{word} example"],
        audio_path=f"word_base/user/noun/{word}.mp3",
        embedding=embedding,
        embedding_model="test-model" if embedding is not None else None,
        is_embedding_ready=embedding is not None,
        status="ready_for_rotation",
    )


def patch_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.data_access.similar_words.load_dictionary_entry_metadata",
        lambda db_session, entry_ids: {
            int(entry_id): {"parts_of_speech": [f"pos-{entry_id}"], "categories": [f"cat-{entry_id}"]}
            for entry_id in entry_ids
        },
    )


def test_find_similar_words_returns_empty_when_source_missing() -> None:
    session = FakeSession(source=None)
    repository = SimilarWordRepository(FakeSessionManager(session))

    payload = repository.find_similar_words(word_id=1, level_id=2, excluded_word_ids=[], limit=3)

    assert payload == []
    assert session.execute_calls == 0
    assert session.scalars_calls == 0


def test_find_similar_words_uses_vector_rows_then_fallback(monkeypatch) -> None:
    patch_metadata(monkeypatch)
    session = FakeSession(
        source=make_entry(1, "source", embedding=[0.1, 0.2]),
        vector_rows=[make_entry(2, "near", embedding=[0.1, 0.3])],
        fallback_rows=[make_entry(3, "fallback")],
    )
    repository = SimilarWordRepository(FakeSessionManager(session))

    payload = repository.find_similar_words(word_id=1, level_id=2, excluded_word_ids=[1], limit=2)

    assert [row["word"] for row in payload] == ["near", "fallback"]
    assert payload[0]["has_embedding"] is True
    assert payload[1]["part_of_speech"] == "pos-3"
    assert session.execute_calls == 1
    assert session.scalars_calls == 1


def test_find_similar_words_skips_translation_overlap_from_vector_and_fallback(monkeypatch) -> None:
    patch_metadata(monkeypatch)
    session = FakeSession(
        source=make_entry(1, "warehouse", embedding=[0.1, 0.2]),
        vector_rows=[
            make_entry(2, "storage", embedding=[0.1, 0.3]),
            make_entry(3, "office", embedding=[0.2, 0.3]),
        ],
        fallback_rows=[
            make_entry(4, "depot"),
            make_entry(5, "harbor"),
        ],
    )
    session.source.translation_uk = "склад, сховище"
    session.vector_rows[0].translation_uk = "склад"
    session.vector_rows[1].translation_uk = "офіс"
    session.fallback_rows[0].translation_uk = "сховище"
    session.fallback_rows[1].translation_uk = "гавань"
    repository = SimilarWordRepository(FakeSessionManager(session))

    payload = repository.find_similar_words(word_id=1, level_id=2, excluded_word_ids=[1], limit=2)

    assert [row["word"] for row in payload] == ["office", "harbor"]


def test_find_similar_words_uses_only_fallback_without_source_embedding(monkeypatch) -> None:
    patch_metadata(monkeypatch)
    session = FakeSession(
        source=make_entry(1, "source"),
        fallback_rows=[make_entry(4, "alpha"), make_entry(5, "beta")],
    )
    repository = SimilarWordRepository(FakeSessionManager(session))

    payload = repository.find_similar_words(word_id=1, level_id=2, excluded_word_ids=[], limit=2)

    assert [row["word"] for row in payload] == ["alpha", "beta"]
    assert session.execute_calls == 0
    assert session.scalars_calls == 1


def test_find_similar_words_skips_fallback_when_vector_rows_fill_limit(monkeypatch) -> None:
    patch_metadata(monkeypatch)
    session = FakeSession(
        source=make_entry(1, "source", embedding=[0.1, 0.2]),
        vector_rows=[make_entry(6, "one", embedding=[0.1]), make_entry(7, "two", embedding=[0.2])],
        fallback_rows=[make_entry(8, "unused")],
    )
    repository = SimilarWordRepository(FakeSessionManager(session))

    payload = repository.find_similar_words(word_id=1, level_id=2, excluded_word_ids=[1], limit=2)

    assert [row["word"] for row in payload] == ["one", "two"]
    assert session.execute_calls == 1
    assert session.scalars_calls == 0


def test_find_similar_words_uses_random_cross_collection_fallback_when_level_rows_are_short(monkeypatch) -> None:
    patch_metadata(monkeypatch)
    idiom = make_entry(9, "break the ice")
    idiom.entry_type = "idiom"
    session = FakeSession(
        source=make_entry(1, "source"),
        fallback_rows=[make_entry(4, "alpha")],
        random_rows=[idiom, make_entry(10, "source-copy")],
    )
    session.random_rows[1].translation_uk = "source-uk"
    repository = SimilarWordRepository(FakeSessionManager(session))

    payload = repository.find_similar_words(word_id=1, level_id=2, excluded_word_ids=[1], limit=2)

    assert [row["word"] for row in payload] == ["alpha", "break the ice"]
    assert payload[1]["entry_type"] == "idiom"
    assert session.execute_calls == 0
    assert session.scalars_calls == 2


def test_find_similar_words_combines_core_and_user_dictionary_fallback(monkeypatch) -> None:
    patch_metadata(monkeypatch)
    session = FakeSession(
        source=make_entry(1, "source"),
        fallback_rows=[make_entry(4, "alpha")],
        user_fallback_rows=[make_user_entry(88, "carry on")],
        user_uuid="00000000-0000-0000-0000-000000000042",
    )
    repository = SimilarWordRepository(FakeSessionManager(session))

    payload = repository.find_similar_words(
        word_id=1,
        level_id=2,
        excluded_word_ids=[1],
        limit=2,
        telegram_user_id=42,
    )

    assert [row["word"] for row in payload] == ["alpha", "carry on"]
    assert [row.get("word_source", "core") for row in payload] == ["core", "user"]


def test_find_similar_words_uses_user_dictionary_source_and_core_distractors(monkeypatch) -> None:
    patch_metadata(monkeypatch)
    session = FakeSession(
        source=make_user_entry(88, "carry on"),
        fallback_rows=[make_entry(4, "alpha")],
        user_fallback_rows=[make_user_entry(89, "keep going")],
        user_uuid="00000000-0000-0000-0000-000000000042",
    )
    repository = SimilarWordRepository(FakeSessionManager(session))

    payload = repository.find_similar_words(
        word_id=88,
        level_id=2,
        excluded_word_ids=[88],
        limit=2,
        word_source="user",
        telegram_user_id=42,
    )

    assert [row["word"] for row in payload] == ["alpha", "keep going"]
    assert [row.get("word_source", "core") for row in payload] == ["core", "user"]
