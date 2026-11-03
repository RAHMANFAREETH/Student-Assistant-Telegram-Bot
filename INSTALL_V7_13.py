"""V7.13 safe installer: DOCX/PPTX -> PDF (existing Student Assistant Bot).

Usage from the original StudentAssistantBot project directory:
    python INSTALL_V7_13.py --dry-run
    python INSTALL_V7_13.py
    python INSTALL_V7_13.py --rollback

No internet, API, Supabase, or Render operations. Does not overwrite main.py.
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
BUNDLE = Path(__file__).resolve().parent / "V713_FILES"
BACKUP = ROOT / ".v713_backup"
NEW_FILES = ("office_pdf_v713.py", "TEST_V7_13_OFFICE_PDF.py")
MARKER = "# V7.13 DOCX/PPTX -> PDF"
BUTTON_DOCX = "📄 DOCX → PDF"
BUTTON_PPTX = "📊 PPTX → PDF"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def _file(name: str) -> Path:
    return ROOT / name


def _plans() -> dict[str, bytes]:
    for name in ("main.py", "pdf_tools.py", "navigation.py", "requirements.txt", "text_pdf_v711.py"):
        if not _file(name).is_file():
            raise RuntimeError(f"Missing {name}. Install V7.11 before V7.13 (same existing project).")
    if not BUNDLE.is_dir():
        raise RuntimeError("V713_FILES is missing beside INSTALL_V7_13.py.")
    plans = {}
    pdf = _file("pdf_tools.py").read_text(encoding="utf-8-sig")
    if "from text_pdf_v711 import" not in pdf:
        raise RuntimeError("This PDF Tools file is not the reviewed V7.11 version; no changes made.")
    import_line = ("from office_pdf_v713 import (\n"
                   "    DOCX_BUTTON, PPTX_BUTTON, register_office_pdf_v713,\n"
                   ")\n")
    if "from office_pdf_v713 import" not in pdf:
        anchor = "# Per-chat PDF tool state."
        if anchor not in pdf:
            raise RuntimeError("PDF import anchor not found; stop to avoid handler conflicts.")
        pdf = pdf.replace(anchor, import_line + "\n" + anchor, 1)
    elif import_line.strip() not in pdf:
        raise RuntimeError("Existing V7.13 PDF imports differ; review before retry.")

    if "types.KeyboardButton(DOCX_BUTTON)" not in pdf:
        anchor = "        types.KeyboardButton(PDF_TEXT_BUTTON),"
        if pdf.count(anchor) != 1:
            raise RuntimeError("Could not uniquely locate the Text → PDF menu button.")
        pdf = pdf.replace(anchor, anchor + "\n        types.KeyboardButton(DOCX_BUTTON),\n        types.KeyboardButton(PPTX_BUTTON),", 1)
    if '"📄 DOCX → PDF\\n"' not in pdf:
        anchor = '            "📝 Text → PDF\\n"'
        if pdf.count(anchor) != 1:
            raise RuntimeError("Could not uniquely locate the PDF menu description.")
        pdf = pdf.replace(anchor, anchor + '\n            "📄 DOCX → PDF\\n"\n            "📊 PPTX → PDF\\n"', 1)
    if "register_office_pdf_v713(bot, pdf_state, _pdf_tools_menu, _mode_keyboard)" not in pdf:
        anchor = "def register_pdf_handlers(bot, show_main_menu):"
        if pdf.count(anchor) != 1:
            raise RuntimeError("Could not safely find the PDF handler registration function.")
        pdf = pdf.replace(anchor, anchor + "\n\n    " + MARKER + "\n    "
                          "register_office_pdf_v713(bot, pdf_state, _pdf_tools_menu, _mode_keyboard)\n", 1)
    for item in ("types.KeyboardButton(DOCX_BUTTON)", "types.KeyboardButton(PPTX_BUTTON)",
                 "register_office_pdf_v713(bot, pdf_state, _pdf_tools_menu, _mode_keyboard)"):
        if item not in pdf:
            raise RuntimeError("Failed to wire all V7.13 PDF features.")
    plans["pdf_tools.py"] = pdf.encode("utf-8")

    nav = _file("navigation.py").read_text(encoding="utf-8-sig")
    action = 'GLOBAL_BUTTONS.update({"📄 DOCX → PDF", "📊 PPTX → PDF"})'
    if action not in nav:
        anchor = "NAVIGATION_BUTTONS = {"
        if nav.count(anchor) != 1:
            raise RuntimeError("Navigation anchor was changed; no files changed.")
        nav = nav.replace(anchor, f"{MARKER}\n{action}\n\n{anchor}", 1)
    plans["navigation.py"] = nav.encode("utf-8")

    req = _file("requirements.txt").read_text(encoding="utf-8-sig")
    for name, spec in (("python-docx", "python-docx>=1.1,<2"),
                       ("python-pptx", "python-pptx>=1.0,<2")):
        if not any(line.strip().lower().startswith(name.lower())
                   for line in req.splitlines() if not line.lstrip().startswith("#")):
            req = req.rstrip() + f"\n{spec}\n"
    plans["requirements.txt"] = req.encode("utf-8")

    ignore_path = _file(".gitignore")
    ignore = ignore_path.read_text(encoding="utf-8-sig") if ignore_path.exists() else ""
    if ".v713_backup/" not in ignore.splitlines():
        ignore = ignore.rstrip() + "\n.v713_backup/\n"
    plans[".gitignore"] = ignore.encode("utf-8")

    for name in NEW_FILES:
        path = BUNDLE / name
        if not path.is_file():
            raise RuntimeError(f"Missing upgrade file: {name}")
        proposed = path.read_bytes()
        if _file(name).exists() and _sha(_file(name).read_bytes()) != _sha(proposed):
            raise RuntimeError(f"Local {name} differs from the package. No files changed.")
        plans[name] = proposed

    for name, data in plans.items():
        if name.endswith(".py"):
            ast.parse(data.decode("utf-8"), filename=name)
    return plans


def _install(dry_run: bool) -> None:
    plans = _plans()
    changes = [name for name, data in plans.items()
               if not _file(name).exists() or _sha(_file(name).read_bytes()) != _sha(data)]
    if not changes:
        print("V7.13 already installed; no files changed.")
        return
    print("V7.13 files to update:", ", ".join(changes))
    if dry_run:
        print("DRY RUN PASSED: no files modified.")
        return
    if BACKUP.exists():
        raise RuntimeError("Backup .v713_backup exists. Inspect it before reinstalling.")
    BACKUP.mkdir()
    before = {}
    try:
        for name in changes:
            existed = _file(name).is_file()
            before[name] = existed
            if existed:
                shutil.copy2(_file(name), BACKUP / name)
        (BACKUP / "manifest.json").write_text(json.dumps({
            "existed": before,
            "installed": {name: _sha(plans[name]) for name in changes}
        }, indent=2), encoding="utf-8")
        for name in changes:
            temporary = _file(name + ".v713_tmp")
            temporary.write_bytes(plans[name])
            temporary.replace(_file(name))
    except Exception:
        _rollback(silent=True)
        raise
    print("V7.13 installed. Original files backed up in .v713_backup/.")
    print("Test: python -m unittest TEST_V7_13_OFFICE_PDF.py -v")


def _rollback(silent=False):
    manifest_path = BACKUP / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("V7.13 backup is missing. Nothing can be rolled back.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, sha in manifest["installed"].items():
        if not _file(name).exists() or _sha(_file(name).read_bytes()) != sha:
            raise RuntimeError(f"{name} changed after installation. Rollback stopped to protect your edits.")
    for name, existed in manifest["existed"].items():
        if existed:
            shutil.copy2(BACKUP / name, _file(name))
        else:
            _file(name).unlink(missing_ok=True)
    shutil.rmtree(BACKUP)
    if not silent:
        print("V7.13 rollback completed. Previous files restored.")


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
        print("V7.13 INSTALL STOPPED:", exc, file=sys.stderr)
        raise SystemExit(1)
