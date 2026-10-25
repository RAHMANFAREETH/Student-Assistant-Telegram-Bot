# Student Assistant Bot V7.2 — Smart AI Notes Organization

This is a **patch for the existing Telegram bot**, not a new bot or service.

## Features

- `🗂 Organize AI Notes` inside the existing Study Revision keyboard
- `/studyorganize` or `/studyrecent`: browse recently **saved** AI Study notes, eight per page
- `/studyfavorites`: view favorite AI Study notes
- `/studysubjects`: browse six subject folders: Science, Mathematics, Languages, History, Technology, General
- Open a saved AI note and tap `⭐ Favorite / 🏷 Subject` to favorite/unfavorite or assign a subject
- Preserves V7.1 TXT/Markdown per-note downloads, full exports, search, revision, `/reviews`, and navigation
- Per-user data isolation: sender's numeric Telegram ID is verified, and every note is re-fetched by `user_id` before changing metadata or showing private content
- No AI provider calls, quota changes, or extra packages

**Scope:** V7.2 organizes notes saved with the `AI Study:` title prefix. It does not modify ordinary/manual Notes or automatically classify subject from text. Recently saved order is by note ID, *not* recently opened/viewed.

## 1 — Back up the project

Make a backup of `C:\Users\Pros\Desktop\StudentAssistantBot` or commit your working V7.1 project to Git.

## 2 — Copy the upgrade files

Extract the V7.2 ZIP; copy these files into the **top-level** `StudentAssistantBot` folder alongside `revision_hub_v66.py`:

- `study_organizer_v72.py`
- `INSTALL_V7_2.py`
- `TEST_V7_2_ORGANIZER.py`
- `SQL_V7_2_NOTE_ORGANIZER.sql`
- `README_V7_2.md` (documentation)

The ZIP includes one test fixture (`FIXTURE_V7_1_REVISION_HUB.txt`) needed for the offline installer test. Copy that into the same folder, too. **Do not replace `revision_hub_v66.py` manually**; the installer safely updates it.

## 3 — Install

Run from VS Code PowerShell in your project root:

```powershell
python -m unittest TEST_V7_2_ORGANIZER.py -v
python INSTALL_V7_2.py
python -m py_compile revision_hub_v66.py study_organizer_v72.py
python -m unittest TEST_V7_2_ORGANIZER.py TEST_V7_1_NOTE_ACTIONS.py TEST_V7_0_MARKDOWN_EXPORT.py TEST_V6_9_EXPORT.py TEST_V6_8_FULL_TEXT_SEARCH.py TEST_V6_7_LIBRARY.py TEST_V6_6_REVISION_HUB.py -v
```

If all previous test files are present, expect **146 tests**. If prior tests are unavailable, run `python -m unittest TEST_V7_2_ORGANIZER.py -v` for the 19 V7.2-focused tests.

The installer is idempotent, UTF-8/CRLF compatible, creates `revision_hub_v66.py.before_v72.bak`, and refuses unfamiliar/custom code instead of overwriting it. It modifies **only `revision_hub_v66.py`**. Other V7.1 files are left untouched.

## 4 — Create the metadata table (REQUIRED for Favorites/Subjects)

1. Open **Supabase → your existing project → SQL Editor → New query**.
2. Paste the content of `SQL_V7_2_NOTE_ORGANIZER.sql` and run it **once**.
3. It creates `public.ai_note_organizer_v72` to store just `(user_id, note_id, favorite, subject)` — no saved note contents are copied. It enables RLS and revokes anon/authenticated table access. The bot's backend secret/service-role key accesses it.
4. Do **not** paste database credentials or API tokens in chat/GitHub.

`/studyrecent` works even without this table, but Favorites and Subjects won't save or load until the SQL step is completed.

**SQL safety:** Creates one new table and two indexes. Does not alter or delete any existing notes, flashcards, or student data.

## 5 — Push to GitHub and deploy

```powershell
git add revision_hub_v66.py study_organizer_v72.py INSTALL_V7_2.py TEST_V7_2_ORGANIZER.py FIXTURE_V7_1_REVISION_HUB.txt SQL_V7_2_NOTE_ORGANIZER.sql README_V7_2.md
git commit -m "Add V7.2 AI notes favorites and subject organization"
git push origin main
```

Wait until your existing Render service shows a **Live** deployment. No Render environment variables or new API keys are required.

## 6 — Test in Telegram private chat

1. `/studyrecent` — newest saved AI notes appear; tap one of them.
2. Tap `⭐ Add to favorites` and then `/studyfavorites` — verify your note appears.
3. Tap `🏷 Change subject`, select `Science` or another folder, then `/studysubjects` — verify the folder shows the note.
4. Tap the same note again to remove favorite or clear its subject.
5. `/studylibrary` — open a note and check that existing `📄 Download TXT` and `📝 Download Markdown` actions still work.
6. `🏠 Main Menu`, `/studyexport`, `/studyexportmd`, `/ai`, `/aihealth` — spot-check existing features.

Favorites and subject changes are manual and do **not** count against AI request limits.

## Rollback

1. Keep the backend offline while rolling back.
2. Restore the exact bytes from `revision_hub_v66.py.before_v72.bak` to `revision_hub_v66.py`. Remove the V7.2 helper if needed.
3. Commit and push the restored source, then redeploy.
4. Do **not** drop the V7.2 metadata table automatically; it can retain harmless favorite metadata for a future retry. Removing it would erase users' V7.2 favorites/tags.

## Important limits

- Favorite and subject lists scan up to 200 metadata rows and display up to 8 note choices at a time.
- Subject folders are fixed categories, not AI-predicted labels; you can clear an assigned subject.
- The bot does not expose private records in groups. It does not alter Cloudflare AI, Gemini developer-only integration, or `GEMINI_API_KEY`.
- Offline tests have passed in the build environment; **your live Supabase table permissions and Render connectivity still need verification**.
