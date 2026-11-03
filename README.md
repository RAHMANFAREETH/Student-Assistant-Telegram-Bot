# V11.8.3 OCR test-isolation correction

The reported test error is caused by the environment variable `LIBRARY_MEDIA_OCR_ENABLED=true` activating real Telegram-file download in `test_contributor_uses_review_channel`. Its fake `Bot` has no `get_file` method. That test verifies the review channel, not OCR.

The fix sets `LIBRARY_MEDIA_OCR_ENABLED=false` **inside only that test's environment patch**. Other tests, the application, and your Render environment are not changed. No database migration or redeployment is needed for this test-only fix.

## Windows PowerShell
Extract the two files from this ZIP into your existing bot project directory, then run:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 PATCH_V1183_TEST_OCR_ISOLATION.py --check
python -X utf8 PATCH_V1183_TEST_OCR_ISOLATION.py --apply
python -X utf8 -m unittest TEST_LIBRARY_SEARCH_UI_V1183 TEST_LIBRARY_MEDIA_V117 TEST_GROUP_BOOK_ONLY_V116 TEST_LIBRARY_MANAGE_V118 -q
```

If these tests pass, continue with your wider release checks. There is no need to push a test-only fix to Render to make the search feature function.

You can also use a non-file workaround: temporarily set `$env:LIBRARY_MEDIA_OCR_ENABLED='false'` **only in your PowerShell session**, rerun the tests, and restore your previous value afterward. The test-only patch is better because it stops the failure recurring when OCR is enabled in your environment.

Expected output: `Ran 119 tests ... OK` (the test suite may print expected exception logs from negative test cases).
