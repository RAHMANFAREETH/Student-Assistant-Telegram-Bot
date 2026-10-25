"""Install V6.6 revision hub into existing V6.5.1 Student Assistant project.

Only changes main.py, ui_v57.py, navigation.py after strict preflight.
Backups use *.before_v66.bak and files are written atomically with rollback.
No modifications to Cloudflare, Gemini, Notes, Flashcards, or Supabase records.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import tempfile

MARKER_MAIN = "# V6.6 Revision Hub integration"
MARKER_UI = "# V6.6 revision hub menu options"
MARKER_NAV = "# V6.6 revision hub global navigation"
TARGETS = ("main.py", "ui_v57.py", "navigation.py")


class InstallationError(ValueError):
    pass


def replace_once(source, original, replacement, where):
    if source.count(original) != 1:
        raise InstallationError(f"{where}: expected exactly one code anchor; no files changed")
    return source.replace(original, replacement, 1)


def patch_main(src):
    ast.parse(src, filename="main.py")
    if MARKER_MAIN in src:
        if (src.count(MARKER_MAIN) != 1 or
                src.count("from revision_hub_v66 import register_revision_hub_v66_handlers") != 1 or
                src.count("register_revision_hub_v66_handlers(bot, show_main_menu)") != 1):
            raise InstallationError("Partial V6.6 main.py patch detected")
        return src, False
    if "revision_hub_v66" in src:
        raise InstallationError("Unexpected existing revision hub code")
    if ("register_ui_v57_handlers(bot, show_main_menu)" not in src or
            "register_achievements_v58_handlers(bot, show_main_menu)" not in src or
            "register_ai_study_assistant_handlers" not in src):
        raise InstallationError("Expected V5.8–V6.5 handler registrations missing")
    src = replace_once(src, "from ui_v57 import greeting, register_ui_v57_handlers",
                       "from ui_v57 import greeting, register_ui_v57_handlers\n"
                       "# V6.6 Revision Hub integration\n"
                       "from revision_hub_v66 import register_revision_hub_v66_handlers", "main.py")
    reg = "register_achievements_v58_handlers(bot, show_main_menu)"
    src = replace_once(src, reg, reg + "\nregister_revision_hub_v66_handlers(bot, show_main_menu)", "main.py")
    ast.parse(src, filename="main.py")
    return src, True


def patch_ui(src):
    ast.parse(src, filename="ui_v57.py")
    if MARKER_UI in src:
        if (src.count(MARKER_UI) != 1 or
                src.count('"📚 My AI Study Library"') != 1 or
                src.count('"🧠 Practice Saved Cards"') != 1):
            raise InstallationError("Partial V6.6 UI patch detected")
        return src, False
    study = '(CAT_STUDY, ["📚 Subjects", "📝 Notes", "📚 Study Materials", "🔎 Global Search"]),'
    study_new = '''# V6.6 revision hub menu options
    (CAT_STUDY, ["📚 Subjects", "📝 Notes", "📚 Study Materials", "🔎 Global Search",
                 "📖 Revision Hub", "📚 My AI Study Library", "🔄 Revise AI Note"]),'''
    practice = '''(CAT_PRACTICE, ["🧠 Flashcards", "🧠 Due Reviews", "📊 Review Stats", "❓ Quiz",
                    "📚 Revision Planner"]),'''
    practice_new = '''(CAT_PRACTICE, ["🧠 Flashcards", "🧠 Due Reviews", "📊 Review Stats", "❓ Quiz",
                    "📚 Revision Planner", "🧠 Practice Saved Cards", "📊 Revision Progress",
                    "⏰ Revision Reminders"]),'''
    if '# V5.8 achievements category' not in src:
        raise InstallationError("Expected V5.8 category menu missing")
    src = replace_once(src, study, study_new, "ui_v57.py")
    src = replace_once(src, practice, practice_new, "ui_v57.py")
    ast.parse(src, filename="ui_v57.py")
    return src, True


def patch_navigation(src):
    ast.parse(src, filename="navigation.py")
    if MARKER_NAV in src:
        required = ('"📖 Revision Hub"', '"📚 My AI Study Library"',
                    '"🔄 Revise AI Note"', '"🧠 Practice Saved Cards"',
                    '"📊 Revision Progress"', '"⏰ Revision Reminders"')
        if src.count(MARKER_NAV) != 1 or any(src.count(x) != 1 for x in required):
            raise InstallationError("Partial V6.6 navigation patch detected")
        return src, False
    if ('# V5.8 achievements navigation' not in src or
            'LEGACY_MAIN_MENU = "⬅️ Main Menu"' not in src):
        raise InstallationError("Expected V5.8 + V6.5.1 navigation missing")
    new = '''# V6.6 revision hub global navigation
# Older stateful handlers must yield when a user taps these buttons.
GLOBAL_BUTTONS.update({
    "📖 Revision Hub", "📚 My AI Study Library", "🔄 Revise AI Note",
    "🧠 Practice Saved Cards", "📊 Revision Progress", "⏰ Revision Reminders",
})

NAVIGATION_BUTTONS = {'''
    src = replace_once(src, "NAVIGATION_BUTTONS = {", new, "navigation.py")
    ast.parse(src, filename="navigation.py")
    return src, True


PATCHERS = {"main.py": patch_main, "ui_v57.py": patch_ui, "navigation.py": patch_navigation}


def install(root=Path(".")):
    root = Path(root)
    if not (root / "revision_hub_v66.py").is_file():
        raise InstallationError("Copy revision_hub_v66.py into the bot folder first")
    paths = {name: root / name for name in TARGETS}
    if any(not path.is_file() for path in paths.values()):
        raise InstallationError("Missing main.py, ui_v57.py, or navigation.py")
    new_text = {}
    for name, path in paths.items():
        with path.open("r", encoding="utf-8", newline="") as fh:
            original = fh.read()
        eol = "\r\n" if "\r\n" in original else "\n"
        patched, changed = PATCHERS[name](original.replace("\r\n", "\n"))
        ast.parse(patched, filename=name)
        if changed:
            if (root / (name + ".before_v66.bak")).exists():
                raise InstallationError(f"Backup for {name} already exists: no files changed")
            new_text[name] = patched.replace("\n", eol)
    if not new_text:
        return []

    temp_paths = {}
    backed_up = []
    replaced = []
    try:
        for name, contents in new_text.items():
            tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=root,
                                              prefix=".v66_", suffix=".tmp", delete=False)
            with tmp:
                tmp.write(contents)
            temp_paths[name] = Path(tmp.name)
        for name in new_text:
            shutil.copy2(paths[name], root / (name + ".before_v66.bak"))
            backed_up.append(name)
        for name, tmp in temp_paths.items():
            os.replace(tmp, paths[name])
            replaced.append(name)
    except Exception:
        for name in replaced:
            shutil.copy2(root / (name + ".before_v66.bak"), paths[name])
        raise
    finally:
        for path in temp_paths.values():
            path.unlink(missing_ok=True)
    return list(new_text)


if __name__ == "__main__":
    try:
        changed = install()
    except (ValueError, OSError, UnicodeError, SyntaxError) as exc:
        print("V6.6 install stopped safely:", exc)
        raise SystemExit(1)
    print("V6.6 " + ("installed: " + ", ".join(changed) if changed else "already installed; no files changed"))
    print("Run: python -m unittest TEST_V6_6_REVISION_HUB.py -v")
