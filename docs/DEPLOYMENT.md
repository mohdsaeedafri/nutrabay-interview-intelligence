# Free-tier deployment guide

The production-shaped demo uses three free services:

| Layer | Service | Purpose | Cost for this demo |
|---|---|---|---|
| Web application | Streamlit Community Cloud | Job-description input, AI generation, manager review | Free Community Cloud account |
| AI | Gemini Developer API, `gemini-3.6-flash` | Structured question generation and replacement | Free-tier API usage, subject to Google's current limits |
| Scoring and data | Google Apps Script + Google Sheets | Public scorecard and cloud persistence | Included with the owner's Google account, subject to quotas |

No card, paid database, custom domain, or separate backend is required. Use fictional sample data only. The Gemini free tier may use submitted content to improve Google products, so never paste candidate data or confidential material into the generator.

## What the owner must have

- Write access to the GitHub repository.
- A personal Google account with Google Sheets and Apps Script access.
- A Streamlit Community Cloud account connected to that GitHub account.
- A Gemini API key created in Google AI Studio.
- One random integration token. Keep the API key and token in secret managers; never put them in Git, chat, screenshots, or documentation.

## 1. Generate the integration token

Run this once on a trusted machine:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Save the output temporarily in a password manager. The identical value is entered in Google Apps Script and Streamlit secrets.

## 2. Create the Google Sheet and Apps Script project

1. In Google Sheets, create a blank spreadsheet named `Nutrabay Interview Intelligence - Demo Data`.
2. Open **Extensions → Apps Script**. This creates a script bound to the Sheet.
3. Create or replace the project files using the repository's `apps-script/` directory:
   - Script files: `Code.gs`, `Domain.gs`, `Tests.gs`
   - HTML files: `Index.html`, `Styles.html`, `Scripts.html`
   - In **Project Settings**, enable the manifest file and replace `appsscript.json`.
4. In **Project Settings → Script properties**, add:

   | Property | Value |
   |---|---|
   | `INTEGRATION_TOKEN` | The random token from step 1 |

5. Select `setupSpreadsheet` in the editor and click **Run**. Approve the Google authorization shown to the owner. This creates `Question_Sets`, `Responses`, and `Config` tabs and saves the bound spreadsheet ID in Script Properties.
6. Select `runAllTests`, click **Run**, and confirm the returned object has `ok: true` and `passed: 5` in the execution log/result.

### Deploy the Apps Script web app

1. Click **Deploy → New deployment**.
2. Select **Web app**.
3. Description: `Nutrabay scoring form v1`.
4. **Execute as:** `Me` (the owner).
5. **Who has access:** `Anyone`.
6. Click **Deploy**, approve the requested permissions, and copy the URL ending in `/exec`.

Use the `/exec` production URL, not the `/dev` test URL. When Apps Script code changes later, open **Deploy → Manage deployments**, edit the existing deployment, select **New version**, and deploy so the public URL remains stable.

## 3. Create the Gemini key

1. Open Google AI Studio's API-key page in the owner account.
2. Create an API key for this demo.
3. Store it only in Streamlit's secret settings.

The application defaults to the stable model string `gemini-3.6-flash`. It first uses the configured model, then tries free stable compatibility models only when the configured model is unavailable. The curated demo set remains available if the live AI service is unavailable or the key has not yet been configured.

## 4. Deploy Streamlit Community Cloud

First ensure the completed code is on the repository's `main` branch.

1. Open Streamlit Community Cloud and connect the GitHub account if necessary.
2. Click **Create app → Yup, I have an app**.
3. Configure:

   | Field | Value |
   |---|---|
   | Repository | `mohdsaeedafri/nutrabay-interview-intelligence` |
   | Branch | `main` |
   | Main file path | `streamlit_app.py` |
   | Python | `3.12` |
   | Suggested subdomain | `nutrabay-interview-intelligence` (or any available variant) |

4. Open **Advanced settings → Secrets** and paste:

```toml
GEMINI_API_KEY = "replace-with-owner-key"
GEMINI_MODEL = "gemini-3.6-flash"
APPS_SCRIPT_WEB_APP_URL = "https://script.google.com/macros/s/REPLACE_DEPLOYMENT_ID/exec"
INTEGRATION_TOKEN = "replace-with-the-same-random-token"
```

5. Click **Deploy** and wait for the health check to finish.
6. Copy the assigned `https://...streamlit.app` URL.

### Live AI diagnostics

`Deployment readiness` distinguishes a secret that merely exists from a connection that has actually succeeded. A failed request displays a safe diagnostic code without exposing the key:

| Code | Meaning | Action |
|---|---|---|
| `AI-KEY` | Invalid, expired, leaked, or blocked key | Create a fresh Gemini API key in Google AI Studio and replace only `GEMINI_API_KEY` |
| `AI-ACCESS` | Key lacks Gemini permission | Use a Google AI Studio Gemini key, not OAuth credentials or an Apps Script token |
| `AI-REGION` | Free tier unavailable for the key's project/region | Verify one prompt with the same key in Google AI Studio |
| `AI-QUOTA` | Free-tier rate or usage limit reached | Wait for the limit to reset, then retry |
| `AI-MODEL` | Configured and fallback models unavailable | Recheck the model name and Google AI Studio access |
| `AI-SERVICE` / `AI-TIMEOUT` | Temporary Google service/network failure | Retry shortly; application edits remain in the session |

## 5. Production URL validation

Use fictional values throughout this validation.

1. Open the Streamlit URL in a private/incognito window.
2. Confirm the sample JD is preloaded and the live AI button is enabled.
3. Generate 15 questions. Verify exactly five category sections appear.
4. Edit one question, change one category, exclude and re-include one question, and add/remove an empty draft if desired.
5. Confirm invalid sets cannot be approved; restore a valid 10–15-question set covering all five categories.
6. Click **Approve and create scoring form**.
7. Open the generated Apps Script scoring URL.
8. Enter `Sample Candidate - Demo`, assign a 1–5 score to every question, add one sample note, and submit.
9. Confirm the success receipt appears once.
10. In Google Sheets, verify one `Responses` row contains the timestamp, candidate, each question, each score, each note, raw total, and weighted percentage.
11. Refresh and submit a second distinct sample candidate to verify repeated use.
12. Test the Streamlit and Apps Script URLs on a phone-width browser window.

## Operational notes

- Streamlit Community Cloud and Apps Script are suitable for a low-traffic assignment demo, not an SLA-backed production hiring system.
- Google quotas can change, and a quota exception stops the affected Apps Script execution.
- The scoring form is intentionally public. Treat its URL as shareable and keep the Google Sheet private to the owner.
- Candidate names and notes are stored in the Sheet. For this demo, use fictional data only.
- Question publishing is protected by the 32+ character server-side integration token; scoring submissions do not expose that token.
