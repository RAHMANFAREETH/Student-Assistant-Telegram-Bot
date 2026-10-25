# Student Assistant Telegram Bot — V7.7
## Private extracted-text downloads from Study Materials

**Requirement:** V7.6 (and V7.5) installed. Your existing Telegram bot stays the same; this is an add-on.

### What this does

When you open a document with `/materialpreview 12` or via `/materiallibrary`, its preview gains two actions:

- 📥 TXT Extract — download the **stored extracted text** as UTF-8 `.txt`.
- 📝 Markdown Extract — download the **stored extracted text** as UTF-8 `.md`.

Commands are `/materialdownload 12` or `/materialdownloadmd 12`, replacing `12` with the document's actual ID.

**Important:** The current Study Materials table stores extracted text, **not the original uploaded PDF/DOCX/TXT binary**. V7.7 does *not* recover or download that original attachment. Exporting an image-only PDF with no stored OCR text will show a helpful error. The export is read-only and does not count against the AI quota.

### Privacy and resource controls

- Works only in the student's private Telegram bot chat.
- The document is read with the student ID, then checked for ownership.
- Explicit confirmation required; expires after 5 minutes and cannot be reused.
- Student ownership is checked **again** immediately before the document is sent.
- The export has a **2 MB UTF-8 maximum**. Large exports are refused, never truncated without warning.
- No Supabase migrations, API keys, AI requests, or new dependencies.
- Saves no file on the Render filesystem; streams it in memory to Telegram.
- Existing Upload, OCR, Search, Filters, Statistics, Delete and Navigation code is untouched.

### Installation — Windows PowerShell / VS Code

1. Back up your project or commit your current working files first.
2. Extract the downloaded ZIP. Its **five files are at the ZIP root**, not in a nested folder.
3. Copy all five files directly into `C:\Users\Pros\Desktop\StudentAssistantBot` (the folder containing your `main.py`). You do **not** need to overwrite `material_library_v75.py` manually. The installer will update it safely.
4. Verify you copied the files:

```powershell
cd C:\Users\Pros\Desktop\StudentAssistantBot
Test-Path .\INSTALL_V7_7.py
Test-Path .\TEST_V7_7_MATERIAL_EXPORT.py
Test-Path .\material_download_v77.py
```

Each must print `True`. If not, return to step 3 rather than running Python commands.

5. Test and install:

```powershell
python -m unittest TEST_V7_7_MATERIAL_EXPORT.py -v
python INSTALL_V7_7.py
python -m py_compile material_library_v75.py material_download_v77.py
python -m unittest TEST_V7_7_MATERIAL_EXPORT.py TEST_V7_6_MATERIAL_FILTERS.py TEST_V7_5_MATERIAL_LIBRARY.py -v
```

When the V7.5 and V7.6 test files are present, the final command should say **Ran 80 tests ... OK**. The standalone V7.7 suite contains **27 tests**. The installer saves `material_library_v75.py.before_v77.bak`. If the installed code is unfamiliar or partially patched, the installer refuses to modify it. A second successful run changes nothing.

6. Only when tests pass, publish:

```powershell
git add material_library_v75.py material_download_v77.py INSTALL_V7_7.py TEST_V7_7_MATERIAL_EXPORT.py FIXTURE_V7_6_MATERIAL_LIBRARY.txt README_V7_7.md
git commit -m "Add V7.7 private material text exports"
git push origin main
```

`LF will be replaced by CRLF` warnings from Git on Windows are generally harmless.

### Live Telegram test

After Render shows **Live**:

1. Send `/materiallibrary`.
2. Choose one previously uploaded material that has readable extracted text.
3. Tap **📥 TXT Extract** and read the warning, then **✅ Download Extracted Text**.
4. Check that the `.txt` file contains Tamil / Sinhala / Arabic correctly, if used.
5. Repeat with **📝 Markdown Extract**.
6. Check `/materialfilters`, `/materialstats`, and `🏠 Main Menu` still work.

### Rollback

If needed, stop and restore the exact installer backup using PowerShell:

```powershell
Copy-Item .\material_library_v75.py.before_v77.bak .\material_library_v75.py -Force
python -m py_compile material_library_v75.py
```

Commit the restored file and push to deploy the previous version. The extra `material_download_v77.py` is inert when the registration is removed.

### Gemini and Cloudflare

`GEMINI_API_KEY`, Cloudflare AI, AI monitoring and student access are unchanged. Gemini remains a developer-only integration in the existing mixed-age bot.
