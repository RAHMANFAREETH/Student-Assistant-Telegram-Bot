# Student Assistant Bot V7.13 — DOCX/PPTX → PDF + Optional Image Filters

This is an installable patch **for the existing bot and existing Render web service**, not a replacement bot or a new service. It adds two office converters and the uploaded local image filter enhancements to the existing PDF Tools module.

## Important prerequisites

- Your existing project already runs **V7.11 Text → PDF**; `main.py`, `pdf_tools.py`, `text_pdf_v711.py`, and `INSTALL_TEXT_PDF_FONTS.py` should be at the project root.
- Your existing `requirements.txt` must retain **all older Bot dependencies** (not just the new `fpdf2` and `uharfbuzz`). In particular, verify `python-dotenv` and your existing Supabase, Word/PDF and translation dependencies are present.
- `Dockerfile` and `.dockerignore` are needed for Docker deployment. No secrets, Telegram token, or custom fonts are bundled.
- A **native Python Render service will not convert DOCX/PPTX** because it lacks LibreOffice. A switch to Docker on the **same Render service** is required.

## 1. Install locally in VS Code / PowerShell

Extract the ZIP, copy `INSTALL_V7_13.py` and the **entire `V713_FILES` folder** beside your existing `main.py` and `pdf_tools.py`:

```powershell
python INSTALL_V7_13.py --dry-run
```

Only if it reports `DRY RUN OK`:

```powershell
python INSTALL_V7_13.py
python -m py_compile pdf_tools.py office_to_pdf_v713.py image_filters_v713.py
python -m unittest TEST_V7_13_OFFICE_PDF.py TEST_V7_13_IMAGE_FILTERS.py -v
python -m unittest TEST_V7_11_TEXT_PDF.py -v
```

The office conversion suite has two real LibreOffice tests. If LibreOffice isn't installed on Windows, those real conversion tests will **SKIP**, not PASS; you can install LibreOffice (https://www.libreoffice.org/download/download-libreoffice/) for local end-to-end testing. The test fixtures use `python-docx`, `python-pptx`, and optionally `pypdf` (install locally if missing). `PyPDF2` is still needed by your existing `pdf_tools.py` unless that file has been migrated.

If the installer reports an unexpected `pdf_tools.py` layout, stop and share the error; it will not overwrite a custom file it doesn't recognize. If you already have a different `Dockerfile` or `.dockerignore`, it likewise stops rather than replacing it.

To **rollback** only this patch (if those files haven't been edited since installation):

```powershell
python INSTALL_V7_13.py --rollback
```

Your `main.py`, AI, broadcasts, Supabase, and `.env` are never edited by this installer.

## 2. Git staging — review before push

```powershell
git status --short
git check-ignore .env
git ls-files .env
git ls-files INSTALL_TEXT_PDF_FONTS.py
```

`git ls-files .env` must be empty. `INSTALL_TEXT_PDF_FONTS.py` should be tracked so it is available in Docker. If it isn't tracked, add that script only after reviewing it and ensuring it has no secrets.

Stage **only** the production files and tests:

```powershell
git add -- pdf_tools.py office_to_pdf_v713.py image_filters_v713.py
git add -- TEST_V7_13_OFFICE_PDF.py TEST_V7_13_IMAGE_FILTERS.py
git add -- Dockerfile .dockerignore README_V7_13.md
git diff --cached --check
git --no-pager diff --cached --stat
git diff --cached --name-only
```

Review staged files and make sure no unrelated deletions or secret files are staged. Then:

```powershell
git commit -m "V7.13 add DOCX and PPTX to PDF conversion"
git push origin main
```

Do **not** use `git add .` in your project: old backups and temporary files may be present.

## 3. Convert your **existing** Render web service to Docker

Render officially supports changing a service's runtime without creating a new service:
https://render.com/docs/native-runtimes#changing-a-services-runtime

1. Open **Render Dashboard → your current Student Assistant Bot web service → Settings**.
2. Under **Build**, find **Source**, click **Edit**, keep the same Git repository and `main` branch, and change **Runtime** from `Python` to `Docker`.
3. Use **Dockerfile path `./Dockerfile`** (at the repo root) and deploy. Keep all Render environment variables: `BOT_TOKEN`, `WEBHOOK_SECRET`, Supabase keys, Cloudflare, Gemini etc. You do not need to make a new service or API keys.
4. Docker uses the `Dockerfile` to install **LibreOffice Writer + Impress**, Python dependencies, and V7.11 Unicode fonts, then runs `gunicorn main:app` on the existing port. Do not paste the old native Python build command into a Docker command. Docker uses the `CMD` in `Dockerfile`.
5. Wait until Render reports **Live**, not merely **Build successful**. Check Logs for startup/import errors. LibreOffice makes the image larger and may consume too much memory on a Free instance for big files.

Dockerfile `COPY . .` copies the repository context. `.dockerignore` excludes `.env` and backups, but you must still verify no secrets are tracked and staged; do not upload private documents or API keys in the repository.

**Rollback deployment** if necessary: your old Git commit remains available for redeploy, and Render's runtime can be switched back to Python in the same Settings → Build → Source → Edit screen. Do not run the new Office conversion buttons under native Python; they require LibreOffice.

## 4. Test in Telegram after the Docker deployment is Live

- `/docxpdf` → send a small `.docx` file containing a heading/table → receive an actual PDF attachment.
- `/pptxpdf` → send a simple `.pptx` with two slides → receive a **two-page** PDF.
- **PDF Tools** menu → **📄 DOCX → PDF** and **📊 PPTX → PDF** buttons.
- **Images → PDF** → **🎨 Choose Filter**, **👁 Preview Last**, **🗑 Remove Last**; then **✅ Create PDF**.
- Recheck `/textpdf`, Merge PDFs, `/ai`, Study Materials, and `/broadcastall`.

Office converter limits: private chat only; one active conversion; input max **12 MB**, output max **18 MB**; **100 seconds** timeout. LibreOffice tries to preserve Word and PowerPoint formatting, but complex animations, uncommon fonts, embedded objects and advanced layouts may differ. Old `.doc` / `.ppt` files are **not** supported by these commands. PDF conversion is local to your server, not a third-party upload service.

If there is no response: check whether the new handlers were installed into `pdf_tools.py` and whether the latest Docker deployment is Live. If it says `Office conversion is not installed on this server`, the runtime or Docker deployment was not completed.

## Notes on verification

The installation has been simulated against the **V7.11 PDF Tools file** from your previous upgrade, not against your current local file, which can contain newer custom changes. The package was tested with **48 new V7.13 tests** (including real LibreOffice conversions) and **21 earlier V7.11 regression tests** in the preparation environment. Docker image build and live Render Telegram conversion have not been executed in your account.
