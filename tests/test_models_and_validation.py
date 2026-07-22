from __future__ import annotations

import hashlib

import pytest

from src.models import Category, FinalizedQuestion, FinalizedQuestionSet, ReviewQuestion, TARGET_DISTRIBUTIONS
from src.question_validation import normalize_question, validate_generated_distribution, validate_review_questions
from src.sample_data import load_demo_questions, load_sample_jd


def demo_questions() -> list[ReviewQuestion]:
    return load_demo_questions()[1]


def test_sample_assets_are_valid_and_specific() -> None:
    role, questions = load_demo_questions()
    jd = load_sample_jd()
    assert role == "Senior Analyst - D2C Growth"
    assert len(questions) == 15
    assert len(jd) > 500
    assert not validate_generated_distribution(questions, 15)
    assert validate_review_questions(questions).is_valid


@pytest.mark.parametrize("total", range(10, 16))
def test_target_distributions_sum_to_requested_total(total: int) -> None:
    distribution = TARGET_DISTRIBUTIONS[total]
    assert sum(distribution.values()) == total
    assert set(distribution) == set(Category)


def test_question_count_boundaries() -> None:
    questions = demo_questions()
    included_indices = {0, 1, 2, 3, 4, 5, 8, 9, 12, 13}
    for index, question in enumerate(questions):
        question.included = index in included_indices
    questions[13].included = False
    assert not validate_review_questions(questions).is_valid

    questions[13].included = True
    assert validate_review_questions(questions).is_valid

    extra = [ReviewQuestion(category=Category.INTENT, text=f"Unique additional question {index}?") for index in range(2)]
    too_many = demo_questions() + extra
    assert not validate_review_questions(too_many).is_valid


def test_blank_duplicate_and_missing_category_are_rejected() -> None:
    questions = demo_questions()
    questions[0].text = "   "
    assert any("contain text" in item for item in validate_review_questions(questions).errors)

    questions = demo_questions()
    questions[1].text = questions[0].text.upper() + "..."
    assert any("duplicate" in item.lower() for item in validate_review_questions(questions).errors)

    questions = demo_questions()
    for question in questions:
        if question.category == Category.EQ:
            question.included = False
    assert any("Missing: EQ" in item for item in validate_review_questions(questions).errors)


@pytest.mark.parametrize("text", ["Too short?", "x" * 1_201])
def test_included_question_length_matches_apps_script_contract(text: str) -> None:
    questions = demo_questions()
    questions[0].text = text
    assert any("12-1,200" in item for item in validate_review_questions(questions).errors)


def test_normalization_is_case_and_punctuation_insensitive() -> None:
    assert normalize_question("  Why this role? ") == normalize_question("WHY   THIS ROLE!!!")


def test_finalized_payload_uses_expected_contract() -> None:
    questions = demo_questions()[:10]
    final = FinalizedQuestionSet(
        role_title="Test role",
        source_jd_hash=hashlib.sha256(b"jd").hexdigest(),
        questions=[
            FinalizedQuestion(id=item.id, position=index, category=item.category, text=item.text)
            for index, item in enumerate(questions, 1)
        ],
    )
    payload = final.integration_payload("x" * 32)
    assert payload["action"] == "upsertQuestionSet"
    assert payload["integrationToken"] == "x" * 32
    assert payload["questions"][0]["position"] == 1
    assert payload["questions"][0]["category"] == questions[0].category.value
