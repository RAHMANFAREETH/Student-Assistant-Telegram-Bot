# V11.4 Book Library Privacy — V11.3 Compatibility Fix

## What was wrong

The first V11.4 installer expected the V11.2 implementation of `book_library_bot.py::_search()`. Your correctly installed V11.3 already inserts `show_smart_search()` before the V11.2 path. The original installer rejected the valid source, failed before changing any files, and the V11.4 privacy unit tests then failed because the new handlers were absent.

This replacement supports **both** exact, known V11.2-compatible and V11.3 smart-search layouts. It **preserves V11.3 smart search** and refuses to modify any unknown or duplicated code anchors. It changes only `book_library_bot.py`, `book_library_v112_bot.py`, and `book_library_v113_bot.py`, creating a backup before applying. All three are prepared in memory before any file is changed.

## Installation on Windows

Extract all six files in this ZIP into your existing `C:\Users\Pros\Desktop\StudentAssistantBot` folder, **replacing** the older V11.4 installer, tests, and related files. The package contains:

- `INSTALL_BOOK_LIBRARY_PRIVACY_V114.py` (corrected installer)
- `book_library_privacy_v114.py` (privacy helper)
- `V114_PATCH_OPS.json` (the approved exact patches)
- `TEST_BOOK_LIBRARY_PRIVACY_V114.py` (includes the V11.3 regression test)
- `V114_TEST_BASELINES.zip` (test fixture only)
- `README_BOOK_LIBRARY_PRIVACY_V114.md` (this guide)

Open PowerShell in the bot directory:

```powershell
python INSTALL_BOOK_LIBRARY_PRIVACY_V114.py --check
```

**Review the diff**. It should add owner checks, private-group routing, and menu cleanup to the three library files only. No changes should be made during `--check`.

```powershell
python INSTALL_BOOK_LIBRARY_PRIVACY_V114.py --apply
python INSTALL_BOOK_LIBRARY_PRIVACY_V114.py --check
python -m py_compile book_library_bot.py book_library_v112_bot.py book_library_v113_bot.py book_library_privacy_v114.py
python -X utf8 -m unittest TEST_BOOK_LIBRARY_PRIVACY_V114 -q
```

Expected focused suite: **21 tests OK**. Then run the full library suite with the legacy public-group tests in their expected mode:

```powershell
$oldPrivacy = $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS
try {
    $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS = 'false'
    python -X utf8 -m unittest TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_V113 TEST_BOOK_LIBRARY_PRIVACY_V114 -q
}
finally {
    if ($null -eq $oldPrivacy) { Remove-Item Env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS -ErrorAction SilentlyContinue }
    else { $env:BOOK_LIBRARY_PRIVATE_GROUP_RESULTS = $oldPrivacy }
}
```

Expected combined suite: **186 tests OK** (165 older tests plus 21 V11.4 tests). This was tested offline in a simulated V11.3 working tree. Real Telegram permissions, multi-user callbacks, and Supabase access must still be checked in deployment.

## Git commit

After tests pass, stage **exactly** these six new V11.4 files plus the three modified library Python files:

```powershell
git add -- book_library_privacy_v114.py INSTALL_BOOK_LIBRARY_PRIVACY_V114.py V114_PATCH_OPS.json TEST_BOOK_LIBRARY_PRIVACY_V114.py V114_TEST_BASELINES.zip README_BOOK_LIBRARY_PRIVACY_V114.md
git add -p -- book_library_bot.py book_library_v112_bot.py book_library_v113_bot.py
git diff --cached --check
git diff --cached --name-only
```

Inspect the staged diff. Avoid `git add .`; do not stage backups. Commit and push when satisfied:

```powershell
git commit -m "V11.4: Fix private group book search and menu ownership"
git push origin main
```

## Render settings after live deployment

Keep the existing public-library and adult-only AI settings. Once the code is deployed and Live:

```dotenv
BOOK_LIBRARY_PRIVATE_GROUP_RESULTS=true
BOOK_LIBRARY_AUTODELETE_MENU=true
BOOK_LIBRARY_DELETE_GROUP_COMMANDS=true
```

A bot can only send private results to a user who has already started a private conversation with it. Group-command deletion requires the relevant Telegram administrator rights. URL/deep-link button taps cannot reliably trigger deletion.

**No new Supabase migration, new bot, or API key is required.** This patch does not claim to isolate older PDF, quiz, or AI workflows outside the Book Library.
