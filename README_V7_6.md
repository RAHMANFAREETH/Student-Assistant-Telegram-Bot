# Student Assistant Telegram Bot V7.6 — Study Materials Filters & Statistics

Compatible with **V7.5 Study Materials Library**. This upgrade changes only the existing `material_library_v75.py` file and adds `material_filters_v76.py`. The **document-upload routing fix**, original reading and search handlers, `study_materials.py`, Cloudflare AI, Gemini developer integration, and all Supabase data remain unchanged.

## New commands and interface

- `/materialfilters` — **🧰 Filters & Stats** menu, accessible also through the V7.5 Material Library button.
- `/materialtype pdf` — only PDF study materials. Also accepts `docx`, `txt`, `other`, and `all`.
- `/materialsubject` — list available subject IDs for recently saved materials; choose via buttons.
- `/materialsubject 5` — documents assigned to subject ID 5; `/materialsubject none` for **No Subject**.
- `/materialstats` — counts of PDF, DOCX, TXT, other, assigned subjects, and stored extracted-text character totals for the **most recent 100 saved materials**.
- **Inline pagination:** six materials per page, with Newer / Older navigation. Selecting a material reuses the ownership-checked V7.5 preview.

Existing `/materiallibrary`, `/materialfind keyword`, `/materialpreview ID`, reading, searching inside document text, and upload routines are **not replaced**.

## Limits and privacy

- All features are private-chat-only and use the existing `get_materials(user_id, limit=100)` query; there are no background jobs or additional AI calls.
- Statistics cover only the **latest 100 materials**, **not** all-time Supabase totals. Subject names are **not** fetched; subjects display as existing numeric IDs.
- The original files are not reconstructed. Material previews still show stored extracted text, not a visual PDF/DOCX preview.
- Clicking a document uses V7.5's fresh ownership check. The new filters also reject foreign-user rows if a backend accidentally returns them.
- V7.6 does not add a new Supabase table, API key, Render environment variable, or Python package.

## Install with VS Code on Windows

**Prerequisite:** V7.5 installed and functioning. Back up or commit your existing project first.

1. Download and extract the V7.6 ZIP, then copy these five files directly to the folder containing `main.py` and `material_library_v75.py`, e.g. `C:\Users\Pros\Desktop\StudentAssistantBot`:

   - `material_filters_v76.py`
   - `INSTALL_V7_6.py`
   - `TEST_V7_6_MATERIAL_FILTERS.py`
   - `FIXTURE_V7_5_MATERIAL_LIBRARY.txt`
   - `README_V7_6.md`

2. In VS Code **PowerShell**, from the project folder:

```powershell
Test-Path .\material_library_v75.py
Test-Path .\INSTALL_V7_6.py
Test-Path .\TEST_V7_6_MATERIAL_FILTERS.py
python -m unittest TEST_V7_6_MATERIAL_FILTERS.py -v
python INSTALL_V7_6.py
python -m py_compile material_library_v75.py material_filters_v76.py study_materials.py main.py
python -m unittest TEST_V7_6_MATERIAL_FILTERS.py TEST_V7_5_MATERIAL_LIBRARY.py -v
```

All three `Test-Path` commands must report `True`. With the unchanged V7.5 test file present, expect **53 tests OK**. The installer makes an exact-byte backup: `material_library_v75.py.before_v76.bak`. It is idempotent (a second install prints "already installed"). If it reports `INSTALL BLOCKED`, **do not force-edit the module**; inspect the installed V7.5 file first.

3. Only after tests pass:

```powershell
git add material_library_v75.py material_filters_v76.py INSTALL_V7_6.py TEST_V7_6_MATERIAL_FILTERS.py FIXTURE_V7_5_MATERIAL_LIBRARY.txt README_V7_6.md
git commit -m "Add V7.6 Study Materials filters and stats"
git push origin main
```

No SQL is required. Do **not** commit `.env`, backup files, or API keys.

4. After Render reports the new deployment **Live**, open the bot in a **private Telegram chat**:

   - `/materiallibrary` → **🧰 Filters & Stats** → **📄 PDF** or **📃 TXT**.
   - `/materialsubject` → choose an existing subject ID or No Subject.
   - `/materialstats` → verify per-file-type counts for the latest 100 documents.
   - Open a filtered material → the **same V7.5 preview** appears.
   - Test `/materialfind pandas`, **➕ Add Material**, and **🏠 Main Menu** to ensure earlier functionality is preserved.

This package has **53 passing offline tests** (32 V7.6 + 21 V7.5); Render/Telegram production tests are not yet performed.

## Rollback

If you need to roll back only the V7.6 feature:

```powershell
Copy-Item .\material_library_v75.py.before_v76.bak .\material_library_v75.py -Force
python -m py_compile material_library_v75.py
python -m unittest TEST_V7_5_MATERIAL_LIBRARY.py -v
git add material_library_v75.py
git commit -m "Rollback V7.6 filters"
git push origin main
```

You can leave the new `material_filters_v76.py` in your folder unused until a later upgrade.
