from __future__ import annotations

from collections import Counter
import html
import hashlib
import json
from pathlib import Path
from typing import Any

import streamlit as st

from src.apps_script_client import AppsScriptClient, AppsScriptError
from src.config import load_settings
from src.models import Category, FinalizedQuestion, FinalizedQuestionSet, ReviewQuestion
from src.question_generator import GenerationError, GeminiQuestionGenerator
from src.question_validation import validate_review_questions
from src.sample_data import load_demo_questions, load_sample_jd
from src.ui_state import add_question, approval_fingerprint, reset_application_state


ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Nutrabay Interview Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(f"<style>{(ROOT / 'assets' / 'styles.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

try:
    secret_source: Any = st.secrets
except Exception:
    secret_source = {}
settings = load_settings(secret_source)


def initialize_state() -> None:
    st.session_state.setdefault("jd_text", load_sample_jd())
    st.session_state.setdefault("generation_count", 15)
    st.session_state.setdefault("questions", [])
    st.session_state.setdefault("role_title", "")
    st.session_state.setdefault("generation_source", "")
    st.session_state.setdefault("finalization_result", None)
    st.session_state.setdefault("finalized_fingerprint", "")


def current_questions() -> list[ReviewQuestion]:
    return [ReviewQuestion.model_validate(item) for item in st.session_state.questions]


def save_questions(questions: list[ReviewQuestion]) -> None:
    st.session_state.questions = [item.model_dump(mode="json") for item in questions]


def progress_markup(has_questions: bool, finalized: bool) -> str:
    step1 = "done" if has_questions else "active"
    step2 = "done" if finalized else ("active" if has_questions else "")
    step3 = "active" if finalized else ""
    return f"""
    <div class="steps">
      <span class="step {step1}">1 · Generate</span>
      <span class="step {step2}">2 · Review & approve</span>
      <span class="step {step3}">3 · Score in Apps Script</span>
    </div>
    """


def load_demo_set() -> None:
    role_title, questions = load_demo_questions()
    save_questions(questions)
    st.session_state.role_title = role_title
    st.session_state.generation_source = "Curated assignment demo set"
    st.session_state.finalization_result = None
    st.session_state.finalized_fingerprint = ""


def generate_live() -> None:
    jd = st.session_state.jd_text.strip()
    if not 100 <= len(jd) <= 20_000:
        st.error("Enter a job description between 100 and 20,000 characters.")
        return
    generator = GeminiQuestionGenerator(settings.gemini_api_key, settings.gemini_model)
    with st.spinner("Building a role-specific interview plan…"):
        role_title, questions = generator.generate(jd, int(st.session_state.generation_count))
    save_questions(questions)
    st.session_state.role_title = role_title
    st.session_state.generation_source = f"Live AI · {settings.gemini_model}"
    st.session_state.finalization_result = None
    st.session_state.finalized_fingerprint = ""


def current_approval_fingerprint(questions: list[ReviewQuestion]) -> str:
    return approval_fingerprint(
        questions,
        st.session_state.jd_text,
        st.session_state.get("role_title", ""),
    )


def clear_finalization_if_changed(questions: list[ReviewQuestion]) -> bool:
    old_fingerprint = st.session_state.get("finalized_fingerprint", "")
    if old_fingerprint and old_fingerprint != current_approval_fingerprint(questions):
        st.session_state.finalization_result = None
        st.session_state.finalized_fingerprint = ""
        return True
    return False


def finalize(questions: list[ReviewQuestion]) -> None:
    included = [item for item in questions if item.included]
    jd_hash = hashlib.sha256(st.session_state.jd_text.strip().encode("utf-8")).hexdigest()
    question_set = FinalizedQuestionSet(
        role_title=st.session_state.role_title or "Interview Question Set",
        source_jd_hash=jd_hash,
        questions=[
            FinalizedQuestion(id=item.id, position=index, category=item.category, text=item.text.strip())
            for index, item in enumerate(included, start=1)
        ],
    )

    fingerprint = current_approval_fingerprint(questions)
    if settings.integration_configured:
        client = AppsScriptClient(settings.apps_script_url, settings.integration_token)
        with st.spinner("Publishing the approved question set…"):
            result = client.publish(question_set)
        st.session_state.finalization_result = result
    else:
        st.session_state.finalization_result = {
            "ok": True,
            "previewOnly": True,
            "questionSetId": question_set.question_set_id,
            "payload": question_set.integration_payload("CONFIGURE_IN_STREAMLIT_SECRETS"),
        }
    st.session_state.finalized_fingerprint = fingerprint


initialize_state()
questions = current_questions()
clear_finalization_if_changed(questions)
finalized = bool(st.session_state.finalization_result)

st.markdown(
    """
    <section class="hero">
      <div class="hero-kicker">AI-first hiring workflow</div>
      <h1>Nutrabay Interview Intelligence</h1>
      <p>Turn a job description into a structured, manager-approved interview plan, then score every candidate consistently in Google Apps Script.</p>
    </section>
    """,
    unsafe_allow_html=True,
)
st.markdown(progress_markup(bool(questions), finalized), unsafe_allow_html=True)
st.markdown(
    """
    <div class="privacy-note"><strong>Demo privacy:</strong> Enter job descriptions only. Do not paste resumes, candidate names, phone numbers, email addresses, or other personal data into the AI generator.</div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.subheader("1. Generate an interview plan")
    st.caption("The assignment JD is preloaded. Replace it with another JD when needed.")
    st.text_area("Job description", key="jd_text", height=310, max_chars=20_000)
    left, middle, right = st.columns([1, 1.25, 1.25])
    with left:
        st.select_slider("Question count", options=list(range(10, 16)), key="generation_count")
    with middle:
        if settings.ai_configured:
            if st.button("✦ Generate with AI", type="primary", use_container_width=True):
                try:
                    generate_live()
                    st.rerun()
                except GenerationError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Question generation failed safely. Retry or load the curated demo set.")
        else:
            st.button(
                "✦ Generate with AI",
                disabled=True,
                use_container_width=True,
                help="Add GEMINI_API_KEY to Streamlit secrets.",
            )
            st.caption("Live AI activates after the free Gemini key is added.")
    with right:
        if st.button("Load curated demo set", use_container_width=True):
            load_demo_set()
            st.rerun()

if questions:
    st.markdown("---")
    st.subheader("2. Review and approve")
    st.caption("Edit freely. Exclude, replace, recategorize, or add questions before publishing.")

    for category in Category:
        category_items = [item for item in questions if item.category == category]
        with st.expander(f"{category.value} · {len(category_items)}", expanded=True):
            for item in category_items:
                text_key = f"q_text_{item.id}"
                cat_key = f"q_cat_{item.id}"
                inc_key = f"q_inc_{item.id}"
                st.session_state.setdefault(text_key, item.text)
                st.session_state.setdefault(cat_key, item.category.value)
                st.session_state.setdefault(inc_key, item.included)

                with st.container(border=True):
                    controls = st.columns([1.35, 1, 1])
                    with controls[0]:
                        included_value = st.checkbox("Include", key=inc_key)
                    with controls[1]:
                        category_value = st.selectbox(
                            "Category",
                            options=[value.value for value in Category],
                            key=cat_key,
                            label_visibility="collapsed",
                        )
                    with controls[2]:
                        if st.button(
                            "Replace with AI",
                            key=f"replace_{item.id}",
                            use_container_width=True,
                            disabled=not settings.ai_configured,
                        ):
                            try:
                                generator = GeminiQuestionGenerator(settings.gemini_api_key, settings.gemini_model)
                                existing = [other.text for other in questions if other.id != item.id]
                                replacement = generator.replace(
                                    st.session_state.jd_text,
                                    Category(category_value),
                                    st.session_state[text_key],
                                    existing,
                                )
                                st.session_state[text_key] = replacement
                                item.text = replacement
                                save_questions(questions)
                                st.rerun()
                            except GenerationError as exc:
                                st.error(str(exc))

                    item.included = bool(included_value)
                    item.category = Category(category_value)
                    item.text = st.text_area(
                        "Interview question",
                        key=text_key,
                        height=112,
                        max_chars=1_200,
                        label_visibility="collapsed",
                    )

            if st.button(f"＋ Add {category.value} question", key=f"add_{category.value}"):
                new_item = add_question(questions, category)
                save_questions(questions)
                st.session_state[f"q_text_{new_item.id}"] = ""
                st.rerun()

    save_questions(questions)
    if clear_finalization_if_changed(questions):
        st.rerun()
    validation = validate_review_questions(questions)
    counts = Counter(item.category for item in questions if item.included)
    included_count = sum(1 for item in questions if item.included)
    safe_generation_source = html.escape(str(st.session_state.generation_source))

    st.markdown(
        f"""
        <div class="status-grid">
          <div class="status-card"><div class="status-label">Included</div><div class="status-value">{included_count} / 15</div></div>
          <div class="status-card"><div class="status-label">Categories</div><div class="status-value">{sum(1 for c in Category if counts[c] > 0)} / 5</div></div>
          <div class="status-card"><div class="status-label">Source</div><div class="status-value" style="font-size:.95rem">{safe_generation_source}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for error in validation.errors:
        st.error(error)
    for warning in validation.warnings:
        st.warning(warning)

    finalize_col, reset_col = st.columns([2, 1])
    with finalize_col:
        if st.button(
            "Approve and create scoring form",
            type="primary",
            use_container_width=True,
            disabled=not validation.is_valid,
        ):
            try:
                finalize(questions)
                st.rerun()
            except AppsScriptError as exc:
                st.error(str(exc))
            except Exception:
                st.error("The question set could not be published safely. Your edits are still available; please retry.")
    with reset_col:
        if st.button("Reset current session", use_container_width=True):
            reset_application_state(st.session_state)
            st.rerun()

result = st.session_state.get("finalization_result")
if result:
    st.markdown("---")
    with st.container(border=True):
        st.subheader("3. Question set approved")
        st.success(f"Question set `{result['questionSetId']}` is ready.")
        if result.get("scoringUrl"):
            st.link_button(
                "Open Google Apps Script scoring form ↗",
                result["scoringUrl"],
                type="primary",
                use_container_width=True,
            )
        else:
            st.info(
                "Preview mode is complete. Add the Apps Script URL and integration token to Streamlit secrets to publish this set to the live Google Sheet."
            )
            payload = json.dumps(result.get("payload", {}), ensure_ascii=False, indent=2)
            st.download_button(
                "Download approved question-set JSON",
                data=payload,
                file_name="approved_question_set.json",
                mime="application/json",
                use_container_width=True,
            )

with st.expander("Deployment readiness"):
    st.write("Live AI", "✅ Configured" if settings.ai_configured else "○ Awaiting Gemini key")
    st.write(
        "Google Apps Script",
        "✅ Configured" if settings.integration_configured else "○ Awaiting deployed /exec URL and token",
    )
    st.caption("Secrets are read server-side and are never displayed to reviewers.")

st.markdown(
    "<div class='footer'>Structured interviews · Human-reviewed questions · Consistent scoring · Sample data only</div>",
    unsafe_allow_html=True,
)
