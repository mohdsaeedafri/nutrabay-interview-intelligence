# Requirements traceability

| Assignment requirement | Implementation | Validation |
|---|---|---|
| Accept a job description | Streamlit `Job description` text area with length limits and preloaded sample | Streamlit AppTest load and workflow tests |
| Generate 10–15 questions | Gemini structured output with an exact distribution for each count from 10 through 15 | Model, validation, and generator unit tests |
| Intent questions | `Intent` enum/category, prompt target, review section, score weighting | Distribution and curated-data tests |
| Quantitative questions | `Quant Ability` enum/category, prompt target, review section, score weighting | Distribution and curated-data tests |
| Job competency questions | `Job Competency` enum/category, prompt target, review section, score weighting | Distribution and curated-data tests |
| Core competency questions | `Core Competency` enum/category, prompt target, review section, score weighting | Distribution and curated-data tests |
| Emotional intelligence questions | `EQ` enum/category, prompt target, review section, score weighting | Distribution and curated-data tests |
| Manager can edit/reword | Editable question text areas | Streamlit AppTest and state tests |
| Manager can replace | `Replace with AI` per question; manual edit remains available without AI | Generator replacement tests |
| Manager can remove | Per-question `Include` control excludes it from finalization | Validation and AppTest workflow |
| Manager can add | Per-category add controls | State helper tests |
| Manager confirms final set | Approval button enabled only for a valid 10–15 question set with all categories | Validation tests and AppTest finalization |
| Final scoring UI in Google Apps Script | Responsive Apps Script HTML scorecard loaded by question-set ID | Client syntax check plus server self-tests |
| Candidate name | Required 2–100 character field, revalidated server-side | Apps Script validation logic |
| Each finalized question displayed | Question set loaded from the Sheet and rendered in category order | Apps Script data and rendering logic |
| Required 1–5 score per question | Radio controls plus server-side integer/range checks | Apps Script self-tests and validation logic |
| Optional notes | Per-question 2,000-character notes field | Apps Script row-builder test |
| Submit to Google Sheet | Locked, idempotent single-row write to `Responses` | Apps Script self-tests and deployment E2E checklist |
| Timestamp and totals | Server timestamp, raw total/max, weighted percentage | Score-calculation and row-shape tests |
| Free demo deployment | Streamlit Community Cloud, Gemini free tier, Apps Script, Google Sheets | Deployment guide and live URL checklist |
| Safe public demo | No secrets in repository, token-protected publishing, formula-injection escaping, sample-data warnings | Config tests, self-tests, secret scan in release checklist |
