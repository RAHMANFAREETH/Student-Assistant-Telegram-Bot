# Student Assistant Telegram Bot V7.1 — One-Note Quick Actions

## What changes

V7.1 lets a student open **one saved AI Study note** and download just that note as a Unicode TXT or Markdown file. A **Back to Library** button and `/studytips` help command make the existing Study Library easier to navigate.

- **No changes to:** `main.py`, Telegram menu/navigation files, Cloudflare AI, Gemini developer integration, Supabase tables, existing TXT/Markdown *all-notes* exports, quota, safety settings or previous features.
- **Exactly one existing file is patched:** `revision_hub_v66.py`; the installer creates `revision_hub_v66.py.before_v71.bak` before applying the patch.
- **New module:** `study_note_actions_v71.py`.
- Existing `/studyexport` and `/studyexportmd` continue to export **all** notes. The new buttons export **only the selected note**.
- No new packages, environment variables, SQL tables, AI calls or Supabase writes.
- Current command `🏠 Main Menu` stays unchanged.

## Requirements

V7.0 must already be installed. The project must contain `revision_hub_v66.py`, `study_export_v69.py` with V7.0 integration, `study_markdown_v70.py`, the existing runtime dependencies and your existing test files `TEST_V6_6_REVISION_HUB.py` and `TEST_V6_9_EXPORT.py`.

## Windows VS Code installation

1. Back up or commit your current bot code before modifying it.
2. Extract the V7.1 ZIP and copy these files **directly** to `C:\Users\Pros\Desktop\StudentAssistantBot` (not inside a nested folder):
   - `study_note_actions_v71.py`
   - `INSTALL_V7_1.py`
   - `TEST_V7_1_NOTE_ACTIONS.py`
   - `FIXTURE_V7_0_REVISION_HUB.txt`
   - `README_V7_1.md`
3. In the project's PowerShell terminal run:

```powershell
python -m unittest TEST_V7_1_NOTE_ACTIONS.py -v
python INSTALL_V7_1.py
python -m py_compile revision_hub_v66.py study_note_actions_v71.py
python -m unittest TEST_V7_1_NOTE_ACTIONS.py TEST_V7_0_MARKDOWN_EXPORT.py TEST_V6_9_EXPORT.py TEST_V6_8_FULL_TEXT_SEARCH.py TEST_V6_7_LIBRARY.py TEST_V6_6_REVISION_HUB.py -v
```

The test file checks the V7.0 fixture, so it works both before and after installing V7.1. The installer is repeat-safe: running it again prints `V7.1 already installed; no files changed.`

4. Only when tests pass, commit and push:

```powershell
git add revision_hub_v66.py study_note_actions_v71.py INSTALL_V7_1.py TEST_V7_1_NOTE_ACTIONS.py FIXTURE_V7_0_REVISION_HUB.txt README_V7_1.md
git commit -m "Add V7.1 private per-note downloads and library shortcuts"
git push origin main
```

5. Wait for Render's latest deployment to show **Live**, then test in your private Telegram chat:
   - `/studylibrary` → choose **📖 one saved AI Study note**
   - Look below its text for **📄 Download TXT**, **📝 Download Markdown**, **📚 Back to Library**
   - Download both formats and verify Tamil/Sinhala/Arabic and English text
   - `/studytips` for all Study Library commands
   - Recheck `/studyexport`, `/studyexportmd`, `/ai`, and `🏠 Main Menu`

## Privacy and limits

- Private Telegram chat required for the buttons.
- Every download looks up the selected note again in Supabase filtered by **sender Telegram user ID** and note ID; another student's note cannot be fetched by changing callback text.
- The title must begin with `AI Study:`; manually saved personal notes are not exported by this action.
- The chosen note is converted in memory and sent as a UTF-8 TXT or Markdown file with a non-sensitive numerical filename.
- Reuses the existing **3.5 MB** export size limit. Oversized notes will not be partially sent.
- No database modifications, no AI requests and no AI quota usage.
- As with any exported private file, the user decides where to save/share it.

## Rollback

If the new functionality causes a problem and you have not manually changed `revision_hub_v66.py` since installing V7.1, in PowerShell:

```powershell
Copy-Item .\revision_hub_v66.py.before_v71.bak .\revision_hub_v66.py -Force
python -m py_compile revision_hub_v66.py
```

Then commit and push the restored file. The new helper may remain unused; it is not registered without the patch.

## Notes

This release is **not a PDF exporter**. Correct Tamil, Sinhala and Arabic rendering in generated PDFs requires suitable Unicode fonts and layout/shaping, so V7.1 deliberately avoids delivering unreadable multilingual PDFs. Your existing Markdown/TXT backups remain intact.

Offline tests verify the expected code and fake database/Telegram behavior. A real Render/Supabase run is still required to confirm live functionality.
