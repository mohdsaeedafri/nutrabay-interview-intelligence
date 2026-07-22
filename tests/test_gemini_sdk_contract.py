from __future__ import annotations

import json

import httpx
from google import genai
from google.genai import types

from src.models import GeneratedQuestion, GeneratedQuestionSet
from src.question_generator import GeminiQuestionGenerator
from src.sample_data import load_demo_questions, load_sample_jd


def test_real_sdk_serializes_and_parses_generate_content_contract() -> None:
    role, demo_questions = load_demo_questions()
    payload = GeneratedQuestionSet(
        role_title=role,
        questions=[
            GeneratedQuestion(category=question.category, text=question.text)
            for question in demo_questions
        ],
    ).model_dump_json()
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": payload}],
                        },
                        "finishReason": "STOP",
                    }
                ]
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    sync_http = httpx.Client(transport=transport)
    async_http = httpx.AsyncClient(transport=transport)
    sdk_client = genai.Client(
        api_key="test-only",
        http_options=types.HttpOptions(
            httpx_client=sync_http,
            httpx_async_client=async_http,
        ),
    )
    generator = GeminiQuestionGenerator("", "gemini-3.6-flash", client=sdk_client)

    generated_role, questions = generator.generate(load_sample_jd(), 15)

    assert generated_role == "Senior Analyst - D2C Growth"
    assert len(questions) == 15
    assert captured["url"].endswith("/v1beta/models/gemini-3.6-flash:generateContent")
    request_body = captured["body"]
    assert isinstance(request_body, dict)
    generation_config = request_body["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert generation_config["responseJsonSchema"]["additionalProperties"] is False


def test_real_sdk_falls_back_to_interactions_contract() -> None:
    role, demo_questions = load_demo_questions()
    payload = GeneratedQuestionSet(
        role_title=role,
        questions=[
            GeneratedQuestion(category=question.category, text=question.text)
            for question in demo_questions
        ],
    ).model_dump_json()
    requests: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        requests.append((str(request.url), body))
        if request.url.path.endswith(":generateContent"):
            return httpx.Response(
                400,
                json={
                    "error": {
                        "code": 400,
                        "status": "INVALID_ARGUMENT",
                        "message": "Structured generateContent is unavailable for this mock key",
                    }
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "model": "gemini-3.6-flash",
                "steps": [
                    {
                        "type": "model_output",
                        "content": [{"type": "text", "text": payload}],
                    }
                ],
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    sdk_client = genai.Client(
        api_key="test-only",
        http_options=types.HttpOptions(
            httpx_client=httpx.Client(transport=transport),
            httpx_async_client=httpx.AsyncClient(transport=transport),
        ),
    )
    generator = GeminiQuestionGenerator("", "gemini-3.6-flash", client=sdk_client)

    generated_role, questions = generator.generate(load_sample_jd(), 15)

    assert generated_role == "Senior Analyst - D2C Growth"
    assert len(questions) == 15
    assert len(requests) == 2
    assert requests[0][0].endswith("/v1beta/models/gemini-3.6-flash:generateContent")
    assert requests[1][0].endswith("/v1beta/interactions")
    response_format = requests[1][1]["response_format"]
    assert response_format["mime_type"] == "application/json"
    assert response_format["schema"]["required"] == ["role_title", "questions"]
