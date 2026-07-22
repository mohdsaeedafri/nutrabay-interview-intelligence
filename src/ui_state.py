from __future__ import annotations

import hashlib
import json
from typing import Any, MutableMapping

from src.models import Category, ReviewQuestion


APP_STATE_KEYS = {
    "questions",
    "role_title",
    "generation_source",
    "finalization_result",
    "finalized_fingerprint",
    "generation_count",
}


def question_fingerprint(questions: list[ReviewQuestion]) -> str:
    data = [item.model_dump(mode="json") for item in questions]
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def approval_fingerprint(questions: list[ReviewQuestion], job_description: str, role_title: str) -> str:
    data = {
        "questions": [item.model_dump(mode="json") for item in questions],
        "job_description_hash": hashlib.sha256(job_description.strip().encode("utf-8")).hexdigest(),
        "role_title": role_title.strip(),
    }
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def reset_application_state(state: MutableMapping[str, Any]) -> None:
    for key in list(state.keys()):
        if key in APP_STATE_KEYS or key.startswith(("q_text_", "q_cat_", "q_inc_")):
            del state[key]


def add_question(questions: list[ReviewQuestion], category: Category) -> ReviewQuestion:
    question = ReviewQuestion(category=category, text="")
    questions.append(question)
    return question
