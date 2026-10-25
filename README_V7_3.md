# Student Assistant Telegram Bot — V7.3 Smart Study Collections

**For your existing V7.2 Bot.** No new Telegram bot, repo, Render service, API key, Python dependency, or provider change.

## What's new?

- `📁 My Collections` in `/studyhub` reply menu, or `/collections` directly.
- Create personal collections: `/collectioncreate Biology Revision`.
- Open `/studylibrary`, select a saved AI note, then tap **📁 Add to Collection** and choose a collection.
- Browse collections and open saved AI notes, including older pages (8 notes/page).
- Rename: `/collectionrename 12 Biology 2026` (replace **12** with the ID shown in `/collections`).
- Delete: `/collectiondelete 12` then tap **Confirm Delete**. Only the collection and its links are deleted. **The original AI notes remain in Supabase Notes.**
- Remove individual collection membership with **➖ Remove this note**.
- Maximum **30 collections/student**, **100 notes/collection**, and **60 characters/collection name**. Collections use the existing user's Telegram numeric ID as the scope.

Supported note types: *AI Study:* notes saved through the existing AI save workflow. Ordinary personal notes are intentionally not offered by this release.

### Safety and data model

- Adds only `ai_study_collections_v73` and `ai_study_collection_notes_v73` tables.
- All database requests are scoped to the Telegram **sender** user ID. Callback note IDs are **not** trusted; ownership is rechecked in the Notes table whenever a note is added, opened, or removed.
- Private chat only. Group chats are refused. No client-facing RLS policies; bot backend needs its existing Supabase secret/service-role key.
- SQL uses composite foreign key `(collection_id,user_id)` to prevent association with another student's collection. Note record ownership is additionally verified by Python.
- No note content is sent to AI in V7.3. No AI quota usage or automatic Gemini requests. Cloudflare AI and Gemini developer integration are untouched.
- No existing Supabase notes, favorite status, subject labels, exports, or flashcards are modified by the installer.

## Prerequisites

- Your current `StudentAssistantBot` folder is running V7.2 successfully, including `revision_hub_v66.py` and `study_organizer_v72.py`.
- V7.2 organizer SQL was already executed.
- `.env` and existing Render Environment Variables remain unchanged.

## Windows installation (VS Code / PowerShell)

1. Back up your whole project (`git status` first; commit or copy your working state).
2. Extract this ZIP. Copy **all six** included files directly into your existing `StudentAssistantBot` project folder, *not* a nested `v73` folder. Do not replace `revision_hub_v66.py` manually; the installer patches it.
3. Run these commands **inside** the existing `StudentAssistantBot` folder:

```powershell
python -m unittest TEST_V7_3_COLLECTIONS.py -v
python INSTALL_V7_3.py
python -m py_compile revision_hub_v66.py study_collections_v73.py
python -m unittest TEST_V7_3_COLLECTIONS.py TEST_V7_2_ORGANIZER.py TEST_V7_1_NOTE_ACTIONS.py TEST_V7_0_MARKDOWN_EXPORT.py TEST_V6_9_EXPORT.py TEST_V6_8_FULL_TEXT_SEARCH.py TEST_V6_7_LIBRARY.py TEST_V6_6_REVISION_HUB.py -v
```

Expected test summary if all previous test files remain: **168 tests, OK**. Tests run offline with mocked DB data; they cannot prove your live Supabase schema has been created.

4. Supabase Dashboard → **your existing project** → SQL Editor → paste the contents of `SQL_V7_3_COLLECTIONS.sql` → **Run**. Check for `Success`. Do **not** run any SQL from untrusted sources. This script does not drop or alter prior tables.
5. Commit and push:

```powershell
git add revision_hub_v66.py study_collections_v73.py INSTALL_V7_3.py TEST_V7_3_COLLECTIONS.py FIXTURE_V7_2_REVISION_HUB.txt SQL_V7_3_COLLECTIONS.sql README_V7_3.md
git commit -m "Add V7.3 private AI Study Collections"
git push origin main
```

6. In Render, confirm the latest deployment shows **Live**. There are **no new Render environment variables**.

## Telegram live tests

1. Private chat → `/studyhub` → **📁 My Collections** or `/collections`.
2. `/collectioncreate Biology Revision` → should confirm creation.
3. `/studylibrary` → open a saved AI Study note → **📁 Add to Collection** → select Biology Revision.
4. `/collections` → Biology Revision → should list the saved note. Open the note and check content.
5. `/collectionrename ID Biology Notes` (use the collection's real ID).
6. Remove one note from the collection. Confirm the note still exists in `/studylibrary`.
7. `/collectiondelete ID`, choose **Confirm Delete**. Confirm notes still exist and `🏠 Main Menu` works.
8. Sanity-check `/ai`, `/studyfavorites`, `/studysubjects`, `/studyexport`, `/studyexportmd`.

## Troubleshooting

- `ModuleNotFoundError: No module named 'TEST_V7_3_COLLECTIONS'`: copy the ZIP's files into the same directory where you run the commands.
- `V7.3 installer stopped safely`: do not force the update. Check you're on V7.2, inspect `revision_hub_v66.py`, and compare with the backup. The installer refuses unexpected local edits.
- `Collections unavailable`: check that you ran `SQL_V7_3_COLLECTIONS.sql` in the **same Supabase project** Render uses, and that `SUPABASE_SECRET_KEY` still works. Do not paste secrets into chat.
- Collection name already exists: choose another name. Names are unique per student ignoring case.
- Some notes missing: V7.3 collections only accept saved notes titled `AI Study:`; other note types remain outside these collections.
- Failed test with Windows decoding: the bundled test and installer explicitly use UTF-8.

## Rollback

To undo only the Python patch **before** new deployments:

```powershell
Copy-Item .\revision_hub_v66.py.before_v73.bak .\revision_hub_v66.py -Force
```

Commit and push the restored `revision_hub_v66.py` if you want Render to roll back. You can leave the two V7.3 Supabase tables untouched while the code is rolled back; never drop tables containing student data without a backup. The original V7.2 organizer and all other features remain intact.

**Limitations:** This release does not include full-text collection searches, drag-and-drop ordering, PDF export, or collection sharing. It does not automatically migrate existing subject folders into custom collections.
