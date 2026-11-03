# Student Assistant Bot V7.15 — ✂️ Photo/Image Crop

**Independent Image Crop tool**, under **📄 PDF Tools**, as well as the `/cropimage` command. It produces a **cropped JPG/PNG**, not a PDF. Your existing **Images → PDF → Auto Crop** remains as it was; this is a separate feature.

## Simple Telegram workflow

1. Open **📄 PDF Tools → ✂️ Photo/Image Crop** or type `/cropimage` in a **private chat**.
2. Send a **photo** or a **JPG / PNG / WEBP as a document** (the latter retains original resolution in Telegram).
3. Choose **⬜ Square 1:1**, **📷 Portrait 4:5**, **📱 Story 9:16**, **🖼 Landscape 16:9**, **📄 Auto Page Crop**, or **📐 Custom Edges**.
4. The bot sends a **preview**. For **Custom Edges**, send percentages `LEFT TOP RIGHT BOTTOM` — e.g., `10 5 90 95` trims 10% of the width from each side and 5% of the height from the top and bottom. You can preview again with **👁 Preview Crop**.
5. Tap **✅ Save Cropped Image** to receive the cropped image as a document (not compressed again by Telegram). The bot then returns to PDF Tools.
6. **🔄 Change Photo** replaces your current image. **❌ Cancel Crop** or **🔙 PDF Tools** abandons the crop.

**Important:** Preset crops are **centered**, so preview before saving. **Auto Page Crop** is conservative: if the sheet borders cannot be reliably detected, the crop may be unchanged. No perspective correction or on-image drag-to-select is supported. Custom Edges allows exact percentage control instead.

## Requirements

- Your existing **V7.14 Optional Auto Crop** code must already be installed (`image_crop_v714.py`, `image_filters_v713.py`, and the V7.14-modified `pdf_tools.py`).
- **Pillow**, already installed for PDF image features. **No new Python dependency, font installation, SQL, API key, Telegram Bot, or Render service** is needed.

## Windows VS Code PowerShell installation

1. Extract `StudentAssistantBot_V7_15_Photo_Image_Crop_Safe_Patch.zip`.
2. Copy the **`INSTALL_V7_15.py`** file and the complete **`V715_FILES`** folder into your existing `StudentAssistantBot` folder, beside `main.py` and `pdf_tools.py`.
3. Pre-check:

```powershell
Test-Path .\image_crop_v714.py
Test-Path .\image_filters_v713.py
Test-Path .\V715_FILES\photo_crop_v715.py
```

All must print `True`. If not, **do not copy an older pdf_tools.py over your new code**; install V7.14 first or share the current version for a compatible patch.

4. Dry-run:

```powershell
python INSTALL_V7_15.py --dry-run
```

5. If dry-run passes, install and test:

```powershell
python INSTALL_V7_15.py
python -m unittest TEST_V7_15_PHOTO_CROP.py -v
python -m unittest TEST_V7_14_AUTO_CROP.py TEST_V7_15_PHOTO_CROP.py -v
```

If the last command fails because V7.14's test file is not present, run the V7.15 test alone and check the old features manually. Do not deploy after any test failures.

## Safe GitHub push

**Do not** use `git add .` / `git add -A`; you may have `.env`, backups, other uncommitted changes, or ZIP archives in the project folder. Stage just these files:

```powershell
git add -- pdf_tools.py photo_crop_v715.py TEST_V7_15_PHOTO_CROP.py
git diff --cached --check
git diff --cached --name-only
git ls-files .env
```

Ensure the staged list has only those **three files**. `git ls-files .env` must print nothing. If there are other staged files, **review/unstage unrelated files before committing**:

```powershell
git commit -m "V7.15 add standalone photo image crop"
git push origin main
```

Your **existing Render build/start commands remain unchanged**. Wait for Render **Live**, then try `/cropimage` with a real picture.

## Security, privacy, and limits

- Runs locally **inside your Bot's Render process** with Pillow; no external image API or AI service.
- Works only in private chats. The submitted image remains in temporary in-memory session state and is discarded on exit/change/save; user image data is not saved to Supabase. The original Telegram-uploaded image remains subject to Telegram's normal storage policy.
- Limits: **12 MB per upload**, **24 megapixels per photo**, **18 MB maximum generated file**.
- EXIF orientation is applied, EXIF metadata (including GPS) is stripped from the output. PNG alpha is preserved.
- User image documents supported: JPG/JPEG, PNG, WEBP. Preset previews are smaller JPGs, but final output preserves cropped resolution.
- `main.py`, broadcast modules, Gemini/Cloudflare, Study Materials, old PDF filter/auto crop code, Supabase, Render and `.env` are unchanged.
- Offline tests validate crop ratios, Unicode button flows, private-chat handling, preview/download, user state isolation, file limits, EXIF, transparent PNG, and old Images → PDF routing. **Live Telegram + Render testing still required**.

## Rollback

If the installed `pdf_tools.py` and newly created files haven't been edited since installation:

```powershell
python INSTALL_V7_15.py --rollback
```

Rollback checks hashes first. It refuses to delete any file that has changed.
