# Student Assistant Bot — V12.1 Study & Mind Games Arcade

**Status:** installation package ready for local verification; **not deployed**. All 32 new activities are delivered together. The existing V12.0.2 68-tool Mini App and `/library` are intentionally retained.

## Contents

- 12 study games: Quick Quiz, Flashcard Sprint, MCQ Challenge, Match the Pairs, Fill in the Blanks, Sentence Builder, Spelling Bee, Math Race, Formula Match, Science Challenge, Geography Quiz, Timeline Challenge.
- 12 mind games: Memory Flip, Sequence Recall, 9×9 Sudoku, 2048 Puzzle, solvable Sliding Puzzle, Word Search, Number Patterns, Maze Escape, Make 24, Logic Grid, Observation Challenge, Reaction Challenge.
- 8 study helpers: Exam Countdown, Spaced Repetition, Revision Topic Wheel, Practice Question Builder, Study Streak Calendar, Study Load Estimator, Scorecard Export, Daily Study Scheduler.
- Distinct mobile-responsive `GET /app/arcade` screen linked from the existing `/app` Home panel.
- UI labels and activity names in English, Tamil and Sinhala. The first built-in question banks are English; this is indicated in the interface and is not represented as fully translated content.
- Offline/device-only results and question banks using `localStorage` with a session-only fallback. No new Supabase SQL, no cloud leaderboard, no AI API, no third-party tracker, and no addition to the bot's existing private-user APIs.
- CSV and PNG scorecards generated in the browser; image sharing is offered if the phone supports Web Share. Actual Telegram save behavior must be checked on a real device.

## Prerequisite

V12.0.2 must already be installed; both `super_miniapp_v120.py` and `super_miniapp_v120.html` are required, including the V12.0.2 `register_v120_exports(app)` hook. This package uses a guarded minimal injection into those two existing files. It **does not replace** V12.0.2 CSS, JS, calculators, export service, `/library`, `navigation.py`, `main.py`, `friendly_v119.py`, age verification or AI features.

## Windows PowerShell install

Extract this ZIP directly into `C:\Users\Pros\Desktop\StudentAssistantBot`, **preserving `V121_ARCADE_PAYLOAD/`**, and then run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V121_ARCADE.py --check
```

Only continue if `CHECK OK` is shown with the intended two V12.0.2 injections and new V12.1 files:

```powershell
python INSTALL_V121_ARCADE.py --apply
python -m py_compile super_miniapp_v120.py super_miniapp_v121.py
node --test TEST_V121_ARCADE.mjs
python -X utf8 -m unittest TEST_V121_ARCADE TEST_INSTALL_V121_ARCADE -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

The baseline regression may include two newly discovered modules. Keep `SUPER_ARCADE_V121_ENABLED` unset/false during these baseline compatibility tests; separate V12.1 tests explicitly exercise the enabled path. Do not ignore any failures.

**Do not enable or deploy if any test fails.** The installer creates a timestamped `V121_ARCADE_BACKUP_*` directory containing originals of any changed files. It refuses unexpected existing V12.1 file layouts.

## Activation (only after tests + GitHub/Render deployment)

New feature flag: `SUPER_ARCADE_V121_ENABLED=true` on Render, then restart/redeploy. The existing `SUPER_MINIAPP_V120_ENABLED=true` must also be set. When the V12.1 flag is false, the existing V12.0.2 endpoints and private feature access are unaffected; the new routes are not registered. The installed `/app` references an optional entry module that may 404 while V12.1 is disabled, but the existing application logic is separate.

Open the existing bot Mini App at `/app`, then choose `🎮 Study & Mind Games Arcade`. Direct URL `/app/arcade` is also available when enabled. All core Arcade games are public, device-only; this grants **no** access to existing signed Telegram tasks, planner records, or restricted AI.

## Live checklist (mobile Telegram)

- Open all 32 activity cards. Exit each active timer/game using All games; it must not continue updating hidden pages.
- Complete a Quick Quiz and check that it adds XP; reload and check persistence on the same device.
- Finish at least one memory pair, 2048 move, Sudoku validation, Make 24 solution, and Maze movement.
- Save a custom practice question; reopen it. Save a daily study schedule and mark a study day.
- Export CSV and PNG scorecards. On phones with blocked downloads, use the image preview/Share fallback; test actual saving separately. There is no automatic upload to Render.
- Switch languages to Tamil and Sinhala; check names and navigation, and note that bundled exercise prompts currently remain in English.
- Confirm the existing 68 V12.0.2 tools (especially password, discount, world clock and image exports) and Book Library still function.
- On a separate test account, confirm signed private tasks and planner data remain isolated.

## Security and limitations

All new HTML, JavaScript and CSS is served from the same Render app. New routes are static GET endpoints only and follow the existing CSP (`style-src self`, no inline styles). No browser code is allowed to supply user IDs for existing task/planner APIs. Scores are editable browser data and **not trusted for public ranking**; do not display them as certified ability or IQ assessments. Students sharing one device/browser profile can see that profile's local progress. Clear browser data to remove it. No new database tables, paid AI API, multiplayer services, purchases or third-party downloads are introduced.

## Selective Git workflow (after local tests pass)

Check the staging list before pushing. Do **not** use `git add .`. Only stage the V12.1 sources, controlled test files and minimal V12 integration changes. Backup directories, `.env`, development payload backups, private data and unrelated edits must not be staged.

Suggested tracked set: `super_miniapp_v120.py`, `super_miniapp_v120.html`, root `super_miniapp_v121.*` and `TEST_V121_ARCADE.*`, plus this README. The installer and installer test may be kept locally, or if committed for repeatability, commit their `V121_ARCADE_PAYLOAD` dependency too. Review `git diff --cached --check` and `git diff --cached --stat` before committing.

## Rollback

Turn `SUPER_ARCADE_V121_ENABLED=false` and redeploy/restart to hide all V12.1 routes immediately; the existing 68-tool Mini App remains available. To undo source additions locally, restore only `super_miniapp_v120.py` and `super_miniapp_v120.html` from the correct timestamped `V121_ARCADE_BACKUP_*` folder; avoid reverting unrelated changes. New V12.1 files can remain inactive until deliberately removed.
