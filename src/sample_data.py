from __future__ import annotations

import json
from pathlib import Path

from src.models import GeneratedQuestionSet, ReviewQuestion


ROOT = Path(__file__).resolve().parents[1]


def load_sample_jd() -> str:
    return (ROOT / "assets" / "sample_jd.txt").read_text(encoding="utf-8").strip()


def load_demo_questions() -> tuple[str, list[ReviewQuestion]]:
    payload = json.loads((ROOT / "assets" / "fallback_questions.json").read_text(encoding="utf-8"))
    batch = GeneratedQuestionSet.model_validate(payload)
    return batch.role_title, [ReviewQuestion.from_generated(item) for item in batch.questions]

