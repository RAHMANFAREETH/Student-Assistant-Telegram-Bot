# Student Assistant Telegram Bot V6.1 — Gemini on Render: safe diagnostics

**Same Telegram bot, same GitHub repository, same Render service.** No new bot/token, database table or `pip` dependencies. This upgrade leaves `main.py`, `navigation.py`, `ai_study_assistant.py` and all Cloudflare student handlers **unchanged**.

### What this does

1. Updates the **admin-only** `/aiops` report with a **configuration indicator** for the Render `GEMINI_API_KEY` environment variable. The report never prints the key or calls Gemini. The variable is **not** `AI_OPS_ADMIN_IDS` (that is only for admin authorization).
2. Adds `gemini_render_v61.py`: a **private developer CLI** that can either check the environment **without a network request** or, using explicit `--live`, make **one harmless request** to Google AI Studio with a fixed arithmetic question. No student data or output text is logged.
3. Reports sanitized HTTP status categories: permissions/auth (401/403), missing model (404), quota (429), service/network failures; when supplied by Google, `usageMetadata` token counts are for **that one diagnostic request**. This **cannot** read remaining requests per minute/day, overall Gemini spend or actual billing quota.
4. Keeps Gemini **disabled for all Telegram user messages**: this is not a provider switch, chatbot command, fallback path or adult age-gate.

**Age restrictions:** The Google Gemini API Additional Terms of Service effective March 23, 2026 prohibit using the API as part of an application likely to be accessed by under-18 users. A public student bot including O/L/A/L learners therefore must not send its users' messages to Gemini; don't treat adding a key, using an admin allowlist, or creating an age-confirmation button as permission to do so. Source: https://ai.google.dev/gemini-api/terms

## Installation (Windows 11 / VS Code PowerShell)

1. Back up your working V6.0 project / commit. Copy **only** these files from the ZIP into `C:\Users\Pros\Desktop\StudentAssistantBot`:
   - `gemini_render_v61.py`
   - `INSTALL_V6_1.py`
   - `TEST_V6_1_GEMINI_RENDER.py`
   - `README_V6_1.md`
2. Make sure existing `ai_ops_v60.py` and `gemini_ai_studio_v59.py` are still in that folder. Run:

```powershell
python INSTALL_V6_1.py
python -m py_compile ai_ops_v60.py gemini_render_v61.py INSTALL_V6_1.py
python -m unittest TEST_V6_1_GEMINI_RENDER.py TEST_V6_0_AI_OPS.py TEST_V5_9_GEMINI.py -v
```

The installer **patches only `ai_ops_v60.py`** and creates `ai_ops_v60.py.before_v61.bak` once; on repeat it prints `already installed`. It refuses missing/incompatible files and existing backups (without overwriting them). Tested with UTF-8/emoji and Windows CRLF. The combined test suite passed **72 offline tests** in our reference V5.9–V6.0 environment; run on your own project to confirm compatibility.

3. Confirm that your existing Render Environment already contains `GEMINI_API_KEY` (Google AI Studio credential) and `AI_OPS_ADMIN_IDS` (your numeric Telegram account ID). **No new secrets or variables** are needed. Do **not** paste your secret key into Terminal commands, GitHub or chat.
4. Commit and push only the relevant files (do not include `.bak` or `.env`):

```powershell
git status
git add ai_ops_v60.py gemini_render_v61.py INSTALL_V6_1.py TEST_V6_1_GEMINI_RENDER.py README_V6_1.md
git commit -m "Add V6.1 Gemini Render configuration diagnostics"
git push origin main
```

5. Wait for **Render → Deploys → Live**. In your Telegram bot's **private chat** with the admin account, send `/aiops`. It should display `Gemini API key on Render: configured; connectivity: not tested by /aiops`. This means only that the Render process can see the variable; it is **not** evidence the Gemini API works from Render. `/ai` stays on Cloudflare.

## Optional live API test *from Render*

**Paid Render web service / supported workers only:** Render Dashboard → your service → **Shell**:

```bash
python gemini_render_v61.py --check
python gemini_render_v61.py --live
```

- `--check` reads just the Render environment and makes **zero** API requests.
- `--live` explicitly makes **one developer-only** API request using the `GEMINI_API_KEY` already stored in that environment. It does not show private input/output text or the key. No automatic retry.
- Example successful output: `Live probe status: ok`; optional token counts are from this probe only.
- If `Live probe status: quota`, inspect Google AI Studio's rate limits/usage; if `authentication` or `permission`, check key permissions; if `model_unavailable`, check model access. No raw API error bodies or secrets are printed.

**If your Render web service is on the Free plan:** Render does **not** provide Dashboard Shell or SSH access for free web services. See https://render.com/docs/ssh and https://render.com/docs/free . You can still confirm configuration via `/aiops`; the V5.9 local smoke test verifies connectivity **from your computer, not Render**. This ZIP intentionally does **not** add a public `/gemini` endpoint, a web diagnostic URL, or an automatic startup request to a mixed-age student application. A truly Render-origin live request requires an appropriate private/paid execution environment.

## Quick local behavior check (optional)

To check from your own PC you must separately have `GEMINI_API_KEY` configured as a local environment variable; Render environment variables are **not automatically available** in VS Code. The private V5.9 local tester remains available:

```powershell
python GEMINI_V5_9_DEV_TEST.py --smoke
```

## Rollback

If an issue appears, replace `ai_ops_v60.py` with `ai_ops_v60.py.before_v61.bak`, then commit and push the restored file. Alternatively revert the V6.1 Git commit. The other V6.1 files can remain unused; Cloudflare and the student data are unaffected.

## Security / behavior guarantees and limits

- `GEMINI_API_KEY` stays only in environment variables, never printed or embedded in URLs; auth uses `x-goog-api-key` header.
- No private data, Telegram IDs, notes, PDFs, answers, or HTTP error bodies are transmitted or logged by this diagnostic. The live probe uses one fixed, benign question.
- `/aiops` is already restricted to a private chat and `AI_OPS_ADMIN_IDS` by V6.0. This update does not change its authorization logic.
- Tests are offline and mock the API. We **have not remotely logged into your Render service or made a live Gemini request from it**.
- No background polling/automatic API usage. Output token numbers do **not** equal remaining API allowance or cost.
