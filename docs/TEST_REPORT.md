# Test report

## Automated validation

| Suite | Result | Coverage |
|---|---:|---|
| Python compile | Pass | Streamlit entrypoint, domain modules, tests |
| Pytest | 39 passed on the last verified main build | Models, distributions, validation, Gemini API contracts, safe diagnostics, configuration, state, HTTP integration, Streamlit workflow |
| Apps Script server self-tests | 5 passed | Formula escaping, weighted math, payload validation, row schema, token comparison |
| Apps Script client syntax | Pass | Browser JavaScript compiles under Node's JavaScript parser |
| Streamlit HTTP smoke test | Pass | Headless server starts and `/_stcore/health` returns `ok` |
| GitHub Actions | Pass on the last verified main build | Python 3.12 and 3.14 matrix validation |
| Clean-clone release test | Pass on the last verified main build | Full Python and Apps Script suites |
| Git whitespace check | Pass | No whitespace errors |
| Secret scan | Pass with documented placeholders only | No API key, personal email, token value, or GitHub credential in tracked source |

## Streamlit workflow exercised by AppTest

- Starts without secrets and without an exception.
- Live-AI action is safely disabled when no key exists.
- A present but untested key is not falsely labelled as connected.
- Curated demo set loads all 15 questions.
- Review controls render and a valid set can be approved.
- Preview finalization produces an approved JSON download without pretending that Apps Script was contacted.

## Live production validation

The public deployment has now completed the core end-to-end path:

- Streamlit production app loaded successfully.
- Live Gemini generation succeeded with `gemini-3.5-flash-lite`.
- The resulting set contained 15 included questions across all five required categories.
- Individual AI question replacement succeeded.
- Final approval and Apps Script publishing succeeded.
- The generated public Apps Script scorecard opened successfully.
- A fictional candidate name, scores for all 15 questions, and a sample note were submitted.
- The scorecard returned a receipt with a raw score of 60/75 and a weighted score of 80%.

## Final owner-only verification still required

Before submission, the owner should:

- open the private Google Sheet and visually confirm at least one complete `Responses` row;
- confirm the intended Google Sheet sharing permission and include its shareable URL in the submission;
- run the final workflow once in an incognito browser;
- check both Streamlit and the Apps Script scorecard at mobile width;
- preserve screenshots of the final generated set, approval state, scorecard receipt, and sample Sheet row.

## Known free-tier constraints

- Gemini API and Apps Script quotas can change or be exhausted.
- Gemini free-tier content may be used by Google to improve its products; use non-confidential JDs and fictional candidate data.
- Streamlit Community Cloud is intended for demos/community workloads and does not provide a production SLA for this project.
