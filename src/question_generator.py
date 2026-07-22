from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.models import Category, GeneratedQuestion, GeneratedQuestionSet, ReviewQuestion
from src.prompt_builder import build_generation_prompt, build_repair_prompt, build_replacement_prompt
from src.question_validation import validate_generated_distribution


class GenerationError(RuntimeError):
    """A safe, user-displayable generation failure."""


class GeminiQuestionGenerator:
    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        if not api_key and client is None:
            raise ValueError("A Gemini API key is required for live generation.")
        self.model = model
        if client is not None:
            self.client = client
        else:
            from google import genai

            self.client = genai.Client(api_key=api_key)

    def _generate(self, prompt: str, schema: type[GeneratedQuestionSet] | type[GeneratedQuestion]) -> Any:
        from google.genai import types

        return self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.35,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )

    @staticmethod
    def _parse(response: Any, schema: type[GeneratedQuestionSet] | type[GeneratedQuestion]) -> Any:
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, schema):
                return parsed
            return schema.model_validate(parsed)
        text = getattr(response, "text", "")
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
                last_output = getattr(response, "text", "") or json.dumps(
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
            except Exception as exc:
                if attempt == 0:
                    errors = ["The AI request failed and will be retried once."]
                    last_output = "The request failed before a structured response was returned."
                else:
                    raise GenerationError(
                        "Live question generation is temporarily unavailable. Please retry or load the curated demo set."
                    ) from exc

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
        except Exception as exc:
            raise GenerationError("The replacement question could not be generated. Please retry or edit it manually.") from exc
        if item.category != category:
            raise GenerationError("The replacement did not stay in the requested category. Please retry.")
        return item.text
