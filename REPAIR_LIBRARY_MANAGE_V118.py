"""Focused, reversible V11.8 installer/menu repair.

Usage (from StudentAssistantBot directory):
    python -X utf8 REPAIR_LIBRARY_MANAGE_V118.py --check
    python -X utf8 REPAIR_LIBRARY_MANAGE_V118.py --apply

Only edits INSTALL_LIBRARY_MANAGE_V118.py and (if its admin menu is missing)
library_media_v117_bot.py. Never edits main.py, SQL files or databases.
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

INSTALLER = "INSTALL_LIBRARY_MANAGE_V118.py"
TARGET = "library_media_v117_bot.py"
MARK = "# V11.8: Manage Library Files for older PDFs and new media."

# Unicode characters constructed at runtime so the repair file itself is ASCII-only.
MENU = "('" + chr(0x1F4C1) + " Manage Library Files','manage'),"
UPLOAD = "('" + chr(0x1F4E4) + " Upload Media','upload'),"

NEW_TRANSFORM = r'''def transform(original):
    """Add V11.8 hooks once; repair a missing menu entry in existing installs."""
    text = original
    manage = "('" + chr(0x1F4C1) + " Manage Library Files','manage'),"
    upload = "('" + chr(0x1F4E4) + " Upload Media','upload'),"

    # The former installer used an overly-specific moderation/stats anchor.
    # Use the single Upload Media entry to insert the new button before it.
    if manage not in text:
        text = _one(text, upload, manage + "\n                         " + upload)

    # Already-installed code must keep its existing handlers; never duplicate.
    if MARK in original:
        required = (
            "if action == 'manage'",
            "register_manage_handlers(bot)",
            "if action=='manage':",
        )
        missing = [part for part in required if part not in original]
        if missing:
            raise ValueError("Incomplete V11.8 hooks; refusing partial repair: " + repr(missing))
        return text

    old = "        kb.add(_button(label,data='v117:adm:'+action))\n"
    text = _one(text, old,
                "        if action == 'manage' and os.getenv('LIBRARY_MANAGE_V118_ENABLED','false').lower() not in ('true','yes','1','on'):\n"
                "            continue\n" + old)
    old = ("    from telebot.handler_backends import ContinueHandling\n\n"
           "    @bot.message_handler(commands=['libraryadmin','mediaadmin'])")
    text = _one(text, old,
                "    from telebot.handler_backends import ContinueHandling\n"
                f"    {MARK}\n"
                "    from library_manage_v118 import register_manage_handlers\n"
                "    register_manage_handlers(bot)\n\n"
                "    @bot.message_handler(commands=['libraryadmin','mediaadmin'])")
    old = "                if action=='pending':return _pending_panel(bot,c.message.chat.id)\n"
    text = _one(text, old, old +
                "                if action=='manage':\n"
                "                    from library_manage_v118 import list_panel,enabled as management_enabled\n"
                "                    if not management_enabled():return _message(bot,c.message.chat.id,'\\u26a0\\ufe0f File management is not enabled yet.')\n"
                "                    return list_panel(bot,c.from_user.id,c.message.chat.id)\n")
    return text


'''


def _read(path: Path) -> tuple[str, bytes]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path.name} is not UTF-8; refusing change") from exc
    return text.replace("\r\n", "\n"), raw


def _encode(text: str, old: bytes) -> bytes:
    if b"\r\n" in old:
        text = text.replace("\n", "\r\n")
    return (b"\xef\xbb\xbf" if old.startswith(b"\xef\xbb\xbf") else b"") + text.encode("utf-8")


def _diff(path: Path, old: str, new: str) -> str:
    return "".join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True),
        fromfile=path.name + " current", tofile=path.name + " proposed"))


def prepare(root: Path):
    installer_path = root / INSTALLER
    target_path = root / TARGET
    for path in (installer_path, target_path):
        if not path.is_file():
            raise FileNotFoundError("Required file missing: " + str(path))

    installer, installer_raw = _read(installer_path)
    target, target_raw = _read(target_path)
    if MARK not in target:
        raise ValueError("V11.8 registration marker not found in library file; refusing to patch V11.7 directly")
    for token in ("register_manage_handlers(bot)", "if action=='manage':", "if action == 'manage'"):
        if token not in target:
            raise ValueError(f"V11.8 hook missing ({token!r}); refusing to patch an incomplete installation")

    # Replace only the transform function, preserving the rest of the installer.
    transform_pattern = r"(?ms)^def transform\(original\):\n.*?(?=^def integrate\()"
    matches = list(re.finditer(transform_pattern, installer))
    if len(matches) != 1 or "def _one(" not in installer or "MARK = " not in installer:
        raise ValueError("Unexpected installer layout; refusing to rewrite")
    new_installer = (installer[:matches[0].start()] + NEW_TRANSFORM + installer[matches[0].end():])
    compile(new_installer, str(installer_path), "exec")

    new_target = target
    if MENU not in target:
        if target.count(UPLOAD) != 1:
            raise ValueError("Cannot uniquely locate Upload Media button in installed admin panel")
        new_target = target.replace(UPLOAD, MENU + "\n                         " + UPLOAD, 1)
    compile(new_target, str(target_path), "exec")

    candidates = [(installer_path, installer, new_installer, installer_raw),
                  (target_path, target, new_target, target_raw)]
    return [(p, old, new, raw) for p, old, new, raw in candidates if _encode(new, raw) != raw]


def repair(root: Path, apply: bool) -> None:
    changes = prepare(root)
    if not changes:
        print("Already repaired; no modifications necessary.")
        return
    for path, old, new, _ in changes:
        print(_diff(path, old, new))
    if not apply:
        print("CHECK OK. Nothing modified. Files to update:", ", ".join(p.name for p, *_ in changes))
        return

    backup = root / ("V118_REPAIR_BACKUP_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    backup.mkdir()
    for path, _, _, _ in changes:
        shutil.copy2(path, backup / path.name)
    written = []
    try:
        for path, _, new, raw in changes:
            tmp = path.with_name(path.name + ".v118repair.tmp")
            tmp.write_bytes(_encode(new, raw))
            os.replace(tmp, path)
            written.append(path)
    except Exception:
        for path in written:
            shutil.copy2(backup / path.name, path)
        raise
    print("Repair applied. Backup:", backup)
    print("Next: python -X utf8 -m py_compile INSTALL_LIBRARY_MANAGE_V118.py library_media_v117_bot.py library_manage_v118.py")
    print("Then: python -X utf8 -m unittest TEST_LIBRARY_MANAGE_V118 -q")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.add_mutually_exclusive_group(required=True)
    args.add_argument("--check", action="store_true")
    args.add_argument("--apply", action="store_true")
    options = parser.parse_args()
    repair(Path.cwd(), apply=options.apply)
