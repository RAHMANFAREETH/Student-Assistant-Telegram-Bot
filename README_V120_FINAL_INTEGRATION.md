# Student Assistant Super Mini App V12.0 — Telegram launch + Supabase SQL review

**Development-only patch.** Do not publish V12.0 yet; the existing Book Library and V11.9.2.1 production bot should remain working. The user-reported previous baseline was 96/96 regression modules, 1,886 Python tests and 54/54 Node tests.

## What is included

- `super_miniapp_v120_launch.py`: Adds private-chat `/superapp` and `/app` commands **when enabled** and builds an inline Telegram Web App launch button. It uses the **same Telegram bot** and existing HTTPS `/app` route. It does **not** change the existing `/library` route, Book Library button or global BotFather menu.
- `INSTALL_V120_TELEGRAM_LAUNCH.py`: Safe `--check` / `--apply` installer. Adds command registration to `main.py` *before old fallback message handlers*, and a pilot allowlist check after existing signed Telegram authentication and verified-18+ checks in `super_miniapp_v120.py`. Both modified files are backed up. An unrecognized file layout fails closed. Running it twice is safe.
- `SQL_V120_QUICK_TASKS_REVIEWED.sql`: Complete, **reviewed replacement for** the previously distributed `SQL_V120_QUICK_TASKS.sql`. Use the new file **instead of** the old migration. It creates only `public.v120_quick_tasks` and its supporting index, function and trigger. Adds explicit PUBLIC/function privilege revocations. **No SQL is executed by installing this package.**
- `SQL_V120_QUICK_TASKS_VERIFY.sql`: Read-only queries to check RLS, table grants and trigger after applying the new migration.
- Three test files for launcher, installer, and static SQL checks. These tests do not require connecting to your Telegram or Supabase account.

## 1. Local installation (VS Code PowerShell)

Extract ZIP into `C:\Users\Pros\Desktop\StudentAssistantBot`, so all new files are directly in the project root. Keep your existing V12 files and existing Library unchanged.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V120_TELEGRAM_LAUNCH.py --check
```

Expect `UPDATE main.py`, `UPDATE super_miniapp_v120.py`, and `CHECK OK` (unless previously applied). Inspect the diff. If the installer reports an unexpected source layout, stop and share the output; do not bypass safety checks.

After checking:

```powershell
python INSTALL_V120_TELEGRAM_LAUNCH.py --apply
python -m py_compile main.py super_miniapp_v120.py super_miniapp_v120_launch.py
python -X utf8 -m unittest TEST_V120_TELEGRAM_LAUNCH TEST_INSTALL_V120_TELEGRAM_LAUNCH TEST_V120_SQL_REVIEW TEST_SUPER_MINIAPP_V120 TEST_SUPER_PLANNER_V120 TEST_SUPER_TASK_SYNC_V120 -q
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_SUPER_TASK_SYNC_V120.mjs
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

**Do not commit, push or deploy as a production release yet.** Keep `SUPER_MINIAPP_V120_ENABLED=false` in Render; the launcher also stays off when `SUPER_MINIAPP_V120_LAUNCH_ENABLED` is missing/false. This is an integration patch, not proof of live Telegram/Supabase operation.

## 2. Supabase migration (separate manual step after local checks)

Review `SQL_V120_QUICK_TASKS_REVIEWED.sql`. In the **existing Supabase project**, open **SQL Editor** and run **that reviewed SQL file only** when preparing the restricted live pilot. It does not delete or update assignments, exams or Library records. It uses a 100-task-per-user safety quota and requires the existing server-side `db.supabase` connection to use a `service_role`/secret key with appropriate privileges. The frontend **must never receive this key**.

After success, run **`SQL_V120_QUICK_TASKS_VERIFY.sql`** in the same SQL Editor. Expected: RLS enabled (`true`), no `anon`/`authenticated` table grants, `service_role` table grants, trigger `v120_quick_tasks_guard_trigger`, and `anon_execute=false`, `authenticated_execute=false`. The query lists grants; review unexpected grantees as well. Database verification is not done in this offline patch.

**Do not paste Supabase secret keys, Telegram bot tokens, phone login codes or `.env` values into chat.**

## 3. Telegram controlled pilot — later (NOT NOW)

When the full V12 integration is ready for a deliberately authorized pilot, use the existing Render HTTPS service, the same bot and the same Supabase project. The new launcher has two independent safety switches and a configurable pilot list. Before any deliberate pilot deployment set:

```text
SUPER_MINIAPP_V120_ENABLED=true
SUPER_MINIAPP_V120_LAUNCH_ENABLED=true
SUPER_MINIAPP_V120_LAUNCH_PUBLIC=false
SUPER_MINIAPP_V120_PILOT_IDS=<your actual numeric Telegram user ID>
SUPER_MINIAPP_V120_PUBLIC_URL=https://YOUR-EXISTING-RENDER-HOST/app
```

`SUPER_MINIAPP_V120_PILOT_IDS` may contain comma-separated IDs for **verified adults**. The pilot list is checked on the **API**, not only on the `/app` or `/superapp` button. Without `SUPER_MINIAPP_V120_LAUNCH_PUBLIC=true`, the `/app` command does not expose a button to unlisted users. If the pilot ID setting is accidentally omitted while the App flag is enabled, the existing verified-adult API policy still applies, so **always configure and check the pilot IDs** before enabling it. Keep the `LAUNCH_PUBLIC` flag false until the final coordinated public release.

If `SUPER_MINIAPP_V120_PUBLIC_URL` is omitted, the script derives the URL from `RENDER_EXTERNAL_URL` or `BOOK_LIBRARY_PUBLIC_URL`. The launcher rejects non-HTTPS URLs and any destination other than `/app`. It does not overwrite the current BotFather menu button; a global menu change is a **separate explicit release action**.

During later pilot, verify (a) a signed, verified-adult account can use the button, (b) non-adult and unlisted users cannot use private APIs, (c) a second adult cannot read/edit another account's tasks, (d) saved tasks persist across two devices, (e) existing `/library` still works, (f) `SUPER_MINIAPP_V120_ENABLED=false` immediately closes V12 routes as a rollback option, and (g) older bot commands work.

## Rollback

The installer stores the original `main.py` and `super_miniapp_v120.py` under `V120_TELEGRAM_LAUNCH_BACKUP_<timestamp>`. Restore those two files if rollback is necessary, after inspecting current modifications. The migration is **not** undone by restoring files; if applied, leave the isolated task table in place until its data can be backed up, rather than dropping it casually.

Official Telegram reference: https://core.telegram.org/bots/webapps (launching via inline Web App buttons and menu buttons; signed `initData` validation).
