# Student Assistant Telegram Bot — V7.8
## Read Full Extracted Text & Search Within One Material

**Prerequisite:** V7.7 Study Materials text export upgrade installed. This is an additive upgrade for your existing bot; it does not replace other modules.

### What's new

- **`/materialread 12`** reads the saved extracted text for material ID `12`, 2,500 characters per Telegram message. Use the **Next ➡️** and **⬅️ Previous** inline buttons to navigate. These pages are **text sections, not PDF page numbers**.
- **`/materialinside 12 photosynthesis`** searches inside one material's saved extracted text. It gives up to five short matching snippets and reports the number of matches in the scanned text. Queries may be in Tamil, Sinhala, Arabic, or English.
- The existing `/materialpreview 12` page gains **📖 Read Full Text** and **🔎 Search Inside** buttons, alongside the V7.7 TXT/Markdown exports and previous actions.
- All reading is from **`extracted_text` already saved in Supabase**, not from the original PDF/DOCX file. Scanned PDFs need OCR text to have been stored before this will work.

### Search limitations

Search scans at most the **first 500,000 characters** of an individual material. If the document is longer, the bot explicitly says the search was partial. Searches look for a literal phrase (case insensitive) and do not use AI or semantic matching. The entire saved extracted text is available through sequential pages, subject to Telegram and Supabase performance.

### Access and protection

- Works in the student's private chat only.
- Reads are scoped by the student's Telegram ID, and ownership is re-checked whenever a page, hint, or search is requested.
- **Read-only:** No Supabase writes, new tables, provider API calls, AI quota use, extra packages, or environment variables.
- Existing Study Materials upload, OCR, file filters/statistics, previews, text exports, and delete confirmation are unchanged.
- Cloudflare AI and developer-only Gemini integration are not modified.

### Installation — Windows / VS Code

1. **Back up your working project** or create a Git commit before proceeding.
2. Unzip `StudentAssistantBot_V7_8_Material_Reading_Search.zip`. Its **5 files are at the ZIP root**.
3. Copy all 5 files to `C:\Users\Pros\Desktop\StudentAssistantBot`, next to your current `material_library_v75.py`. Do not manually replace that file; the installer patches it after validation.
4. In PowerShell:

```powershell
cd C:\Users\Pros\Desktop\StudentAssistantBot
Test-Path .\INSTALL_V7_8.py
Test-Path .\TEST_V7_8_MATERIAL_READER.py
Test-Path .\material_reader_v78.py
```

All three should print `True` before continuing. Then:

```powershell
python -m unittest TEST_V7_8_MATERIAL_READER.py -v
python INSTALL_V7_8.py
python -m py_compile material_library_v75.py material_reader_v78.py
python -m unittest TEST_V7_8_MATERIAL_READER.py TEST_V7_7_MATERIAL_EXPORT.py TEST_V7_6_MATERIAL_FILTERS.py TEST_V7_5_MATERIAL_LIBRARY.py -v
```

With all previous test files present, the final suite should show **103 tests, OK**. The V7.8-only suite has **23 tests**. Mocked error logs from failure-path tests may appear and are expected.

The installer:
- Looks for the specific V7.7 library structure.
- Creates `material_library_v75.py.before_v78.bak` with the original bytes.
- Refuses unrecognized or partly patched files and preserves the existing file.
- Can be run twice: a second successful run reports 'already installed'.

### Deploy to GitHub and Render

Only after successful tests:

```powershell
git add material_library_v75.py material_reader_v78.py INSTALL_V7_8.py TEST_V7_8_MATERIAL_READER.py FIXTURE_V7_7_MATERIAL_LIBRARY.txt README_V7_8.md
git commit -m "Add V7.8 material reader and inside search"
git push origin main
```

Wait for Render to show **Live** before testing in Telegram.

### Telegram live test

1. `/materiallibrary` — pick your saved TXT or PDF material with extracted text.
2. Tap **📖 Read Full Text** and, on a long document, **Next ➡️** then **⬅️ Previous**.
3. Tap **🔎 Search Inside** to see how to use the command.
4. Send `/materialinside 12 pandas` with your **real material ID and search term**.
5. Confirm that `/materialdownload 12`, `/materialfilters`, and `🏠 Main Menu` still work.

### Roll back safely

```powershell
Copy-Item .\material_library_v75.py.before_v78.bak .\material_library_v75.py -Force
python -m py_compile material_library_v75.py
```

Commit and push that restored file if reverting the Render deployment. `material_reader_v78.py` remains inactive once the registration is removed.
