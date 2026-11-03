"""Safe V7.14 Auto Crop installer for V7.13 Images -> PDF.

No network access, external APIs, secrets, or changes to main.py/Render/SQL.
Python 3.9+; in the project root run:
    python INSTALL_V7_14.py --dry-run
    python INSTALL_V7_14.py
    python INSTALL_V7_14.py --rollback
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

ROOT = Path.cwd()
SOURCE = Path(__file__).resolve().parent / "V714_FILES"
BACKUPS = ROOT / ".v714_backup"
TARGETS = ("pdf_tools.py", "image_filters_v713.py")
NEW_FILES = ("image_crop_v714.py", "TEST_V7_14_AUTO_CROP.py")
MARKER = "from image_crop_v714 import ("


def digest(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def replace(text: str, old: str, new: str, description: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"Unsupported project version: {description} matched {n} times. No files changed.")
    return text.replace(old, new, 1)


def patch_filters(source: str) -> str:
    if "from image_crop_v714 import auto_crop_image" in source:
        return source
    source = replace(source,
        "FILTER_BUTTON = \"🎨 Choose Filter\"\n",
        "from image_crop_v714 import auto_crop_image\n\nFILTER_BUTTON = \"🎨 Choose Filter\"\n",
        "filters import")
    source = replace(source,
        "def make_preview(data: bytes, filter_code: str) -> BytesIO:",
        "def make_preview(data: bytes, filter_code: str, auto_crop: bool = False) -> BytesIO:",
        "preview signature")
    source = replace(source,
        "        filtered = filter_image(image, filter_code)\n        try:\n",
        "        crop_source = auto_crop_image(image) if auto_crop else image.copy()\n"
        "        try:\n"
        "            filtered = filter_image(crop_source, filter_code)\n"
        "        finally:\n"
        "            crop_source.close()\n"
        "        try:\n",
        "preview processing")
    source = replace(source,
        'def images_to_pdf(image_items: list[bytes], filter_code: str = "original") -> BytesIO:',
        'def images_to_pdf(image_items: list[bytes], filter_code: str = "original",\n'
        '                  auto_crop: bool = False) -> BytesIO:',
        "PDF signature")
    source = replace(source,
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
    return source


def patch_pdf(source: str) -> str:
    if MARKER in source:
        return source
    source = replace(source,
        "    images_to_pdf,\n)\n\nfrom navigation import should_yield_to_navigation\n",
        "    images_to_pdf,\n)\n"
        "from image_crop_v714 import (\n"
        "    CROP_MENU_BUTTON, CROP_ORIGINAL_BUTTON, CROP_AUTO_BUTTON,\n"
        "    CROP_NAMES, selected_crop,\n"
        ")\n\nfrom navigation import should_yield_to_navigation\n",
        "crop imports")
    source = replace(source,
        "        [FILTER_BUTTON, PREVIEW_BUTTON],\n"
        "        [REMOVE_BUTTON, \"✅ Create PDF\"],\n"
        "        [\"🔙 PDF Tools\", \"🏠 Main Menu\"],\n",
        "        [FILTER_BUTTON, PREVIEW_BUTTON],\n"
        "        [CROP_MENU_BUTTON, REMOVE_BUTTON],\n"
        "        [\"✅ Create PDF\", \"🔙 PDF Tools\"],\n"
        "        \"🏠 Main Menu\",\n",
        "images keyboard")
    source = replace(source,
        "def _image_filter_keyboard():\n",
        "def _image_crop_keyboard():\n"
        "    return _mode_keyboard(\n"
        "        [CROP_ORIGINAL_BUTTON, CROP_AUTO_BUTTON],\n"
        "        BACK_BUTTON,\n"
        "        \"🏠 Main Menu\",\n"
        "    )\n\n\n"
        "def _image_filter_keyboard():\n",
        "crop choice keyboard")
    source = replace(source,
        '            "image_filter": "original",\n        }',
        '            "image_filter": "original",\n            "image_autocrop": False,\n        }',
        "default image state")
    source = replace(source,
        '                "Choose 🎨 Choose Filter (default: Original).\\n"\n',
        '                "Default: Original image, Original filter (no crop).\\n"\n'
        '                "Optional: ✂️ Crop Mode → Auto Crop to remove desk edges.\\n"\n'
        '                "Choose 🎨 Choose Filter for scan/color effects.\\n"\n',
        "start instructions")
    anchor = '''    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == BACK_BUTTON
'''
    crop_handlers = '''    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) == CROP_MENU_BUTTON
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def open_crop_picker(message):
        state = pdf_state[message.chat.id]
        bot.send_message(
            message.chat.id,
            "✂️ Crop Mode\\n\\n"
            f"Current: {CROP_NAMES[selected_crop(state)]}\\n"
            "Original keeps the whole image (default).\\n"
            "Auto Crop tries to remove a clearly visible desk/background. "
            "If it cannot detect the page safely, it keeps the original.",
            reply_markup=_image_crop_keyboard(),
        )

    @bot.message_handler(
        func=lambda m: getattr(m, "text", None) in (CROP_ORIGINAL_BUTTON, CROP_AUTO_BUTTON)
        and pdf_state.get(m.chat.id, {}).get("mode") == "images"
    )
    def choose_crop_mode(message):
        state = pdf_state[message.chat.id]
        state["image_autocrop"] = (message.text == CROP_AUTO_BUTTON)
        bot.send_message(
            message.chat.id,
            f"✅ Crop Mode: {CROP_NAMES[selected_crop(state)]}\\n"
            "Use 👁 Preview Last before creating the PDF.",
            reply_markup=_image_tools_keyboard(),
        )

'''
    source = replace(source, anchor, crop_handlers + anchor, "crop handlers")
    source = replace(source,
        "            output = make_preview(images[-1], selected_filter(state))\n",
        "            output = make_preview(images[-1], selected_filter(state),\n"
        "                                  auto_crop=selected_crop(state))\n",
        "preview crop forwarding")
    source = replace(source,
        '                    caption=f"👁 Preview of last image: {FILTER_NAMES[selected_filter(state)]}\\n"\n'
        '                            "The same filter will be used for all PDF pages.",\n',
        '                    caption=f"👁 Preview: {FILTER_NAMES[selected_filter(state)]}\\n"\n'
        '                            f"Crop: {CROP_NAMES[selected_crop(state)]}\\n"\n'
        '                            "Preview shows the settings for every PDF page.",\n',
        "preview text")
    source = replace(source,
        "            output = images_to_pdf(images, selected_filter(state))\n",
        "            output = images_to_pdf(images, selected_filter(state),\n"
        "                                   auto_crop=selected_crop(state))\n",
        "PDF crop forwarding")
    source = replace(source,
        '                    caption=f"✅ PDF ready! Filter: {FILTER_NAMES[selected_filter(state)]} "\n'
        '                            f"• Pages: {len(images)}",\n',
        '                    caption=f"✅ PDF ready! Filter: {FILTER_NAMES[selected_filter(state)]} "\n'
        '                            f"• Crop: {CROP_NAMES[selected_crop(state)]} "\n'
        '                            f"• Pages: {len(images)}",\n',
        "PDF description")
    return source


def ensure_project():
    if not (ROOT / "main.py").is_file():
        raise RuntimeError("Run inside your StudentAssistantBot directory (main.py missing).")
    if not (ROOT / "image_filters_v713.py").is_file():
        raise RuntimeError("V7.13 image filters not found. Install V7.13 first; no files changed.")
    if not SOURCE.is_dir() or not all((SOURCE / f).is_file() for f in NEW_FILES):
        raise RuntimeError("Copy V714_FILES alongside INSTALL_V7_14.py first.")


def planned_updates():
    old = {name: (ROOT / name).read_bytes() for name in TARGETS}
    def decode(data):
        return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    if MARKER in decode(old["pdf_tools.py"]):
        # Do not silently claim installed if only one file changed.
        if "from image_crop_v714 import auto_crop_image" in decode(old["image_filters_v713.py"]) and all((ROOT / n).is_file() for n in NEW_FILES):
            return old, None
        raise RuntimeError("Partial V7.14 installation detected; please share the error before continuing.")
    changed = {
        "pdf_tools.py": patch_pdf(decode(old["pdf_tools.py"])).encode("utf-8"),
        "image_filters_v713.py": patch_filters(decode(old["image_filters_v713.py"])).encode("utf-8"),
    }
    for name, data in changed.items():
        ast.parse(data.decode("utf-8"), filename=name)
    for name in NEW_FILES:
        ast.parse((SOURCE / name).read_text(encoding="utf-8"), filename=name)
        if (ROOT / name).exists():
            raise RuntimeError(f"{name} exists already; refusing to overwrite.")
    return old, changed


def install(dry_run=False):
    ensure_project()
    old, changed = planned_updates()
    if changed is None:
        print("V7.14 already installed; no files changed.")
        return
    if BACKUPS.exists():
        raise RuntimeError(".v714_backup already exists; stop and inspect before retrying.")
    print("V7.14 will modify: pdf_tools.py and image_filters_v713.py")
    print("V7.14 will add: image_crop_v714.py and TEST_V7_14_AUTO_CROP.py")
    print("Default remains: Original image / Original filter; Auto Crop OFF.")
    if dry_run:
        print("Dry run OK. No files changed.")
        return
    BACKUPS.mkdir()
    manifest = {"before": {n: digest(old[n]) for n in TARGETS},
                "after": {n: digest(changed[n]) for n in TARGETS},
                "added": {n: digest((SOURCE / n).read_bytes()) for n in NEW_FILES}}
    try:
        for name in TARGETS:
            (BACKUPS / name).write_bytes(old[name])
        (BACKUPS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for name, data in changed.items():
            tmp = ROOT / (name + ".v714_tmp")
            tmp.write_bytes(data)
            os.replace(tmp, ROOT / name)
        for name in NEW_FILES:
            shutil.copyfile(SOURCE / name, ROOT / name)
    except Exception:
        for name in TARGETS:
            (ROOT / name).write_bytes(old[name])
        for name in NEW_FILES:
            if (ROOT / name).exists() and digest((ROOT / name).read_bytes()) == manifest["added"][name]:
                (ROOT / name).unlink()
        shutil.rmtree(BACKUPS, ignore_errors=True)
        raise
    print("V7.14 installed. Backups in .v714_backup/.")
    print("Test: python -m unittest TEST_V7_13_IMAGE_FILTERS.py TEST_V7_14_AUTO_CROP.py -v")


def rollback():
    if not BACKUPS.is_dir():
        raise RuntimeError("No V7.14 backup found. Nothing to roll back.")
    manifest = json.loads((BACKUPS / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["after"].items():
        if not (ROOT / name).is_file() or digest((ROOT / name).read_bytes()) != expected:
            raise RuntimeError(f"{name} has changed since installation; refusing to roll back.")
    for name, expected in manifest["added"].items():
        if not (ROOT / name).is_file() or digest((ROOT / name).read_bytes()) != expected:
            raise RuntimeError(f"{name} has changed since installation; refusing to delete it.")
    for name in TARGETS:
        shutil.copyfile(BACKUPS / name, ROOT / name)
    for name in NEW_FILES:
        (ROOT / name).unlink()
    shutil.rmtree(BACKUPS)
    print("V7.14 rolled back; original V7.13 files restored.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--rollback", action="store_true")
    args = p.parse_args()
    try:
        if args.rollback:
            rollback()
        else:
            install(dry_run=args.dry_run)
    except (OSError, RuntimeError, ValueError, SyntaxError, UnicodeError) as ex:
        print("V7.14 safely stopped:", ex)
        sys.exit(1)
