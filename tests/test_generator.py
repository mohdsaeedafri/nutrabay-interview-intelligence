from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.models import Category, GeneratedQuestion, GeneratedQuestionSet
from src.question_generator import GenerationError, GeminiQuestionGenerator
from src.sample_data import load_demo_questions, load_sample_jd


@dataclass
class FakeResponse:
    parsed: object | None = None
    text: str = ""
    output_text: str = ""


class FakeApiError(Exception):
    def __init__(self, code: int, status: str, message: str) -> None:
        self.code = code
        self.status = status
        self.message = message
        super().__init__(message)


class FakeModels:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = responses
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeClient:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.models = FakeModels(responses)


class FakeInteractions:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = responses
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeCurrentClient:
    def __init__(
        self,
        interaction_responses: list[FakeResponse | Exception],
        legacy_responses: list[FakeResponse | Exception] | None = None,
    ) -> None:
        self.interactions = FakeInteractions(interaction_responses)
        self.models = FakeModels(legacy_responses or [])


def valid_generated_set() -> GeneratedQuestionSet:
    role, questions = load_demo_questions()
    return GeneratedQuestionSet(
        role_title=role,
        questions=[GeneratedQuestion(category=item.category, text=item.text) for item in questions],
    )


def test_generator_accepts_structured_pydantic_response() -> None:
    client = FakeClient([FakeResponse(parsed=valid_generated_set())])
    generator = GeminiQuestionGenerator("", "test-model", client=client)
    role, questions = generator.generate(load_sample_jd(), 15)
    assert role == "Senior Analyst - D2C Growth"
    assert len(questions) == 15
    assert len(client.models.calls) == 1


def test_generator_prefers_current_interactions_api_and_json_schema() -> None:
    payload = valid_generated_set().model_dump_json()
    client = FakeCurrentClient([FakeResponse(output_text=payload)])
    generator = GeminiQuestionGenerator("", "gemini-3.6-flash", client=client)

    role, questions = generator.generate(load_sample_jd(), 15)

    assert role == "Senior Analyst - D2C Growth"
    assert len(questions) == 15
    assert len(client.interactions.calls) == 1
    assert len(client.models.calls) == 0
    response_format = client.interactions.calls[0]["response_format"]
    assert response_format["mime_type"] == "application/json"
    assert response_format["schema"]["properties"]["questions"]["maxItems"] == 15
    assert "maxLength" not in response_format["schema"]["properties"]["role_title"]


def test_generator_uses_legacy_endpoint_when_current_contract_is_rejected() -> None:
    current_error = FakeApiError(400, "INVALID_ARGUMENT", "Unknown field response_format")
    client = FakeCurrentClient([current_error], [FakeResponse(parsed=valid_generated_set())])
    generator = GeminiQuestionGenerator("", "gemini-3.6-flash", client=client)

    _, questions = generator.generate(load_sample_jd(), 15)

    assert len(questions) == 15
    assert len(client.interactions.calls) == 1
    assert len(client.models.calls) == 1
    config = client.models.calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["required"] == ["role_title", "questions"]


def test_generator_falls_back_when_configured_model_is_missing() -> None:
    client = FakeClient(
        [
            FakeApiError(404, "NOT_FOUND", "Configured model was not found"),
            FakeResponse(parsed=valid_generated_set()),
        ]
    )
    generator = GeminiQuestionGenerator("", "retired-model", client=client)

    _, questions = generator.generate(load_sample_jd(), 15)

    assert len(questions) == 15
    assert [call["model"] for call in client.models.calls] == ["retired-model", "gemini-3.6-flash"]
    assert generator.last_model == "gemini-3.6-flash"


def test_invalid_key_returns_actionable_code_without_retry() -> None:
    client = FakeClient(
        [FakeApiError(400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key.")]
    )
    generator = GeminiQuestionGenerator("", "gemini-3.6-flash", client=client)

    with pytest.raises(GenerationError, match=r"\[AI-KEY\].*Google rejected"):
        generator.generate(load_sample_jd(), 15)

    assert len(client.models.calls) == 1


def test_quota_error_returns_safe_diagnostic() -> None:
    client = FakeClient([FakeApiError(429, "RESOURCE_EXHAUSTED", "Rate limit exceeded")])
    generator = GeminiQuestionGenerator("", "gemini-3.6-flash", client=client)

    with pytest.raises(GenerationError, match=r"\[AI-QUOTA\]"):
        generator.generate(load_sample_jd(), 15)


def test_empty_response_keeps_validation_diagnostic() -> None:
    generator = GeminiQuestionGenerator("", "gemini-3.6-flash", client=FakeClient([FakeResponse()]))

    with pytest.raises(GenerationError, match=r"\[AI-VALIDATION\].*empty response"):
        generator.generate(load_sample_jd(), 15)


def test_generator_repairs_invalid_first_response_once() -> None:
    client = FakeClient(
        [
            FakeResponse(text='{"role_title":"Test","questions":[]}'),
            FakeResponse(parsed=valid_generated_set()),
        ]
    )
    generator = GeminiQuestionGenerator("", "test-model", client=client)
    _, questions = generator.generate(load_sample_jd(), 15)
    assert len(questions) == 15
    assert len(client.models.calls) == 2
    assert "VALIDATION FAILURES" in client.models.calls[1]["contents"]


def test_single_question_replacement_preserves_category() -> None:
    replacement = GeneratedQuestion(category=Category.EQ, text="Describe a role-specific learning moment under pressure?")
    client = FakeClient([FakeResponse(parsed=replacement)])
    generator = GeminiQuestionGenerator("", "test-model", client=client)
    result = generator.replace(load_sample_jd(), Category.EQ, "Old question?", ["Existing question?"])
    assert result == replacement.text


def test_replacement_rejects_wrong_category() -> None:
    replacement = GeneratedQuestion(category=Category.INTENT, text="Why do you want this specific growth role now?")
    generator = GeminiQuestionGenerator("", "test-model", client=FakeClient([FakeResponse(parsed=replacement)]))
    with pytest.raises(GenerationError, match="requested category"):
        generator.replace(load_sample_jd(), Category.EQ, "Old question?", [])


def test_generator_stops_after_single_failed_repair() -> None:
    client = FakeClient([
        FakeResponse(text='{"role_title":"Test","questions":[]}'),
        FakeResponse(text='{"role_title":"Still invalid","questions":[]}'),
    ])
    generator = GeminiQuestionGenerator("", "test-model", client=client)
    with pytest.raises(GenerationError, match="validated"):
        generator.generate(load_sample_jd(), 15)
    assert len(client.models.calls) == 2
