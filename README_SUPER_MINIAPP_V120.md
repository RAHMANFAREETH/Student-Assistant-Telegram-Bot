# Student Assistant Super Mini App — V12.0 development preview

**Status:** First working development package, **not** the complete V12.0 production release. Existing V11.9.2.1 live bot, Book Library (`/library`), Supabase data, all webhook handlers, and Render configuration are untouched until the installer is explicitly run in your local project. Default environment flag is OFF.

## Delivered in this package

- `/app` mobile-friendly Super Mini App interface; home, Library link, 30 interactive utilities, local Planner, Profile, dark/light themes, favorites, tool search and recent-use data.
- Date/age/date-add/day-of-year, world clock, stopwatch/timer, Unix time, unit/temperature/base converters, calculator/percentage/discount/BMI/electrical power, password/UUID/random generators, word counter/case converter, to-do/Pomodoro, local image compress/metadata-removal re-encode/watermark/signature, coin/dice/reaction tools.
- Existing `/library` opens in its own page. Existing Library APIs remain completely unchanged; there is **no** in-app Book Library rewrite.
- Personal tasks/favorites stored in device-local browser storage per signed Telegram user (not synchronized to Supabase). Timer notifications work only while Mini App stays open. No claimed background reminders.
- Every access to new session endpoint requires fresh Telegram `initData` validated via existing `v8_miniapp.validate_init_data`, plus `study_access_v9.is_verified_adult` server-side verification. Existing 18+ access gate is not bypassed.
- Default `SUPER_MINIAPP_V120_ENABLED=false` causes all new routes to return 404; no bot menu entry added in this preview.

## Installation on Windows / VS Code (local development)

1. Extract all package files into your existing project folder: `C:\Users\Pros\Desktop\StudentAssistantBot`.
2. Run these commands in **PowerShell**:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 -q
python -m py_compile super_miniapp_v120.py INSTALL_SUPER_MINIAPP_V120.py
python INSTALL_SUPER_MINIAPP_V120.py --check
```

3. Inspect the unified diff from `--check`: it must add only two Python lines plus markers **after the existing V8 Mini App registration** in `main.py`. If the installer refuses because your current `main.py` differs, **do not force the patch**. Share its output for review.
4. After the check and other local tests pass, run:

```powershell
python INSTALL_SUPER_MINIAPP_V120.py --apply
python -m py_compile main.py super_miniapp_v120.py
python INSTALL_SUPER_MINIAPP_V120.py --check
```

A backup of original `main.py` is saved under `V120_SUPER_MINIAPP_BACKUP_<timestamp>/main.py` and a second `--apply` is idempotent.

5. If Node.js is installed locally, run browser-engine tests:

```powershell
node --test TEST_SUPER_TOOLS_V120.mjs
```

## Enablement & testing

- Do **not** set `SUPER_MINIAPP_V120_ENABLED=true` on your production Render service yet. This is a development preview. Leave absent or set `false`.
- To perform a real access test later, run on a separate test environment with an HTTPS URL (Telegram Mini Apps require a Telegram launch context with valid signed `initData`) and a **verified 18+** tester. Route is `/app`. Visiting `/app` directly in a normal browser cannot authenticate.
- This preview has no BotFather mini app menu integration or button; these come during the full V12 rollout.
- If you commit the preview files later and Render auto-deploys from `main`, the default flag stays off. Note that any Render restart can still terminate an active RAM-only `/mediabulk` session.
- Do not `git add .`. Stage only explicitly reviewed new files and `main.py` when you are ready. Do not commit backup folders, `.env` files, session files or credentials.

## Missing from the final V12.0 scope (not claimed completed)

- Tamil/Sinhala complete UI localization, Supabase-synced tasks/goals/reminders, production Telegram Mini App launch integration, scientific extensions, all proposed 40+ screenshot-derived tools (e.g. QR, Sudoku, currency rates, image grids), and comprehensive device/regression/live validation.
- Existing Book Library integration here is a safe navigation link; unified Library presentation and data access are still future work.

## Safety & rollback

- Code added only by `INSTALL_SUPER_MINIAPP_V120.py` to existing files is a small registration block in `main.py`; it has no effect while the flag is false (though import/route registration occurs).
- To disable the preview immediately, leave `SUPER_MINIAPP_V120_ENABLED=false`.
- To restore `main.py`, manually copy it from the installer-created backup **after confirming no newer changes need to be retained**. Do not blindly overwrite subsequent edits.
- Production release requires old Library, V8/V9, admin hub, Smart Bulk, ZIP import tests, signed auth/verified-adult negative tests, responsive device testing and Telegram live verification.

