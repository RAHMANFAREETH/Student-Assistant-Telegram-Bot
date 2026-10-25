# Student Assistant Bot V6.8 — Search Inside Saved AI Notes

This is an **incremental upgrade for your existing Telegram bot**. It requires **V6.7 installed first** (including `revision_hub_v66.py`). It retains V6.5.1 Main Menu compatibility, V6.6 revision tools, V6.7 browsing/title search, Cloudflare AI, the existing Gemini developer integration, and your Supabase data.

## New feature

- `/studysearch photosynthesis` searches BOTH the **titles and content** of your saved AI study notes. Other examples: `/studysearch ஒளிச்சேர்க்கை`, `/studysearch الرياضيات`, `/studysearch විද්‍යාව`.
- Search is **literal** (a `%` or `_` is not a Supabase wildcard) and **case-insensitive**.
- Matching titles appear before body-only matches. For body matches, a short preview around the matching text appears; tap a note button to open its complete content.
- Searches only the **current Telegram sender's** saved AI notes in a **private chat**. Opening a note always performs a fresh owner-filtered database lookup.
- Searches at most the **200 newest AI study notes**. Displays up to **8 matching note buttons**, and reports if the 200-note scan limit is hit. This is not full-library indexing or searching every note. Search terms must be **2–60 characters**.
- This is read-only. It **does not** add an AI request, use AI daily quota, create tables, modify records, or add environment variables.

## Files in the ZIP

Copy these **four files from the ZIP root** into:

`C:\Users\Pros\Desktop\StudentAssistantBot`

1. `INSTALL_V6_8.py` — safe version-aware patch for `revision_hub_v66.py` only.
2. `TEST_V6_8_FULL_TEXT_SEARCH.py` — 19 offline tests; depends on the already-installed V6.6 test module.
3. `FIXTURE_V6_7_REVISION_HUB.txt` — an **offline test fixture**, never replace your real bot module with this file.
4. `README_V6_8.md` — this guide.

**Prerequisite:** V6.7 must have been successfully installed. If the installer reports an unexpected/missing V6.7 section, **stop**; do not overwrite your module with older code.

## Install — Windows PowerShell

First back up your entire working `StudentAssistantBot` folder. Then open VS Code Terminal **inside** that folder:

```powershell
Test-Path .\revision_hub_v66.py
Test-Path .\INSTALL_V6_8.py
Test-Path .\TEST_V6_8_FULL_TEXT_SEARCH.py
Test-Path .\FIXTURE_V6_7_REVISION_HUB.txt
```

All four commands should return `True`.

```powershell
python -m unittest TEST_V6_8_FULL_TEXT_SEARCH.py -v
python INSTALL_V6_8.py
python -m py_compile revision_hub_v66.py
python -m unittest TEST_V6_8_FULL_TEXT_SEARCH.py TEST_V6_7_LIBRARY.py TEST_V6_6_REVISION_HUB.py -v
```

If the existing prior-version test files are present, the combined regression suite should run **64 tests** and finish `OK`. Some tests deliberately trigger database failures in mocks, which can print short diagnostic lines even when they pass.

The installer makes a UTF-8 backup named `revision_hub_v66.py.before_v68.bak` and preserves CRLF on Windows. Running it twice does not duplicate the patch. An existing V6.8 backup plus an unpatched file causes the installer to refuse overwriting that backup. It modifies **only** `revision_hub_v66.py`.

## Commit and deploy

Only after all tests pass:

```powershell
git status
git diff -- revision_hub_v66.py
git add revision_hub_v66.py INSTALL_V6_8.py TEST_V6_8_FULL_TEXT_SEARCH.py FIXTURE_V6_7_REVISION_HUB.txt README_V6_8.md
git commit -m "Add V6.8 full-text search for saved AI notes"
git push origin main
```

Wait until your existing Render service shows `Live` before testing the Telegram bot. Do **not** commit `.env`, API keys, credentials, or the backup file.

## Telegram smoke test

In your **private chat** with the bot:

1. `/studylibrary` — the help text now mentions `/studysearch`.
2. `/studysearch photosynthesis` — finds the phrase in titles OR saved AI note bodies (if saved notes contain it).
3. `/studysearch ஒளிச்சேர்க்கை` — verify Tamil terms match your saved notes.
4. Tap a note result; verify its full content opens correctly.
5. Check `/studyfind biology` (older title-only search), Older/Newer buttons, `/studypractice`, `/ai`, and `🏠 Main Menu` still work.

If you have no saved AI notes, save one via `/ai` → `💾 Save AI Answer` → `✅ Confirm Save`, then test.

## Rollback

Restore the backup **only if it was created by this installer**:

```powershell
Copy-Item .\revision_hub_v66.py.before_v68.bak .\revision_hub_v66.py -Force
python -m py_compile revision_hub_v66.py
git add revision_hub_v66.py
git commit -m "Rollback V6.8 study search"
git push origin main
```

This restores the V6.7 behavior without deleting any notes or flashcards.

## Security and status

Offline tests: **64 passed** (19 new V6.8, 17 V6.7, 28 V6.6). These use mocks, not your live Supabase or Telegram account. Live verification is needed after Render deploy.

Gemini (`GEMINI_API_KEY`) remains installed for developer testing only; V6.8 does not route mixed-age public bot requests to Gemini. Cloudflare AI, rate limits, safety filters, and all existing AI Study features remain unchanged.
