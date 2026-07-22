# Owner-only handoff checklist

The codebase does not need any more product information to run. The remaining inputs are deployment credentials or owner-account actions and must not be shared in chat or committed to Git.

## Already decided

- Product name: Nutrabay Interview Intelligence
- Planned new repository: `mohdsaeedafri/nutrabay-interview-intelligence`
- Access: public demo
- Branding: polished default theme
- Data: fictional sample data only
- Persistence: Google Sheets; no separate database
- Deployment: Streamlit Community Cloud + Google Apps Script

## Owner actions still required for a live URL

1. Confirm whether “23” means **23 July 2026 in Asia/Kolkata**. This date does not change the code, but it matters for the submission record.
2. Create the Gemini API key in Google AI Studio and place it directly in Streamlit secrets. Do not send the key to an agent.
3. Create the Google Sheet, add the Apps Script files, set the private integration token, run setup/tests, and deploy the `/exec` web app as described in `DEPLOYMENT.md`.
4. Connect the GitHub repository to Streamlit Community Cloud, add the secrets directly there, and deploy.
5. Share only the non-secret public Streamlit URL and Apps Script `/exec` URL if an agent will perform final public-browser validation. Never share passwords, OTPs, API keys, or the integration token.
