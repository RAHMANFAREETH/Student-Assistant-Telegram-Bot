# V11.8.8 — Group Search Test Environment Isolation

**Purpose:** Repair the legacy group-search test fixture, not the live bot.

## Why the combined tests failed

`TEST_GROUP_BOOK_ONLY_V116.GateTests.test_plain_nonmatch_silent` expects an unmatched ordinary group message to remain silent. This describes the original match-only auto-search mode. `LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED=true` intentionally enables the newer V11.8.6 behavior that searches *all* ordinary text (subject to group permissions), even if there is no matching file. When this flag is inherited from your local environment, the old test contradicts the newer mode and triggers a fake Telegram keyboard error. The isolated regression runner removes the environment variable and passed 84/84 modules, 1,707 tests (3 skipped) on the user's Windows Python 3.14 system.

## Fix

The guarded installer modifies only `TEST_GROUP_BOOK_ONLY_V116.py`:

- sets `LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED=false` explicitly inside the legacy test fixture; this does not modify actual environment variables;
- adds a second test to prove that `true` intentionally routes unmatched ordinary group text to the search handler.

The patch does **not** change group routing, messages, permissions, V11.8.8 production files, any secret, database setting, Git remote, or Render configuration. No new packages or services are required.

## PowerShell

Extract the ZIP into `C:\Users\Pros\Desktop\StudentAssistantBot` **alongside the existing tests**, then:

```powershell
cd "C:\Users\Pros\Desktop\StudentAssistantBot"
python -X utf8 PATCH_GROUP_SEARCH_TEST_V1188.py --check
python -X utf8 PATCH_GROUP_SEARCH_TEST_V1188.py --apply
python -X utf8 -m unittest TEST_SMART_BULK_V1188 TEST_LIBRARY_LARGE_RELAY_V1187 TEST_LIBRARY_MEDIA_V117 TEST_GROUP_BOOK_ONLY_V116 TEST_LIBRARY_MANAGE_V118 -q
python -X utf8 RUN_REGRESSION_SAFE_V1184.py
```

Expected targeted total: **147 tests**, all passing, if the source matches the verified baseline. The group-only test module will have **24 tests** instead of 23. Log entries from negative tests such as deliberately simulated DB errors and failed Telegram deletion can appear even when the final result says `OK`.

## Deployment precautions

The new Smart Bulk Upload feature is **not yet deployed** by applying this test-only patch. After Windows tests pass, review and stage only the necessary V11.8.8 production files (`library_media_v117_bot.py` and the new `library_smart_bulk_v1188.py`). Do not run `git add .` in this repository because it contains old backups, test logs, and unrelated edits. If you commit tests, review and stage `TEST_SMART_BULK_V1188.py` and the corrected `TEST_GROUP_BOOK_ONLY_V116.py` separately.

Do not disable the all-text search flag on Render simply to make the old test pass. For ordinary discussion groups, be aware that enabling all-text search can cause casual chat messages to produce book-search responses. Keep it enabled only where that behavior is wanted and where group and adult-access restrictions are configured correctly.

## Verification by patch author

- Reproduced the original failure with `LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED=true`.
- After patch, group test module: **24 tests, OK**.
- After patch, five-module focused command: **147 tests, OK**, even when the all-text flag was deliberately enabled in the parent process (Python 3.13.5 sandbox; no real Telegram network actions).
- Local full regression was attempted afterward but interrupted; the Windows Python 3.14 full isolated regression result before this test-only patch was **84/84 modules, 1,707 tests, 3 skipped, 0 failed**.
