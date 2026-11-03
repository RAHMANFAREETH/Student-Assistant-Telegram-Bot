# V7.16 Document Scanner — Existing-File Installer Fix

**This fixes an installation guard, not the scanner engine.** Your error `A scanner module/test file already exists` occurs when `scan_document_v716.py` and/or `TEST_V7_16_SCAN_DOCUMENT.py` were copied directly into your bot folder before running the original installer. In that state, the scanner is not yet wired into `pdf_tools.py`, so bot-flow tests fail even though image processing tests pass.

## On Windows / VS Code PowerShell

1. Keep a backup or Git commit of the existing project before installing.
2. From this ZIP, copy **only `INSTALL_V7_16.py`** into `C:\Users\Pros\Desktop\StudentAssistantBot` to replace the previous installer. Keep your existing `V716_FILES` folder unchanged. Do **not** replace `pdf_tools.py`, `main.py`, or your existing scanner module/test file manually.
3. Run from your bot project folder:

```powershell
python INSTALL_V7_16.py --dry-run
```

Expected: `scanner files already present and matching` and `Dry-run OK`. Only proceed on success:

```powershell
python INSTALL_V7_16.py
python -m pip install -r requirements.txt
python -m unittest TEST_V7_16_SCAN_DOCUMENT.py -v
python -m py_compile pdf_tools.py scan_document_v716.py
```

Expected: `V7.16 installed`, then **21 tests**, `OK`. On the first install `requirements.txt` may add `opencv-python-headless>=4.10,<5`; pip may replace your manually installed version 5.0 with a compatible 4.x version. This is normal.

If the installer reports a scanner file **differs from the packaged version**, or **Unsupported PDF Tools layout**, stop. Do not delete or rename anything: provide the installer output and your current `pdf_tools.py` for an exact compatible fix.

## What changed in the installer?

The installer now checks any existing scanner/test file against the original packaged content (with Windows CRLF normalization). If identical, it **reuses the existing file** and installs only missing PDF Tools wiring and the OpenCV requirement. If different, it **refuses to overwrite it**. A rollback restores `pdf_tools.py` and `requirements.txt` while preserving scanner files that existed before this installation.

## After tests pass (before deployment)

```powershell
git status --short
git diff --check
git ls-files .env
```

`.env` must not be tracked. Stage only the intended production changes when ready:

```powershell
git add -- pdf_tools.py requirements.txt scan_document_v716.py TEST_V7_16_SCAN_DOCUMENT.py
git diff --cached --check
git --no-pager diff --cached --stat
```

Only after reviewing and all tests pass: commit/push, then wait for Render `Live`. Do not stage `.v716_backup/`, `V716_FILES/`, `.env` or local installers. Existing Render build/start commands stay unchanged.

## Offline verification performed

- Existing scanner/test files: dry run, installation, 21 offline tests PASS, idempotent install, rollback retaining pre-existing files.
- New project without scanner files: installation, idempotence and rollback work.
- Pre-existing edited scanner file: safely rejected with **no changes**.

**This patch was tested with the packaged V7.15-compatible PDF Tools layout. Your exact Windows project was not directly accessible; its dry run is the final compatibility check.**
