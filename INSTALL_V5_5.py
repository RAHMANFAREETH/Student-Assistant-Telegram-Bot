"""Safely patch current V5.4 main.py + navigation.py, preserving later fixes.
Run from the project root: python INSTALL_V5_5.py
Backups are created only when a file actually needs modification.
"""
from pathlib import Path
import ast
import shutil
import sys

MAIN = Path("main.py")
NAV = Path("navigation.py")
MODULE = Path("ai_study_assistant.py")


def backup(path):
    candidate = path.with_suffix(path.suffix + ".before_v55.bak")
    if not candidate.exists():
        shutil.copy2(path, candidate)
    return candidate


def update_main(src):
    changed = False
    imp = "from ai_study_assistant import register_ai_study_assistant_handlers\n"
    if imp.strip() not in src:
        anchor = "from navigation_handlers import ("
        if anchor not in src:
            raise ValueError("Could not find navigation_handlers import in main.py; patch manually")
        src = src.replace(anchor, imp + "\n" + anchor, 1)
        changed = True
    reg = "register_ai_study_assistant_handlers(bot, show_main_menu)"
    if reg not in src:
        anchor = "register_spaced_repetition_handlers("
        if anchor not in src:
            anchor = "register_pdf_handlers("
        if anchor not in src:
            raise ValueError("Could not locate handler registration in main.py")
        src = src.replace(anchor, reg + "\n\n" + anchor, 1)
        changed = True
    if "Student Assistant Bot V5.4" in src:
        src = src.replace("Student Assistant Bot V5.4", "Student Assistant Bot V5.5")
        changed = True
    # Only change exact health endpoint field and insert feature within map
    if '"version": "5.4"' in src:
        src = src.replace('"version": "5.4"', '"version": "5.5"', 1)
        changed = True
    if '"ai_study_assistant": True' not in src:
        feature = '"spaced_repetition": True,'
        if feature in src:
            src = src.replace(feature, feature + '\n            "ai_study_assistant": True,', 1)
            changed = True
    # Add brief AI help while keeping the rest of the Help text untouched.
    if '"/ai\\n"' not in src and '"/ai"' not in src:
        marker = '"/healthcheck\\n"'
        if marker in src:
            src = src.replace(marker, '"/ai\\n"\n            "/aiclear\\n"\n            "/aistats\\n"\n            ' + marker, 1)
            changed = True
    ast.parse(src, filename="main.py")
    return src, changed


def update_navigation(src):
    changed = False
    if 'ASK_AI = "🤖 Ask AI"' not in src:
        anchor = 'HELP = "ℹ️ Help"'
        if anchor not in src:
            raise ValueError("navigation.py missing HELP constant")
        src = src.replace(anchor, 'ASK_AI = "🤖 Ask AI"\n\n' + anchor, 1)
        changed = True
    if '(ASK_AI,)' not in src:
        anchor = '    (HELP,),'
        if anchor not in src:
            raise ValueError("navigation.py missing (HELP,) menu row")
        src = src.replace(anchor, '    (ASK_AI,),\n' + anchor, 1)
        changed = True
    ast.parse(src, filename="navigation.py")
    return src, changed


def main():
    if not all(p.exists() for p in (MAIN, NAV, MODULE)):
        print("Missing main.py, navigation.py or ai_study_assistant.py in current folder")
        return 1
    targets = [(MAIN, update_main), (NAV, update_navigation)]
    revisions = []
    try:
        for path, fn in targets:
            original = path.read_text(encoding="utf-8")
            new, changed = fn(original)
            if changed:
                revisions.append((path, new))
        # all parsing/anchors pass before any changes
        for path, new in revisions:
            bp = backup(path)
            path.write_text(new, encoding="utf-8")
            print("Updated", path, "(backup:", bp, ")")
        if not revisions:
            print("Already integrated; no changes needed.")
        else:
            print("V5.5 code integrated. Run tests and review git diff before deploying.")
        return 0
    except Exception as exc:
        print("INSTALL FAILED. No new changes were written:", exc)
        return 1

if __name__ == "__main__":
    sys.exit(main())
