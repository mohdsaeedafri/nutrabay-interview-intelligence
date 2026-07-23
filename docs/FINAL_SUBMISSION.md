# Nutrabay Interview Intelligence

## Process Analyst - Founder's Office Take-Home Assignment

**Working application:** https://nutrabay-interview-intelligence-3duq37sbxlfsunvebjwmdc.streamlit.app/

**Google Apps Script scorecard:** https://script.google.com/macros/s/AKfycbyxPOvs8DgQACKtmb2iHJksyzyVscO0AOo26a7wg4U4S1x4PDqemw5w3TNmBvIRvEc/exec

**Source repository:** https://github.com/mohdsaeedafri/nutrabay-interview-intelligence

> Before submitting, add the shareable Google Sheet URL in the submission email or cover note and verify that the reviewer has the intended access. The Sheet URL is intentionally not stored in this public repository.

## 1. What I built

Nutrabay Interview Intelligence is a three-part interview workflow:

1. A Streamlit application accepts a job description and uses Gemini to generate 10-15 role-specific questions.
2. A manager review layer allows a non-technical hiring manager to edit, replace, recategorize, add, exclude, validate, and approve questions.
3. A Google Apps Script scorecard displays the approved questions, records 1-5 scores and optional notes, and writes the completed evaluation to Google Sheets.

The workflow is:

```text
Job Description
  -> Streamlit question generation
  -> Manager review and approval
  -> Secure publish to Google Apps Script
  -> Public scorecard
  -> Google Sheets response record
```

## 2. Tools selected and why

### Streamlit

Streamlit was selected for the question-generation and review experience because it supports a polished Python-first interface, server-side secret management, fast iteration, and free Community Cloud deployment. It also makes the review layer usable without technical knowledge.

### Gemini Developer API

Gemini was selected because the assignment allows any AI tool for question generation and the Developer API supports structured JSON output. The deployed demo uses `gemini-3.5-flash-lite`, which was the model verified successfully with the available free-tier project.

The generation prompt requires:

- 10-15 questions;
- all five assignment categories;
- an exact category distribution for the chosen total;
- questions tied to the responsibilities, metrics, tools, and seniority in the supplied JD;
- numerical information in Quant Ability questions;
- no protected-personal-attribute questions;
- JSON-only structured output.

The application validates the model response locally and performs one repair attempt if the response does not meet the schema or category distribution.

### Google Apps Script and Google Sheets

Google Apps Script was used because it is the assignment's non-negotiable scoring technology. It provides the public HTML scorecard and writes responses directly to an owner-controlled Google Sheet. Google Sheets was used as the transparent backend so a reviewer can inspect both approved question sets and completed evaluation rows without a separate database.

## 3. Manager review layer

Questions are grouped under:

- Intent
- Quant Ability
- Job Competency
- Core Competency
- EQ

For every question, the manager can:

- read the generated text in its category;
- edit or reword the text directly;
- replace the individual question with AI;
- change its category;
- include or exclude it from the final set;
- add a new question to a category.

The application prevents approval unless:

- 10-15 questions are included;
- every required category is represented;
- every included question has valid text;
- duplicate questions are removed.

Approval creates a fingerprint of the finalized state. If the questions change afterward, the set must be approved again before publishing.

## 4. Generated questions for the supplied JD

The following 15-question set is the curated, submission-safe output for the provided Senior Analyst - D2C Growth JD. The live system also successfully generated and approved a 15-question set with all five categories.

### Intent

1. What specifically attracts you to the Senior Analyst - D2C Growth role at Nutrabay at this point in your career, and which two D2C problems would you most want to own in your first 90 days?
2. Over the next two years, what are you optimizing for in your career - depth of analytics, ownership of business outcomes, stakeholder exposure, or something else - and how does this role support that goal?

### Quant Ability

3. In one week, 200,000 users add an item to cart, 120,000 start checkout, and 84,000 place an order. Sixty percent of orders are COD. COD RTO is 22% and prepaid RTO is 4%. Calculate cart-to-order conversion and realized orders after RTO for COD, prepaid, and total. Which lever would you investigate first, and why?
4. Weekly cancellation rate rises from 5% to 8% on 20,000 orders with an average order value of INR 2,000. Estimate the incremental cancelled orders and GMV at risk. What else would you need before calling the movement statistically and commercially meaningful?

### Job Competency

5. Nutrabay's checkout conversion drops from 3.8% to 3.1% in three days. Build a hypothesis tree and describe the first cuts you would make by traffic source, device, geography, SKU, and customer segment. How would you separate a symptom from the root cause?
6. Design a cohort analysis to determine whether first-time buyers acquired through discount-heavy campaigns become valuable 90-day customers. Define the cohort, outcome metrics, comparison groups, and biases that could make the result misleading.
7. You must build a daily D2C health dashboard covering cancellation rate, cart drop-off, checkout conversion, COD-to-prepaid ratio, RTO percentage, and funnel leakage. How would you define the metrics, choose alert thresholds, and prevent false alarms from seasonality or low volume?
8. Walk us through an analysis or dashboard you built faster using an LLM or vibe-coding tool. What did the model create, how did you validate the calculations and code, and what controls prevented data leakage or confident but incorrect output?

### Core Competency

9. A founder gives you the brief, "Conversion is down - fix it by Friday." How would you reframe the problem, align on the decision that must be made, and push back on unsupported assumptions without creating friction?
10. Tell us about an important business problem or anomaly that nobody assigned to you. How did you notice it, decide it deserved attention, investigate it, and ensure the finding resulted in action?
11. A competitor introduces a shorter checkout flow and a prepaid offer. How would you turn that observation into Nutrabay-specific hypotheses, prioritize them, and design a test that distinguishes correlation from causation?
12. Your analysis suggests the highest-priority fix belongs to Product, while Marketing and Visual Merchandising believe their initiatives matter more. How would you present the evidence, make trade-offs explicit, and drive a decision and follow-through?

### EQ

13. Describe a time you were confident in an analysis and later found that you were wrong. How was the error discovered, how did you communicate it, and what did you change in your working method?
14. Tell us about a stakeholder who rejected or challenged a well-supported conclusion. What did you do to understand the resistance, and how did you preserve the relationship without weakening the analytical standard?
15. A serious metric anomaly appears while several leaders are requesting immediate answers and the data is incomplete. How do you manage the pressure, communicate uncertainty, divide the work, and avoid publishing a premature conclusion?

## 5. Google Apps Script scoring interface

The Apps Script web app receives a finalized question-set identifier and loads the associated questions from the `Question_Sets` tab. The interviewer sees:

- the role title;
- all approved questions grouped by category;
- a required 1-5 score for every question;
- an optional notes field for every question;
- a candidate-name field;
- a submit button.

### Scoring scale

| Score | Anchor |
|---:|---|
| 1 | No evidence / poor |
| 2 | Weak evidence |
| 3 | Meets expectations |
| 4 | Strong evidence |
| 5 | Exceptional evidence |

A five-point anchored scale was chosen because it is familiar, quick to apply during an interview, and provides enough separation without implying false precision. The text anchors reduce manager-to-manager interpretation differences.

### Category weights

| Category | Weight |
|---|---:|
| Intent | 10% |
| Quant Ability | 20% |
| Job Competency | 30% |
| Core Competency | 25% |
| EQ | 15% |

Job Competency receives the highest weight because the role is execution-heavy and requires direct evidence of D2C analytics capability. Core Competency is next because the role works with founders and cross-functional teams and requires structured RCA, ownership, and clear communication. Quant Ability is essential for funnel and product-metric reasoning. Intent and EQ remain meaningful but do not dominate demonstrated job performance.

The weighted result is calculated by averaging scores within each category and applying the category weight. This prevents a category from receiving extra influence merely because it contains more questions.

## 6. What is written to Google Sheets

### `Question_Sets`

Each approved question is stored with:

- question-set ID;
- role title;
- creation timestamp;
- source JD fingerprint;
- position;
- question ID;
- category;
- question text;
- active status.

### `Responses`

Each completed scorecard is written as one row with:

- server timestamp;
- submission ID;
- question-set ID;
- role title;
- candidate name;
- raw total;
- raw maximum;
- weighted percentage;
- category, question, score, and notes columns for up to 15 questions.

The fixed 15-question schema keeps the Sheet straightforward even when a manager approves 10-14 questions; unused columns remain blank.

## 7. Reliability, validation, and privacy

The implementation includes:

- strict question-count and category validation;
- duplicate-question detection;
- server-side score and input validation;
- UUID validation for question sets, questions, and submissions;
- script locking around writes;
- duplicate-submission protection;
- spreadsheet-formula injection escaping;
- a 32+ character shared integration token for Streamlit-to-Apps-Script publishing;
- Streamlit secret storage for the Gemini API key and integration configuration;
- no candidate names, scores, or notes sent to Gemini.

The public demonstration is intended for fictional data only.

## 8. Validation completed

The repository includes and has previously passed:

- Python compilation;
- 39 Python tests covering domain models, validation, Streamlit state, Gemini request contracts, diagnostics, and integration behavior;
- five Apps Script domain tests;
- browser JavaScript syntax validation;
- Streamlit health checks;
- GitHub Actions checks on Python 3.12 and 3.14.

Live validation completed successfully for:

- Streamlit production loading;
- Gemini generation using `gemini-3.5-flash-lite`;
- 15 included questions across all five categories;
- individual AI question replacement;
- final approval and Apps Script publishing;
- public scorecard opening;
- candidate name, all scores, and a sample note submission;
- receipt generation;
- a test result of 60/75 raw and 80% weighted.

## 9. Limitations and improvements with more time

- Gemini free-tier quotas or model availability may temporarily block live generation. The curated set keeps the workflow demonstrable when this occurs.
- Streamlit Community Cloud and Apps Script are appropriate for an assignment demo, not an SLA-backed production hiring platform.
- The public scorecard uses possession of the generated URL rather than user authentication. A production version would add interviewer authentication and authorization.
- Candidate information is stored in Google Sheets. A production rollout would require a formal retention policy, access controls, audit logging, and privacy review.
- Formal accessibility and cross-device testing could be expanded.
- A production system would add question-quality analytics, interviewer calibration reporting, role templates, version history, and controlled question banks.

## 10. Evaluator instructions

1. Open the Streamlit application.
2. Use the preloaded JD or paste the supplied assignment JD.
3. Generate 15 questions with AI, or load the curated set if the free-tier service is temporarily unavailable.
4. Review, edit, exclude, replace, or recategorize questions.
5. Approve the valid final set.
6. Open the generated Google Apps Script scorecard.
7. Enter a fictional candidate name, score every question, and add an optional note.
8. Submit and confirm the receipt and weighted score.
9. Open the shared Google Sheet to inspect the approved questions and sample response row.

## 11. Links to include in the final submission

- Streamlit application: https://nutrabay-interview-intelligence-3duq37sbxlfsunvebjwmdc.streamlit.app/
- Google Apps Script scorecard: https://script.google.com/macros/s/AKfycbyxPOvs8DgQACKtmb2iHJksyzyVscO0AOo26a7wg4U4S1x4PDqemw5w3TNmBvIRvEc/exec
- GitHub repository: https://github.com/mohdsaeedafri/nutrabay-interview-intelligence
- Google Sheet: **add the owner-approved shareable Sheet URL before submission**
