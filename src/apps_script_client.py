from __future__ import annotations

import time
from typing import Any

import requests

from src.models import FinalizedQuestionSet


class AppsScriptError(RuntimeError):
    """A safe, user-displayable Apps Script integration failure."""


class AppsScriptClient:
    def __init__(
        self,
        web_app_url: str,
        integration_token: str,
        session: Any = requests,
        timeout_seconds: float = 20,
    ) -> None:
        self.web_app_url = web_app_url
        self.integration_token = integration_token
        self.session = session
        self.timeout_seconds = timeout_seconds

    def publish(self, question_set: FinalizedQuestionSet) -> dict[str, Any]:
        payload = question_set.integration_payload(self.integration_token)
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response = self.session.post(
                    self.web_app_url,
                    json=payload,
                    timeout=self.timeout_seconds,
                    allow_redirects=True,
                )
                status = int(response.status_code)
                if status == 429 or status >= 500:
                    raise requests.HTTPError(f"Transient Apps Script response: HTTP {status}")
                if status >= 400:
                    raise AppsScriptError("The scoring service rejected the question set.")
                data = response.json()
                if not data.get("ok"):
                    raise AppsScriptError(data.get("message") or "The scoring service could not save the question set.")
                scoring_url = str(data.get("scoringUrl", ""))
                if not scoring_url.startswith("https://script.google.com/"):
                    raise AppsScriptError("The scoring service returned an invalid scoring URL.")
                return data
            except AppsScriptError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.35 * (2**attempt))

        raise AppsScriptError(
            "The scoring service is temporarily unavailable. Your reviewed questions remain in this session; please retry."
        ) from last_error

