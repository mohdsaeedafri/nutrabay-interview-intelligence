from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re

from src.models import Category, ReviewQuestion, SUGGESTED_RANGES, TARGET_DISTRIBUTIONS


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    category_counts: dict[Category, int] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def normalize_question(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return normalized.rstrip("?.! ")


def validate_review_questions(questions: list[ReviewQuestion]) -> ValidationResult:
    result = ValidationResult()
    included = [item for item in questions if item.included]

    if not 10 <= len(included) <= 15:
        result.errors.append("Include between 10 and 15 questions before finalizing.")

    if any(not item.text.strip() for item in included):
        result.errors.append("Every included question must contain text.")

    if any(item.text.strip() and not 12 <= len(item.text.strip()) <= 1_200 for item in included):
        result.errors.append("Every included question must contain 12-1,200 characters.")

    normalized = [normalize_question(item.text) for item in included if item.text.strip()]
    duplicates = {text for text, count in Counter(normalized).items() if count > 1}
    if duplicates:
        result.errors.append("Remove or rewrite duplicate questions before finalizing.")

    counts = Counter(item.category for item in included)
    result.category_counts = {category: counts.get(category, 0) for category in Category}
    missing = [category.value for category in Category if counts.get(category, 0) == 0]
    if missing:
        result.errors.append("Every category must be represented. Missing: " + ", ".join(missing) + ".")

    for category, (minimum, maximum) in SUGGESTED_RANGES.items():
        count = counts.get(category, 0)
        if count and not minimum <= count <= maximum:
            result.warnings.append(
                f"{category.value} has {count} question(s); the suggested range is {minimum}-{maximum}."
            )

    return result


def validate_generated_distribution(questions: list[ReviewQuestion], total: int) -> list[str]:
    errors: list[str] = []
    target = TARGET_DISTRIBUTIONS[total]
    counts = Counter(item.category for item in questions)
    if len(questions) != total:
        errors.append(f"Expected {total} questions but received {len(questions)}.")
    for category, expected in target.items():
        actual = counts.get(category, 0)
        if actual != expected:
            errors.append(f"Expected {expected} {category.value} questions but received {actual}.")
    normalized = [normalize_question(item.text) for item in questions]
    if len(set(normalized)) != len(normalized):
        errors.append("The generated set contains duplicate questions.")
    return errors
