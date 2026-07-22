from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(StrEnum):
    INTENT = "Intent"
    QUANT = "Quant Ability"
    JOB = "Job Competency"
    CORE = "Core Competency"
    EQ = "EQ"


CATEGORY_ORDER: tuple[Category, ...] = tuple(Category)

TARGET_DISTRIBUTIONS: dict[int, dict[Category, int]] = {
    10: {Category.INTENT: 2, Category.QUANT: 2, Category.JOB: 2, Category.CORE: 2, Category.EQ: 2},
    11: {Category.INTENT: 2, Category.QUANT: 2, Category.JOB: 3, Category.CORE: 2, Category.EQ: 2},
    12: {Category.INTENT: 2, Category.QUANT: 2, Category.JOB: 3, Category.CORE: 3, Category.EQ: 2},
    13: {Category.INTENT: 2, Category.QUANT: 2, Category.JOB: 4, Category.CORE: 3, Category.EQ: 2},
    14: {Category.INTENT: 2, Category.QUANT: 2, Category.JOB: 4, Category.CORE: 4, Category.EQ: 2},
    15: {Category.INTENT: 2, Category.QUANT: 2, Category.JOB: 4, Category.CORE: 4, Category.EQ: 3},
}

SUGGESTED_RANGES: dict[Category, tuple[int, int]] = {
    Category.INTENT: (2, 3),
    Category.QUANT: (2, 3),
    Category.JOB: (3, 4),
    Category.CORE: (3, 4),
    Category.EQ: (2, 3),
}


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    text: str = Field(min_length=12, max_length=1_200)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.split())


class GeneratedQuestionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_title: str = Field(min_length=2, max_length=160)
    questions: list[GeneratedQuestion] = Field(min_length=10, max_length=15)

    @field_validator("role_title")
    @classmethod
    def clean_role_title(cls, value: str) -> str:
        return " ".join(value.split()).strip(" |:-")


class ReviewQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    id: str = Field(default_factory=lambda: str(uuid4()))
    category: Category
    text: str
    included: bool = True

    @classmethod
    def from_generated(cls, item: GeneratedQuestion) -> "ReviewQuestion":
        return cls(category=item.category, text=item.text)


class FinalizedQuestion(BaseModel):
    id: str
    position: int = Field(ge=1, le=15)
    category: Category
    text: str = Field(min_length=12, max_length=1_200)


class FinalizedQuestionSet(BaseModel):
    question_set_id: str = Field(default_factory=lambda: str(uuid4()))
    role_title: str
    source_jd_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    questions: list[FinalizedQuestion] = Field(min_length=10, max_length=15)

    def integration_payload(self, token: str) -> dict[str, Any]:
        return {
            "action": "upsertQuestionSet",
            "integrationToken": token,
            "questionSetId": self.question_set_id,
            "roleTitle": self.role_title,
            "sourceJdHash": self.source_jd_hash,
            "createdAt": self.created_at,
            "questions": [
                {
                    "id": item.id,
                    "position": item.position,
                    "category": item.category.value,
                    "text": item.text,
                }
                for item in self.questions
            ],
        }
