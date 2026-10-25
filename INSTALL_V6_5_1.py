"""V6.5.1 compatible old/new Main Menu labels across legacy Notes/Reminders.

Runs against known V5.4/V6.5 layout; preflights every file, writes backups
before atomic updates, and never changes AI, database, or configuration code.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import tempfile

TARGETS = ("navigation.py", "navigation_handlers.py", "notes.py", "reminders.py")
OLD = '"⬅️ Main Menu"'
CANONICAL = '"🏠 Main Menu"'
GUARD_NOTES = '''        # V6.5.1: navigation must never be saved as a note.
        if text in ("🏠 Main Menu", "⬅️ Main Menu"):
            note_mode.pop(chat_id, None)
            temp_note.pop(chat_id, None)
            show_main_menu(chat_id, message.from_user.first_name or "Friend")
            return
'''
GUARD_REMINDERS = '''        # V6.5.1: navigation must never be saved as a reminder field.
        if text in ("🏠 Main Menu", "⬅️ Main Menu"):
            reminder_state.pop(chat_id, None)
            temp_reminder.pop(chat_id, None)
            show_main_menu(chat_id, message.from_user.first_name or "Friend")
            return
'''


def once_replace(source: str, old: str, new: str, filename: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"{filename}: unexpected code structure near {old[:50]!r}; nothing changed")
    return source.replace(old, new, 1)


def patch_text(name: str, text: str) -> tuple[str, bool]:
    if name not in TARGETS:
        raise ValueError(f"Unsupported target: {name}")
    ast.parse(text, filename=name)
    eol = "\r\n" if "\r\n" in text else "\n"
    src = text.replace("\r\n", "\n")
    if name == "navigation.py":
        if 'LEGACY_MAIN_MENU = "⬅️ Main Menu"' in src:
            if src.count("    LEGACY_MAIN_MENU,") != 1:
                raise ValueError("Incomplete navigation alias patch")
            return text, False
        src = once_replace(src, 'MAIN_MENU = "🏠 Main Menu"',
                           'MAIN_MENU = "🏠 Main Menu"\nLEGACY_MAIN_MENU = "⬅️ Main Menu"', name)
        src = once_replace(src, 'NAVIGATION_BUTTONS = {\n    MAIN_MENU,',
                           'NAVIGATION_BUTTONS = {\n    MAIN_MENU,\n    LEGACY_MAIN_MENU,', name)
    elif name == "navigation_handlers.py":
        if "    LEGACY_MAIN_MENU," in src:
            if src.count("    LEGACY_MAIN_MENU,") != 2:
                raise ValueError("Incomplete global menu handler patch")
            return text, False
        src = once_replace(src, 'from navigation import (\n    MAIN_MENU,',
                           'from navigation import (\n    MAIN_MENU,\n    LEGACY_MAIN_MENU,', name)
        src = once_replace(src, 'm.text in {\n            MAIN_MENU,',
                           'm.text in {\n            MAIN_MENU,\n            LEGACY_MAIN_MENU,', name)
    elif name in ("notes.py", "reminders.py"):
        if "# V6.5.1: navigation must never" in src:
            if src.count("# V6.5.1: navigation must never") != 1:
                raise ValueError(f"{name}: incomplete handler patch")
            return text, False
        src = once_replace(src, OLD, CANONICAL, name)
        if name == "notes.py":
            anchor = '    def handle_note_input(message):'
            guard = GUARD_NOTES
        else:
            anchor = '    def reminder_input(message):'
            guard = GUARD_REMINDERS
        if src.count(anchor) != 1:
            raise ValueError(f"{name}: expected state handler not found")
        start = src.index(anchor)
        offset = src.index("        text = message.text.strip()", start) + len("        text = message.text.strip()")
        src = src[:offset] + "\n\n" + guard + src[offset:]
    ast.parse(src, filename=name)
    return src.replace("\n", eol), True


def install(root: Path = Path(".")) -> list[str]:
    root = Path(root)
    patches = {}
    for name in TARGETS:
        p = root / name
        if not p.is_file():
            raise ValueError(f"Missing {name}; no files changed")
        with p.open("r", encoding="utf-8", newline="") as f:
            before = f.read()
        after, changed = patch_text(name, before)
        if changed:
            backup = root / (name + ".before_v651.bak")
            if backup.exists():
                raise ValueError(f"Backup already exists: {backup.name}; no files changed")
            patches[name] = (before, after)
    if not patches:
        return []
    # Prepare temporary files and backups before replacing any actual modules.
    temps = {}
    try:
        for name, (before, after) in patches.items():
            target = root / name
            tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=root,
                                              prefix=".v651_", suffix=".tmp", delete=False)
            with tmp:
                tmp.write(after)
            temps[name] = Path(tmp.name)
            shutil.copy2(target, root / (name + ".before_v651.bak"))
        for name in patches:
            os.replace(temps[name], root / name)
    except Exception:
        for name in patches:
            bak = root / (name + ".before_v651.bak")
            if bak.is_file():
                shutil.copy2(bak, root / name)
        raise
    finally:
        for path in temps.values():
            path.unlink(missing_ok=True)
    return list(patches)


if __name__ == "__main__":
    try:
        updated = install()
    except (OSError, SyntaxError, UnicodeError, ValueError) as exc:
        print("V6.5.1 stopped safely:", exc)
        raise SystemExit(1)
    print("V6.5.1: " + ("updated " + ", ".join(updated) if updated else "already installed; no files changed"))
