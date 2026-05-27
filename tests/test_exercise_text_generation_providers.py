from __future__ import annotations

from typing import Any

from app.application.admin.exercise_texts.providers import ExerciseTextGenerationRequest
from app.external_providers.exercise_texts import (
    OpenAIExerciseTextGenerationProvider,
)


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "output": [{"content": [{"text": '{"schema_version": 1}'}]}],
            "usage": {"input_tokens": 5, "output_tokens": 7},
        }


class FakeHttpClient:
    last_request: dict[str, Any] | None = None

    def __init__(self, *, timeout: int) -> None:
        self.timeout = timeout

    def __enter__(self) -> FakeHttpClient:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]) -> FakeResponse:
        FakeHttpClient.last_request = {"url": url, "headers": headers, "json": json}
        return FakeResponse()


def test_openai_exercise_text_provider_uses_responses_api_payload(monkeypatch) -> None:
    import app.external_providers.exercise_texts as exercise_texts

    monkeypatch.setattr(exercise_texts.httpx, "Client", FakeHttpClient)
    monkeypatch.setattr(exercise_texts, "resolve_openai_api_key", lambda: "test-token")
    provider = OpenAIExerciseTextGenerationProvider(model="gpt-test", api_url="https://api.example.test/v1/responses")

    result = provider.generate(
        ExerciseTextGenerationRequest(
            stage="content",
            exercise_text={"content_jsonb": {"schema_version": 1}},
        )
    )

    request = FakeHttpClient.last_request
    assert result.raw_json_text == '{"schema_version": 1}'
    assert request is not None
    assert request["headers"]["Authorization"] == "Bearer test-token"
    assert "input" in request["json"]
    assert "messages" not in request["json"]
    assert request["json"]["text"]["format"]["type"] == "json_object"
