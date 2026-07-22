# Nutrabay Interview Intelligence

A production-shaped assignment demo that turns a job description into a structured, human-reviewed interview plan and then scores candidates consistently.

## How it works

1. **Streamlit** accepts a JD and generates 10–15 structured questions with Gemini.
2. A manager can edit, replace, add, recategorize, exclude, and approve questions.
3. **Google Apps Script** serves the required public scorecard.
4. **Google Sheets** stores approved sets and one complete response row per evaluation.

Google Sheets is the free cloud data store; no separate database is required. A clearly labelled curated question set keeps the demo usable when AI secrets are not configured.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run streamlit_app.py
```

Never commit `.streamlit/secrets.toml`. Its expected server-side values are:

```toml
GEMINI_API_KEY = "replace-locally"
GEMINI_MODEL = "gemini-3.5-flash"
APPS_SCRIPT_WEB_APP_URL = "https://script.google.com/macros/s/DEPLOYMENT_ID/exec"
INTEGRATION_TOKEN = "replace-with-a-random-value-at-least-32-characters-long"
```

## Validation

```bash
python -m compileall -q streamlit_app.py src tests
pytest
node scripts/apps_script_self_test.js
```

The repository includes Python unit tests, Streamlit AppTest coverage, Apps Script server self-tests, client JavaScript syntax validation, and GitHub Actions CI.

## Documentation

- [Free-tier deployment and live E2E checklist](docs/DEPLOYMENT.md)
- [Requirements traceability](docs/REQUIREMENTS_TRACEABILITY.md)
- [Reusable AI-agent build prompt](docs/AI_AGENT_BUILD_PROMPT.md)
- [Test report](docs/TEST_REPORT.md)

## Privacy

Only job-description text is sent to Gemini. Candidate names, scores, and notes remain in the owner-controlled Apps Script/Sheet workflow. Use fictional sample data only in this public demo.
