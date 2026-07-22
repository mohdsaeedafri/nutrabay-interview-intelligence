from __future__ import annotations

import hashlib

import pytest

from src.apps_script_client import AppsScriptClient, AppsScriptError
from src.models import FinalizedQuestion, FinalizedQuestionSet
from src.sample_data import load_demo_questions


class FakeResponse:
    def __init__(self, status_code: int, data: dict) -> None:
        self.status_code = status_code
        self._data = data

    def json(self) -> dict:
        return self._data


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = []

    def post(self, *args, **kwargs) -> FakeResponse:
        self.calls.append((args, kwargs))
        return self.responses.pop(0)


def final_set() -> FinalizedQuestionSet:
    questions = load_demo_questions()[1][:10]
    return FinalizedQuestionSet(
        role_title="Senior Analyst - D2C Growth",
        source_jd_hash=hashlib.sha256(b"jd").hexdigest(),
        questions=[
            FinalizedQuestion(id=item.id, position=index, category=item.category, text=item.text)
            for index, item in enumerate(questions, 1)
        ],
    )


def test_publish_follows_redirects_and_returns_scoring_url() -> None:
    scoring_url = "https://script.google.com/macros/s/test/exec?questionSetId=abc"
    session = FakeSession([FakeResponse(200, {"ok": True, "questionSetId": "abc", "scoringUrl": scoring_url})])
    client = AppsScriptClient("https://script.google.com/macros/s/test/exec", "x" * 32, session=session)
    result = client.publish(final_set())
    assert result["scoringUrl"] == scoring_url
    _, kwargs = session.calls[0]
    assert kwargs["allow_redirects"] is True
    assert kwargs["json"]["integrationToken"] == "x" * 32


def test_publish_surfaces_safe_service_validation_error() -> None:
    session = FakeSession([FakeResponse(200, {"ok": False, "message": "Invalid question set."})])
    client = AppsScriptClient("https://script.google.com/macros/s/test/exec", "x" * 32, session=session)
    with pytest.raises(AppsScriptError, match="Invalid question set"):
        client.publish(final_set())


def test_publish_retries_transient_failures(monkeypatch) -> None:
    monkeypatch.setattr("src.apps_script_client.time.sleep", lambda _seconds: None)
    scoring_url = "https://script.google.com/macros/s/test/exec?questionSetId=abc"
    session = FakeSession(
        [
            FakeResponse(503, {}),
            FakeResponse(429, {}),
            FakeResponse(200, {"ok": True, "questionSetId": "abc", "scoringUrl": scoring_url}),
        ]
    )
    client = AppsScriptClient("https://script.google.com/macros/s/test/exec", "x" * 32, session=session)
    assert client.publish(final_set())["scoringUrl"] == scoring_url
    assert len(session.calls) == 3


def test_publish_rejects_invalid_scoring_url() -> None:
    session = FakeSession([FakeResponse(200, {"ok": True, "scoringUrl": "https://example.com/form"})])
    client = AppsScriptClient("https://script.google.com/macros/s/test/exec", "x" * 32, session=session)
    with pytest.raises(AppsScriptError, match="invalid scoring URL"):
        client.publish(final_set())


def test_publish_does_not_retry_permanent_http_error(monkeypatch) -> None:
    monkeypatch.setattr("src.apps_script_client.time.sleep", lambda _seconds: None)
    session = FakeSession([FakeResponse(403, {})])
    client = AppsScriptClient("https://script.google.com/macros/s/test/exec", "x" * 32, session=session)
    with pytest.raises(AppsScriptError, match="rejected"):
        client.publish(final_set())
    assert len(session.calls) == 1
