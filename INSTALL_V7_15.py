"""Safety-first V7.15 Photo/Image Crop installer (existing-file compatibility fix).

Place this file in StudentAssistantBot/ next to the original V715_FILES/ folder.
From StudentAssistantBot/ run:
  python INSTALL_V7_15.py --dry-run
  python INSTALL_V7_15.py
  python INSTALL_V7_15.py --rollback

When an existing photo_crop_v715.py differs from the bundled source, refuse by
DEFAULT. You may explicitly choose --replace-existing after reviewing the file.
All replaced files are backed up and restored during rollback.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path.cwd().resolve()
SOURCE = Path(__file__).resolve().parent / "V715_FILES"
BACKUP = ROOT / ".v715_backup"
MANIFEST = BACKUP / "manifest.json"
FILES = ("photo_crop_v715.py", "TEST_V7_15_PHOTO_CROP.py")
TARGET = ROOT / "pdf_tools.py"

sys.path.insert(0, str(SOURCE))
try:
    from PATCH_V7_15_CORE import patch_pdf_tools
except ImportError as exc:
    raise SystemExit("Installer package incomplete: V715_FILES/PATCH_V7_15_CORE.py is missing") from exc


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    handle, name = tempfile.mkstemp(prefix=".v715_", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def normalized(data: bytes) -> str:
    return data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def encode_like(original: bytes, modified: str) -> bytes:
    if b"\r\n" in original:
        return modified.replace("\n", "\r\n").encode("utf-8")
    return modified.encode("utf-8")


def preflight() -> None:
    if not TARGET.is_file():
        raise RuntimeError("Run from the StudentAssistantBot directory containing pdf_tools.py")
    for name in ("image_crop_v714.py", "image_filters_v713.py"):
        if not (ROOT / name).is_file():
            raise RuntimeError(f"V7.14 is required: missing {name}")
    for name in FILES + ("PATCH_V7_15_CORE.py", "CROP_HANDLERS_V715.txt"):
        if not (SOURCE / name).is_file():
            raise RuntimeError(f"Missing V715_FILES/{name}; copy the original V7.15 ZIP contents first")
    if BACKUP.exists():
        raise RuntimeError("Existing .v715_backup/ detected; review previous install/rollback before proceeding")


def plan(replace_existing: bool):
    preflight()
    old = TARGET.read_bytes()
    text = normalized(old)
    fragment = (SOURCE / "CROP_HANDLERS_V715.txt").read_text(encoding="utf-8")
    proposed_text = patch_pdf_tools(text, fragment)
    ast.parse(proposed_text, filename="pdf_tools.py")
    targets = {}
    for name in FILES:
        new = (SOURCE / name).read_bytes()
        ast.parse(normalized(new), filename=name)
        dest = ROOT / name
        previous = dest.read_bytes() if dest.is_file() else None
        if previous is None:
            mode = "add"
        elif normalized(previous) == normalized(new):
            mode = "keep"
        elif name == "photo_crop_v715.py" and not replace_existing:
            raise RuntimeError(
                "Your existing photo_crop_v715.py DIFFERS from the packaged V7.15 helper. "
                "No files changed. Compare it against V715_FILES/photo_crop_v715.py. "
                "Only if you want to replace it with a backed-up V7.15 copy, "
                "run python INSTALL_V7_15.py --replace-existing."
            )
        else:
            mode = "replace"
        targets[name] = {"old": previous, "new": new, "action": mode}
    if proposed_text == text:
        if not all((ROOT / name).is_file() for name in FILES):
            raise RuntimeError("V7.15 handlers already exist but runtime/test file is missing; inspect before proceeding")
        if any(info["action"] == "replace" for info in targets.values()):
            raise RuntimeError("Photo Crop handlers already installed but files differ; review before changing")
        return {"already": True, "original": old, "modified": old, "files": targets}
    return {"already": False, "original": old, "modified": encode_like(old, proposed_text), "files": targets}


def describe(plan_data, dry_run: bool) -> None:
    print("V7.15 Photo Crop compatibility check:")
    print("  pdf_tools.py: PATCH (preserve other PDF features)")
    for name, item in plan_data["files"].items():
        print(f"  {name}: {item['action'].upper()}")
    if any(item["action"] == "replace" for item in plan_data["files"].values()):
        print("  Pre-existing files will be backed up into .v715_backup/originals/.")
    print("  Unchanged: main.py, other tools, Supabase, Render, Gemini, .env")
    if dry_run:
        print("Dry-run passed. No files modified.")


def install(dry_run: bool, replace_existing: bool) -> None:
    p = plan(replace_existing)
    if p["already"]:
        print("V7.15 already integrated; no code changed. Check the latest tests separately.")
        return
    describe(p, dry_run)
    if dry_run:
        return
    BACKUP.mkdir(exist_ok=False)
    originals = BACKUP / "originals"
    written = []
    try:
        originals.mkdir()
        atomic_write(BACKUP / "pdf_tools.py.before", p["original"])
        # Back up every overwritten file before editing any application source.
        for name, item in p["files"].items():
            if item["action"] == "replace":
                atomic_write(originals / name, item["old"])
        atomic_write(TARGET, p["modified"])
        for name, item in p["files"].items():
            if item["action"] in ("add", "replace"):
                atomic_write(ROOT / name, item["new"])
                written.append(name)
        record = {
            "version": "7.15-compat",
            "pdf_before": sha(p["original"]),
            "pdf_after": sha(p["modified"]),
            "files": {name: {
                "action": item["action"],
                "before": sha(item["old"]) if item["old"] is not None else None,
                "after": sha((ROOT / name).read_bytes()),
            } for name, item in p["files"].items()},
        }
        (MANIFEST).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    except BaseException:
        # Attempt to restore the unchanged working tree if any write fails.
        atomic_write(TARGET, p["original"])
        for name in written:
            old = p["files"][name]["old"]
            if old is None:
                (ROOT / name).unlink(missing_ok=True)
            else:
                atomic_write(ROOT / name, old)
        shutil.rmtree(BACKUP)
        raise
    print("V7.15 installation completed. Backup: .v715_backup/ (including prior helper/test when replaced).")
    print("Next: python -m unittest TEST_V7_15_PHOTO_CROP.py -v")


def rollback() -> None:
    if not MANIFEST.is_file():
        raise RuntimeError("No V7.15 compatibility installation manifest found; rollback stopped")
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if record.get("version") != "7.15-compat":
        raise RuntimeError("Manifest belongs to another installer. Use its original rollback script")
    backup_pdf = (BACKUP / "pdf_tools.py.before").read_bytes()
    if sha(backup_pdf) != record["pdf_before"] or not TARGET.is_file() or sha(TARGET.read_bytes()) != record["pdf_after"]:
        raise RuntimeError("pdf_tools.py changed after installation or backup is corrupt. Rollback stopped")
    for name, item in record["files"].items():
        path = ROOT / name
        if not path.is_file() or sha(path.read_bytes()) != item["after"]:
            raise RuntimeError(f"{name} was edited after installation; rollback stopped")
        if item["action"] == "replace":
            old_path = BACKUP / "originals" / name
            if not old_path.is_file() or sha(old_path.read_bytes()) != item["before"]:
                raise RuntimeError(f"Original {name} backup invalid; rollback stopped")
    atomic_write(TARGET, backup_pdf)
    for name, item in record["files"].items():
        if item["action"] == "add":
            (ROOT / name).unlink()
        elif item["action"] == "replace":
            atomic_write(ROOT / name, (BACKUP / "originals" / name).read_bytes())
    shutil.rmtree(BACKUP)
    print("V7.15 rolled back; previous files restored.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    parser.add_argument("--replace-existing", action="store_true", help="Explicitly replace a modified crop helper with a backed-up copy")
    args = parser.parse_args()
    try:
        if args.rollback:
            rollback()
        else:
            install(args.dry_run, args.replace_existing)
    except (OSError, ValueError, RuntimeError, SyntaxError, UnicodeError) as error:
        print("V7.15 stopped safely:", str(error))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
