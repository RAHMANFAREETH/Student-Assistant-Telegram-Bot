# V11.8.6.1 — Search stability and V11.2 test isolation

This is a **small compatibility patch for the previously installed V11.8.6 release**. It is not a replacement for V11.8.6; install V11.8.6 first.

Changes only:
- `library_media_v117_bot.py`: when an older test double lacks `edit_message_text`, send a replacement without generating an `AttributeError` stack trace.
- `library_search_ui_v1183.py`: same capability check for found-file results, and attempt to delete the old progress message in the fallback.
- `TEST_BOOK_LIBRARY_V112.py`, `TEST_BOOK_LIBRARY.py`, `TEST_BOOK_PUBLIC_LATEST5.py`: set `BOOK_LIBRARY_V113_ENABLED=false` in this legacy test's local environment, so production V11.3 settings cannot turn on handlers unsupported by that test's fake bot. **Does not turn off V11.3 in production.**

The patch verifies source markers and syntax, creates timestamped backups, and supports repeat application. It changes no other modules, environment variables, databases, or bot tokens.

## Windows PowerShell

Extract this ZIP's files into the existing `C:\Users\Pros\Desktop\StudentAssistantBot` folder, then run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 PATCH_LIBRARY_SEARCH_STABILITY_V11861.py --check
python -X utf8 PATCH_LIBRARY_SEARCH_STABILITY_V11861.py --apply
python -m py_compile library_media_v117_bot.py library_search_ui_v1183.py TEST_BOOK_LIBRARY_V112.py
python -X utf8 -m unittest TEST_LIBRARY_SEARCH_STABILITY_V11861 TEST_LIBRARY_SEARCH_FEEDBACK_V1186 TEST_LIBRARY_LANGUAGE_PICKER_V1185 TEST_LIBRARY_SEARCH_UI_V1183 TEST_LIBRARY_MEDIA_V117 TEST_BOOK_LIBRARY_V112 TEST_BOOK_LIBRARY_PRIVACY_V114 TEST_BOOK_LIBRARY TEST_BOOK_PUBLIC_LATEST5 TEST_GROUP_BOOK_ONLY_V116 TEST_GROUP_LIBRARY_MENU_V1161 TEST_GROUP_UI_V115 TEST_LIBRARY_MANAGE_V118 -q
```

The fake V11.2 bot cannot support inline V11.3 registration, but production's real TeleBot can. This fixes the **test configuration** rather than weakening production features.

If this passes, run `python -X utf8 RUN_REGRESSION_SAFE_V1184.py` and inspect the remaining V8/V9 access-related test failures separately; do not redeploy until remaining critical checks and manual privacy verification are complete.

No rendering wait/delay is added: search progress may be very brief when Supabase responds quickly. Catalog metadata correction for Tamil PDF records is a separate task.
