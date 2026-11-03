# Student Assistant Bot V7.13 — Real DOCX/PPTX → PDF

## What it actually does

- Adds **📄 DOCX → PDF** and **📊 PPTX → PDF** inside the existing **📄 PDF Tools** keyboard.
- `/docxpdf` or `/pptxpdf` works as an alternative.
- Student taps a tool → uploads one Word `.docx` or PowerPoint `.pptx` file → bot returns a **real PDF attachment**.
- DOCX goes through **LibreOffice Writer** (paragraphs, tables, images and normal page layout); PPTX goes through **LibreOffice Impress** (one PDF page for each slide). Rendering is limited by installed fonts and LibreOffice compatibility with Microsoft Office formats.
- Keeps your existing `main.py`, other PDF tools, Cloudflare/Gemini, Supabase and broadcast modules untouched. **No new Telegram bot, Render web service, database or paid API.**
- Supports **private chats only**, file limit **12 MB**, output PDF limit **18 MB**, **100-second timeout**, one conversion at a time (helps protect small Render instances). Files are processed in temporary directories and deleted after sending. Conversions run in a background worker so the Telegram webhook responds quickly. No online conversion provider.

## Important: This is not a Python-only conversion

A DOCX/PPTX Office renderer is essential for visually faithful output. `python-docx` and `python-pptx` can read/edit their respective formats but **cannot** accurately render them to PDF on their own. The native Render Python runtime does **not** include LibreOffice. Docker is the supported way to install OS packages like LibreOffice for the **same existing Render service**: see https://render.com/docs/native-runtimes and https://render.com/docs/docker .

**Do not deploy this update on native Python and assume conversion works.** Its buttons would appear but conversion would report "Office conversion is not installed on this server." You must arrange an Office renderer at runtime, e.g. using the included Dockerfile and changing the existing service runtime to Docker. If changing runtime is not available in your service's settings, pause and seek an alternative hosting arrangement rather than deploying a non-working button.

## Step 1 — Install in your existing VS Code project (Windows)

Extract this ZIP, then copy **`INSTALL_V7_13.py`** and the entire **`V713_FILES`** folder to your existing `StudentAssistantBot` folder (where `pdf_tools.py` is located). In PowerShell:

```powershell
python INSTALL_V7_13.py --dry-run
```

Review the output, then:

```powershell
python INSTALL_V7_13.py
python -m unittest TEST_V7_13_OFFICE_PDF.py -v
```

Expected: 22 tests pass if LibreOffice, python-docx, and python-pptx are installed locally; the two real-conversion tests are skipped when LibreOffice is absent. If the test environment needs Office fixture packages:

```powershell
python -m pip install python-docx python-pptx
```

For actual conversion **on your Windows PC**, install LibreOffice from https://www.libreoffice.org/download/download-libreoffice/ . The installer searches Program Files automatically. If installed elsewhere, configure a local environment variable:

```powershell
$env:OFFICE_CONVERTER_BINARY = 'C:\Program Files\LibreOffice\program\soffice.exe'
python -m unittest TEST_V7_13_OFFICE_PDF.py -v
```

The local installer only *inserts* two buttons and one registration inside your existing `pdf_tools.py`, even if you have custom Crop/Scan tools. It does **not** replace the entire PDF module. It adds `office_to_pdf_v713.py`, tests, README, Dockerfile and `.dockerignore` if absent. An existing Dockerfile/.dockerignore is preserved and must be merged manually.

Rollback if no later changes were made to `pdf_tools.py`:

```powershell
python INSTALL_V7_13.py --rollback
```

## Step 2 — Make LibreOffice available in the SAME Render service

The installer places `Dockerfile` and `.dockerignore` at your project root if they do not already exist. The Dockerfile uses Python 3.12 with LibreOffice Writer, LibreOffice Impress and Noto fonts; installs **all packages from your existing `requirements.txt`**, and runs `INSTALL_TEXT_PDF_FONTS.py` to preserve V7.11 Text → PDF functionality. It starts Gunicorn with `main:app` (same bot).

1. In your existing Render web service, **Settings → Runtime / Language**, choose **Docker** (if supported by your current service configuration). **Do not create another Render service.** Keep the same repository, branch and environment variables.
2. The Dockerfile path is `./Dockerfile` (repository root). Docker handles installing OS packages. The previous Python **Build Command** (`pip install ... && python INSTALL_TEXT_PDF_FONTS.py`) is for the old native runtime and is no longer used by Docker; the Dockerfile now does both jobs.
3. Keep your Telegram webhook, `BOT_TOKEN`, `WEBHOOK_SECRET`, Supabase credentials and other Render environment variables exactly as before. The Render domain need not change.
4. The Docker image is substantially larger than a native Python build. The Free plan might hit memory or build limits when converting complex presentations. Test with a **small Word file and two-slide PPTX** before inviting everyone to use the feature. Larger files, videos, complex animations and some fonts can render differently. PPTX animations are not embedded in PDF.
5. If the Render Dashboard does not offer an in-place runtime change for your service, **do not blindly change build commands**; ask for help identifying the available options. This upgrade requires LibreOffice on the running server.

### Security note

The provided `.dockerignore` excludes `.env` and local backups. **Before committing**, check `git ls-files .env` returns no result, and inspect `git status` for tracked secrets. Never push your Bot token, Supabase secret key, or Gemini key. Do not use `git add .` in your project because it contains old backup files.

## Step 3 — Stage only these files and deploy (after tests)

```powershell
git add -- pdf_tools.py office_to_pdf_v713.py TEST_V7_13_OFFICE_PDF.py README_V7_13.md Dockerfile .dockerignore
git diff --cached --check
git --no-pager diff --cached --stat
git ls-files .env
```

Only after reviewing the staged list and confirming **no secrets or unrelated files**:

```powershell
git commit -m "V7.13 real DOCX and PPTX to PDF with LibreOffice"
git push origin main
```

Use **the same Render service**. Wait for **Live**, not merely "Build successful". For Docker, the build should install LibreOffice; there should be no missing `soffice` binary at runtime.

## Step 4 — Telegram end-to-end checklist

1. `/start` → **🎙 Voice & PDF** → **📄 PDF Tools**.
2. Tap **📄 DOCX → PDF**, upload a real `.docx` (ideally one page containing a heading, paragraph, table and an image). The bot should send back a `.pdf`. Open it and compare the layout.
3. Tap **📊 PPTX → PDF**, upload a real `.pptx` containing two slides. The returned PDF should have **two pages**.
4. Test **🔙 PDF Tools**, **❌ Cancel**, **🏠 Main Menu**, and an invalid file.
5. Confirm existing **Merge PDFs**, **Text → PDF**, **Images → PDF**, **Scan Document**, **Crop**, and AI/Study commands remain working.

If the bot says **"Office conversion is not installed on this server"**, your Render service is still running without LibreOffice. If it says **"Conversion failed"**, inspect Render logs and try a simple Word/PowerPoint file first. Do not send private documents to a third-party conversion website.

## Technical overview

- `office_to_pdf_v713.py`: validated OOXML, untrusted filename sanitization, subprocess isolation/timeouts, private Telegram upload handlers.
- `pdf_tools.py`: only imports the new handler, registers it **before generic document handlers**, and adds two keyboard buttons.
- `Dockerfile`: install operating-system LibreOffice and existing Python dependencies in same Render service.
- `TEST_V7_13_OFFICE_PDF.py`: offline flow tests and **real LibreOffice DOCX and PPTX rendering tests** (when installed).
- `.v713_backup/pdf_tools.py.original`: local backup to permit rollback.

No database migration is necessary.
