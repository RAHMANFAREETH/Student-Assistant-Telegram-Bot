# V5.7 UI test compatibility fix

The original `TEST_V5_7_UI.py` tested Telegram reply keyboards with `.rows`, which is not provided by real `pyTelegramBotAPI` ReplyKeyboardMarkup objects. The corrected test uses `markup.to_dict()["keyboard"]`, and the fallback test stub matches the same structure. The test cache is prepopulated to avoid unnecessary Supabase queries during offline tests.

## Install

1. Open `C:\Users\Pros\Desktop\StudentAssistantBot` in VS Code.
2. Back up your original `TEST_V5_7_UI.py`.
3. Copy the provided `TEST_V5_7_UI.py` to your project, replacing the old **test file only**.
4. Run:

```powershell
python -m unittest TEST_V5_7_UI.py -v
```

Expected: `Ran 13 tests` and `OK`.

No need to rerun `INSTALL_V5_7.py`, change Supabase SQL, or deploy bot code to Render for this test-only fix. If you want to track the corrected test in Git, use `git add TEST_V5_7_UI.py`, then commit/push after reviewing `git status`.
