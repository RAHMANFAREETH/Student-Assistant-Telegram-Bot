"""Upgrade an existing V5.6 StudentAssistantBot to categorized V5.7 navigation.

Run from the project directory: python INSTALL_V5_7.py
Only main.py and navigation.py are modified; both are backed up.
This patch intentionally does NOT replace Cloudflare AI, Azure, OCR, AssemblyAI,
Supabase credentials or any original feature handler module.
"""
import ast
from pathlib import Path
import shutil
import sys

MAIN_FILE = Path("main.py")
NAV_FILE = Path("navigation.py")
UI_FILE = Path("ui_v57.py")
V57_MAIN_IMPORT = "from ui_v57 import greeting, register_ui_v57_handlers"
V57_REGISTER = "register_ui_v57_handlers(bot, show_main_menu)"
V57_NAV_MARKER = "# V5.7 CATEGORY MENU START"


def patch_main(source):
    """Use AST locations for the existing show_main_menu function; never regex across it."""
    if V57_MAIN_IMPORT in source and V57_REGISTER in source:
        ast.parse(source, filename="main.py")
        return source, False
    if V57_MAIN_IMPORT in source or V57_REGISTER in source:
        raise ValueError("Partial V5.7 installation in main.py; restore backup and retry")

    tree = ast.parse(source, filename="main.py")
    if "register_study_context_handlers" not in source or "register_ai_study_assistant_handlers" not in source:
        raise ValueError("V5.6 Cloudflare Ask My Notes/PDF module is required before V5.7")
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "show_main_menu"]
    if len(funcs) != 1:
        raise ValueError("Could not safely locate exactly one show_main_menu function")
    func = funcs[0]
    if len(func.args.args) < 1 or func.args.args[0].arg != "chat_id":
        raise ValueError("Unexpected show_main_menu signature")
    if not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "send_message" for n in ast.walk(func)):
        raise ValueError("Unexpected show_main_menu content")
    lines = source.splitlines(keepends=True)
    replacement = '''def show_main_menu(chat_id, first_name="Friend"):\n    """V5.7 compact menu; existing modules still receive original button text."""\n    bot.send_message(\n        chat_id,\n        greeting(first_name, chat_id),\n        reply_markup=build_main_menu_markup(),\n    )\n\n'''
    lines[func.lineno - 1:func.end_lineno] = [replacement]
    source = "".join(lines)

    # After rewriting, register the new category handler BEFORE ALL legacy modules.
    # Earliest module registration is determined using the AST (no fragile text match).
    tree = ast.parse(source, filename="main.py")
    first = None
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            name = call.func.id if isinstance(call.func, ast.Name) else ""
            if name.startswith("register_") and name.endswith("_handlers"):
                first = node.lineno
                break
    if first is None:
        raise ValueError("Couldn't locate legacy module-handler registrations")
    lines = source.splitlines(keepends=True)
    lines.insert(first - 1, f"# V5.7 category handlers MUST come before legacy handlers.\n{V57_REGISTER}\n\n")
    source = "".join(lines)

    # Import before navigation imports to keep all custom UI functions defined.
    imp_anchor = "from navigation import ("
    if imp_anchor not in source:
        raise ValueError("Missing navigation import anchor")
    source = source.replace(imp_anchor, V57_MAIN_IMPORT + "\n\n" + imp_anchor, 1)

    # Minor health version update, without overwriting other features.
    for previous in ('"version": "5.4"', '"version": "5.5"', '"version": "5.6"'):
        if previous in source:
            source = source.replace(previous, '"version": "5.7"', 1)
            break
    ast.parse(source, filename="main.py")
    return source, True


def patch_navigation(source):
    if V57_NAV_MARKER in source:
        ast.parse(source, filename="navigation.py")
        return source, False
    tree = ast.parse(source, filename="navigation.py")
    main_rows = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MAIN_MENU_ROWS" for t in n.targets)]
    if len(main_rows) != 1:
        raise ValueError("Can't safely find MAIN_MENU_ROWS in navigation.py")
    rows_assign = main_rows[0]
    if not isinstance(rows_assign.value, (ast.List, ast.Tuple)):
        raise ValueError("Unsupported navigation.py MAIN_MENU_ROWS format")
    if 'ASK_PDF = "📄 Ask My PDF"' not in source:
        raise ValueError("V5.6 Ask My PDF navigation entry missing; integrate V5.6 first")
    # Insert menu override AFTER legacy rows, BEFORE GLOBAL_BUTTONS comprehension.
    new_ui = '''\n# V5.7 CATEGORY MENU START\n# Retain the exact legacy button labels for all older feature handlers.\nLEGACY_MENU_ROWS = MAIN_MENU_ROWS\n\nUI_AI = "🤖 AI & Questions"\nUI_STUDY = "📚 Study Tools"\nUI_PLAN = "📅 Plans & Reminders"\nUI_PRACTICE = "🧠 Practice & Quiz"\nUI_LANGUAGES = "🌍 Languages"\nUI_PROGRESS = "📊 My Progress"\nUI_FILES = "🎙 Voice & PDF"\nUI_MORE = "📦 More Tools"\nUI_HELP = "❓ Help & Tutorial"\nUI_LANGUAGE = "🌐 Menu Language"\nUI_CATEGORIES = "↩️ All Categories"\n\nMAIN_MENU_ROWS = [\n    (UI_AI, UI_STUDY),\n    (UI_PLAN, UI_PRACTICE),\n    (UI_LANGUAGES, UI_PROGRESS),\n    (UI_FILES, UI_MORE),\n    (UI_HELP, UI_LANGUAGE),\n]\n\n# V5.7 CATEGORY MENU END\n'''
    lines = source.splitlines(keepends=True)
    lines.insert(rows_assign.end_lineno, new_ui)
    source = "".join(lines)
    # Retain every legacy label in GLOBAL_BUTTONS so stateful modules yield
    # navigation to the original registered feature handlers.
    anchor = 'GLOBAL_BUTTONS.add(REVIEW_STATS)'
    extra = '''GLOBAL_BUTTONS.update(button for row in LEGACY_MENU_ROWS for button in row)\nGLOBAL_BUTTONS.update({\n    UI_CATEGORIES,\n    "🇬🇧 English", "🇱🇰 தமிழ்", "🇱🇰 සිංහල", "🇸🇦 العربية",\n    "🚀 Getting Started", "🤖 Ask AI Guide", "📄 Ask My PDF Guide",\n    "🧠 Flashcards Guide", "📅 Study Planning Guide",\n    "🎙 Voice Notes Guide", "🔒 Privacy Tips",\n})\n'''
    if anchor not in source:
        raise ValueError("Missing global review-button anchor; navigation version differs")
    source = source.replace(anchor, anchor + "\n" + extra, 1)
    ast.parse(source, filename="navigation.py")
    return source, True


def main():
    if not all(p.is_file() for p in (MAIN_FILE, NAV_FILE, UI_FILE)):
        print("ERROR: Put INSTALL_V5_7.py and ui_v57.py beside main.py/navigation.py")
        return 1
    try:
        changes = []
        for path, patcher in [(MAIN_FILE, patch_main), (NAV_FILE, patch_navigation)]:
            original = path.read_text(encoding="utf-8")
            updated, changed = patcher(original)
            if changed:
                changes.append((path, updated))
        # Validate every patch before touching any project file.
        if not changes:
            print("V5.7 already installed; no files changed.")
            return 0
        for path, new_source in changes:
            backup = path.with_name(path.name + ".before_v57.bak")
            if backup.exists():
                # Avoid silently overwriting earlier, potentially valuable backups.
                raise ValueError(f"Backup already exists: {backup}; investigate before rerunning")
        for path, new_source in changes:
            backup = path.with_name(path.name + ".before_v57.bak")
            shutil.copy2(path, backup)
            path.write_text(new_source, encoding="utf-8")
            print(f"UPDATED {path.name}; backed up as {backup.name}")
        print("V5.7 navigation installed. Run tests and inspect git diff before pushing.")
        return 0
    except Exception as exc:
        print("INSTALL FAILED: " + str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
