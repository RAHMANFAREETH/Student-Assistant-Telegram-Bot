# Student Assistant Bot V7.0 — Private Markdown AI Notes Export

**Prerequisite: V6.9 private TXT export already installed.** This is an add-on for the same bot; it does not create a second Telegram bot or change Supabase.

## New feature

- `/studyexportmd` — in your **private chat** with the bot, tap **✅ Export Markdown** and receive a `.md` file containing your saved AI Study notes.
- `/studyexport` — the original V6.9 TXT export continues to work unchanged.
- Notes are restricted by Telegram sender ID and the `AI Study:` title prefix using the existing V6.9 Supabase query.
- Keeps Tamil, Sinhala, English and Arabic in UTF-8. The file includes dates, headings and verbatim study note text in safe Markdown code blocks.
- Maximum **2,000 notes / 3.5 MB**. Rejects oversized collections rather than sending a partial backup.
- Uses zero additional AI calls, no database writes, and no new Render secrets.
- Saved notes might contain personal material. Only export in your private bot chat and keep downloaded files private.

## Files in the ZIP

1. `study_markdown_v70.py` — new helper; copy into the project root.
2. `INSTALL_V7_0.py` — patches existing `study_export_v69.py` after version checks; creates `study_export_v69.py.before_v70.bak`.
3. `TEST_V7_0_MARKDOWN_EXPORT.py` — 24 focused offline tests (uses existing V6.6 and V6.9 test files).
4. `FIXTURE_V6_9_EXPORT.txt` — fixed baseline used only by installer tests.
5. `README_V7_0.md` — this guide.

**Do not replace your existing `study_export_v69.py` with the fixture.** The installer edits that actual file safely. Preserve your existing `revision_hub_v66.py`, `main.py`, navigation and AI files.

## Windows installation

Back up your project, then extract and copy the five files above into:

`C:\Users\Pros\Desktop\StudentAssistantBot`

From a PowerShell terminal **inside that folder**:

```powershell
Test-Path .\study_export_v69.py
Test-Path .\study_markdown_v70.py
Test-Path .\FIXTURE_V6_9_EXPORT.txt
python -m unittest TEST_V7_0_MARKDOWN_EXPORT.py -v
python INSTALL_V7_0.py
python -m py_compile study_export_v69.py study_markdown_v70.py
python -m unittest TEST_V7_0_MARKDOWN_EXPORT.py TEST_V6_9_EXPORT.py TEST_V6_8_FULL_TEXT_SEARCH.py TEST_V6_7_LIBRARY.py TEST_V6_6_REVISION_HUB.py -v
```

Expected for the five suites, if all older test files are present: `Ran 108 tests` followed by `OK`.

The installer refuses unfamiliar or partially installed V6.9 files. If it stops, **do not manually paste the patch into unknown code**. Investigate differences or use the backup.

## GitHub and Render

After tests pass:

```powershell
git add study_export_v69.py study_markdown_v70.py INSTALL_V7_0.py TEST_V7_0_MARKDOWN_EXPORT.py FIXTURE_V6_9_EXPORT.txt README_V7_0.md
git commit -m "Add V7.0 private Markdown AI notes export"
git push origin main
```

Wait for Render's latest deployment to be marked `Live`. Test in your bot's own private chat:

1. `/studyexportmd` → `✅ Export Markdown` → verify the `.md` file arrives and opens.
2. `/studyexport` → check the older `.txt` download still works.
3. `/studylibrary`, `/studysearch` and `🏠 Main Menu` → verify navigation is unchanged.
4. Cancel Markdown export → confirm no file is sent.

## Rollback

The installer backs up exactly `study_export_v69.py`. Restore that file from `study_export_v69.py.before_v70.bak`, commit the restoration and push to Render. You may leave `study_markdown_v70.py` unused or remove it from your repository. Never delete your Supabase data during rollback.

## What this does *not* do

- It does not make or claim to make a Google Gemini live request on Render.
- It does not enable Gemini for public student requests; existing Gemini developer testing remains unchanged.
- It does not create PDF, DOCX, or cloud storage backups, and does not automatically export content.
- Local automated tests do not guarantee your Render/Supabase live path is healthy; test in Telegram after deploying.
