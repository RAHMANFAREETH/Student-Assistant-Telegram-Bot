# Student Assistant — V12.0 development patch 3: secure task synchronization and translated results

**STATUS: DEVELOPMENT ONLY.** Keep `SUPER_MINIAPP_V120_ENABLED=false` in Render. Do not push a public V12 release until full production verification.

This patch is designed **only** for the V12.0 Super Mini App after the `V120_Multilingual_Planner_Integration.zip` package (the one whose local regression was 94/94 modules and whose Node tests passed 45/45). It is not a standalone bot.

## New behavior

- Adds an **independent new table** `public.v120_quick_tasks`, and a Flask API under `/app/api/tasks` for creating, listing, checking off, and deleting quick tasks. It uses the bot's existing server-side `db.supabase` connection. No service key is placed in JavaScript.
- Every endpoint checks signed Telegram Mini App initData and the existing server-side verified-18+ record; every database operation uses the verified Telegram ID as `user_id` and scopes mutations to it. It does **not** accept a client-supplied user ID.
- When the API is available, tasks are saved on the server and can be viewed from multiple devices signed in to the same Telegram account. Up to **100** quick tasks per user are supported. A database trigger guards the quota even for simultaneous inserts.
- Existing device-only quick tasks are **not silently uploaded or overwritten**. After synchronization connects, an **Import older device-only tasks** button appears. Import is initiated only by the user, uses stable UUIDs to avoid duplicate inserts on retries, and saves a local backup under `tasks_backup_before_import` after successful import. An interrupted import preserves the original tasks for retry.
- If the task service is unavailable or the new SQL table is not installed, the app explicitly reports **device-only/offline mode** and keeps existing local tasks. Do not confuse device-only changes with synchronized tasks.
- Adds English, Tamil and Sinhala UI strings for sync status, import and common calculation result labels. Most numeric outputs are translated; raw user text is never rewritten. Some tool descriptions, dropdown choices, image editor help and exceptional error details still require translation/native-language review. Do not claim 100% localization yet.
- Does not alter the Book Library route, PDF conversion services, Admin Hub, Smart Bulk, existing assignments/exams tables, reminders, or hosting configuration.

**A new Supabase migration is required before real remote synchronization can work.** The installer copies `SQL_V120_QUICK_TASKS.sql` into your project; **it does not execute it**. The migration is deliberately separate and should be reviewed and applied only after local code tests, before a controlled Telegram pilot.

## Install in VS Code (Windows PowerShell)

1. Extract all ZIP contents into `C:\Users\Pros\Desktop\StudentAssistantBot`. Preserve the `V120_TASK_SYNC_PAYLOAD` directory beside the installer script.
2. Run a non-writing check:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V120_TASK_SYNC.py --check
```

The expected changes are **five UPDATEs and five ADDs**. If you see `Unexpected local changes`, **stop** and review your files. Do not copy over a file manually or bypass the hash guard.

3. Apply the patch **only after CHECK OK**:

```powershell
python INSTALL_V120_TASK_SYNC.py --apply
python -m py_compile main.py super_miniapp_v120.py super_miniapp_v120_tasks.py
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 TEST_SUPER_PLANNER_V120 TEST_SUPER_TASK_SYNC_V120 TEST_INSTALL_V120_TASK_SYNC -q
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_SUPER_TASK_SYNC_V120.mjs
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

4. **Do not deploy yet.** Share the terminal output and we can review it. Keep `SUPER_MINIAPP_V120_ENABLED=false`. Existing Render production remains V11.9.2.1 until a deliberate V12 release.

## Supabase SQL (later, before pilot)

Review `SQL_V120_QUICK_TASKS.sql` in your project and run its SQL in your existing Supabase project's SQL Editor only when preparing the controlled test. It creates one table with row-level security enabled, revokes public client privileges, grants server-side service-role access, and adds a task limit trigger. No existing table is dropped or modified.

**Do not paste your service-role secret, bot token, `.env` or SQL Editor credentials here.** You do not need another Supabase project.

## Later Telegram pilot and full release

- Test `/app`, `/app/api/session`, `/app/api/planner`, `/app/api/tasks` with actual signed Mini App requests and verified-adult accounts.
- Verify task creation, completion and deletion on two real devices using the **same** account, and confirm a second adult account cannot view or modify those tasks.
- Verify old local tasks survive when the service is unavailable; explicitly import them and check no duplicates are created after retry.
- Complete remaining localization/native-speaker review and accessibility checks.
- Add the Telegram Bot menu launch button **only after** you have a working HTTPS `/app` route in a restricted pilot. Telegram requires signed `WebApp.initData` to be validated on the backend; do not trust `initDataUnsafe`. See <https://core.telegram.org/bots/webapps>.
- Rerun the complete regression suite, do a live phone-based Mini App test, and merge/deploy a single coordinated production V12 upgrade.

## Verified in the ChatGPT development container

- Python app / task store / auth mock tests: **35 run, 2 skipped** (Flask not installed in this standalone container).
- JavaScript and regression-of-tools tests: **54/54 pass**.
- Guarded installer self-tests: **5/5 pass**.
- Simulated installer test: dry-run, apply, second dry-run (idempotent) passed; 5 UPDATE and 5 ADD only.
- A real browser smoke test was **not** completed in this container because the sandbox blocks loopback and external test navigation. These offline checks do **not** confirm your real Telegram/Supabase connection.

## Rollback

`INSTALL_V120_TASK_SYNC.py --apply` creates a timestamped `V120_TASK_SYNC_BACKUP_...` directory with the five files it replaces. The five added files can be removed after validating the diff. The SQL migration is not applied by the installer and would require a separate, deliberate schema rollback (after exporting any data). Do not `git add .` or upload development backups, `.env` files, or Telegram session files to GitHub.
