from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from src.models import Category, GeneratedQuestion, GeneratedQuestionSet, ReviewQuestion
from src.prompt_builder import build_generation_prompt, build_repair_prompt, build_replacement_prompt
from src.question_validation import validate_generated_distribution


LOGGER = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
FALLBACK_GEMINI_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash-lite")

# Keep the API-facing schema deliberately small. Application-side Pydantic
# validation still enforces text lengths and the exact category distribution.
# This avoids sending unsupported Pydantic JSON-Schema keywords to older
# generateContent endpoints while remaining valid for the current
# Interactions API.
QUESTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": [category.value for category in Category],
        },
        "text": {"type": "string"},
    },
    "required": ["category", "text"],
    "additionalProperties": False,
}

QUESTION_SET_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "role_title": {"type": "string"},
        "questions": {
            "type": "array",
            "items": QUESTION_JSON_SCHEMA,
            "minItems": 10,
            "maxItems": 15,
        },
    },
    "required": ["role_title", "questions"],
    "additionalProperties": False,
}


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _schema_json(schema: type[GeneratedQuestionSet] | type[GeneratedQuestion]) -> dict[str, Any]:
    if schema is GeneratedQuestionSet:
        return QUESTION_SET_JSON_SCHEMA
    if schema is GeneratedQuestion:
        return QUESTION_JSON_SCHEMA
    raise TypeError(f"Unsupported response model: {schema.__name__}")


def _exception_details(exc: Exception) -> tuple[int, str, str]:
    raw_code = getattr(exc, "code", None) or getattr(exc, "status_code", None) or 0
    try:
        code = int(raw_code)
    except (TypeError, ValueError):
        code = 0
    status = str(getattr(exc, "status", "") or "").upper()
    message = str(getattr(exc, "message", "") or str(exc))
    return code, status, message


def _safe_log_message(message: str) -> str:
    # Gemini keys normally begin with AIza. Redact any key-like value before a
    # diagnostic reaches Streamlit's server logs.
    redacted = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED_API_KEY]", message)
    return " ".join(redacted.split())[:500]


def _is_key_error(code: int, message: str) -> bool:
    text = message.lower()
    key_terms = ("api key", "api_key", "apikey")
    failure_terms = ("invalid", "expired", "blocked", "leaked", "reported as leaked", "not valid")
    return any(term in text for term in key_terms) and any(term in text for term in failure_terms) or code == 401


def _is_model_error(code: int, status: str, message: str) -> bool:
    text = message.lower()
    return code == 404 or status == "NOT_FOUND" or (
        "model" in text and any(term in text for term in ("not found", "not available", "unsupported"))
    )


def _can_try_current_endpoint(exc: Exception) -> bool:
    code, status, message = _exception_details(exc)
    if _is_key_error(code, message):
        return False
    if code in {401, 403, 429} or status in {"PERMISSION_DENIED", "RESOURCE_EXHAUSTED"}:
        return False
    # The stable generateContent API is the primary production path. Only a
    # request-shape/SDK compatibility failure should fall through to the newer
    # Interactions endpoint. Model-not-found errors should instead try the next
    # stable model candidate.
    return code == 400 or isinstance(exc, (AttributeError, TypeError, ValueError))


def generation_error_from_exception(exc: Exception) -> "GenerationError":
    code, status, message = _exception_details(exc)
    text = message.lower()
    LOGGER.warning(
        "Gemini request failed: type=%s http_code=%s status=%s message=%s",
        type(exc).__name__,
        code or "unknown",
        status or "unknown",
        _safe_log_message(message),
    )

    if _is_key_error(code, message):
        return GenerationError(
            "Google rejected the Gemini API key. Create a fresh Gemini API key in Google AI Studio, "
            "replace only GEMINI_API_KEY in Streamlit Secrets, save, and reboot the app.",
            diagnostic_code="AI-KEY",
        )
    if code == 400 and (status == "FAILED_PRECONDITION" or "free tier" in text or "country" in text):
        return GenerationError(
            "Gemini free-tier access is unavailable for this key's project or region. Verify the key "
            "with one prompt in Google AI Studio, then replace GEMINI_API_KEY if needed.",
            diagnostic_code="AI-REGION",
        )
    if code == 403 or status == "PERMISSION_DENIED":
        return GenerationError(
            "The configured key exists but does not have Gemini API permission. Use a Gemini API key "
            "created in Google AI Studio—not an OAuth client ID or an Apps Script token.",
            diagnostic_code="AI-ACCESS",
        )
    if _is_model_error(code, status, message):
        return GenerationError(
            "No compatible free stable Gemini model is available to this key right now. The app tried "
            "the configured model and its stable fallbacks.",
            diagnostic_code="AI-MODEL",
        )
    if code == 429 or status == "RESOURCE_EXHAUSTED":
        return GenerationError(
            "The Gemini free-tier quota or rate limit is exhausted. Wait for the limit to reset, then retry.",
            diagnostic_code="AI-QUOTA",
        )
    if code in {500, 502, 503} or status in {"INTERNAL", "UNAVAILABLE"}:
        return GenerationError(
            "Google Gemini is temporarily unavailable after automatic retries. Please retry shortly.",
            diagnostic_code="AI-SERVICE",
        )
    if code == 504 or status == "DEADLINE_EXCEEDED" or "timed out" in text or "timeout" in text:
        return GenerationError(
            "The Gemini request timed out. Please retry; your job description and edits are still available.",
            diagnostic_code="AI-TIMEOUT",
        )
    if code == 400 or status == "INVALID_ARGUMENT":
        return GenerationError(
            "Gemini rejected the structured request after both current and compatibility API attempts.",
            diagnostic_code="AI-REQUEST",
        )
    return GenerationError(
        "The live Gemini request failed safely. Retry once; if it repeats, check the AI diagnostic in "
        "Deployment readiness.",
        diagnostic_code="AI-UNKNOWN",
    )


class GenerationError(RuntimeError):
    """A safe, user-displayable generation failure."""

    def __init__(self, message: str, diagnostic_code: str = "AI-VALIDATION") -> None:
        self.diagnostic_code = diagnostic_code
        super().__init__(f"[{diagnostic_code}] {message}")


class GeminiQuestionGenerator:
    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        if not api_key and client is None:
            raise ValueError("A Gemini API key is required for live generation.")
        self.model = model or DEFAULT_GEMINI_MODEL
        self.model_candidates = _unique((self.model, *FALLBACK_GEMINI_MODELS))
        self.last_model = self.model
        if client is not None:
            self.client = client
        else:
            from google import genai
            from google.genai import types

            self.client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=60_000,
                    retry_options=types.HttpRetryOptions(attempts=2),
                ),
            )

    def _generate_legacy(
        self,
        model: str,
        prompt: str,
        schema: type[GeneratedQuestionSet] | type[GeneratedQuestion],
    ) -> Any:
        from google.genai import types

        return self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=8_192,
                response_mime_type="application/json",
                response_json_schema=_schema_json(schema),
            ),
        )

    def _generate_current(
        self,
        model: str,
        prompt: str,
        schema: type[GeneratedQuestionSet] | type[GeneratedQuestion],
    ) -> Any:
        return self.client.interactions.create(
            model=model,
            input=prompt,
            store=False,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": _schema_json(schema),
            },
            generation_config={"max_output_tokens": 8_192},
            timeout=30,
        )

    def _generate(self, prompt: str, schema: type[GeneratedQuestionSet] | type[GeneratedQuestion]) -> Any:
        last_error: Exception | None = None
        supports_current_api = hasattr(self.client, "interactions") and hasattr(
            self.client.interactions, "create"
        )

        for model in self.model_candidates:
            try:
                response = self._generate_legacy(model, prompt, schema)
                self.last_model = model
                return response
            except Exception as exc:
                last_error = exc
                code, status, message = _exception_details(exc)
                if _is_model_error(code, status, message):
                    continue
                if not supports_current_api or not _can_try_current_endpoint(exc):
                    raise

            try:
                response = self._generate_current(model, prompt, schema)
                self.last_model = model
                return response
            except Exception as exc:
                last_error = exc
                code, status, message = _exception_details(exc)
                if _is_model_error(code, status, message):
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("No Gemini model candidates were configured.")

    @staticmethod
    def _response_text(response: Any) -> str:
        for name in ("output_text", "text"):
            value = getattr(response, name, "")
            if value:
                return str(value)
        return ""

    @staticmethod
    def _parse(response: Any, schema: type[GeneratedQuestionSet] | type[GeneratedQuestion]) -> Any:
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, schema):
                return parsed
            return schema.model_validate(parsed)
        text = GeminiQuestionGenerator._response_text(response)
        if not text:
            raise GenerationError("The AI service returned an empty response. Please try again.")
        return schema.model_validate_json(text)

    def generate(self, job_description: str, total: int = 15) -> tuple[str, list[ReviewQuestion]]:
        prompt = build_generation_prompt(job_description, total)
        last_output = ""
        errors: list[str] = []

        for attempt in range(2):
            request_prompt = prompt if attempt == 0 else build_repair_prompt(prompt, last_output, errors)
            try:
                response = self._generate(request_prompt, GeneratedQuestionSet)
                last_output = self._response_text(response) or json.dumps(
                    getattr(response, "parsed", {}), default=str
                )
                generated = self._parse(response, GeneratedQuestionSet)
                questions = [ReviewQuestion.from_generated(item) for item in generated.questions]
                errors = validate_generated_distribution(questions, total)
                if not errors:
                    category_rank = {category: rank for rank, category in enumerate(Category)}
                    ordered = sorted(questions, key=lambda item: category_rank[item.category])
                    return generated.role_title, ordered
            except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
                errors = [f"The response did not match the required structure: {exc}"]
            except GenerationError:
                raise
            except Exception as exc:
                # The SDK already retries transient 429/5xx failures with
                # exponential backoff. Do not repeat non-retryable key,
                # permission, region, or malformed-request failures.
                raise generation_error_from_exception(exc) from exc

        raise GenerationError("The AI response could not be validated after one repair attempt.")

    def replace(
        self,
        job_description: str,
        category: Category,
        current_question: str,
        existing_questions: list[str],
    ) -> str:
        prompt = build_replacement_prompt(job_description, category, current_question, existing_questions)
        try:
            response = self._generate(prompt, GeneratedQuestion)
            item = self._parse(response, GeneratedQuestion)
        except GenerationError:
            raise
        except Exception as exc:
            raise generation_error_from_exception(exc) from exc
        if item.category != category:
            raise GenerationError("The replacement did not stay in the requested category. Please retry.")
        return item.text
