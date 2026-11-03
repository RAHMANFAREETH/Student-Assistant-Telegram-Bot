"""V7.14 image engine repair: preserve V7.13 filters and V7.14 crop UI.

Run from StudentAssistantBot directory:
    python INSTALL_V7_14_ENGINE_REPAIR.py --dry-run
    python INSTALL_V7_14_ENGINE_REPAIR.py
    python INSTALL_V7_14_ENGINE_REPAIR.py --rollback

Only image_filters_v713.py is modified. No external APIs, SQL, or Render changes.
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

ROOT = Path.cwd()
SOURCE_NAME = "image_filters_v713.py"
BACKUP = ROOT / ".v714_engine_repair_backup"


def normalized_digest(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def exactly_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"Unsupported image_filters_v713.py layout ({label}: matched {count}). "
            "No files changed. Send your current image_filters_v713.py for review."
        )
    return source.replace(old, new, 1)


def get_function(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source, filename=SOURCE_NAME)
    defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(defs) != 1 or not isinstance(defs[0], ast.FunctionDef):
        raise RuntimeError(f"Expected exactly one normal {name} function. No changes made.")
    return defs[0]


def has_arg(func: ast.FunctionDef, name: str) -> bool:
    return any(arg.arg == name for arg in [*func.args.posonlyargs, *func.args.args, *func.args.kwonlyargs])


def patch_engine(text: str) -> tuple[str, list[str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    ast.parse(text, filename=SOURCE_NAME)
    required = ["FILTER_BUTTON =", "def make_preview(", "def images_to_pdf(", "def filter_image("]
    if not all(token in text for token in required):
        raise RuntimeError("Unexpected image filters module. Stopping without changes.")
    changed: list[str] = []
    import_anchor = 'FILTER_BUTTON = "🎨 Choose Filter"\n'
    if "from image_crop_v714 import auto_crop_image" not in text:
        text = exactly_once(text, import_anchor,
                            "from image_crop_v714 import auto_crop_image\n\n" + import_anchor,
                            "V7.14 crop import")
        changed.append("crop import")

    if not has_arg(get_function(text, "make_preview"), "auto_crop"):
        text = exactly_once(text,
                            "def make_preview(data: bytes, filter_code: str) -> BytesIO:",
                            "def make_preview(data: bytes, filter_code: str, auto_crop: bool = False) -> BytesIO:",
                            "preview signature")
        changed.append("preview signature")

    if not has_arg(get_function(text, "images_to_pdf"), "auto_crop"):
        text = exactly_once(text,
                            'def images_to_pdf(image_items: list[bytes], filter_code: str = "original") -> BytesIO:',
                            'def images_to_pdf(image_items: list[bytes], filter_code: str = "original",\n'
                            '                  auto_crop: bool = False) -> BytesIO:',
                            "PDF signature")
        changed.append("PDF signature")

    preview_fn = get_function(text, "make_preview")
    preview_body = ast.get_source_segment(text, preview_fn)
    if "auto_crop_image(" not in preview_body:
        text = exactly_once(text,
                            "        filtered = filter_image(image, filter_code)\n        try:\n",
                            "        crop_source = auto_crop_image(image) if auto_crop else image.copy()\n"
                            "        try:\n"
                            "            filtered = filter_image(crop_source, filter_code)\n"
                            "        finally:\n"
                            "            crop_source.close()\n"
                            "        try:\n",
                            "preview crop processing")
        changed.append("preview crop processing")

    pdf_fn = get_function(text, "images_to_pdf")
    pdf_body = ast.get_source_segment(text, pdf_fn)
    if "auto_crop_image(" not in pdf_body:
        text = exactly_once(text,
                            "            original = _read_image(data)\n"
                            "            try:\n"
                            "                converted.append(filter_image(original, filter_code))\n"
                            "            finally:\n"
                            "                original.close()\n",
                            "            original = _read_image(data)\n"
                            "            try:\n"
                            "                crop_source = auto_crop_image(original) if auto_crop else original.copy()\n"
                            "                try:\n"
                            "                    converted.append(filter_image(crop_source, filter_code))\n"
                            "                finally:\n"
                            "                    crop_source.close()\n"
                            "            finally:\n"
                            "                original.close()\n",
                            "PDF crop processing")
        changed.append("PDF crop processing")

    # Validate signatures, functionality and an independent compile before writing.
    ast.parse(text, filename=SOURCE_NAME)
    for name in ("make_preview", "images_to_pdf"):
        fn = get_function(text, name)
        body = ast.get_source_segment(text, fn)
        if not has_arg(fn, "auto_crop") or "auto_crop_image(" not in body:
            raise RuntimeError(f"Incomplete {name} after repair; no files changed.")
    return text, changed


def install(dry_run: bool):
    for filename in ("main.py", "pdf_tools.py", SOURCE_NAME, "image_crop_v714.py"):
        if not (ROOT / filename).is_file():
            raise RuntimeError(f"Missing {filename}; run from the full V7.14 StudentAssistantBot folder.")
    current = (ROOT / SOURCE_NAME).read_bytes()
    original = current.decode("utf-8-sig")
    new_text, changes = patch_engine(original)
    if not changes:
        print("V7.14 image processing engine is already compatible; no files changed.")
        return
    if BACKUP.exists():
        raise RuntimeError("A repair backup already exists. Refusing a second repair; inspect before continuing.")
    pdf_tools = (ROOT / "pdf_tools.py").read_text(encoding="utf-8-sig")
    if "auto_crop=selected_crop(state)" not in pdf_tools or "from image_crop_v714 import" not in pdf_tools:
        raise RuntimeError("V7.14 Telegram crop handler not found in pdf_tools.py; refusing an engine-only patch.")
    print("Repair needed:", ", ".join(changes))
    print("Only image_filters_v713.py will change. V7.13 filters and V7.14 handlers will be preserved.")
    if dry_run:
        print("DRY RUN OK. No files changed.")
        return
    updated = new_text.encode("utf-8")
    BACKUP.mkdir()
    try:
        shutil.copy2(ROOT / SOURCE_NAME, BACKUP / SOURCE_NAME)
        manifest = {"before": normalized_digest(current), "after": normalized_digest(updated)}
        (BACKUP / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temp = ROOT / ".image_filters_v713_v714_repair.tmp"
        temp.write_bytes(updated)
        os.replace(temp, ROOT / SOURCE_NAME)
    except Exception:
        # Source remains restored even on failure.
        if (BACKUP / SOURCE_NAME).exists():
            shutil.copy2(BACKUP / SOURCE_NAME, ROOT / SOURCE_NAME)
        shutil.rmtree(BACKUP, ignore_errors=True)
        raise
    print("V7.14 engine repair completed. Backup:", BACKUP.name)
    print("Now run: python -m unittest TEST_V7_13_IMAGE_FILTERS.py TEST_V7_14_AUTO_CROP.py -v")


def rollback():
    manifest_path = BACKUP / "manifest.json"
    if not manifest_path.is_file() or not (BACKUP / SOURCE_NAME).is_file():
        raise RuntimeError("No valid repair backup found.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = ROOT / SOURCE_NAME
    if not target.is_file() or normalized_digest(target.read_bytes()) != manifest["after"]:
        raise RuntimeError("Engine changed after repair. Refusing rollback to protect your work.")
    if normalized_digest((BACKUP / SOURCE_NAME).read_bytes()) != manifest["before"]:
        raise RuntimeError("Backup checksum mismatch. Refusing rollback.")
    shutil.copyfile(BACKUP / SOURCE_NAME, target)
    shutil.rmtree(BACKUP)
    print("V7.14 engine repair rolled back; original image_filters_v713.py restored.")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    group = cli.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--rollback", action="store_true")
    args = cli.parse_args()
    try:
        if args.rollback:
            rollback()
        else:
            install(args.dry_run)
    except (OSError, RuntimeError, SyntaxError, UnicodeError) as error:
        print("REPAIR STOPPED SAFELY:", error, file=sys.stderr)
        sys.exit(1)
