# V12.0 Super Mini App — 50 Tools Expansion (development only)

**Prerequisite:** You have already installed the V12.0 development preview via `INSTALL_SUPER_MINIAPP_V120.py --apply` and its corrected Flask test suite passes. Your latest user-reported baseline: 92/92 regression modules, 1,853 tests, 3 skipped. This expansion changes only four Mini App assets and adds/updates two Node test files, **not** `main.py`, `super_miniapp_v120.py`, bot handlers, `/library`, Supabase, requirements, Dockerfile or Render settings.

## What's new

50 tools total, up from 30. Additional 20 tools: Weekday Finder, Days Until Date, Add/Subtract Months, Time Duration, Simplify Fraction, Simplify Ratio, Mean/Median, weighted GPA (user-supplied 0–4 grade points), Tip/Split Bill, Simple Interest, Compound Interest, estimated Loan Payment, Prime Number Test, Square Root, Sort Lines, Remove Duplicate Lines, Reading Time, Reverse Text, URL Encode/Decode, and Color Contrast.

Three-language **preview**: English / தமிழ் / සිංහල main navigation, category labels, all 50 tool names and core headings/search. Other tool descriptions, form labels, calculations, messages, existing Library and account pages are currently English. Tamil/Sinhala labels should be reviewed by native speakers before a public launch.

Most tools run entirely on the device; image tools also remain on-device. Finance calculations are educational estimates. The GPA form requires numerical grade points and credits and does not encode any particular university's grading policy. This update does **not** include saved Supabase tasks, real background reminders, exchange-rate data, a rewritten Library, new QR/Sudoku tools, or production Telegram menu integration. Existing `/library` link and all its APIs are unaffected.

## Safe local installation in VS Code PowerShell

1. Extract **all contents** of `V120_Super_MiniApp_50_Tools_Expansion.zip` directly into `C:\Users\Pros\Desktop\StudentAssistantBot`. Keep the `V120_50_TOOLS_PAYLOAD` directory beside `INSTALL_V120_50_TOOLS.py`.
2. Copy and paste:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python INSTALL_V120_50_TOOLS.py --check
```

You should see only four asset updates, one Node test update, and one new Node test file. If the installer refuses because a local file differs, **stop** and review it rather than overwriting custom changes.

3. Apply and run the focused test suites:

```powershell
python INSTALL_V120_50_TOOLS.py --apply
python -m py_compile main.py super_miniapp_v120.py
python -X utf8 -m unittest TEST_SUPER_MINIAPP_V120 -q
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs
python INSTALL_V120_50_TOOLS.py --check
```

4. Then run the isolated existing full regression (which you have already used successfully):

```powershell
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

**Expected focused results on a correctly installed preview:** 12 Flask Python tests and 39 Node JS tests (verify actual output). Existing full suite counts may grow or vary. The installer creates a timestamped backup for changed files and is idempotent. No Python production file is modified by this expansion.

## Keep production safe

- Leave `SUPER_MINIAPP_V120_ENABLED=false` (default). This is NOT the final V12.0 production release.
- Don't push or deploy this expansion as a public release until localized form labels, user data integrations, signed Telegram live flows, and final complete regression/device tests are done.
- Never stage `git add .` in your backup-heavy repository. Do not commit Telegram session files, local backups or secrets.
- The installer will refuse locally modified preview files; review diffs before any replacement. It never overwrites your `main.py`.
- The browser visual smoke test was run using mocked Telegram access on a local static page; it **does not** establish server-side production auth or Telegram live behavior.

## Rollback

The installer stores old copies in `V120_50_TOOLS_BACKUP_.../`. Keep `SUPER_MINIAPP_V120_ENABLED=false`. If reverting files, review changes made since this installer ran before copying backups back.
