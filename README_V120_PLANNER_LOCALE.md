# Student Assistant V12.0 — Trilingual Forms + Read-Only Academic Planner

**DEVELOPMENT BUILD ONLY. Keep `SUPER_MINIAPP_V120_ENABLED=false`. Do not deploy/enable for all users yet.**

This package upgrades the user's locally installed 50-tool V12 preview. It **does not** modify `main.py`, the existing `/library` app, the old bot handlers, the Render environment, requirements, Dockerfile or the Supabase database schema.

## What's included

- Preserves all **50** working tools, original Library link, and existing 18+ Telegram-signed session requirements.
- Localized **67 calculator/form field labels**, tool calculate/copy controls, common planner text, and essential navigation in English, Tamil and Sinhala. The original 50 localized tool names are retained.
- Adds a **read-only private academic overview** on the Planner tab: pending assignments and upcoming exams from the existing `assignments.py`/`exam_planner.py` Supabase-backed query functions. It displays up to 30 of each, with a manual Refresh button, and never writes to existing tables. Records are filtered by the **server-verified Telegram account ID**, not an ID passed from the browser.
- Quick tasks and favorites are still stored only on the current device in browser local storage; they **are not synchronized** and are **not** backend reminders. For editing assignments/exams and receiving scheduled alerts, continue using the working bot.
- The local task ID generator also works in browsers without `crypto.randomUUID`, which helps development on non-HTTPS origins. Production continues to require HTTPS through Telegram.
- Handles Supabase/API failures with a generic message instead of exposing database errors in the response.

**Localization is not yet 100% complete:** 50 tool names and 67 field labels plus main UI are translated, but many calculated result strings, validation errors, dropdown options, tool descriptions, image editor prompts, and portions of the old Library remain in English. Native-speaker review is still required before a public V12 release. Do not claim otherwise.

## Install in VS Code (Windows PowerShell)

1. Extract **all** ZIP contents directly into `C:\Users\Pros\Desktop\StudentAssistantBot`. Preserve the `V120_PLANNER_LOCALIZATION_PAYLOAD` directory next to the installer.
2. Confirm the 50-tool expansion was previously applied and local tests passed (your previous results: 12 Python, 39 Node, 92/92 regression modules).
3. Run the read-only installer check:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V120_PLANNER_LOCALE.py --check
```

Expected: six UPDATEs (five Mini App files plus corrected Python test) and two ADDs (new planner/locale test files). If `--check` stops because any installed file has changed, **do not overwrite it**; review the differences first.

4. Apply only if the check is clean:

```powershell
python INSTALL_V120_PLANNER_LOCALE.py --apply
python -m py_compile main.py super_miniapp_v120.py
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 TEST_SUPER_PLANNER_V120 TEST_INSTALL_V120_PLANNER_LOCALE -q
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

The guarded installer makes a timestamped `V120_PLANNER_LOCALE_BACKUP_...` folder and is repeatable (idempotent). It copies only the six specific existing development files and adds two test files. A separate installer self-test file is included directly in the ZIP root.

### Important limitations

- In the ChatGPT standalone build (Flask not installed), 19 Python app tests ran with **2 Flask-specific HTTP tests skipped**, the installer self-tests ran **5/5**, and Node ran **45/45**. A mobile browser smoke test with **mock Telegram and planner responses** passed. These are **not** a substitute for your real Flask/Telegram tests.
- No Supabase SQL migration is needed for this read-only integration, but the existing `assignments` and `exams` tables must be configured and accessible through the existing bot's database client.
- If the upstream bot module names or `get_assignments` / `get_exams` signatures changed, the private planner API may show a temporary unavailable notice. Do not change production data to make the preview work.
- The Planner tab requires a signed Telegram Mini App session and verified 18+ access; a normal browser cannot access user records.
- To test the Mini App live later, we must create a secure adult-only pilot, verify real Telegram data, and then test mobile browser behavior. Do **not** enable the public feature flag yet.
- Keep any `.env`, Telegram Telethon sessions, backups, access tokens, and Supabase service secrets out of GitHub. Never `git add .` in this repository.

## Security/compatibility check

No new writes to existing academic tables, no unauthenticated endpoint, no Supabase key sent to the browser, no new cross-origin access, and no change to `/library`. Planner API uses the same opt-in feature flag as `/app` and the same `verify_super_session` validation.

## Rollback

The installer creates `V120_PLANNER_LOCALE_BACKUP_...` containing every overwritten file. Keep `SUPER_MINIAPP_V120_ENABLED=false`. If rollback is needed, restore only the named files after checking whether you made later edits, and remove the two new tests if desired.
