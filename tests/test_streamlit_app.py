from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def find_button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_app_loads_without_secrets_or_exceptions() -> None:
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    assert any("Nutrabay Interview Intelligence" in markdown.value for markdown in app.markdown)
    assert find_button(app, "✦ Generate with AI").disabled
    assert not find_button(app, "Load curated demo set").disabled


def test_curated_review_and_preview_finalization_flow() -> None:
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    find_button(app, "Load curated demo set").click()
    app.run()
    assert not app.exception
    assert len([area for area in app.text_area if area.label == "Interview question"]) == 15
    approve = find_button(app, "Approve and create scoring form")
    assert not approve.disabled
    approve.click()
    app.run()
    assert not app.exception
    assert app.session_state["finalization_result"]["previewOnly"] is True
    assert len(app.download_button) == 1

