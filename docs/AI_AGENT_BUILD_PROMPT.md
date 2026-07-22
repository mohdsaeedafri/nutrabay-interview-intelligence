# Reusable AI-agent build and deployment prompt

Copy the prompt below into a capable coding agent. Replace values in angle brackets, provide the original assignment PDF, and do not paste credentials or secret values into the conversation.

---

You are the senior engineer and release owner for a small but production-shaped hiring workflow. Work autonomously through investigation, implementation, verification, deployment preparation, and live validation. Do not claim completion or invent a URL unless the deployed application has been opened and verified. Preserve unrelated repository changes. Never commit or print secrets.

## Project context

- Product name: **Nutrabay Interview Intelligence**
- Repository: `<GITHUB_REPOSITORY_URL>`
- Branch: `main`
- Access: public demo
- Branding: polished default styling; no custom logo required
- Data policy: fictional sample data only
- Target deadline: `<CONFIRMED_DATE_TIME_AND_TIMEZONE>`
- Owner account actions must be performed by the owner; never request passwords, OTPs, API keys, or recovery codes in chat.

Read the attached product specification first and create a requirements traceability table before changing code. If the repository contains existing work, inspect and reuse it where sound. If a requirement conflicts with this prompt, follow the product specification and explicitly document the conflict.

## Mandatory architecture

Build a hybrid solution because the final scoring interface must be Google Apps Script:

1. **Streamlit** for job-description input, AI question generation, and manager review.
2. **Gemini Developer API** for structured generation. Keep the model configurable by a server-side secret and provide a clearly labelled curated fallback for demo resilience.
3. **Google Apps Script HTML Service** for the final candidate scorecard.
4. **Google Sheets** as the free cloud data store. Do not add a separate database unless a specification explicitly requires one.
5. **Streamlit Community Cloud** for the free public demo deployment.

## Functional requirements

### A. Question generation

- Accept a pasted job description between 100 and 20,000 characters.
- Let the manager select a total from 10 through 15.
- Generate exactly the selected total with full coverage of these five categories:
  - Intent
  - Quant Ability
  - Job Competency
  - Core Competency
  - EQ
- Define an explicit target distribution for every allowed total, not just for 15.
- Questions must be specific to the JD, non-duplicative, concise, interview-ready, and free of unsupported assumptions.
- Use a structured JSON response schema validated by Pydantic. Reject extra fields.
- Make one repair attempt for invalid model output, then fail with a safe user-facing message.
- Do not silently present fallback questions as AI-generated.

### B. Manager review

- Group questions by category.
- Allow editing/rewording, category changes, exclusion/removal, manual addition, and optional AI replacement.
- Retain stable UUIDs for questions.
- Revalidate after every change.
- Disable approval unless 10–15 included questions remain, all text is valid and unique, and all five categories are present.
- Display the included count, category coverage, and generation source.
- Keep state scoped to the current Streamlit session.

### C. Approval and integration

- Hash the JD with SHA-256 and send only the hash—not the JD—to Apps Script.
- Publish approved questions from Streamlit to the Apps Script `/exec` endpoint using a 32+ character server-side integration token.
- Never send the token to the scoring browser.
- Validate the Apps Script URL and all outbound/inbound payloads.
- Retry only safe transient HTTP failures and use bounded timeouts.
- Return a scoring URL containing an opaque UUID question-set ID.
- If integration secrets are absent, support a clearly labelled preview JSON download without pretending it was published.

### D. Google Apps Script scorecard

- Load the approved question set by validated UUID.
- Display the role, scoring guide, every finalized question, and category grouping.
- Require candidate name and exactly one integer score from 1 to 5 for every question.
- Allow optional per-question notes up to 2,000 characters.
- Revalidate everything server-side; never trust the browser.
- On submit, write exactly one row to Google Sheets containing:
  - server timestamp
  - submission UUID
  - question-set UUID and role
  - candidate name
  - raw total and maximum
  - weighted percentage
  - every question's category, full text, score, and note
- Use weights: Intent 10%, Quant Ability 20%, Job Competency 30%, Core Competency 25%, EQ 15%.
- Use a script lock around writes.
- Make submissions idempotent: double-clicks and retries using the same submission ID must never create duplicate rows.
- Escape spreadsheet formula-leading characters (`=`, `+`, `-`, `@`) in all user/model-controlled values.
- Use DOM `textContent`, not HTML interpolation, for question and user-controlled content.
- Provide responsive, accessible styles and clear loading, validation, failure, and success states.

## Sheet schema

Create and freeze headers for:

- `Question_Sets`: question-set ID, role, creation time, JD hash, position, question ID, category, text, active flag.
- `Responses`: timestamp, submission ID, question-set ID, role, candidate, raw total, raw max, weighted percent, then four columns per possible question (category, question, score, notes) through question 15.
- `Config`: schema version, category order, weights, and 1–5 scoring anchors.

Provide a one-run `setupSpreadsheet()` function for a Sheet-bound script and `runAllTests()` for Apps Script self-tests.

## Security and privacy

- Commit only a `.streamlit/secrets.toml.example`; ignore the real secrets file.
- Keep Gemini key, Apps Script URL, and integration token in Streamlit secret settings.
- Store the matching integration token in Apps Script Script Properties.
- Do not log raw keys/tokens, full JDs, candidate data, or model responses.
- Show a prominent warning that the public demo uses fictional sample data only.
- Candidate data may go only to the owner-controlled Apps Script/Sheet; it must never be sent to Gemini.
- Use generic error messages at trust boundaries and preserve useful local edits after errors.

## Engineering standards

- Target Python 3.12.
- Pin direct dependencies to tested versions.
- Keep domain logic outside the Streamlit page where practical.
- Use Pydantic models, type hints, clear names, small functions, and UTF-8 files.
- Add CI for compile checks, Python tests, Streamlit AppTest, Apps Script server self-tests, and client JavaScript syntax.
- Include a curated, role-specific sample JD and 15-question demo set.
- Include deployment documentation, requirements traceability, a test report, and this reusable agent prompt.

## Required test matrix

Run and record all of the following:

1. Python compile check.
2. Unit tests for model constraints, exact distributions 10–15, duplicate/missing/blank questions, final payloads, config parsing, state reset, HTTP success/failure/retry/URL validation, Gemini structured parsing/repair/failure, and fallback data.
3. Streamlit AppTest for clean startup without secrets and the complete curated generation → review → approval → preview flow.
4. Apps Script self-tests for score math, row width, payload validation, formula-injection escaping, and constant-time token comparison.
5. Client JavaScript syntax validation.
6. Secret scan and `git diff --check`.
7. On real deployed URLs, browser-test:
   - desktop and phone-width layouts
   - live AI generation
   - manager edit, exclude, add, recategorize, replacement, and approval validation
   - publish to Apps Script
   - empty candidate validation
   - missing score validation
   - all 1 and all 5 boundary scores
   - notes and long-but-valid input
   - successful Sheet row and totals
   - duplicate-click/idempotency behavior
   - invalid/missing question-set ID
   - reload and second-candidate use
   - browser console errors

Do not describe a test as passed if it was skipped, mocked, or blocked. Separate automated, mocked, and live results.

## Free deployment sequence

1. Finish and test the code locally.
2. Commit and push to `main` only with repository-owner authorization.
3. Have the owner create a blank Google Sheet, bind the Apps Script project, add the provided files, set `INTEGRATION_TOKEN`, run `setupSpreadsheet`, run `runAllTests`, and deploy as a web app executing as the owner with access set to `Anyone`.
4. Have the owner create the Gemini key and place it in Streamlit secrets; never ask them to send it to you.
5. Deploy the repository on Streamlit Community Cloud with `streamlit_app.py`, Python 3.12, the Apps Script `/exec` URL, matching token, Gemini key, and stable model string.
6. Obtain the real Streamlit and Apps Script URLs from the deployment UIs.
7. Execute the live browser test matrix and verify resulting Sheet rows.

If authentication or owner consent blocks deployment, stop at the exact boundary and give the owner the minimum numbered clicks required. Continue immediately after they provide only the non-secret deployment URL or confirmation. Never invent credentials, bypass sign-in, or claim the application is live before verifying it.

## Acceptance gates

The task is complete only when:

- Every specification row is mapped to code and evidence.
- All automated tests pass.
- No secret or personal email is committed.
- The public Streamlit URL loads without an exception.
- Live AI returns a valid question set.
- Approval produces a working Apps Script scoring URL.
- A fully scored fictional candidate creates exactly one correct Sheet row.
- Invalid inputs fail safely and duplicates do not create extra rows.
- Documentation contains exact reproduction and deployment steps.

Final response format:

1. Streamlit URL.
2. Apps Script scoring URL (a real finalized demo set, if safe to share).
3. Repository URL and commit hash.
4. Test results, split into automated and live.
5. Free-tier/privacy limitations.
6. Any owner-only follow-up, with no secrets included.

---
