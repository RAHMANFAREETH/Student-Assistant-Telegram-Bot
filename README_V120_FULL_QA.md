# Student Assistant V12.0.1 — Full Tool QA & 62-Tool Rebuild

**Scope:** Client-side Mini App JavaScript + related tests. **No changes** to `main.py`, `friendly_v119.py`, `navigation.py`, Flask APIs, Book Library, Supabase schema, or Render environment variables. The existing `/app` and `/library` URLs remain unchanged.

## What the patch fixes

- **Calculate buttons:** Tools previously placed their `type="submit"` button outside its `<form>` without associating the button with the form. The button is now explicitly bound to the active form, and results recompute on edits.
- **Stale results:** Discount, Word Counter, URL Encode, and other generic calculators update as fields change and on Calculate.
- **Password length:** Uses `form.elements.namedItem('length')`, not `form.elements.length` (which is the number of inputs).
- **Timer and Pomodoro:** Previously created a `<div>` and accessed `.elements` as if it were a form. Converted it to a form; Start reads the entered time. Pause and Reset also work.
- **UUID:** Uses the existing secure cryptographic UUID-v4 fallback when `crypto.randomUUID()` is unavailable on an older webview.
- **Dice:** The interface now allows **1–5 dice**, matching its description instead of always rolling exactly two.
- **Unicode handling:** Word Frequency now preserves combining marks used by Tamil and other scripts; Word Counter and Reverse Text use grapheme clusters when `Intl.Segmenter` is available.

## 12 new functioning browser tools

1. Percentage Change
2. Sales Tax / VAT
3. Profit & Margin
4. Average Speed
5. Grade Percentage
6. Standard Deviation (population and sample)
7. Quadratic Equation (real and complex roots)
8. Factorial (exact big integers up to 200!)
9. Combinations / nCr (exact up to n=200)
10. Find & Replace (literal and optional case-insensitive)
11. Word Frequency (Unicode-aware)
12. Study Session Planner (focus and break totals)

**Total: 62 tools**. All new tools use browser-local calculations. They do not send text or numbers to the bot server. Tamil and Sinhala tool names are included. Some new field labels/results currently fall back to English; do not describe this as fully localized.

## Install in VS Code / Windows PowerShell

Extract this package **directly** into:

`C:\Users\Pros\Desktop\StudentAssistantBot`

The installer accepts the reviewed V12.0 public-access baseline or an already installed copy of this exact patch. It **refuses to overwrite a changed/unrecognized version** of the source. No `--force` override is offered.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"

python INSTALL_V120_FULL_QA.py --check
```

Expected if using the previous V12.0 public-access version: **5 UPDATE, 1 ADD**, `CHECK OK`.

Only if the check passes:

```powershell
python INSTALL_V120_FULL_QA.py --apply
python -m py_compile main.py super_miniapp_v120.py
python -X utf8 -m unittest TEST_INSTALL_V120_FULL_QA -q
node --test TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_SUPER_TASK_SYNC_V120.mjs TEST_V120_REBUILT_TOOLS.mjs
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

The patch's focused JS suite passed **69/69** locally, and the installer passed **4/4** tests. A headless Chromium mobile-sized interface test opened **all 62 tool screens**, clicked all generic calculators, exercised changed inputs, tested Password and UUID, Timer, Signature PNG, 3 Image exports, and language switching; it reported **zero page errors**.

**These are offline tests, not a guarantee of live behavior.** Do real Android/iOS Telegram checks, particularly for file downloads, passwords, timers, and private task synchronization.

### Optional browser test

The bundle also includes `BROWSER_QA_V120.py` as an offline test script; it runs on your own machine *only if* Playwright, a compatible Chromium browser, and Pillow are installed. It does not contact Telegram, Supabase or Render. This test is **optional**; the Node/Python commands above are the primary release gate.

## Safe commit (after all tests)

Use **selective staging** because your project has many unrelated backups and modified files:

```powershell
git add -- super_miniapp_v120.js super_miniapp_v120_tools.mjs TEST_SUPER_TOOLS_V120.mjs TEST_SUPER_TOOLS_EXPANSION_V120.mjs TEST_SUPER_LOCALE_PLANNER_V120.mjs TEST_V120_REBUILT_TOOLS.mjs TEST_INSTALL_V120_FULL_QA.py INSTALL_V120_FULL_QA.py V120_QA_TEST_FIXTURES

git diff --cached --check
git diff --cached --stat
git diff --cached -- super_miniapp_v120.js super_miniapp_v120_tools.mjs
```

If the staged diff is expected and your full regression passes, commit and push:

```powershell
git commit -m "Repair V12.0 Mini App tools and expand to 62 verified utilities"
git push origin main
```

**Do not run `git add .`.** The test fixture folder contains only old, sanitized Mini App source files for regression testing—no keys. It is included in the staged set because `TEST_INSTALL_V120_FULL_QA.py` needs it on fresh clones. You may omit the installer, its test and fixtures as a group if you prefer committing only production assets and tool tests.

## Production cautions

- If incorrect calculations are currently public, you may temporarily disable `SUPER_MINIAPP_V120_ENABLED` and `SUPER_MINIAPP_V120_LAUNCH_ENABLED` during the repair/deployment. Reenable after verifying the new commit is live.
- The existing public guest-tools settings can remain `SUPER_MINIAPP_V120_PUBLIC_TOOLS=true` and `SUPER_MINIAPP_V120_REQUIRE_ADULT=false` after the new code is tested. Personal tasks and planner APIs still need valid signed Telegram identity; this patch does **not** bypass private-data access controls.
- Do not upload bot tokens, Telethon sessions, `.env` secrets or personal data into Git.
- A backend route/SQL migration is **not** necessary for these UI/math changes.
- The old Book Library and its menu remain unchanged.
