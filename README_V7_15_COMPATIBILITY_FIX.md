# V7.15 Photo/Image Crop — safe installer + test compatibility fix

## Why your previous attempt failed

The original installer intentionally refused to patch `pdf_tools.py` because `photo_crop_v715.py` already existed. Therefore the Photo Crop handlers were not registered and tests reported `KeyError: 100`, no preview/download, etc. Separately, the old test read `.rows`, whereas newer `pyTelegramBotAPI` uses `.keyboard`.

## Install on Windows PowerShell

**Do not delete `photo_crop_v715.py`, `pdf_tools.py`, `.env`, or any backup.**

1. Extract this ZIP.
2. Copy `INSTALL_V7_15.py` into your existing `StudentAssistantBot/` folder, replacing *only the old installer*.
3. Copy `V715_FILES/TEST_V7_15_PHOTO_CROP.py` into `StudentAssistantBot/V715_FILES/`, replacing *only the old test template*.
4. Ensure the original `V715_FILES/PATCH_V7_15_CORE.py`, `V715_FILES/CROP_HANDLERS_V715.txt`, and `V715_FILES/photo_crop_v715.py` are still present. This small ZIP contains only the compatibility corrections, not the original V7.15 feature files.
5. From your project root:

```powershell
python INSTALL_V7_15.py --dry-run
```

The expected plan is `photo_crop_v715.py: KEEP` if your existing helper is the same as the bundled release. The test file will be safely backed up and replaced if necessary.

**If it says the helper DIFFERS, stop and send the output; do not overwrite it blindly.** Only after reviewing the existing helper and intentionally approving replacement, you can run `python INSTALL_V7_15.py --dry-run --replace-existing` then `python INSTALL_V7_15.py --replace-existing`.

6. If the dry-run passes:

```powershell
python INSTALL_V7_15.py
python -m unittest TEST_V7_15_PHOTO_CROP.py -v
python -m unittest TEST_V7_14_AUTO_CROP.py -v
```

You should see `Ran 28 tests ... OK` for V7.15. The `PyPDF2` deprecation warning is unrelated.

## Safety and rollback

- `pdf_tools.py` is backed up under `.v715_backup/`.
- A pre-existing test or helper file that needs replacement is separately backed up under `.v715_backup/originals/`.
- The installer refuses to overwrite an *unrecognized* helper unless `--replace-existing` is explicitly specified.
- The installer does not touch `main.py`, Supabase, Render, AI, `.env`, or Git.
- If you need rollback after installation and before manually editing these files:

```powershell
python INSTALL_V7_15.py --rollback
```

- After tests pass, inspect `git status --short` and stage **only** the actual feature files you intend to deploy. Do not run `git add .`; do not upload backups or API keys.

## Testing note

The fix was tested in a local simulated V7.14 project, including fresh install, existing matching helper, explicit replacement with rollback, and 28 Photo Crop tests. This is not a claim that your Render deployment has been tested.
