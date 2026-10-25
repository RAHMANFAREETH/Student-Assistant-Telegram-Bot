# Student Assistant Bot V7.4 — Smart Collection Management

**For your existing V7.3 Telegram Bot.** Adds collection-name search, collection statistics, a quick tools menu, and a **confirmed, private Markdown export of one collection**. No new Telegram bot, Supabase table, SQL, Render variable, paid API, or Python dependency.

## Features

- `/collectiontools` — shortcuts to collection statistics, your collections, and search/export instructions. A **📊 Collection Tools** inline button also appears in `/collections` when you have collections.
- `/collectionsearch biology` — case-insensitive, Unicode-aware literal search of **your collection names only**, including Tamil/Sinhala/Arabic names. Tap a result to open the collection. The term must be 2–60 characters.
- `/collectionstats` — counts your personal collections, collection-note **links**, distinct linked note IDs, and per-collection link counts. Counts are not the same as a verified count of accessible notes. No AI requests are made.
- `/collectionexport 12` — requests a Markdown backup of only **your collection 12**. Replace `12` with the actual collection ID from `/collections`. Before any private file is sent, tap **✅ Export Markdown**. You can also open a collection and tap **📤 Export Collection (MD)**.
- Markdown exports use the existing V7.0 UTF-8-BOM format, preserve Tamil/Sinhala/Arabic, and remain in memory instead of writing private study text to Render's disk. The filename includes the collection ID. Limits: **100 notes / 3.5 MB**. The export is refused if any linked note no longer belongs to you or is not a saved `AI Study:` note. **No partial export.**
- Existing V7.3 add/remove/rename/delete, V7.2 subjects/favorites, V7.0 whole-library exports, and Main Menu are preserved.

## Installation on Windows / VS Code

Prerequisites: your existing V7.3 install, including `study_collections_v73.py`, `study_markdown_v70.py`, `revision_hub_v66.py`, and existing V7.3 test files. There is **no new SQL**; retain the V7.3 Supabase tables. Do not copy the included V7.3 fixture into the live module.

1. Back up your working project (`git status` and commit your existing changes), then extract the ZIP and copy its **five files** directly into `C:\Users\Pros\Desktop\StudentAssistantBot`:

   - `study_collection_tools_v74.py`
   - `INSTALL_V7_4.py`
   - `TEST_V7_4_COLLECTION_TOOLS.py`
   - `FIXTURE_V7_3_COLLECTIONS.txt` (test reference; **do not rename**)
   - `README_V7_4.md`

2. From the project folder in VS Code **PowerShell** run:

```powershell
python -m unittest TEST_V7_4_COLLECTION_TOOLS.py -v
python INSTALL_V7_4.py
python -m py_compile study_collections_v73.py study_collection_tools_v74.py
python -m unittest TEST_V7_4_COLLECTION_TOOLS.py TEST_V7_3_COLLECTIONS.py TEST_V7_2_ORGANIZER.py TEST_V7_1_NOTE_ACTIONS.py TEST_V7_0_MARKDOWN_EXPORT.py TEST_V6_9_EXPORT.py TEST_V6_8_FULL_TEXT_SEARCH.py TEST_V6_7_LIBRARY.py TEST_V6_6_REVISION_HUB.py -v
```

Expected on the unchanged V7.3 test suite: **193 tests, OK**. Older tests use V6.6–V7.3 fixtures and SQL files you previously installed. If a file is missing, restore that test/fixture from its prior upgrade ZIP rather than deleting tests. Tests are offline; they don't verify your real Supabase or Render connectivity.

3. If all tests pass, commit and deploy:

```powershell
git add study_collections_v73.py study_collection_tools_v74.py INSTALL_V7_4.py TEST_V7_4_COLLECTION_TOOLS.py FIXTURE_V7_3_COLLECTIONS.txt README_V7_4.md
git commit -m "Add V7.4 private collection search stats and Markdown export"
git push origin main
```

4. In Render, confirm the latest deployment is **Live**. No Environment Variable changes are required.

## Telegram live tests

1. Private chat: `/collections` → see **📊 Collection Tools** or use `/collectiontools` directly.
2. `/collectionsearch Biology` → tap a matching collection. For a Tamil-named collection try `/collectionsearch தமிழ்`.
3. `/collectionstats` → check that your own collection names and membership counts are shown.
4. `/collectionexport ID` → review the confirmation prompt, first try **❌ Cancel** (no file); then request again and choose **✅ Export Markdown**. Confirm that its `.md` file contains *only* notes from that collection. **Do not share the private export in this chat.**
5. In the same collection, test **📤 Export Collection (MD)**. Then verify `/studyorganize`, `/studylibrary`, `/studyexportmd`, and `🏠 Main Menu` still work.

## Safety and limitations

- Telegram sender ID must match the **private chat ID**. Every database query is scoped to the sender's ID, including confirmation callbacks. File generation additionally reloads notes from Supabase using an explicit owner filter. Collection links are not automatically treated as proof of note ownership.
- Export fails rather than silently omitting stale/deleted/foreign notes. If this happens, open the collection and remove unavailable note links (where possible) or review your records, then retry.
- Collection statistics count membership **links**, including stale ones; they are not exam progress or a live model token/billing quota. The stats feature reads no note contents.
- Collection search checks names, not note contents. Use `/studysearch <word>` for your existing AI-note full-text search.
- Maximum 30 collections/student and 100 notes/collection, as in V7.3. Export is `.md`, not PDF. Existing `.txt` and `.md` full-library exports remain supported.
- Cloudflare AI, Gemini developer integration, AI quotas, Azure/AssemblyAI, Notes and Flashcards **are not modified**. The V7.4 installer patches only `study_collections_v73.py` after verifying the expected V7.3 layout.

## Rollback

The installer creates an exact file backup named `study_collections_v73.py.before_v74.bak`. To revert only the V7.4 Python patch:

```powershell
Copy-Item .\study_collections_v73.py.before_v74.bak .\study_collections_v73.py -Force
git add study_collections_v73.py
git commit -m "Rollback V7.4 collection tools"
git push origin main
```

There is **no new table to delete**. The helper can remain unused on disk after a rollback. If `INSTALL_V7_4.py` reports an unexpected customized module or an existing backup, stop rather than forcing a replacement.
