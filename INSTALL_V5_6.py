"""Patch a V5.5 StudentAssistantBot project to add Ask My Notes/PDF.
Run in project folder: python INSTALL_V5_6.py
Creates backups of main.py and navigation.py; does not replace AI/translator code.
"""
import ast
from pathlib import Path
import shutil
import sys

MAIN = Path("main.py")
NAV = Path("navigation.py")
MODULE = Path("study_context_ai.py")


def update_main(src):
    changed = False
    ai_import = "from ai_study_assistant import register_ai_study_assistant_handlers"
    context_import = "from study_context_ai import register_study_context_handlers"
    if ai_import not in src:
        raise ValueError("V5.5 AI import missing; install V5.5 Cloudflare first.")
    if context_import not in src:
        src = src.replace(ai_import, context_import + "\n" + ai_import, 1)
        changed = True

    ai_register = "register_ai_study_assistant_handlers(bot, show_main_menu)"
    context_register = "register_study_context_handlers(bot, show_main_menu)"
    if ai_register not in src:
        raise ValueError("V5.5 AI handler registration missing; check main.py.")
    if context_register not in src:
        src = src.replace(ai_register, context_register + "\n" + ai_register, 1)
        changed = True

    # No changes to existing main.py help text, webhook, translator, voice etc.
    ast.parse(src, filename="main.py")
    return src, changed


def update_navigation(src):
    changed = False
    ai_const = 'ASK_AI = "🤖 Ask AI"'
    if ai_const not in src:
        raise ValueError("V5.5 AI menu constant missing in navigation.py")
    add = 'ASK_NOTES = "📝 Ask My Notes"\nASK_PDF = "📄 Ask My PDF"\n'
    if 'ASK_NOTES = "📝 Ask My Notes"' not in src:
        src = src.replace(ai_const, ai_const + "\n" + add, 1)
        changed = True
    if '(ASK_NOTES, ASK_PDF),' not in src:
        target = '    (ASK_AI,),'
        if target not in src:
            raise ValueError("AI menu row not found in navigation.py")
        src = src.replace(target, target + '\n    (ASK_NOTES, ASK_PDF),', 1)
        changed = True
    ast.parse(src, filename="navigation.py")
    return src, changed


def run():
    if not all(x.exists() for x in (MAIN, NAV, MODULE)):
        print("ERROR: Place INSTALL_V5_6.py and study_context_ai.py beside main.py and navigation.py")
        return 1
    try:
        changes = []
        for file, updater in ((MAIN, update_main), (NAV, update_navigation)):
            text = file.read_text(encoding="utf-8")
            result, changed = updater(text)
            if changed:
                changes.append((file, result))
        for file, content in changes:
            backup = file.with_suffix(file.suffix + ".before_v56.bak")
            if not backup.exists():
                shutil.copy2(file, backup)
            file.write_text(content, encoding="utf-8")
            print("UPDATED", file, "BACKUP", backup)
        if not changes:
            print("Already installed. No changes needed.")
        else:
            print("V5.6 source-based AI commands and menu installed. Run Python tests before deploying.")
        return 0
    except Exception as error:
        print("INSTALL NOT COMPLETED:", str(error))
        return 1


if __name__ == "__main__":
    sys.exit(run())
