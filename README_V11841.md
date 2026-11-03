# Student Assistant Bot — V11.8.4.1 Study Access Test Isolation

## What this fixes

V8/V9 historical pilot-mode unit tests fail when the Windows/Render-style environment contains `STUDY_ACCESS_MODE=verified_adults`. Their fixture user IDs are deliberately fake and not verified adults. The test-only runner V11.8.4 removes `V8_*`/`V9_*` variables, but previously left `STUDY_ACCESS_MODE` in the child environment.

The patch fixes **test setup only**:

- `TEST_V8_STUDY_LAB.py` — explicitly select pilot mode for the test cases and restore the previous value afterward.
- `TEST_V9_ACADEMIC_TOOLKIT.py` — use pilot mode in the temporary `patch.dict` for bot tests.
- `RUN_REGRESSION_SAFE_V1184.py` — remove `STUDY_ACCESS_MODE` from the inherited environment in its isolated test subprocesses.

**No changes** to `v8_bot.py`, `v9_bot.py`, `study_access_v9.py`, production age verification, configuration, database, Telegram handlers, or deployment. Never set `STUDY_ACCESS_MODE=pilot` globally just to make tests pass.

## How to use on Windows PowerShell

Extract this ZIP to `C:\Users\Pros\Desktop\StudentAssistantBot` alongside the three target files. Do not copy anything into a second nested folder.

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 PATCH_STUDY_ACCESS_TEST_ISOLATION_V11841.py --check
python -X utf8 PATCH_STUDY_ACCESS_TEST_ISOLATION_V11841.py --apply
python -X utf8 -m unittest TEST_V8_STUDY_LAB -q
python -X utf8 -m unittest TEST_V9_ACADEMIC_TOOLKIT -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py --affected-only
```

Expected: V8: 45 tests OK; V9: 38 tests OK; affected-only: 10 modules, 254 tests, zero failures, **if no other issue is present on your machine**.

Afterward run the full uppercase test suite:

```powershell
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

### Important

- The installer prints a diff and makes no changes on `--check`.
- `--apply` backs up every altered file in `V11841_TEST_BACKUP_<timestamp>`. It checks all source anchors before modifying anything. Re-applying is a no-op.
- The patch is **test-only** and is not a production fix, deployment, or proof that your library features are working in Telegram.
- Review any generated report before sharing to avoid disclosing credentials.
- If `--check` reports an unknown source anchor, stop; the local files are a different version and need inspection. Do not force the patch.
