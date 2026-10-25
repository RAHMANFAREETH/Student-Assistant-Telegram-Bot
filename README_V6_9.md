# Student Assistant Bot V6.9 — Export Your Saved AI Study Notes

**Incremental upgrade:** install V6.8 first. V6.9 works in your **existing Telegram bot** and adds private, confirmed export of saved AI Study notes as a UTF-8 `.txt` file. Cloudflare AI, Gemini developer integration, Supabase notes/flashcards, V6.5.1 navigation fixes, V6.6 revision, V6.7 browsing, and V6.8 search stay unchanged.

## What students get

- `/studyexport` — request an export of **their own** saved AI Study notes.
- Tap **✅ Export My Notes** to confirm; **❌ Cancel** sends no file and makes no database queries.
- Output: `Student_Assistant_AI_Study_Notes.txt`, with title, saved date and complete saved text, including Tamil, Sinhala, English, Arabic.
- Up to **2,000** notes / **3.5 MB** per export. If too large, no partial file is sent and the student receives a clear warning. Large collections are retrieved in pages of 100.
- Exports only notes whose titles start with `AI Study:`. Ordinary Notes aren't included.
- `/studyhub` and `/studylibrary` mention the export command.
- **No new AI requests, Supabase SQL, database writes, Render environment variables, or new Telegram bot.**

## Privacy

Export is accepted only from the **student's own private Telegram chat**. The database query includes the student’s Telegram sender ID (`user_id`) on **every page**; inline confirmation callbacks are checked against the chat ID. No export file is stored on Render disk. The output is still a sensitive file in the student's Telegram chat and on Telegram's servers; students should keep the file private and avoid forwarding it.

## Files in V6.9 ZIP

Copy **all five** files directly to `C:\Users\Pros\Desktop\StudentAssistantBot`:

1. `study_export_v69.py` — new export and confirm/cancel handlers.
2. `INSTALL_V6_9.py` — safe V6.8-to-V6.9 installer.
3. `TEST_V6_9_EXPORT.py` — 20 new offline tests.
4. `FIXTURE_V6_8_REVISION_HUB.txt` — **only a test fixture**, do **NOT** overwrite `revision_hub_v66.py` with it.
5. `README_V6_9.md` — this guide.

**Pre-requisite:** V6.8 must already be installed. If the installer reports unexpected/custom source, do **not** force it or restore an older file. The file may have local changes requiring a custom merge.

## Installation — Windows PowerShell

Back up the existing project folder first. Open VS Code Terminal at `C:\Users\Pros\Desktop\StudentAssistantBot`:

```powershell
Test-Path .\study_export_v69.py
Test-Path .\INSTALL_V6_9.py
Test-Path .\TEST_V6_9_EXPORT.py
Test-Path .\FIXTURE_V6_8_REVISION_HUB.txt
```

All four must return `True`. Then:

```powershell
python -m unittest TEST_V6_9_EXPORT.py -v
python INSTALL_V6_9.py
python -m py_compile revision_hub_v66.py study_export_v69.py
python -m unittest TEST_V6_9_EXPORT.py TEST_V6_8_FULL_TEXT_SEARCH.py TEST_V6_7_LIBRARY.py TEST_V6_6_REVISION_HUB.py -v
```

Expect **84 tests** (20 V6.9, 19 V6.8, 17 V6.7, 28 V6.6) and `OK` if the previous test files are present. Intentional simulated database errors may print `V6.x ... failed: RuntimeError` even when the tests pass; these do not indicate a real DB failure.

The installer creates `revision_hub_v66.py.before_v69.bak` only if it makes a change, protects that backup from overwriting, preserves Windows line endings, and is idempotent.

## GitHub and Render

After passing tests:

```powershell
git status
git diff -- revision_hub_v66.py
git add revision_hub_v66.py study_export_v69.py INSTALL_V6_9.py TEST_V6_9_EXPORT.py FIXTURE_V6_8_REVISION_HUB.txt README_V6_9.md
git commit -m "Add V6.9 private AI study notes export"
git push origin main
```

Don't commit `.env` or any API key. Wait for the current Render service to show `Live`.

## Telegram live test

1. Open your **private chat** with the existing bot.
2. Send `/studyexport`, then tap **❌ Cancel**. Verify there is no file.
3. Send `/studyexport` again, tap **✅ Export My Notes**.
4. Open the `.txt` file; verify your saved AI notes, including Tamil/Sinhala/Arabic text, are readable. Another student's notes must not appear.
5. Verify `/studylibrary`, `/studysearch photosynthesis`, `🏠 Main Menu`, `/ai`, `/aihealth` still work.

If no AI Study notes exist yet, use `/ai` → **💾 Save AI Answer** → **✅ Confirm Save**, then try `/studyexport`.

## Rollback

Restore only the `.before_v69.bak` file created by this installer:

```powershell
Copy-Item .\revision_hub_v66.py.before_v69.bak .\revision_hub_v66.py -Force
python -m py_compile revision_hub_v66.py
git add revision_hub_v66.py
git commit -m "Rollback V6.9 export registration"
git push origin main
```

Leave `study_export_v69.py` in place or remove it only after rollback; an unused module does nothing. No saved notes are deleted.

## Offline test status

**84 tests passed** locally against code and mocked Supabase/Telegram; no live Render or Telegram tests were performed here. The export's use of `send_document` follows the Telegram Bot API document upload interface. V6.9 makes no Gemini API calls; `GEMINI_API_KEY` stays configured for developer testing, and Cloudflare remains the public student AI provider.
