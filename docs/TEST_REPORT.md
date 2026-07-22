# Test report

## Automated validation

| Suite | Result | Coverage |
|---|---:|---|
| Python compile | Pass | Streamlit entrypoint, domain modules, tests |
| Pytest | 29 passed | Models, distributions, validation, generator behavior, configuration, state, HTTP integration, Streamlit workflow |
| Apps Script server self-tests | 5 passed | Formula escaping, weighted math, payload validation, row schema, token comparison |
| Apps Script client syntax | Pass | Browser JavaScript compiles under Node's JavaScript parser |
| Streamlit HTTP smoke test | Pass | Headless server starts and `/_stcore/health` returns `ok` |
| Git whitespace check | Pass | `git diff --check` reports no errors |
| Secret scan | Pass with documented placeholders only | No API key, personal email, token value, or GitHub credential in tracked source |

## Streamlit workflow exercised by AppTest

- Starts without secrets and without an exception.
- Live-AI action is safely disabled when no key exists.
- Curated demo set loads all 15 questions.
- Review controls render and the valid set can be approved.
- Preview finalization produces one approved JSON download without pretending that Apps Script was contacted.

## Live deployment validation

Not yet run. It requires the repository to be pushed and the owner to complete the authenticated Google Apps Script and Streamlit Community Cloud deployments. The exact production test procedure is in `DEPLOYMENT.md`. A live item must not be marked passed until the public URL and resulting Google Sheet row have been directly verified.

## Known free-tier constraints

- Gemini API and Apps Script quotas can change or be exhausted.
- Gemini free-tier content may be used by Google to improve its products; use non-confidential JDs and fictional candidate data.
- Streamlit Community Cloud is intended for demos/community workloads and does not provide a production SLA for this project.
