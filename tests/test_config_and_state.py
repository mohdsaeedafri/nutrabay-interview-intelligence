from __future__ import annotations

from src.config import load_settings
from src.models import Category
from src.sample_data import load_demo_questions
from src.ui_state import add_question, approval_fingerprint, question_fingerprint, reset_application_state


def test_settings_require_full_apps_script_configuration() -> None:
    settings = load_settings(
        {
            "GEMINI_API_KEY": "key",
            "GEMINI_MODEL": "model",
            "APPS_SCRIPT_WEB_APP_URL": "https://script.google.com/macros/s/test/exec",
            "INTEGRATION_TOKEN": "x" * 32,
        }
    )
    assert settings.ai_configured
    assert settings.integration_configured


def test_fingerprint_changes_after_edit() -> None:
    questions = load_demo_questions()[1]
    first = question_fingerprint(questions)
    questions[0].text += " Updated"
    assert question_fingerprint(questions) != first


def test_approval_fingerprint_changes_with_jd_or_role() -> None:
    questions = load_demo_questions()[1]
    original = approval_fingerprint(questions, "Original job description", "Original role")
    assert approval_fingerprint(questions, "Updated job description", "Original role") != original
    assert approval_fingerprint(questions, "Original job description", "Updated role") != original


def test_add_question_and_targeted_reset() -> None:
    questions = load_demo_questions()[1]
    added = add_question(questions, Category.EQ)
    assert added.category == Category.EQ
    assert len(questions) == 16

    state = {"questions": [1], "q_text_abc": "x", "jd_text": "preserve", "unrelated": 9}
    reset_application_state(state)
    assert state == {"jd_text": "preserve", "unrelated": 9}
