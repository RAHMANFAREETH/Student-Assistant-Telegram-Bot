# V7.14 Image → PDF compatibility repair

## What the uploaded test log establishes

V7.14 Telegram handlers pass `auto_crop=` into `make_preview` and `images_to_pdf`, but the installed `image_filters_v713.py` does not accept this keyword. This triggers `TypeError`, prevents sending previews/PDFs, and causes cascading failures in both V7.13 and V7.14 tests. The `PyPDF2 is deprecated` message is just a warning and does not explain the failures.

This patch is **engine-only**: it updates the V7.13 image-processing functions to accept V7.14's optional `auto_crop=False` argument and to use `image_crop_v714.auto_crop_image` when enabled. Legacy calls and original output defaults continue to work. The installer refuses unexpected source layouts, takes a backup, and supports rollback. It does not change `pdf_tools.py`, `main.py`, Gemini, Cloudflare, SQL, or Render settings.

## How to install (Windows PowerShell)

1. Extract the ZIP. Copy `INSTALL_V7_14_ENGINE_REPAIR.py` and `TEST_V7_14_ENGINE_COMPAT.py` directly into your existing `C:\Users\Pros\Desktop\StudentAssistantBot` folder. The previously installed `image_filters_v713.py`, `image_crop_v714.py`, and `pdf_tools.py` must also exist there.

2. Before changing anything:

```powershell
python INSTALL_V7_14_ENGINE_REPAIR.py --dry-run
```

3. Only after `DRY RUN OK`:

```powershell
python INSTALL_V7_14_ENGINE_REPAIR.py
python -m unittest TEST_V7_14_ENGINE_COMPAT.py TEST_V7_13_IMAGE_FILTERS.py TEST_V7_14_AUTO_CROP.py -v
```

4. If **all tests pass**, check Git status and stage **only the intended files**:

```powershell
git status --short
git add image_filters_v713.py TEST_V7_14_ENGINE_COMPAT.py
git diff --cached --check
git --no-pager diff --cached --stat
```

Review any other previously staged changes before `git commit` / `git push`. Do not run `git add .` or commit your `.env` or backup directories. If this issue occurs in local tests only and the ZIP is not installed on Render yet, do not push until the rest of the V7.14 deployment is ready.

5. To reverse **only this repair** (not V7.14 itself):

```powershell
python INSTALL_V7_14_ENGINE_REPAIR.py --rollback
```

The backup is kept in `.v714_engine_repair_backup/` and is **not** for GitHub.

## If it stops

Send the full `DRY RUN` output and your local `image_filters_v713.py` for precise review. Do not overwrite that file with an older V7.13 copy; doing so would remove later fixes.
