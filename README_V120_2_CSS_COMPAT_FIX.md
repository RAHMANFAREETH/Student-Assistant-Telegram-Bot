# V12.0.2 corrected installer — preserves V12 planner CSS

The first `INSTALL_V120_2_EXPORT_CLOCK.py` incorrectly required the V12.0 50-tool CSS SHA256 (`a40d9c...`) although the later V12 multilingual planner installer changed the stylesheet (`89afcbf...`). Thus it refused a legitimate installation. **Do not delete or replace your newer CSS.**

This corrected installer supports **only** the exact two previously published CSS baselines and appends V12.0.2 worldwide-clock/export CSS, so the planner styling stays intact. If your CSS differs from both known files, it still stops safely. It does not bypass checks for JavaScript, tests, the Mini App backend, or other files.

## How to install (PowerShell in VS Code)

1. Extract this ZIP into `C:\Users\Pros\Desktop\StudentAssistantBot`, replacing the previous `INSTALL_V120_2_EXPORT_CLOCK.py` and `V120_2_PAYLOAD` folder files. (The payload folder contains only V12 files; no production bot files.)
2. Run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V120_2_EXPORT_CLOCK.py --check
```

Only if it prints **CHECK OK**, run:

```powershell
python INSTALL_V120_2_EXPORT_CLOCK.py --apply
python -m py_compile super_miniapp_v120.py super_miniapp_v120_exports.py
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_SUPER_TASK_SYNC_V120.mjs TEST_V120_REBUILT_TOOLS.mjs TEST_V120_2_EXPORT_WORLD.mjs
python -X utf8 -m unittest TEST_V120_2_EXPORT_CLOCK -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

If `--check` fails on any other changed file, **stop** and do not copy individual files manually or disable guard checks. To help diagnose, run `Get-FileHash -Algorithm SHA256 .\super_miniapp_v120.css` and share only that hash and error text.

The installer creates a timestamped backup folder of any existing files it changes. Do not `git add .`; wait until the tests and Telegram phone downloads work before staging and pushing. No new Supabase schema change is required.

## Verification of corrected installer

Simulated runs against the exact planner CSS and 50-tool CSS: check, apply, repeat check and repeat apply all passed. A modified/unknown CSS still safely refuses installation. Live Telegram download flow is **not yet confirmed**.
