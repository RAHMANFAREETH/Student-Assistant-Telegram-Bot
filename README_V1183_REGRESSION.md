# V11.8.3 Regression Harness Recovery (TEST-ONLY)

## What the uploaded broad log shows

Your previous 119 focused library tests passed. The combined test discovery then
reported 1,649 tests, 21 failures, 99 errors and 3 skipped. Many errors were
caused by older tests sharing fake `telebot`, `navigation`, access flags, and
translation mocks through Python's `sys.modules`. Isolated reruns of affected
modules passed. Several V7 tests still had outdated assertions.

## Files included

- `PATCH_TEST_REGRESSION_V1183.py` — guarded --check/--apply installer;
  backs up historical test files before changing them.
- `TEST_OFFICE_MENU_FIX.py` — recognizes the extra V7.17 Advanced PDF menu row;
  checks Office buttons remain visible and Advanced PDF buttons are present.
- `TEST_V7_9_AUDIT.py` — checks the actual V11-era 11-button root navigation
  and presence of version metadata, without pinning version to V7.9.
- `TEST_V7_13_INSTALLER.py` — verifies the actual, currently integrated Office
  PDF registration and private-chat safeguards instead of importing a removed
  historical installer function.
- `RUN_REGRESSION_ISOLATED_V1183.py` — runs each `TEST_*.py` module in a fresh
  Python subprocess so mocks cannot leak between suites. Reports failures by
  module and writes detailed logs to the system temporary directory by default.

**No production modules are edited.** No SQL or Render configuration changes.

## PowerShell commands

Extract the archive into your original StudentAssistantBot folder. Replacement tests are stored in a bundle subfolder and are **not** overwritten during ZIP extraction; only the guarded installer copies them into place.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 PATCH_TEST_REGRESSION_V1183.py --check
python -X utf8 PATCH_TEST_REGRESSION_V1183.py --apply
python -X utf8 -m unittest TEST_OFFICE_MENU_FIX TEST_V7_9_AUDIT TEST_V7_13_INSTALLER -q
python -X utf8 -m unittest TEST_LIBRARY_SEARCH_UI_V1183 TEST_LIBRARY_MEDIA_V117 TEST_GROUP_BOOK_ONLY_V116 TEST_LIBRARY_MANAGE_V118 -q
python -X utf8 RUN_REGRESSION_ISOLATED_V1183.py
```

If a preflight SHA check stops, do not override it; the local file differs from
the inspected source. Share that specific file for a targeted correction.

The isolated runner may take several minutes. It displays pass/fail progress as
it runs, and always attempts to save its report at the end. Use `--timeout 30`
if a particular test module is hanging. Avoid running the new runner simultaneously
with any other tests.

## Important caveats

- A green isolated run is not proof of a green single-process `unittest discover`
  run. To eliminate shared global state in single-process tests, old fake-module
  tests would need broader refactoring.
- `test_server_safety.py` expects `main.py` NOT to exist, and appears intended
  for a separate adult Gemini bot checkout. It is not a valid requirement for
  the current StudentAssistantBot root. The isolated runner intentionally targets
  only uppercase `TEST_*.py`. Review/move that unrelated test separately.
- Do not deploy to Render solely on the strength of test fixes. Test the search
  UI on Telegram and validate Supabase English/Tamil metadata as well.
- The `V1183_TEST_REGRESSION_BACKUP_...` directory holds the original tests;
  do not commit backup folders or local diagnostic reports to GitHub.
