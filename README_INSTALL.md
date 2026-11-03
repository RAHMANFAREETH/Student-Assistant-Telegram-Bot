# V7.17 — permissively licensed PDF engine update

Your **five V7.17 PDF menu features are already installed**. This update changes only the PDF processing engine and dependencies. No reinstallation of menus, no new Render service, no Dockerfile changes, and no changes to Office, OCR or AI modules.

## Why

The original V7.17 package uses PyMuPDF, which is AGPLv3 or commercial licensed. This replacement uses `pypdf` (BSD-3-Clause), `pypdfium2` (Apache-2.0/BSD-3-Clause, with bundled PDFium third-party notices), and `reportlab` (BSD-style license). Retain and comply with dependency notices when distributing binaries; these dependencies do not automatically license your entire bot under AGPL. See project websites for full terms.

## Install safely in PowerShell

Your working folder was `C:\Users\Pros\Desktop\StudentAssistantBot`. **Before continuing, back up your project** and keep your current four staged files until you have tested replacements.

1. Extract the new ZIP. Copy these three files into the bot project folder, overwriting only the *existing V7.17* copies of the first two files:
   - `advanced_pdf_v717.py`
   - `TEST_V7_17_ADVANCED_PDF.py`
   - `UPDATE_V717_PERMISSIVE.py`

   **Do not copy a new `pdf_tools.py` or `Dockerfile`.** Your existing menu integration remains intact.

2. In PowerShell inside the project folder:

   ```powershell
   python UPDATE_V717_PERMISSIVE.py --check
   python UPDATE_V717_PERMISSIVE.py --apply
   python -m pip install "pypdf>=5,<7" "pypdfium2>=4,<6" "reportlab>=4,<6"
   python -m unittest TEST_V7_17_ADVANCED_PDF -q
   python -m unittest TEST_V7_13_OFFICE_PDF TEST_V7_15_PHOTO_CROP TEST_V7_16_DOCUMENT_SCANNER -q
   python -m unittest TEST_V7_14_ENGINE_COMPAT TEST_V7_14_AUTO_CROP TEST_V7_13_IMAGE_FILTERS -q
   ```

3. Confirm dependency changes and stage **only four files**:

   ```powershell
   git add -- advanced_pdf_v717.py TEST_V7_17_ADVANCED_PDF.py requirements.txt pdf_tools.py
   git diff --cached --name-only
   git diff --cached --check
   git diff --cached --stat
   git diff --cached -- requirements.txt
   ```

   Expected: `requirements.txt` contains `pypdf`, `pypdfium2`, `reportlab` and **not** `PyMuPDF`; the staged advanced module must not import `pymupdf`. Don't use `git add .` because there are many unrelated local backups. If anything is unexpected or tests fail, stop before committing.

4. Once all tests pass and the staged diff looks correct, commit and push:

   ```powershell
   git commit -m "Add V7.17 advanced PDF tools with permissive engine"
   git push origin main
   ```

   Existing Render Docker service should deploy the new commit. Check build logs, then test all five new tools on Telegram with small sample PDFs. **No live deployment was performed by this ZIP.**

## Important limitations

- **Compress PDF:** Light is lossless reserialization; Balanced/Strong attempt image recompression. Some PDFs will not shrink, and original bytes are returned when they are already smaller. Very complex PDFs may not support image rewriting.
- **PDF → Word:** Extracts selectable text into editable paragraphs; it does **not** reconstruct original complex formatting, scanned text, tables or pictures. OCR is a separate step.
- **PDF → Images:** Rasterized at 120 DPI; up to 20 selected pages exported as ZIP.
- **Organize PDF:** Supports reorder, omit, repeat and page ranges.
- **Add Watermark:** English watermarks remain searchable; multilingual ones are rendered using installed Noto fonts as image overlays. Visually verify Tamil, Sinhala and Arabic for your own PDFs.
- **Security/resource limits:** Same 10 MB upload, 50 page and 18 MB result limits and single PDF worker as original package. This is not a sandboxed malware-safe document converter.
- **Tests:** 28 offline tests passed here; two menu integration tests skip when run outside the installed project. Run the commands above for the user's exact environment before pushing.

## Rollback

If you do not like the changes and have not committed, restore the two V7.17 engine/test files from copies made **before overwriting**, and `requirements.txt` from `requirements.txt.pre_perm_*.bak`. Do not use `git restore .` or `git reset --hard` because the project has unrelated work.
