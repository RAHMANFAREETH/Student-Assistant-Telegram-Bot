# V11.8.6.2 — Legacy Book Library regression-test isolation

This patch fixes a **test environment mismatch**, not the runtime search logic.
The older V11.1 / V11.2 / V11.4 tests expect the original `book_library_bot` routing and mock its functions. When your local shell has `LIBRARY_MEDIA_V117_ENABLED=true`, those calls route instead to the V11.7+ unified media search and older tests fail unexpectedly. Other inherited flags can also change intended public/private group conditions.

The four historical tests now explicitly set the flags appropriate to their specific era. New V11.7, V11.8.3 and V11.8.6 search tests continue to exercise the newer code. This package does **not** alter production modules, disable features in Render, access Telegram or Supabase, or change any database records.

## Installation (Windows PowerShell)

Extract the three files from the ZIP into your `C:\Users\Pros\Desktop\StudentAssistantBot` folder (where `TEST_BOOK_LIBRARY.py` lives).

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 PATCH_LIBRARY_LEGACY_TESTS_V11862.py --check
python -X utf8 PATCH_LIBRARY_LEGACY_TESTS_V11862.py --apply
python -X utf8 -m unittest TEST_LIBRARY_LEGACY_TEST_ISOLATION_V11862 TEST_BOOK_LIBRARY TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_BOOK_PUBLIC_LATEST5 -q
```

Then run the V11.8.6 focused suite using your latest tests:

```powershell
python -X utf8 -m unittest TEST_LIBRARY_SEARCH_STABILITY_V11861 TEST_LIBRARY_SEARCH_FEEDBACK_V1186 TEST_LIBRARY_LANGUAGE_PICKER_V1185 TEST_LIBRARY_SEARCH_UI_V1183 TEST_LIBRARY_MEDIA_V117 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_GROUP_BOOK_ONLY_V116 TEST_GROUP_LIBRARY_MENU_V1161 TEST_GROUP_UI_V115 TEST_LIBRARY_MANAGE_V118 -q
```

Finally run the isolated runner to identify outstanding issues:

```powershell
python -X utf8 RUN_REGRESSION_SAFE_V1184.py --affected-only
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

## Scope and limitations

- Four `TEST_*.py` files only; the new regression test verifies installer safety.
- The installer backs up each changed file to a timestamped `V11862_TEST_BACKUP_*` directory and is safe to rerun.
- The code in `book_library_bot.py`, `library_media_v117_bot.py`, `library_search_ui_v1183.py` and the database is untouched.
- **No claim is made that every production feature works on Render.** Verify live group privacy, private deep-link delivery, progress cleanup and English/Tamil language filtering before release.
- If V8 Study Lab or V9 Academic Toolkit still fail under the isolated runner, review their separate report; this patch does not alter them.
- Supabase deprecation messages, simulated `Telegram edit denied`, and simulated `db offline` tracebacks can occur during successful tests. An `OK` summary means the assertions passed; unclosed SSL socket warnings should still be investigated separately.
