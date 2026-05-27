from __future__ import annotations

from datetime import datetime

from app.application.client_learning.card_action_service import ClientLearningCardActionService
from app.contracts import ScreenModel


class FakeCardActionDb:
    def __init__(self) -> None:
        self.active_session = {
            "id": 77,
            "telegram_user_id": 11,
            "language_level_id": 1,
            "level_run_id": 9,
            "stage_position": 0,
            "session_type": "regular",
        }
        self.session_words = [
            {"session_word_id": 501, "session_id": 77, "word_id": 101},
            {"session_word_id": 502, "session_id": 77, "word_id": 102},
        ]
        self.replacement: dict[str, object] | None = {"id": 103, "word": "write"}
        self.status_updates: list[tuple[int, str]] = []
        self.state_updates: list[dict[str, object]] = []
        self.progress_updates: list[dict[str, object]] = []
        self.replacements: list[tuple[int, int]] = []

    def get_session_word(self, session_word_id: int):
        return next((row for row in self.session_words if row["session_word_id"] == session_word_id), None)

    def get_session_words(self, session_id: int):
        return [row for row in self.session_words if row["session_id"] == session_id]

    def update_session_state(self, **kwargs) -> None:
        self.state_updates.append(kwargs)
        self.active_session["stage_position"] = kwargs["stage_position"]
        self.active_session["current_stage"] = kwargs["current_stage"]

    def get_active_session(self, telegram_user_id: int):
        return self.active_session

    def set_card_status(self, session_word_id: int, status: str) -> None:
        self.status_updates.append((session_word_id, status))

    def update_assignment_progress(self, telegram_user_id: int, word_id: int, **kwargs) -> None:
        self.progress_updates.append({"telegram_user_id": telegram_user_id, "word_id": word_id, **kwargs})

    def update(self, telegram_user_id: int, word_id: int, **kwargs) -> None:
        self.update_assignment_progress(telegram_user_id, word_id, **kwargs)

    def select_next_lesson_word(self, **kwargs):
        self.select_next_lesson_word_kwargs = kwargs
        return self.replacement

    def replace_session_word(self, session_word_id: int, word_id: int, *, word_source: str = "core") -> None:
        self.replacements.append((session_word_id, word_id))


class CaptureCardCallbacks:
    def __init__(self) -> None:
        self.now_value = datetime(2026, 4, 6, 10, 0, 0)
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def now(self) -> datetime:
        self.calls.append(("now", ()))
        return self.now_value

    def render(self, session, locale: str) -> ScreenModel:
        self.calls.append(("render", (session, locale)))
        return ScreenModel(screen_id=f"session:{session['id']}", text="session")

    def ready(self, session, locale: str) -> ScreenModel:
        self.calls.append(("ready", (session, locale)))
        return ScreenModel(screen_id="ready", text="ready", metadata=session.get("metadata", {}))


def build_service(db: FakeCardActionDb, callbacks: CaptureCardCallbacks) -> ClientLearningCardActionService:
    return ClientLearningCardActionService(
        db,
        db,
        db,
        current_time=callbacks.now,
        render_session_screen=callbacks.render,
        build_ready_screen=callbacks.ready,
    )


def test_card_action_rejects_invalid_payload_to_current_session() -> None:
    db = FakeCardActionDb()
    callbacks = CaptureCardCallbacks()

    screen = build_service(db, callbacks).handle_action(db.active_session, "uk", None, "known")

    assert screen.screen_id == "session:77"
    assert db.status_updates == []
    assert callbacks.calls == [("render", (db.active_session, "uk"))]


def test_card_action_back_moves_position_back() -> None:
    db = FakeCardActionDb()
    db.active_session["stage_position"] = 1
    callbacks = CaptureCardCallbacks()

    screen = build_service(db, callbacks).handle_action(db.active_session, "uk", 502, "back")

    assert screen.screen_id == "session:77"
    assert db.state_updates[-1]["stage_position"] == 0
    assert db.state_updates[-1]["current_stage"] == "card"


def test_card_action_quiz_opens_ready_screen_and_clears_previous_card() -> None:
    db = FakeCardActionDb()
    db.active_session["stage_position"] = 1
    callbacks = CaptureCardCallbacks()

    screen = build_service(db, callbacks).handle_action(db.active_session, "uk", 502, "quiz")

    assert screen.screen_id == "ready"
    assert db.state_updates[-1]["current_stage"] == "ready_en_uk"
    assert db.state_updates[-1]["stage_position"] == 2
    assert screen.metadata["clear_previous_card"] is True


def test_card_action_known_marks_word_and_uses_replacement() -> None:
    db = FakeCardActionDb()
    callbacks = CaptureCardCallbacks()

    screen = build_service(db, callbacks).handle_action(db.active_session, "uk", 501, "known")

    assert screen.screen_id == "session:77"
    assert db.status_updates == [(501, "known")]
    assert db.progress_updates[0]["is_known"] is True
    assert db.progress_updates[0]["learning_state"] == "learned"
    assert db.progress_updates[0]["current_time"] == callbacks.now_value
    assert db.select_next_lesson_word_kwargs["excluded_word_ids"] == [101, 102]
    assert db.replacements == [(501, 103)]
    assert db.state_updates[-1]["stage_position"] == 0


def test_card_action_accepts_explicit_user_id_without_session_telegram_id() -> None:
    db = FakeCardActionDb()
    callbacks = CaptureCardCallbacks()
    session = {key: value for key, value in db.active_session.items() if key != "telegram_user_id"}

    screen = build_service(db, callbacks).handle_action(
        session,
        "uk",
        501,
        "known",
        telegram_user_id=11,
    )

    assert screen.screen_id == "session:77"
    assert db.progress_updates[0]["telegram_user_id"] == 11
    assert db.select_next_lesson_word_kwargs["telegram_user_id"] == 11


def test_card_action_next_advances_position_without_known_progress() -> None:
    db = FakeCardActionDb()
    callbacks = CaptureCardCallbacks()

    screen = build_service(db, callbacks).handle_action(db.active_session, "uk", 501, "next")

    assert screen.screen_id == "session:77"
    assert db.status_updates == [(501, "next")]
    assert db.progress_updates == []
    assert db.state_updates[-1]["stage_position"] == 1
