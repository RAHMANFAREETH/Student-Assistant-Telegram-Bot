"""Install achievements V5.8 into an existing V5.7 StudentAssistantBot.

Run: python INSTALL_V5_8.py
Patches only main.py, navigation.py, ui_v57.py. Makes timestamped-safe
backups before writing. Does not replace Azure/OCR/AssemblyAI/Cloudflare files.
"""
import ast
from pathlib import Path
import shutil
import sys

MAIN = Path("main.py")
NAV = Path("navigation.py")
UI = Path("ui_v57.py")
MODULE = Path("achievements_v58.py")

MAIN_IMPORT = "from achievements_v58 import register_achievements_v58_handlers"
REGISTRATION = "register_achievements_v58_handlers(bot, show_main_menu)"
NAV_MARKER = "# V5.8 achievements navigation"
UI_MARKER = "# V5.8 achievements category"


def patch_main(source):
    if MAIN_IMPORT in source and REGISTRATION in source:
        ast.parse(source)
        return source, False
    if MAIN_IMPORT in source or REGISTRATION in source:
        raise ValueError("Partial V5.8 main.py integration; inspect file before retrying")
    if "register_ui_v57_handlers(bot, show_main_menu)" not in source:
        raise ValueError("V5.7 category navigation missing in main.py")
    anchor = "from ui_v57 import greeting, register_ui_v57_handlers"
    if source.count(anchor) != 1:
        raise ValueError("Unexpected V5.7 import structure")
    source = source.replace(anchor, anchor + "\n" + MAIN_IMPORT, 1)
    reg = "register_ui_v57_handlers(bot, show_main_menu)"
    source = source.replace(reg, reg + "\n" + REGISTRATION, 1)
    source = source.replace('"version": "5.7"', '"version": "5.8"', 1)
    ast.parse(source, filename="main.py")
    return source, True


def patch_navigation(source):
    if NAV_MARKER in source:
        ast.parse(source)
        return source, False
    anchor = "NAVIGATION_BUTTONS = {"
    if source.count(anchor) != 1 or "# V5.7 CATEGORY MENU START" not in source:
        raise ValueError("Expected V5.7 navigation.py not found")
    snippet = '''# V5.8 achievements navigation
# Add BEFORE ALL_NAVIGATION_BUTTONS is constructed; preserve older buttons.
GLOBAL_BUTTONS.update({"🏆 Achievements", "⭐ My Level"})

'''
    source = source.replace(anchor, snippet + anchor, 1)
    ast.parse(source, filename="navigation.py")
    return source, True


def patch_ui(source):
    if UI_MARKER in source:
        ast.parse(source)
        return source, False
    # Use the exact V5.7 one-line category fragment; refuse unfamiliar layout.
    anchor = '"🔥 Study Streak", "🧠 Smart Insights"'
    if source.count(anchor) != 1 or 'CAT_PROGRESS = "📊 My Progress"' not in source:
        raise ValueError("Unexpected ui_v57.py Progress category; no files changed")
    source = source.replace(anchor,
        '"🔥 Study Streak", "🏆 Achievements", "⭐ My Level", "🧠 Smart Insights"', 1)
    # Bump displayed welcome versions, without interfering with the underlying
    # V5.7 compatibility module or changing existing handler labels.
    source = source.replace("Student Assistant V5.7", "Student Assistant V5.8")
    source = source.replace("Bot V5.7", "Bot V5.8")
    source = source.replace("V5.7", "V5.8")
    source = "# V5.8 achievements category\n" + source
    ast.parse(source, filename="ui_v57.py")
    return source, True


def run_install(folder=Path(".")):
    paths = {"main.py": folder / MAIN, "navigation.py": folder / NAV,
             "ui_v57.py": folder / UI}
    if not (folder / MODULE).is_file():
        raise ValueError("Copy achievements_v58.py into your StudentAssistantBot folder first")
    if any(not path.is_file() for path in paths.values()):
        raise ValueError("Missing V5.7 main.py/navigation.py/ui_v57.py")
    patchers = {"main.py": patch_main, "navigation.py": patch_navigation, "ui_v57.py": patch_ui}
    # Preflight all three files before modifying anything; syntax-test all outputs.
    changes = {}
    for name, path in paths.items():
        original = path.read_text(encoding="utf-8")
        updated, changed = patchers[name](original)
        ast.parse(updated, filename=name)
        if changed:
            changes[name] = updated
    if not changes:
        return []
    # Do not overwrite existing backup filenames after a later reinstallation.
    for name in changes:
        backup = paths[name].with_name(name + ".before_v58.bak")
        if backup.exists():
            raise ValueError(f"Backup already exists: {backup}; preserve it before retrying")
    for name in changes:
        shutil.copy2(paths[name], paths[name].with_name(name + ".before_v58.bak"))
    for name, source in changes.items():
        paths[name].write_text(source, encoding="utf-8")
    return sorted(changes)


def main():
    try:
        changed = run_install(Path("."))
    except (ValueError, OSError, SyntaxError) as error:
        print(f"V5.8 installation stopped safely: {error}")
        return 1
    print("V5.8 installed: " + (", ".join(changed) if changed else "already installed; no files changed"))
    print("Run: python -m py_compile main.py navigation.py ui_v57.py achievements_v58.py")
    print("Then: python -m unittest TEST_V5_8_ACHIEVEMENTS.py -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
