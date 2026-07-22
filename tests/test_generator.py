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


class FakeModels:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.models = FakeModels(responses)


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
