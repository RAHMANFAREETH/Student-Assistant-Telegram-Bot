# Student Assistant Telegram Bot — V6.2 AI Reliability Upgrade

**Upgrade the existing V6.1 project. No new Telegram bot, Render service, Supabase table, API key, or pip package needed.** Cloudflare remains the student-facing AI. Gemini 3.1 Flash-Lite stays developer-only in the same project. No new Gemini student routing or automatic fallback.

## What this actually adds

- A **private `/aihealth`** command, reusing your V6.0 `AI_OPS_ADMIN_IDS` access control and private-chat check. Non-admin accounts and groups cannot view it.
- **Passive Cloudflare model-call monitoring**: rolling 15-minute window, last 300 completed calls maximum, split into generation and Llama Guard safety calls; counts of success/failure and sanitized error categories; approximate 95th-percentile generation latency. Health statuses are inferred from observed calls, not from a live Cloudflare API health endpoint.
- Admin troubleshooting advice for detected auth failures, rate limits, safety errors, and repeated generation failures. The existing student-facing error messages are **not rewritten**.
- A configuration-only summary of `AI_DAILY_LIMIT`; it **does not** provide remaining Cloudflare credits, Gemini quota, billing amounts, or per-user Supabase daily usage. Students can continue to use the existing `/aistats` command.
- A count of unusually short generation responses as a **weak signal to review**, not an assessment of factual correctness or model answer quality.

Privacy: the monitor records **no Telegram IDs, students' messages, notes, file contents, answer text, exception messages, HTTP response bodies, or API secrets**. Metrics are memory-only and reset on Render restarts; separate workers have separate data. Monitoring does not make extra AI API calls, change model outputs, bypass moderation, automatically retry requests, or switch Cloudflare traffic to Gemini.

## Install — Windows PowerShell in VS Code

1. Back up your working V6.1 project, or make a Git commit before changes.
2. Copy **only four files** from the ZIP to `C:\Users\Pros\Desktop\StudentAssistantBot`:
   - `ai_reliability_v62.py`
   - `INSTALL_V6_2.py`
   - `TEST_V6_2_RELIABILITY.py`
   - `README_V6_2.md`
3. **Do not overwrite** your existing `main.py`, `ai_ops_v60.py`, `ai_study_assistant.py`, `gemini_render_v61.py`, or `gemini_ai_studio_v59.py` with old versions. The installer safely adjusts only `ai_ops_v60.py` and `ai_study_assistant.py`, creating unique `.before_v62.bak` files. It refuses incompatible or partly installed previous versions. Running twice is safe.
4. Open **PowerShell** in the project directory (commands below are PowerShell commands, not Python code):

```powershell
python INSTALL_V6_2.py
python -m py_compile ai_reliability_v62.py ai_ops_v60.py ai_study_assistant.py
python -m unittest TEST_V6_2_RELIABILITY.py TEST_V6_1_GEMINI_RENDER.py TEST_V6_0_AI_OPS.py TEST_V5_9_GEMINI.py -v
```

Reference environment: **91 offline tests pass** for V5.9–V6.2 combined. Your locally modified versions may vary; do not deploy if tests fail. Some optional files such as `TEST_V5_9_GEMINI.py` are from your existing upgrades. Run `python -m unittest TEST_V6_2_RELIABILITY.py -v` alone if only checking this upgrade.

5. When all tests pass:

```powershell
git status
git add ai_study_assistant.py ai_ops_v60.py ai_reliability_v62.py INSTALL_V6_2.py TEST_V6_2_RELIABILITY.py README_V6_2.md
git commit -m "Add V6.2 AI reliability diagnostics"
git push origin main
```

**Never commit `.env`, `.bak`, credential files, or API keys.** LF/CRLF warnings from Git on Windows are informational.

6. When Render shows **Live**, open your bot's **private chat using the Telegram account set in `AI_OPS_ADMIN_IDS`**, and send:

```text
/aihealth
```

Expected report with no recent AI calls: `Cloudflare (passive): NO RECENT CALLS`. That is *not* a failure and does *not* test the internet. Next, submit a normal test question via `/ai`, wait for its answer, then send `/aihealth` again. Calls should appear if they were handled by the same Render process. Existing `/aiops`, `/aistats`, `/asknotes`, `/askpdf`, language tools and other student features are unchanged.

### Example status explanations

- `NO RECENT CALLS`: Nothing in the current process's last-15-minute observation window.
- `RECENT CALLS OK`: Successful generation requests observed, not a guarantee of answer correctness.
- `RATE LIMITED`: Cloudflare returned a rate-limit category during a recent request. Check provider quota/rate limits.
- `ACTION NEEDED`: Authentication/permission errors were observed. Check the token and account configuration **in Render**, never in chat.
- `SAFETY CHECK ERRORS`: A moderation request failed; V6.2 does not bypass Llama Guard.

### Google AI Studio — still part of the project

`GEMINI_API_KEY` remains on Render, and V5.9/V6.1 developer tools remain unchanged. V6.2 does **not** connect Telegram student messages or PDFs to Gemini, nor auto-switch when Cloudflare is unavailable. Google's Gemini API terms prohibit use in applications likely to be accessed by under-18 users: https://ai.google.dev/gemini-api/terms .

### Rollback

Restore `ai_study_assistant.py` from `ai_study_assistant.py.before_v62.bak` and `ai_ops_v60.py` from `ai_ops_v60.py.before_v62.bak`, commit and push them. The standalone V6.2 files may remain but will no longer be imported. Or use `git revert` on your V6.2 commit. Do not expose the backup files in Git.

### What has and has not been verified

- The installer is designed for the exact V6.0/V6.1 patch patterns used in the existing upgrade ZIPs, and has been syntax-checked against the V5.5 Cloudflare module plus V6.0 instrumentation and V6.1 admin report. Offline tests mock all AI requests.
- **We have not executed the installer on your private Windows project, connected to your Render account, or confirmed live Telegram behavior**. Follow the above verification sequence before relying on it.
