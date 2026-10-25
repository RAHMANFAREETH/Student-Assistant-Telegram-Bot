# Student Assistant Telegram Bot V6.0 — AI Provider Operations

**Same bot, same GitHub project, same Render service, same Supabase.** Upgrades the existing V5.9 project; does not create a new bot or replace any old modules. No paid APIs, new packages, or SQL tables required.

## What's included

- **Private admin commands:** `/aiops` or `/aiproviders` in a private Telegram chat show AI configuration readiness and anonymous Cloudflare model-call counts, failures and latency averages. `AI_OPS_ADMIN_IDS` must explicitly list your own Telegram numeric ID; if absent, the command is **denied to everyone**. Other bot users cannot see admin statistics.
- **Cloudflare model-call metrics:** observes the **existing** `_provider_call` without changing its requests, outputs, safety checks or exceptions. Separately counts generation and Llama Guard calls. No student questions, answer text, user IDs, private documents, keys or exception bodies are collected or saved. Brief-answer counts are a diagnostic signal, *not* an accuracy score.
- **Error guidance:** only sanitized error category codes are counted. Admin view provides hints for rate-limits, authentication, connectivity and moderation-service problems. Existing student error handling is not replaced.
- **Quality checker:** `AI_V6_0_QUALITY_CHECK.py` offers four built-in harmless, developer-authored examples: English mathematics, Tamil science, Sinhala science and Arabic language. Default is a **local dry run** with no network access. `--gemini` explicitly runs *one developer-only* request through the existing V5.9 Gemini client and presents a manual evaluation checklist. It never sends student content.
- **Existing Gemini preserved:** `gemini_ai_studio_v59.py` remains in the project but is **not imported or called by Telegram user handlers**. No `/gemini` command or automatic fallback has been added.

### Important limits

These are **per-process in-memory counters**, not persisted analytics: counters reset on Render restart and are separate across workers/instances. Counts are **model calls** (one student AI request can cause two moderation calls + one generation call), not unique students, paid tokens, billable usage or student daily quota. Your existing `/aistats` still shows daily quota. No database migrations were added.

Google Gemini API terms effective March 23, 2026 say not to use it as part of an application likely accessed by people under 18. This public Student Assistant Bot may serve O/L and A/L students; the Gemini client is therefore **developer-only** and cannot be used as an automatic Cloudflare fallback here. An age button or Telegram-ID allowlist does not automatically resolve this restriction. Source: https://ai.google.dev/gemini-api/terms

## Installation — Windows VS Code PowerShell

**Step 1 — Back up your working bot first.** From your current bot folder, e.g. `C:\Users\Pros\Desktop\StudentAssistantBot`:

```powershell
git status
```

Make sure V5.9 is working. The new ZIP contains **only these 5 new files** — no `main.py` or `ai_study_assistant.py` replacement:

- `ai_ops_v60.py`
- `INSTALL_V6_0.py`
- `TEST_V6_0_AI_OPS.py`
- `AI_V6_0_QUALITY_CHECK.py`
- `README_V6_0.md`

Extract and copy all five into your existing project folder.

**Step 2 — Install and run offline tests.** These commands belong in PowerShell; never paste plain Python source directly at the `PS>` prompt:

```powershell
python INSTALL_V6_0.py
python -m py_compile main.py ai_study_assistant.py ai_ops_v60.py gemini_ai_studio_v59.py
python -m unittest TEST_V6_0_AI_OPS.py TEST_V5_9_GEMINI.py TEST_V5_8_ACHIEVEMENTS.py TEST_V5_7_UI.py -v
python AI_V6_0_QUALITY_CHECK.py
```

The installer patches **only** `main.py` and `ai_study_assistant.py` and saves them as `main.py.before_v60.bak` and `ai_study_assistant.py.before_v60.bak`. It refuses unknown/partial installations. It is idempotent: rerunning it prints `already installed; no files changed`. If preflight fails, existing files stay unchanged. If old V5.8 test file still raises `UnicodeDecodeError` on Windows, the already-discussed fix is to add `encoding="utf-8"` to its `.read_text()` call(s).

**Step 3 — Configure the private admin ID in Render.** In the **existing** Render service → **Environment** → **Add Environment Variable**:

```text
Key:   AI_OPS_ADMIN_IDS
Value: <your-own-numeric-Telegram-user-ID>
```

For multiple trusted admins, use a comma-separated list, e.g. `123456789,987654321`. Do **not** enter your bot ID, API key, email or username. The admin ID does not need to match `AI_ALLOWED_USER_IDS`. This is not a new API credential. Without this setting, nobody can use `/aiops`.

**Step 4 — Review and commit only approved code.** Do not commit `.env`, API keys or `.bak` files:

```powershell
git diff -- main.py ai_study_assistant.py
git status
git add main.py ai_study_assistant.py ai_ops_v60.py INSTALL_V6_0.py TEST_V6_0_AI_OPS.py AI_V6_0_QUALITY_CHECK.py README_V6_0.md
git commit -m "Add V6.0 private AI operations and quality checks"
git push origin main
```

**Step 5 — Confirm the Render deployment is Live**, then open your bot's **private chat** using the Telegram account whose numeric ID is in `AI_OPS_ADMIN_IDS`:

```text
/aiops
/aiproviders
/ai
/aistats
```

Your diagnostics should show Cloudflare enabled/configured and Gemini as developer-only. Ask one harmless AI study question via `/ai`, then `/aiops` again. You'll see model-call counters if the same Render worker handles both updates. For security, a non-admin and a group should not get the report. Also spot-check `/asknotes`, `/askpdf`, `/achievements`, `/level`, V5.7 categories, Azure translation, AssemblyAI and OCR.

## Developer quality check (optional)

Dry-run only, zero requests:

```powershell
python AI_V6_0_QUALITY_CHECK.py --sample tamil_science
python AI_V6_0_QUALITY_CHECK.py --sample sinhala_science
```

One **explicit** adult-developer-only Gemini API request with the V5.9 client:

```powershell
python AI_V6_0_QUALITY_CHECK.py --sample english_math --gemini
```

You will be prompted for your API key securely if not supplied through the environment. The script shows the generated text so you can score correctness, requested language, clarity, useful examples, honesty about uncertainty and privacy. This is a **manual review**, not a guarantee of answer quality or a fully automated eval.

## Rollback

Restore `main.py.before_v60.bak` and `ai_study_assistant.py.before_v60.bak` over their respective files, commit and push those reverted files, and redeploy your original Render bot. The new module can remain in the repository unused. Keep your database and older features unchanged. If possible, use a prior working Git commit as your rollback point.

## Tested / not yet tested

- Offline: the 20 V6.0 unit tests passed, along with isolated tests of V5.8 registration integration and V5.5 Cloudflare instrumentation compatibility.
- **Not tested:** live Render, your actual V5.9 deployed source, Supabase connectivity or Telegram webhook. Run live smoke tests before declaring V6.0 fully deployed.

## Security and compliance reminders

- No Telegram messages or documents are routed to Gemini by V6.0.
- Do not add `GEMINI_API_KEY` to Render for this public bot; keep developer testing local and separate from student traffic.
- Gemini provider status in `/aiops` refers to module presence, **not** live connectivity or entitlement.
- Admin statistics are access-controlled by numeric Telegram sender ID and private chat; don't share your admin ID or Telegram bot token publicly.
