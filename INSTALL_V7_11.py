"""Safe, local-only installer for Text -> PDF V7.11.

Run from the existing StudentAssistantBot project folder:
    python INSTALL_V7_11.py --dry-run
    python INSTALL_V7_11.py
    python INSTALL_V7_11.py --rollback

No network, API calls, database changes, or Render deployment occur here.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
BUNDLE = Path(__file__).resolve().parent / "V711_FILES"
BACKUP = ROOT / ".v711_backup"
ORIGINAL_PDF_SHA256 = "b474424d4003f6a5cb4440e6f95f0dbc4de5ae43ef612bc108724327f70d8634"
UPDATED_FILES = ("pdf_tools.py", "navigation.py", "requirements.txt", ".gitignore")
NEW_FILES = ("text_pdf_v711.py", "INSTALL_TEXT_PDF_FONTS.py", "TEST_V7_11_TEXT_PDF.py")
MARKER = "# V7.11 Unicode Text -> PDF"


def _normalised_sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def _verify_project():
    for name in ("pdf_tools.py", "navigation.py", "requirements.txt", "main.py"):
        if not (ROOT / name).is_file():
            raise RuntimeError(f"Missing {name}. Run inside the StudentAssistantBot project folder.")
    if not BUNDLE.is_dir():
        raise RuntimeError("V711_FILES is missing. Copy it beside INSTALL_V7_11.py.")


def _changes():
    _verify_project()
    planned = {}
    current_pdf = (ROOT / "pdf_tools.py").read_bytes()
    already = b"from text_pdf_v711 import" in current_pdf
    if already:
        if _normalised_sha(current_pdf) != _normalised_sha((BUNDLE / "pdf_tools.py").read_bytes()):
            raise RuntimeError(
                "Text PDF feature already exists but pdf_tools.py has other local edits. "
                "Installer will not overwrite them; compare your version manually."
            )
    elif _normalised_sha(current_pdf) != ORIGINAL_PDF_SHA256:
        raise RuntimeError(
            "Your pdf_tools.py differs from the reviewed V7.9 source. "
            "No files changed. Share the current pdf_tools.py for a compatible patch."
        )
    planned["pdf_tools.py"] = (BUNDLE / "pdf_tools.py").read_bytes()

    nav = (ROOT / "navigation.py").read_text(encoding="utf-8-sig")
    if 'GLOBAL_BUTTONS.add("📝 Text → PDF")' not in nav:
        anchor = "NAVIGATION_BUTTONS = {"
        if anchor not in nav:
            raise RuntimeError("navigation.py structure changed; refusing to alter it.")
        nav = nav.replace(anchor, 'GLOBAL_BUTTONS.add("📝 Text → PDF")\n\n\n' + anchor, 1)
    planned["navigation.py"] = nav.encode("utf-8")

    req = (ROOT / "requirements.txt").read_text(encoding="utf-8-sig")
    if "fpdf2" not in req.lower():
        req = req.rstrip() + '\n\n' + MARKER + '\nfpdf2>=2.8.5,<3\n'
    if "uharfbuzz" not in req.lower():
        req = req.rstrip() + '\nuharfbuzz>=0.40,<1\n'
    planned["requirements.txt"] = req.encode("utf-8")

    ig_path = ROOT / ".gitignore"
    ignore = ig_path.read_text(encoding="utf-8-sig") if ig_path.exists() else ""
    for item in ("pdf_fonts/", ".v711_backup/"):
        if item not in ignore.splitlines():
            ignore = ignore.rstrip() + '\n' + item + '\n'
    planned[".gitignore"] = ignore.encode("utf-8")

    for name in NEW_FILES:
        if (ROOT / name).exists() and (ROOT / name).read_bytes() != (BUNDLE / name).read_bytes():
            raise RuntimeError(f"{name} already exists with different content. Not overwriting.")
        planned[name] = (BUNDLE / name).read_bytes()

    for name, payload in planned.items():
        if name.endswith(".py"):
            ast.parse(payload.decode("utf-8"), filename=name)
    return planned


def _install(dry_run):
    planned = _changes()
    changes = [name for name, payload in planned.items()
               if not (ROOT / name).exists() or (ROOT / name).read_bytes() != payload]
    if not changes:
        print("V7.11 already installed. No changes required.")
        return
    print("V7.11 files to update:", ", ".join(changes))
    if dry_run:
        print("DRY RUN PASSED: no project files were modified.")
        return
    if BACKUP.exists():
        raise RuntimeError("Existing .v711_backup detected. Use --rollback or inspect it first.")
    BACKUP.mkdir()
    original = {}
    try:
        for name in changes:
            p = ROOT / name
            if p.exists():
                original[name] = True
                shutil.copy2(p, BACKUP / name)
            else:
                original[name] = False
        (BACKUP / "manifest.json").write_text(
            json.dumps({"files": original,
                        "installed_shas": {n: _normalised_sha(planned[n]) for n in changes}}, indent=2),
            encoding="utf-8",
        )
        for name in changes:
            temp = ROOT / (name + ".v711_tmp")
            temp.write_bytes(planned[name])
            temp.replace(ROOT / name)
        print("V7.11 installed. Backups are in .v711_backup/.")
    except Exception:
        _rollback(silent=True)
        raise


def _rollback(silent=False):
    manifest_path = BACKUP / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("No V7.11 backup found; nothing to roll back.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, existed in manifest["files"].items():
        p = ROOT / name
        if p.exists() and _normalised_sha(p.read_bytes()) != manifest["installed_shas"][name]:
            raise RuntimeError(f"{name} changed since installation; rollback paused to preserve edits.")
        if existed:
            shutil.copy2(BACKUP / name, p)
        else:
            p.unlink(missing_ok=True)
    shutil.rmtree(BACKUP)
    if not silent:
        print("V7.11 rollback complete. Original files restored.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--dry-run", action="store_true")
    actions.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    try:
        if args.rollback:
            _rollback()
        else:
            _install(dry_run=args.dry_run)
    except Exception as exc:
        print("INSTALL ERROR:", exc, file=sys.stderr)
        sys.exit(1)
