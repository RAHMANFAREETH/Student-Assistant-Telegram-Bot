# Student Assistant Bot V6.7 — Browse & Search Saved AI Notes

This is an **incremental upgrade** to your **existing V6.6** Student Assistant Telegram Bot project. It keeps V6.5.1 Main Menu navigation, Cloudflare AI, V5.9+ Gemini developer integration, and all existing Supabase records intact.

## New features

- **📚 My AI Study Library / `/studylibrary`**: navigate saved AI notes, eight per page, using **Older notes ➡️** and **⬅️ Newer notes**. Previously, V6.6 showed only the latest eight.
- **🔎 `/studyfind photosynthesis`**: case-insensitive search of your saved AI note **titles**. Works with Tamil, Sinhala, Arabic, and English title text. Example: `/studyfind ஒளிச்சேர்க்கை`.
- Search deliberately looks at **only the 200 most recent AI notes** and shows up to eight matching titles; it does not search full note bodies. If 200 notes exist, the result notes that the search may not cover older content.
- Selecting a note still uses V6.6's **fresh owner-filtered Supabase query** before showing the content. Only private chats can browse or search records.
- This adds **no AI calls**, no daily quota consumption, no Supabase writes, no new SQL, and no Render environment variables.

## What files are included?

Copy **these four files from the ZIP root** into:

`C:\Users\Pros\Desktop\StudentAssistantBot`

1. `INSTALL_V6_7.py` — modifies `revision_hub_v66.py` only, using a safe backup.
2. `TEST_V6_7_LIBRARY.py` — offline tests; imports your existing `TEST_V6_6_REVISION_HUB.py` from V6.6.
3. `FIXTURE_V6_6_REVISION_HUB.txt` — offline test fixture, not running production code.
4. `README_V6_7.md` — these instructions.

**Prerequisite:** V6.6 must already be installed and `revision_hub_v66.py` must exist. If the installer finds a customized or unexpected V6.6 notes handler, it stops without modifying your file. **Do not replace the actual module with the test fixture.**

## Windows PowerShell installation

Back up your working project, then from your project folder:

```powershell
Test-Path .\INSTALL_V6_7.py
Test-Path .\revision_hub_v66.py
Test-Path .\TEST_V6_6_REVISION_HUB.py
python -m unittest TEST_V6_7_LIBRARY.py -v
python INSTALL_V6_7.py
python -m py_compile revision_hub_v66.py
python -m unittest TEST_V6_7_LIBRARY.py TEST_V6_6_REVISION_HUB.py -v
```

The first three `Test-Path` commands should each return `True`. The combined regression suite contains **45 offline tests** and should report `OK`.

The installer preserves UTF-8 and Windows CRLF line endings, creates `revision_hub_v66.py.before_v67.bak`, and makes no further changes when run a second time. It refuses to overwrite a prior backup if files need patching.

If you encounter an `Unexpected ... code` or `Customized V6.6 notes handler` error, do not replace your existing file with an old version. Keep your source unchanged and inspect the mismatch first.

## GitHub / Render

```powershell
git status
git diff -- revision_hub_v66.py
git add revision_hub_v66.py INSTALL_V6_7.py TEST_V6_7_LIBRARY.py FIXTURE_V6_6_REVISION_HUB.txt README_V6_7.md
git commit -m "Add V6.7 searchable paginated AI study library"
git push origin main
```

Do not commit backups, `.env`, API keys, or private Supabase credentials.

## Telegram live tests after Render shows Live

1. In your **private chat** with the bot, run `/studylibrary`. If you have over eight saved AI notes, tap **Older notes ➡️**, then **⬅️ Newer notes**.
2. Run `/studyfind photosynthesis` (or `/studyfind தமிழ்`) to find matching *titles*.
3. Tap a search result to open the saved note; test that `/studypractice` still shows flashcards.
4. Test the V6.5.1 navigation fixes (`🏠 Main Menu` and `⬅️ Main Menu`), `/ai`, and `/aihealth`.
5. If you only have a few notes, the older-notes navigation will not appear until there are more than eight AI notes.

## Rollback

If the V6.7 code needs to be rolled back, restore the existing backup **only if it was created by this installer**:

```powershell
Copy-Item .\revision_hub_v66.py.before_v67.bak .\revision_hub_v66.py -Force
python -m py_compile revision_hub_v66.py
git add revision_hub_v66.py
git commit -m "Rollback V6.7 AI library"
git push origin main
```

This returns the V6.6 revision hub behavior. It does **not** delete students' notes or flashcards.

**Testing scope:** 45 offline tests passed against the saved V6.6 project code and mock Supabase responses; live Render/Telegram functionality has not been verified. Google AI Studio remains developer-only in the public mixed-age bot.
