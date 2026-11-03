# Student Assistant Bot V7.14 — Optional Auto Crop for Images → PDF

## Behavior (no existing feature removed)

Inside **📄 PDF Tools → 🖼 Images → PDF**, an additional **✂️ Crop Mode** button lets you choose:

- **📐 Original (Default)** — **the default**. Keep the full image exactly as V7.13 did, with no cropping. Your filter also defaults to **🌈 Original**.
- **✂️ Auto Crop** — tries to detect the borders of a pale rectangular page on a contrasting desk/background. The desk edges are removed for the PDF. If detection is uncertain, the original image area is retained to avoid cutting off handwriting.

The crop choice and filter choice are **independent**: for example, Auto Crop + Clean Scan. Use **👁 Preview Last** to check the result before generating the PDF. The same setting applies to all images in that PDF. The original uploaded bytes are never overwritten. Choosing Images → PDF again resets to Original/Original.

**Limits:** This is a conservative, rectangular bounding-box crop (Pillow only), not a perspective-correction scanner. It does not straighten tilted papers, remove fingers, or guarantee document detection on light-colored desks. If edges are not obvious, it will keep the full picture. Preview each image, especially handwriting near the paper edge. For tilted/complex backgrounds, manual photo cropping may work better.

## Requirements

- Your existing StudentAssistantBot project with **V7.13 Image Filters already installed**, including `image_filters_v713.py` and `TEST_V7_13_IMAGE_FILTERS.py`.
- Existing Pillow/Python packages; **no new dependencies**, SQL, API keys, Render service, or fonts are required.

## Windows VS Code PowerShell installation

1. Extract `StudentAssistantBot_V7_14_Optional_Auto_Crop_Safe_Patch.zip`.
2. Copy `INSTALL_V7_14.py` and the complete `V714_FILES` folder into `C:\Users\Pros\Desktop\StudentAssistantBot` beside `main.py`.
3. Check the prerequisite files:

```powershell
Test-Path .\image_filters_v713.py
Test-Path .\TEST_V7_13_IMAGE_FILTERS.py
Test-Path .\V714_FILES\image_crop_v714.py
```

All three should print `True`.

4. Dry-run (no changes):

```powershell
python INSTALL_V7_14.py --dry-run
```

**If the installer stops because `pdf_tools.py` differs, stop.** Send the output. Do not overwrite current files with an older ZIP.

5. Install, then test:

```powershell
python INSTALL_V7_14.py
python -m unittest TEST_V7_13_IMAGE_FILTERS.py TEST_V7_14_AUTO_CROP.py -v
```

You can additionally run your existing V7.11/V7.12 suites if present. The V7.14 installer leaves their source files unchanged.

## Safe GitHub push, after tests pass

Your project may contain `.env`, backups, and unrelated local changes. **Do not use `git add .` or `git add -A`.** Stage only the four runtime/test files:

```powershell
git add -- pdf_tools.py image_filters_v713.py image_crop_v714.py TEST_V7_14_AUTO_CROP.py
git diff --cached --check
git --no-pager diff --cached --stat
git diff --cached --name-only
git ls-files .env
```

Review the staged file list; **if unrelated files are staged, unstage them before committing**. `git ls-files .env` must print nothing. If the staged changes contain ONLY the four intended files:

```powershell
git commit -m "V7.14 add optional auto crop to Images to PDF"
git push origin main
```

Keep your existing Render Build Command and Start Command. Wait for Render **Live** deployment; this installer does not deploy your bot.

## Live Telegram test

1. Open `📄 PDF Tools → 🖼 Images → PDF`. It starts with **Original**, no cropping.
2. Upload a photo of notes with clearly visible paper and table edges.
3. Press `✂️ Crop Mode → ✂️ Auto Crop`.
4. Press `👁 Preview Last`. Ensure no handwriting is cut off.
5. Press `✅ Create PDF`. Confirm the desk edges are removed where identifiable.
6. Start again and leave the default **Original** selected. Confirm the whole image remains.
7. Confirm other PDF features (Merge, Extract, Text → PDF, Rotate, Protect) still work.

## Rollback

The installer backs up the two original files in `.v714_backup/`. If the installed source files have **not** been edited since installation:

```powershell
python INSTALL_V7_14.py --rollback
```

Rollback refuses to overwrite source changes or delete modified files.

## Scope / privacy

- Only two existing files are changed: `pdf_tools.py` and `image_filters_v713.py`.
- Two new files are added: `image_crop_v714.py` and `TEST_V7_14_AUTO_CROP.py`.
- No main.py, broadcast, AI, translation, Supabase, Render, `.env`, credentials, or other PDF tools are modified.
- No third-party image processing service or API calls. Photos remain in process memory until the PDF session ends.
- Tested offline with V7.13 tests and V7.14 crop/flow tests, plus installer dry-run/reinstall/rollback checks. Live Render behavior must still be checked.
