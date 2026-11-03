# Student Assistant Telegram Bot — V7.16 Document Scanner

Adds a private-chat **📸 Scan Document** button under the existing **📄 PDF Tools**, and the `/scan` command. **This is not OCR:** it preserves handwritten Arabic, Tamil, Sinhala and English visually in a raster JPG or A4 PDF. The image is **not converted to searchable text**.

## User experience

1. In Telegram, open **📄 PDF Tools → 📸 Scan Document**, or send `/scan`.
2. Send one photo of a page, or JPG/PNG/WEBP **as a document** for full Telegram image quality.
3. Bot detects four corners and applies perspective correction with **2.5% outward margin** around the detected border, to reduce clipping handwriting at the edges. Preview appears automatically.
4. If edges cannot be confidently found, bot sends the **uncropped original** preview and tells you the reason rather than guessing and cutting off notes. Tap **📐 Adjust Corners** to enter positions manually in percentages (see below), then a new preview appears. **🔄 Auto Detect Again** and **↩️ Original Photo** are also available.
5. Choose **🖼 Save as Image** (high-quality JPG) or **📄 Save as PDF** (one-page A4, portrait or landscape based on source). Telegram sends a file/document in the same private chat. **🔁 Change Photo** starts over.

### Manual perspective correction

`📐 Adjust Corners` expects eight numbers as percentages of the original photo's dimensions:

```
TL-x TL-y TR-x TR-y BR-x BR-y BL-x BL-y
5 5 95 5 95 95 5 95
```

- TL = top left; TR = top right; BR = bottom right; BL = bottom left.
- `0 0` is the top-left of the **original photo**, `100 100` is bottom-right.
- Allow extra margin around handwritten ink. Adjusted coordinates are verified to reject crossed or near-zero shapes.
- Telegram doesn't provide an interactive crop handle within this bot. Enter coordinates as percentages; preview helps refine them.

## Compatibility and security

- Supports the existing **V7.11 through V7.15 PDF Tools** layouts, with or without V7.15 Photo/Image Crop. The installer **does not replace** `pdf_tools.py` with an old version: it inserts four small wiring changes and an isolated handler block. It checks strict anchors and syntax before writing.
- Does **not** edit `main.py`, existing crop algorithms, Navigation, Gemini/Cloudflare AI, Broadcast, Supabase SQL/data, `.env`, Render settings or Telegram tokens.
- One active scanned photo per private chat in the running bot process. No photos retained in Supabase or written as files on disk. The Telegram-hosted original still follows Telegram's storage policies.
- Image inputs limited to 12 MB, 24 megapixels; output limited to 18 MB. EXIF orientation is corrected, output EXIF/GPS metadata omitted; preview limited to 1050px. Export retains safe margins.
- Entire image processing is local to your Render process; **no paid scanning service/API key**.
- Auto-detection is best on a flat page, strong contrast, all four corners visible, and bright even lighting. If uncertain it falls back to original, not an aggressive crop. Results should be reviewed before saving.

## 1. Install on your existing Windows project

**First create a Git commit or backup of the existing project.** Then download/extract `StudentAssistantBot_V7_16_Document_Scanner_Safe_Patch.zip` and copy `INSTALL_V7_16.py` and the **entire `V716_FILES` folder** into `C:\Users\Pros\Desktop\StudentAssistantBot` (beside `main.py` and `pdf_tools.py`).

In VS Code PowerShell **inside the StudentAssistantBot folder**:

```powershell
Test-Path .\main.py
Test-Path .\pdf_tools.py
Test-Path .\V716_FILES\scan_document_v716.py
python INSTALL_V7_16.py --dry-run
```

All `Test-Path` checks must be `True` and dry-run must say **Dry-run OK**. If it says "Cannot safely patch" or "Unsupported PDF Tools layout", **stop** and send the output—don't replace your newer `pdf_tools.py` manually.

Then:

```powershell
python INSTALL_V7_16.py
python -m pip install -r requirements.txt
python -m unittest TEST_V7_16_SCAN_DOCUMENT.py -v
python -m py_compile pdf_tools.py scan_document_v716.py
```

The new requirement `opencv-python-headless>=4.10,<5` is appended to the **existing** `requirements.txt` without deleting the previous dependencies (`python-dotenv`, Supabase, fpdf2, etc.). The pip installation downloads a standard dependency. Keep internet access for local installation and Render builds.

If you have `TEST_V7_15_PHOTO_CROP.py` available, also run:

```powershell
python -m unittest TEST_V7_15_PHOTO_CROP.py TEST_V7_16_SCAN_DOCUMENT.py -v
```

**Expected:** 21 V7.16 offline tests pass; 49 combined V7.15 + V7.16 regression tests passed during package preparation. Live Telegram and Render photo tests still required.

## 2. GitHub push carefully

Check no local tests fail, then stage only the four files needed in production + test:

```powershell
git add -- pdf_tools.py requirements.txt scan_document_v716.py TEST_V7_16_SCAN_DOCUMENT.py
git diff --cached --check
git diff --cached --name-only
git ls-files .env
```

Review the staged list. `git ls-files .env` must print **nothing**. Do not stage `.env`, `.v716_backup`, temporary ZIPs, other uncommitted files. Avoid `git add .`. If other files were previously staged, unstage unrelated changes before committing.

```powershell
git commit -m "V7.16 add offline perspective document scanner"
git push origin main
```

Wait until your **existing Render service** deployment is **Live**. Your existing Build Command can stay `pip install -r requirements.txt && python INSTALL_TEXT_PDF_FONTS.py`, which installs OpenCV as part of requirements. Your existing Start Command also stays unchanged. Do **not** create a new bot/Render service or configure a paid API key.

## 3. Live acceptance checks

In a **private Telegram chat**:

- `/scan` → send a clear paper photo with handwritten notes → automatic preview → Save as Image. Inspect page edges and original script.
- `/scan` → another photo → `📐 Adjust Corners` → send `5 5 95 5 95 95 5 95` → preview → Save as PDF. Open and inspect the actual A4 page.
- `/scan` → test blurry background (uncertain edge detection) → ensure it does not chop the page.
- Confirm `/cropimage`, `🖼 Images → PDF`, `/textpdf`, `/broadcastall`, `/ai` and `/start` still work.

## Rollback

The installer writes original `pdf_tools.py` and `requirements.txt` to `.v716_backup` (not for Git). If you have **not edited** the installed files since installing, you can undo it locally:

```powershell
python INSTALL_V7_16.py --rollback
```

It checks all file hashes and **refuses to overwrite later edits**. An offline dry-run never changes source files. This installer does not push to GitHub or deploy Render.
