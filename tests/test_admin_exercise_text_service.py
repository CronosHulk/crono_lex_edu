from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.application.admin.exercise_texts.errors import (
    AdminExerciseTextGenerationError,
    AdminExerciseTextServiceError,
    AdminExerciseTextTTSError,
    admin_exercise_text_generation_error_status_code,
    admin_exercise_text_service_error_status_code,
    admin_exercise_text_tts_error_status_code,
)
from app.application.admin.exercise_texts.exercise_text_service import AdminExerciseTextService
from app.application.admin.exercise_texts.generation_service import (
    AdminExerciseTextGenerationService,
)
from app.application.admin.exercise_texts.providers import (
    ExerciseTextGenerationResult,
    ExerciseTextTTSResult,
)
from app.application.admin.exercise_texts.tts_service import (
    AdminExerciseTextTTSService,
    _audio_file_path,
)
from app.domain.exercise_texts.errors import ExerciseTextVersionConflictError
from app.external_providers.usage import ProviderUsage
from app.time_utils import TimeService


class FakeAclPermissions:
    def __init__(self, disabled_actions: set[str] | None = None) -> None:
        self.disabled_actions = disabled_actions or set()

    def get_effective_rule(self, *, group_title, action, environment):
        if action in self.disabled_actions:
            return "disabled"
        return "enabled"

    def list_group_capabilities(self, *, group_title, environment):
        return []


class FakeExerciseTextRepository:
    def __init__(self) -> None:
        self.items: dict[int, dict[str, Any]] = {}
        self.next_id = 1
        self.last_list_kwargs: dict[str, Any] = {}

    def list_page(self, **kwargs) -> dict[str, Any]:
        self.last_list_kwargs = kwargs
        items = [deepcopy(item) for item in self.items.values() if item["status"] != "archived"]
        return {"items": items, "total": len(items), "page": kwargs["page"], "page_size": kwargs["page_size"], "pages": 1 if items else 0}

    def get(self, exercise_text_id: int) -> dict[str, Any] | None:
        item = self.items.get(exercise_text_id)
        return deepcopy(item) if item is not None else None

    def create(self, **kwargs) -> dict[str, Any]:
        item_id = self.next_id
        self.next_id += 1
        item = {
            "id": item_id,
            "uuid": f"00000000-0000-4000-8000-{item_id:012d}",
            "title": kwargs.get("title"),
            "status": kwargs.get("status", "draft"),
            "difficulty_band": kwargs.get("difficulty_band"),
            "text_types": kwargs.get("text_types") or [],
            "content_jsonb": kwargs.get("content_jsonb") or {},
            "version": 1,
            "topic_ids": kwargs.get("topic_ids") or [],
            "published_at": None,
            "archived_at": None,
            "created": kwargs.get("current_time"),
            "updated": kwargs.get("current_time"),
        }
        self.items[item_id] = item
        return deepcopy(item)

    def update(self, exercise_text_id: int, *, expected_version: int, values: dict[str, Any], topic_ids=None, **kwargs) -> dict[str, Any] | None:
        item = self.items.get(exercise_text_id)
        if item is None:
            return None
        if item["version"] != expected_version:
            raise ExerciseTextVersionConflictError("conflict")
        item.update(values)
        if topic_ids is not None:
            item["topic_ids"] = topic_ids
        item["version"] += 1
        item["updated"] = kwargs.get("current_time")
        return deepcopy(item)


class FakeGrammarTopics:
    def list_active(self) -> list[dict[str, Any]]:
        return [
            {"id": 1, "code": "past-simple", "level": "A1", "min_level": "A1", "title": "Past Simple", "is_active": True},
            {"id": 2, "code": "inversion", "level": "C1", "min_level": "C1", "title": "Inversion", "is_active": True},
        ]


class FakeTTSVoices:
    def list_active(self, *, provider=None) -> list[dict[str, Any]]:
        return [{"id": 1, "provider": provider or "google_tts", "code": "en-US-Neural2-C", "language_code": "en-US"}]


class FakeTaskLogs:
    def __init__(self) -> None:
        self.rows: dict[int, dict[str, Any]] = {}
        self.next_id = 1

    def create_for_user_uuid(self, **kwargs) -> dict[str, Any]:
        row = {"id": self.next_id, **kwargs}
        self.next_id += 1
        self.rows[row["id"]] = row
        return deepcopy(row)

    def update(self, task_log_id: int, **kwargs) -> dict[str, Any] | None:
        row = self.rows.get(task_log_id)
        if row is None:
            return None
        row.update(kwargs)
        return deepcopy(row)

    def get(self, task_log_id: int) -> dict[str, Any] | None:
        row = self.rows.get(task_log_id)
        return deepcopy(row) if row is not None else None


class FakeAIUsageSessions:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def accumulate(self, **kwargs) -> dict[str, Any]:
        self.calls.append(kwargs)
        return kwargs


class FakeExternalProviderSettings:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def get_map(self) -> dict[str, dict[str, Any]]:
        return deepcopy(self.rows)


class FakeDb:
    def __init__(self) -> None:
        self.settings = type("Settings", (), {"app_exercise_text_audio_dir": "word_base/exercise_texts/audio"})()
        self.acl_permissions = FakeAclPermissions()
        self.exercise_texts = FakeExerciseTextRepository()
        self.grammar_topics = FakeGrammarTopics()
        self.tts_voices = FakeTTSVoices()
        self.task_logs = FakeTaskLogs()
        self.ai_usage_sessions = FakeAIUsageSessions()
        self.external_provider_settings = FakeExternalProviderSettings()


def localized(content: str) -> dict[str, Any]:
    return {
        "source": {"lang": "en", "content": content},
        "translations": [
            {"lang": "uk", "content": f"uk {content}"},
            {"lang": "ru", "content": f"ru {content}"},
            {"lang": "pl", "content": f"pl {content}"},
        ],
    }


def valid_publishable_content() -> dict[str, Any]:
    paragraphs = [
        {
            "id": "pg_valid_1",
            "status": {"content": "completed", "translations": "completed", "quiz": "completed"},
            "text": localized("One opens a door. Two enters a room. Three sits down."),
        },
        {
            "id": "pg_valid_2",
            "status": {"content": "completed", "translations": "completed", "quiz": "completed"},
            "text": localized("One reads a book. Two writes a note. Three asks a question."),
        },
        {
            "id": "pg_valid_3",
            "status": {"content": "completed", "translations": "completed", "quiz": "completed"},
            "text": localized("One starts a call. Two shares a screen. Three ends the lesson."),
        },
    ]
    questions = []
    for index, paragraph in enumerate(paragraphs, start=1):
        text = paragraph["text"]["source"]["content"]
        quote = text.split(".")[0] + "."
        questions.append(
            {
                "id": f"qz_valid_{index}",
                "paragraph_ids": [paragraph["id"]],
                "question": localized("What happens?"),
                "options": [
                    {
                        "id": f"op_valid_{index}_{suffix}",
                        "text": localized("Answer."),
                        "is_correct": suffix == "a",
                        "evidence_quote": quote,
                        "evidence_span": {"paragraph_id": paragraph["id"], "start_char": 0, "end_char": len(quote)},
                        "explanation": localized("Explanation."),
                    }
                    for suffix in ("a", "b", "c")
                ],
            }
        )
    return {
        "schema_version": 1,
        "generation_state": {"content": "completed", "translations": "completed", "quiz": "completed"},
        "generated": {
            "title": "Publishable",
            "ai_metadata": {"prompt_versions": {"content": "c1", "translations": "t1", "quiz": "q1"}},
            "difficulty": {"band": "A1_A2"},
            "text_types": ["article"],
            "target_vocabulary": [{"lemma": "door"}],
            "paragraphs": paragraphs,
            "questions": questions,
        },
    }


def service_with_db() -> tuple[AdminExerciseTextService, FakeDb]:
    db = FakeDb()
    return AdminExerciseTextService(db, TimeService("Europe/Kyiv")), db


ACTOR = {"user_uuid": "11111111-1111-4111-8111-111111111111", "acl_group_title": "admin"}


def assert_exercise_text_service_error(error: AdminExerciseTextServiceError, status_code: int) -> None:
    assert admin_exercise_text_service_error_status_code(error) == status_code


def assert_exercise_text_generation_error(error: AdminExerciseTextGenerationError, status_code: int) -> None:
    assert admin_exercise_text_generation_error_status_code(error) == status_code


def assert_exercise_text_tts_error(error: AdminExerciseTextTTSError, status_code: int) -> None:
    assert admin_exercise_text_tts_error_status_code(error) == status_code


def test_admin_exercise_text_service_creates_and_lists_items() -> None:
    service, _db = service_with_db()

    item = service.create_item(
        actor=ACTOR,
        payload={"title": "  Draft text  ", "difficulty_band": "A1_A2", "text_types": ["article"], "topic_ids": [1], "content_jsonb": {"schema_version": 1}},
    )
    page = service.list_items(actor=ACTOR, params={"page": 1, "page_size": 50})

    assert item["title"] == "  Draft text  "
    assert page["total"] == 1


def test_admin_exercise_text_service_blocks_publish_with_stale_status() -> None:
    service, db = service_with_db()
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=valid_publishable_content(),
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )
    item["content_jsonb"]["generation_state"]["quiz"] = "stale"
    db.exercise_texts.items[item["id"]] = item

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.publish_item(actor=ACTOR, exercise_text_id=item["id"], payload={"version": 1})

    assert_exercise_text_service_error(exc_info.value, 400)
    assert exc_info.value.detail["errors"][0]["field"] == "generation_state.quiz"


def test_admin_exercise_text_service_publishes_valid_content() -> None:
    service, db = service_with_db()
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=valid_publishable_content(),
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    result = service.publish_item(actor=ACTOR, exercise_text_id=item["id"], payload={"version": 1})

    assert result["status"] == "published"
    assert result["published_at"] is not None


def test_admin_exercise_text_service_blocks_published_edit() -> None:
    service, db = service_with_db()
    item = db.exercise_texts.create(title="Text", content_jsonb={"schema_version": 1})
    db.exercise_texts.items[item["id"]]["status"] = "published"

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.update_item(actor=ACTOR, exercise_text_id=item["id"], payload={"version": 1, "title": "New"})

    assert_exercise_text_service_error(exc_info.value, 400)
    assert "Published exercise text" in str(exc_info.value.detail)


def test_admin_exercise_text_service_marks_generated_content_stale_on_source_update() -> None:
    service, db = service_with_db()
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=valid_publishable_content() | {"source": {"english_text": "Old text."}},
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    result = service.update_item(
        actor=ACTOR,
        exercise_text_id=item["id"],
        payload={
            "version": 1,
            "content_jsonb": valid_publishable_content() | {"source": {"english_text": "New text."}},
        },
    )

    assert result["content_jsonb"]["generation_state"]["content"] == "stale"
    assert result["content_jsonb"]["generation_state"]["translations"] == "stale"
    assert result["content_jsonb"]["generation_state"]["quiz"] == "stale"
    assert result["content_jsonb"]["generated"]["paragraphs"][0]["status"]["content"] == "stale"


def test_admin_exercise_text_service_marks_generated_content_stale_on_metadata_update() -> None:
    service, db = service_with_db()
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=valid_publishable_content(),
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    result = service.update_item(
        actor=ACTOR,
        exercise_text_id=item["id"],
        payload={"version": 1, "difficulty_band": "B1_B2"},
    )

    assert result["content_jsonb"]["generation_state"]["content"] == "stale"
    assert result["content_jsonb"]["generation_state"]["quiz"] == "stale"


def test_admin_exercise_text_service_confirms_paragraph_stage_and_aggregates_document_state() -> None:
    service, db = service_with_db()
    content = valid_publishable_content()
    content["generation_state"]["content"] = "stale"
    content["generated"]["paragraphs"][0]["status"]["content"] = "stale"
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=content,
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    result = service.confirm_paragraph_stage(
        actor=ACTOR,
        exercise_text_id=item["id"],
        paragraph_id="pg_valid_1",
        payload={"version": 1, "stage": "content"},
    )

    assert result["content_jsonb"]["generated"]["paragraphs"][0]["status"]["content"] == "completed"
    assert result["content_jsonb"]["generation_state"]["content"] == "completed"


def test_admin_exercise_text_service_keeps_document_pending_until_all_paragraphs_have_stage() -> None:
    service, db = service_with_db()
    content = valid_publishable_content()
    content["generation_state"]["quiz"] = "stale"
    content["generated"]["paragraphs"][0]["status"]["quiz"] = "stale"
    del content["generated"]["paragraphs"][1]["status"]["quiz"]
    del content["generated"]["paragraphs"][2]["status"]["quiz"]
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=content,
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    result = service.confirm_paragraph_stage(
        actor=ACTOR,
        exercise_text_id=item["id"],
        paragraph_id="pg_valid_1",
        payload={"version": 1, "stage": "quiz"},
    )

    assert result["content_jsonb"]["generation_state"]["quiz"] == "pending"
    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.publish_item(actor=ACTOR, exercise_text_id=item["id"], payload={"version": 2})
    assert exc_info.value.detail["errors"][0]["field"] == "generation_state.quiz"


def test_admin_exercise_text_service_blocks_ready_with_pending_document_status() -> None:
    service, db = service_with_db()
    content = valid_publishable_content()
    content["generation_state"]["quiz"] = "pending"
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=content,
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.mark_ready(actor=ACTOR, exercise_text_id=item["id"], payload={"version": 1})

    assert_exercise_text_service_error(exc_info.value, 400)
    assert exc_info.value.detail["errors"][0]["field"] == "generation_state.quiz"


def test_admin_exercise_text_service_rejects_manual_confirmation_for_running_or_pending_stage() -> None:
    service, db = service_with_db()
    content = valid_publishable_content()
    content["generated"]["paragraphs"][0]["status"]["quiz"] = "running"
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=content,
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.confirm_paragraph_stage(
            actor=ACTOR,
            exercise_text_id=item["id"],
            paragraph_id="pg_valid_1",
            payload={"version": 1, "stage": "quiz"},
        )

    assert_exercise_text_service_error(exc_info.value, 409)


def test_admin_exercise_text_service_rejects_paragraph_confirmation_for_published_item() -> None:
    service, db = service_with_db()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    db.exercise_texts.items[item["id"]]["status"] = "published"

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.confirm_paragraph_stage(
            actor=ACTOR,
            exercise_text_id=item["id"],
            paragraph_id="pg_valid_1",
            payload={"version": 1, "stage": "content"},
        )

    assert_exercise_text_service_error(exc_info.value, 400)


def test_admin_exercise_text_service_blocks_ready_with_node_stale_status() -> None:
    service, db = service_with_db()
    content = valid_publishable_content()
    content["generated"]["paragraphs"][0]["status"]["quiz"] = "stale"
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=content,
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.mark_ready(actor=ACTOR, exercise_text_id=item["id"], payload={"version": 1})

    assert_exercise_text_service_error(exc_info.value, 400)
    assert exc_info.value.detail["errors"][0]["field"] == "generated.paragraphs.pg_valid_1.status.quiz"


def test_admin_exercise_text_service_blocks_publish_with_evidence_span_mismatch() -> None:
    service, db = service_with_db()
    content = valid_publishable_content()
    content["generated"]["questions"][0]["options"][0]["evidence_span"]["start_char"] = 4
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb=content,
        current_time=datetime(2026, 5, 12, 12, 0, 0),
    )

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.publish_item(actor=ACTOR, exercise_text_id=item["id"], payload={"version": 1})

    assert_exercise_text_service_error(exc_info.value, 400)
    assert any(error["field"].endswith("evidence_span") for error in exc_info.value.detail["errors"])


def test_admin_exercise_text_service_requires_force_for_topic_difficulty_conflict() -> None:
    service, _db = service_with_db()
    payload = {"title": "Text", "difficulty_band": "A1_A2", "text_types": ["article"], "topic_ids": [2], "content_jsonb": {"schema_version": 1}}

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.create_item(actor=ACTOR, payload=payload)

    assert_exercise_text_service_error(exc_info.value, 409)
    payload["force_topic_difficulty"] = {"reason": "Intentional advanced topic"}
    assert service.create_item(actor=ACTOR, payload=payload)["topic_ids"] == [2]


def test_admin_exercise_text_service_rechecks_topic_conflict_on_partial_update() -> None:
    service, db = service_with_db()
    item = db.exercise_texts.create(
        title="Text",
        difficulty_band="A1_A2",
        text_types=["article"],
        topic_ids=[1],
        content_jsonb={"schema_version": 1},
    )

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.update_item(actor=ACTOR, exercise_text_id=item["id"], payload={"version": 1, "topic_ids": [2]})

    assert_exercise_text_service_error(exc_info.value, 409)


def test_admin_exercise_text_service_rejects_invalid_list_filter_value() -> None:
    service, _db = service_with_db()

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.list_items(actor=ACTOR, params={"page": 1, "page_size": 50, "status": ["draft", "broken"]})

    assert_exercise_text_service_error(exc_info.value, 400)
    assert "status contains unsupported value" in str(exc_info.value.detail)


def test_admin_exercise_text_service_validates_extended_list_filters() -> None:
    service, db = service_with_db()

    service.list_items(
        actor=ACTOR,
        params={
            "page": 1,
            "page_size": 50,
            "text_type": ["article", "science"],
            "topic_id": [2, 2],
            "has_quiz": "yes",
            "has_tts": "no",
            "sort": "title_asc",
        },
    )

    assert db.exercise_texts.last_list_kwargs["topic_id"] == [2]
    assert db.exercise_texts.last_list_kwargs["text_type"] == ["article", "science"]
    assert db.exercise_texts.last_list_kwargs["has_quiz"] is True
    assert db.exercise_texts.last_list_kwargs["has_tts"] is False
    assert db.exercise_texts.last_list_kwargs["sort"] == "title_asc"


def test_admin_exercise_text_service_rejects_invalid_extended_list_filter() -> None:
    service, _db = service_with_db()

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.list_items(actor=ACTOR, params={"page": 1, "page_size": 50, "has_quiz": "maybe"})

    assert_exercise_text_service_error(exc_info.value, 400)
    assert "has_quiz must be all, yes or no" in str(exc_info.value.detail)


def test_admin_exercise_text_service_rejects_invalid_sort() -> None:
    service, _db = service_with_db()

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.list_items(actor=ACTOR, params={"page": 1, "page_size": 50, "sort": "title_drop"})

    assert_exercise_text_service_error(exc_info.value, 400)
    assert "sort must be one of" in str(exc_info.value.detail)


class FakeGenerationProvider:
    provider_key = "openai"
    model = "gpt-test"

    def __init__(self, raw_json_text: str) -> None:
        self.raw_json_text = raw_json_text

    def generate(self, request) -> ExerciseTextGenerationResult:
        return ExerciseTextGenerationResult(
            raw_json_text=self.raw_json_text,
            usage=ProviderUsage(
                provider_key="openai",
                model="gpt-test",
                request_count=1,
                input_tokens=10,
                output_tokens=20,
                estimated_cost_usd=Decimal("0.01"),
                pricing_source="test",
            ),
        )


def test_generation_service_saves_valid_provider_document_and_usage() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb={"schema_version": 1})
    service = AdminExerciseTextGenerationService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeGenerationProvider(json.dumps(valid_publishable_content())),
    )

    result = service.start_generation(actor=ACTOR, exercise_text_id=item["id"], stage="quiz")

    assert result["task"]["status"] == "success"
    assert result["exercise_text"]["content_jsonb"]["generated"]["title"] == "Publishable"
    assert result["exercise_text"]["content_jsonb"]["generation_state"]["quiz"] == "completed"
    assert db.ai_usage_sessions.calls[0]["task_key"] == "exercise_texts.content_generation"


def test_generation_service_uses_configured_disabled_provider_without_live_call() -> None:
    db = FakeDb()
    db.external_provider_settings.rows["exercise_texts.content_generation"] = {
        "task_key": "exercise_texts.content_generation",
        "provider_key": "disabled",
        "is_enabled": False,
        "config_json": {},
    }
    item = db.exercise_texts.create(title="Text", content_jsonb={"schema_version": 1})
    service = AdminExerciseTextGenerationService(db, TimeService("Europe/Kyiv"))

    result = service.start_generation(actor=ACTOR, exercise_text_id=item["id"], stage="content")

    assert result["task"]["status"] == "error"
    assert "Exercise text generation provider is disabled" in result["task"]["error_text"]
    assert result["exercise_text"]["content_jsonb"]["generation_state"]["content"] == "failed"
    assert db.ai_usage_sessions.calls == []


def test_generation_service_returns_scoped_generation_task() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb={"schema_version": 1})
    service = AdminExerciseTextGenerationService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeGenerationProvider(json.dumps(valid_publishable_content())),
    )
    started = service.start_generation(actor=ACTOR, exercise_text_id=item["id"], stage="content")

    result = service.get_generation_task(
        actor=ACTOR,
        exercise_text_id=item["id"],
        task_id=started["task"]["id"],
    )

    assert result["task"]["source_type"] == "exercise_text"
    assert result["task"]["source_identifier"] == str(item["id"])


@pytest.mark.parametrize("mode", ["single", "all"])
def test_generation_service_preserves_denied_publish_acl_detail(mode: str) -> None:
    db = FakeDb()
    db.acl_permissions = FakeAclPermissions(disabled_actions={"exercise_texts/publish"})
    item = db.exercise_texts.create(title="Text", content_jsonb={"schema_version": 1})
    service = AdminExerciseTextGenerationService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeGenerationProvider(json.dumps(valid_publishable_content())),
    )

    with pytest.raises(AdminExerciseTextGenerationError) as exc_info:
        if mode == "single":
            service.start_generation(actor=ACTOR, exercise_text_id=item["id"], stage="content")
        else:
            service.generate_all(actor=ACTOR, exercise_text_id=item["id"])

    assert_exercise_text_generation_error(exc_info.value, 403)
    assert exc_info.value.detail == "Access denied"


def test_generation_service_preserves_denied_view_acl_detail() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb={"schema_version": 1})
    task = db.task_logs.create_for_user_uuid(
        task_type="exercise_texts.content_generation",
        status="success",
        current_time=TimeService("Europe/Kyiv").now(),
        user_uuid=ACTOR["user_uuid"],
        source_type="exercise_text",
        source_identifier=str(item["id"]),
        description="done",
        result_json={"exercise_text_id": item["id"], "stage": "content"},
    )
    db.acl_permissions = FakeAclPermissions(disabled_actions={"exercise_texts/view"})
    service = AdminExerciseTextGenerationService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeGenerationProvider(json.dumps(valid_publishable_content())),
    )

    with pytest.raises(AdminExerciseTextGenerationError) as exc_info:
        service.get_generation_task(actor=ACTOR, exercise_text_id=item["id"], task_id=task["id"])

    assert_exercise_text_generation_error(exc_info.value, 403)
    assert exc_info.value.detail == "Access denied"


def test_generation_service_rejects_running_stage() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb={"schema_version": 1, "generation_state": {"content": "running"}})
    service = AdminExerciseTextGenerationService(db, TimeService("Europe/Kyiv"), provider=FakeGenerationProvider("{}"))

    with pytest.raises(AdminExerciseTextGenerationError) as exc_info:
        service.start_generation(actor=ACTOR, exercise_text_id=item["id"], stage="content")

    assert_exercise_text_generation_error(exc_info.value, 409)


def test_generation_service_preserves_previous_content_on_invalid_provider_json() -> None:
    db = FakeDb()
    original = {"schema_version": 1, "generated": {"title": "Keep me"}}
    item = db.exercise_texts.create(title="Text", content_jsonb=original)
    service = AdminExerciseTextGenerationService(db, TimeService("Europe/Kyiv"), provider=FakeGenerationProvider("```json\n{}\n```"))

    result = service.start_generation(actor=ACTOR, exercise_text_id=item["id"], stage="content")

    assert result["task"]["status"] == "error"
    saved = db.exercise_texts.get(item["id"])["content_jsonb"]
    assert saved["generated"]["title"] == "Keep me"
    assert saved["generation_state"]["content"] == "failed"
    assert db.exercise_texts.get(item["id"])["status"] == "draft"


def test_generation_service_blocks_published_content_generation() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb={"schema_version": 1})
    db.exercise_texts.items[item["id"]]["status"] = "published"
    service = AdminExerciseTextGenerationService(db, TimeService("Europe/Kyiv"), provider=FakeGenerationProvider("{}"))

    with pytest.raises(AdminExerciseTextGenerationError) as exc_info:
        service.start_generation(actor=ACTOR, exercise_text_id=item["id"], stage="content")

    assert_exercise_text_generation_error(exc_info.value, 400)


class FakeTTSProvider:
    provider_key = "google_tts"

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def synthesize(self, request) -> ExerciseTextTTSResult:
        self.calls.append({"text": request.text, "voice_code": request.voice_code})
        return ExerciseTextTTSResult(audio_bytes=f"audio:{request.text}".encode(), timestamps=[])


class FakeExerciseAudioStorageProvider:
    def __init__(self, existing_paths: set[str] | None = None) -> None:
        self.existing_paths = existing_paths or set()
        self.exists_calls: list[str] = []
        self.write_calls: list[tuple[str, bytes]] = []

    def resolve_local_path(self, audio_path):
        return Path(str(audio_path))

    def exists(self, audio_path) -> bool:
        path = str(audio_path)
        self.exists_calls.append(path)
        return path in self.existing_paths

    def write_bytes_atomic(self, audio_path, payload: bytes) -> str:
        path = str(audio_path)
        self.write_calls.append((path, payload))
        self.existing_paths.add(path)
        return path

    def copy(self, source_audio_path, target_audio_path) -> str:
        raise AssertionError("copy should not be called")

    def delete_if_under_roots(self, audio_path, audio_roots) -> bool:
        raise AssertionError("delete_if_under_roots should not be called")


def test_tts_service_preserves_denied_generation_acl_detail_before_lookup() -> None:
    db = FakeDb()
    db.acl_permissions = FakeAclPermissions(disabled_actions={"exercise_texts/publish"})
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeTTSProvider(),
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
    )

    with pytest.raises(AdminExerciseTextTTSError) as exc_info:
        service.start_tts_generation(actor=ACTOR, exercise_text_id=999)

    assert_exercise_text_tts_error(exc_info.value, 403)
    assert exc_info.value.detail == "Access denied"


def test_tts_service_generates_paragraph_and_full_audio_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    provider = FakeTTSProvider()
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=provider,
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
        random_choice=lambda voices: voices[0],
    )

    result = service.start_tts_generation(actor=ACTOR, exercise_text_id=item["id"])

    content = result["exercise_text"]["content_jsonb"]
    assert result["task"]["status"] == "success"
    assert content["generation_state"]["tts"] == "completed"
    assert content["generated"]["audio"]["voice_code"] == "en-US-Neural2-C"
    assert content["generated"]["audio"]["files"][0]["scope"] == "full"
    assert content["generated"]["paragraphs"][0]["audio"]["url"].endswith("paragraph_id=pg_valid_1")
    assert content["generated"]["audio"]["files"][0]["path"] == f"word_base/exercise_texts/audio/{item['uuid']}/full.mp3"
    assert provider.calls[-1]["text"].count("\n\n") == 2


def test_tts_service_writes_paragraph_and_full_audio_through_storage_provider(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    storage_provider = FakeExerciseAudioStorageProvider()
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeTTSProvider(),
        audio_storage_provider=storage_provider,
        random_choice=lambda voices: voices[0],
    )

    result = service.start_tts_generation(actor=ACTOR, exercise_text_id=item["id"])

    prefix = f"word_base/exercise_texts/audio/{item['uuid']}"
    assert result["task"]["status"] == "success"
    assert [path for path, _payload in storage_provider.write_calls] == [
        f"{prefix}/pg_valid_1.mp3",
        f"{prefix}/pg_valid_2.mp3",
        f"{prefix}/pg_valid_3.mp3",
        f"{prefix}/full.mp3",
    ]


def test_tts_service_uses_selected_active_voice(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    provider = FakeTTSProvider()
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=provider,
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
    )

    result = service.start_tts_generation(actor=ACTOR, exercise_text_id=item["id"], voice_code="en-US-Neural2-C")

    assert result["exercise_text"]["content_jsonb"]["generated"]["audio"]["voice_code"] == "en-US-Neural2-C"
    assert provider.calls[0]["voice_code"] == "en-US-Neural2-C"


def test_tts_service_rejects_unknown_voice() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeTTSProvider(),
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
    )

    with pytest.raises(AdminExerciseTextTTSError) as exc_info:
        service.start_tts_generation(actor=ACTOR, exercise_text_id=item["id"], voice_code="missing")

    assert_exercise_text_tts_error(exc_info.value, 400)


def test_tts_service_rejects_invalid_audio_scope() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeTTSProvider(),
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
    )

    with pytest.raises(AdminExerciseTextTTSError) as exc_info:
        service.get_audio_path(actor=ACTOR, exercise_text_id=item["id"], scope="bad", paragraph_id=None)

    assert_exercise_text_tts_error(exc_info.value, 400)


def test_tts_service_requires_paragraph_id_for_paragraph_audio() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeTTSProvider(),
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
    )

    with pytest.raises(AdminExerciseTextTTSError) as exc_info:
        service.get_audio_path(actor=ACTOR, exercise_text_id=item["id"], scope="paragraph", paragraph_id=None)

    assert_exercise_text_tts_error(exc_info.value, 400)


def test_tts_service_preserves_denied_audio_acl_detail() -> None:
    db = FakeDb()
    db.acl_permissions = FakeAclPermissions(disabled_actions={"exercise_texts/play_audio"})
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeTTSProvider(),
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
    )

    with pytest.raises(AdminExerciseTextTTSError) as exc_info:
        service.get_audio_path(actor=ACTOR, exercise_text_id=999, scope="full", paragraph_id=None)

    assert_exercise_text_tts_error(exc_info.value, 403)
    assert exc_info.value.detail == "Access denied"


def test_exercise_text_service_audio_placeholder_preserves_denied_acl_detail() -> None:
    db = FakeDb()
    db.acl_permissions = FakeAclPermissions(disabled_actions={"exercise_texts/play_audio"})
    service = AdminExerciseTextService(db, TimeService("Europe/Kyiv"))

    with pytest.raises(AdminExerciseTextServiceError) as exc_info:
        service.get_audio_response(actor=ACTOR, exercise_text_id=999)

    assert_exercise_text_service_error(exc_info.value, 403)
    assert exc_info.value.detail == "Access denied"


def test_tts_service_rejects_unsafe_audio_filename(tmp_path) -> None:
    with pytest.raises(AdminExerciseTextTTSError) as exc_info:
        _audio_file_path(tmp_path, "../escape.mp3")

    assert_exercise_text_tts_error(exc_info.value, 400)


def test_tts_service_does_not_serve_stored_jsonb_path_outside_exercise_audio_root(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "project.env").write_text("SECRET=1")
    db = FakeDb()
    content = valid_publishable_content()
    content["generated"]["audio"] = {
        "files": [
            {
                "scope": "full",
                "path": "project.env",
            }
        ]
    }
    item = db.exercise_texts.create(title="Text", content_jsonb=content)
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeTTSProvider(),
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
    )

    audio_path = service.get_audio_path(actor=ACTOR, exercise_text_id=item["id"], scope="full", paragraph_id=None)

    assert audio_path is None


def test_tts_service_get_audio_path_uses_storage_provider_exists(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    relative_audio_path = f"word_base/exercise_texts/audio/{item['uuid']}/full.mp3"
    content = db.exercise_texts.items[item["id"]]["content_jsonb"]
    content["generated"]["audio"] = {
        "files": [
            {
                "scope": "full",
                "path": relative_audio_path,
            }
        ]
    }
    filesystem_path = tmp_path / relative_audio_path
    filesystem_path.parent.mkdir(parents=True)
    filesystem_path.write_bytes(b"audio")
    storage_provider = FakeExerciseAudioStorageProvider()
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        provider=FakeTTSProvider(),
        audio_storage_provider=storage_provider,
    )

    assert service.get_audio_path(
        actor=ACTOR,
        exercise_text_id=item["id"],
        scope="full",
        paragraph_id=None,
    ) is None
    storage_provider.existing_paths.add(relative_audio_path)

    assert service.get_audio_path(
        actor=ACTOR,
        exercise_text_id=item["id"],
        scope="full",
        paragraph_id=None,
    ) == relative_audio_path
    assert storage_provider.exists_calls == [relative_audio_path, relative_audio_path]


def test_tts_service_rejects_disabled_provider() -> None:
    db = FakeDb()
    item = db.exercise_texts.create(title="Text", content_jsonb=valid_publishable_content())
    db.external_provider_settings.rows["exercise_texts.tts"] = {
        "task_key": "exercise_texts.tts",
        "provider_key": "disabled",
        "is_enabled": False,
        "config_json": {},
    }
    service = AdminExerciseTextTTSService(
        db,
        TimeService("Europe/Kyiv"),
        audio_storage_provider=FakeExerciseAudioStorageProvider(),
    )

    result = service.start_tts_generation(actor=ACTOR, exercise_text_id=item["id"])

    assert result["task"]["status"] == "error"
    assert result["exercise_text"]["content_jsonb"]["generation_state"]["tts"] == "failed"
