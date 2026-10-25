# Student Assistant Telegram Bot V7.5 — Study Materials Library

Works as an **add-on to the existing Study Materials module**. It preserves the V7.4 collections modules, the document-upload routing fix, Cloudflare AI, Gemini developer client, and existing Supabase data.

## What's new

- `📚 Material Library` button under `📚 Study Materials`; command `/materiallibrary`.
- Six documents per page, with Older/Newer navigation across the latest **100 saved materials**.
- `/materialfind biology` searches **document titles and filenames**, including Tamil/Sinhala/Arabic text; matching entries can be paged. The pre-existing `🔎 Search Materials` still searches text *inside* uploaded documents.
- `/materialpreview 12` or tapping an item opens up to the first **950 extracted-text characters**, with a reminder that this is **not a preview of the original PDF/DOCX/TXT binary**. The original binary isn't retained by the current Study Materials save routine.
- From a preview, `🗑 Delete (confirm)` prompts for Yes/Cancel. Confirmations expire after 5 minutes, re-check user ownership, and don't delete on a first tap. The old `🗑 Delete Material` menu remains unchanged.
- Private-chat-only interactions, per-user Supabase queries, and no AI calls or new API keys.

## Installation (VS Code / Windows)

1. Back up or commit your existing working project.
2. Extract ZIP, then copy these files directly to `C:\Users\Pros\Desktop\StudentAssistantBot` (same level as `main.py`):
   - `material_library_v75.py`
   - `INSTALL_V7_5.py`
   - `TEST_V7_5_MATERIAL_LIBRARY.py`
   - `FIXTURE_STUDY_MATERIALS_PRE_V75.txt`
   - `README_V7_5.md`
3. In VS Code PowerShell Terminal, in the project directory, run:

```powershell
python -m unittest TEST_V7_5_MATERIAL_LIBRARY.py -v
python INSTALL_V7_5.py
python -m py_compile main.py study_materials.py material_library_v75.py
python -m unittest TEST_V7_5_MATERIAL_LIBRARY.py -v
```

Expected for the supplied test suite: `Ran 21 tests ... OK`. `INSTALL_V7_5.py` changes **only `study_materials.py`** and makes an exact-bytes backup named `study_materials.py.before_v75.bak`. It is idempotent; on later runs it prints `already installed`.

The installer refuses to change unfamiliar or partially patched code and refuses to overwrite an existing backup. If it refuses, **don't manually force the patch**: inspect the actual file/version before proceeding.

4. Push only after tests pass:

```powershell
git add study_materials.py material_library_v75.py INSTALL_V7_5.py TEST_V7_5_MATERIAL_LIBRARY.py FIXTURE_STUDY_MATERIALS_PRE_V75.txt README_V7_5.md
git commit -m "Add V7.5 Study Materials Library and previews"
git push origin main
```

5. After Render reports a live deployment, test in a **private chat**:

- `📚 Study Materials` → `📚 Material Library` → tap a document.
- `/materialfind pandas` → tap a matching document.
- `/materialpreview 12` (replace `12` with an ID that exists in your `/materiallibrary`).
- Test delete confirmation with a disposable document only. `❌ Cancel` must not delete the material.
- Ensure the previously repaired **➕ Add Material** TXT upload and **🏠 Main Menu** still work.

## Important limits

- No automatic upload retry or parsing changes. If your TXT/PDF/DOCX upload still fails, V7.5 does not fix the original upload route on its own.
- The existing database stores extracted text and metadata; it does **not** store an original downloadable file. V7.5 cannot reconstruct a PDF/DOCX for download.
- Search only scans the **100 most recently saved materials** and uses exact case-insensitive substring matching for title/filename. Search pagination state is in memory and expires in 10 minutes or on Render restart. Search **inside extracted text** via the existing `🔎 Search Materials` feature.
- Delete confirmation state is in memory and expires after five minutes or on Render restart. Each confirmation is scoped to the initiating user, and ownership is rechecked.
- Database actions still depend on your existing `study_materials` table and `SUPABASE_URL`/`SUPABASE_SECRET_KEY` configuration.
- **No new SQL, Render environment variable, library package, or AI quota** needed.

## Rollback

If the new material library causes an issue:

```powershell
Copy-Item .\study_materials.py.before_v75.bak .\study_materials.py -Force
python -m py_compile study_materials.py main.py
git add study_materials.py
git commit -m "Rollback V7.5 Study Materials menu"
git push origin main
```

You may leave `material_library_v75.py` in the project unused until you re-enable the patch. Do not add `.env`, API keys, backup files, or the zipped project itself to Git.
