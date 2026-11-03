"""Safe, narrow V7.17 PDF integration installer. Python 3.10+.

Copy this, advanced_pdf_v717.py and TEST_V7_17_ADVANCED_PDF.py
beside main.py, then run --check, --apply. No Git or Render actions.
"""
from __future__ import annotations

import argparse
import ast
import difflib
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PDF = ROOT / "pdf_tools.py"
REQ = ROOT / "requirements.txt"
ADV = ROOT / "advanced_pdf_v717.py"


class CannotPatch(Exception):
    pass


def patch_pdf(src: str) -> str:
    marker_import = "from office_to_pdf_v713 import register_office_to_pdf_handlers\n"
    new_import = "from advanced_pdf_v717 import ADVANCED_BUTTONS, register_advanced_pdf_handlers\n"
    if new_import not in src:
        if src.count(marker_import) != 1:
            raise CannotPatch("Can't locate Office PDF import; your project differs from the uploaded snapshot.")
        src = src.replace(marker_import, marker_import + new_import, 1)

    start = src.find("def _pdf_tools_menu(bot, chat_id):")
    stop = src.find("\ndef _scanner_keyboard():", start)
    if start < 0 or stop < 0:
        raise CannotPatch("Can't identify PDF menu; no changes will be made.")
    menu = src[start:stop]
    if "ADVANCED_BUTTONS[i:i + 2]" not in menu:
        rows = (
            "    # V7.17: keep all Advanced PDF Tools above Main Menu.\n"
            "    for i in range(0, len(ADVANCED_BUTTONS), 2):\n"
            "        markup.row(*[types.KeyboardButton(label) for label in ADVANCED_BUTTONS[i:i + 2]])\n"
        )
        main_row = '    markup.row(types.KeyboardButton("🏠 Main Menu"))\n'
        if main_row in menu:
            menu = menu.replace(main_row, rows + main_row, 1)
        elif '        types.KeyboardButton("🏠 Main Menu"),\n' in menu:
            menu = menu.replace('        types.KeyboardButton("🏠 Main Menu"),\n', '', 1)
            if "    bot.send_message(" not in menu:
                raise CannotPatch("PDF menu body changed; can't place advanced buttons.")
            menu = menu.replace("    bot.send_message(", rows + main_row + "\n    bot.send_message(", 1)
        else:
            raise CannotPatch("Main Menu layout differs; won't patch automatically.")
    menu_header, send, menu_message = menu.partition("    bot.send_message(")
    if not send:
        raise CannotPatch("PDF menu send_message() not found.")
    if '"🗜 Compress PDF\\n"' not in menu_message:
        label = '"📊 PPTX → PDF"' if '"📊 PPTX → PDF"' in menu_message else '"🔐 Protect PDF"'
        if label not in menu_message:
            raise CannotPatch("PDF menu description changed; can't update it safely.")
        replacement = (label[:-1] + '\\n"\n'
                       '            "🗜 Compress PDF\\n"\n'
                       '            "📄 PDF → Word\\n"\n'
                       '            "🖼 PDF → Images\\n"\n'
                       '            "🔀 Organize PDF\\n"\n'
                       '            "💧 Add Watermark"')
        menu_message = menu_message.replace(label, replacement, 1)
    menu = menu_header + send + menu_message
    src = src[:start] + menu + src[stop:]

    marker_def = "def register_pdf_handlers(bot, show_main_menu):\n"
    integration = (
        "    # V7.17: register before Office and legacy PDF document handlers.\n"
        "    register_advanced_pdf_handlers(\n"
        "        bot, lambda chat_id: _pdf_tools_menu(bot, chat_id),\n"
        "        lambda chat_id: pdf_state.pop(chat_id, None), show_main_menu,\n"
        "    )\n\n"
    )
    if "    register_advanced_pdf_handlers(\n" not in src:
        if src.count(marker_def) != 1:
            raise CannotPatch("Cannot find register_pdf_handlers() safely.")
        src = src.replace(marker_def, marker_def + integration, 1)
    ast.parse(src, filename="pdf_tools.py")
    return src


def patch_requirements(src: str) -> str:
    if any(line.strip().lower().startswith(("pymupdf==", "pymupdf>=", "pymupdf~=", "pymupdf<")) for line in src.splitlines()):
        return src
    return src.rstrip() + "\n\n# V7.17 advanced PDF rendering, optimization, and editable text extraction\nPyMuPDF>=1.26,<1.27\n"


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Print planned changes, change nothing")
    group.add_argument("--apply", action="store_true", help="Backup and update two files")
    args = parser.parse_args()
    try:
        for path in (PDF, REQ, ADV):
            if not path.is_file():
                raise CannotPatch(f"Missing {path.name}. Copy installer to your real bot folder first.")
        current_pdf, current_req = PDF.read_text(encoding="utf-8"), REQ.read_text(encoding="utf-8")
        new_pdf, new_req = patch_pdf(current_pdf), patch_requirements(current_req)
        ast.parse(ADV.read_text(encoding="utf-8"), filename=str(ADV))
    except (CannotPatch, SyntaxError) as exc:
        print("STOP: " + str(exc))
        return 2

    if args.check:
        for name, before, after in (("pdf_tools.py", current_pdf, new_pdf), ("requirements.txt", current_req, new_req)):
            print("".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                               fromfile=name + ":current", tofile=name + ":planned")))
        print("CHECK OK. No files changed. Run --apply if differences look correct.")
        return 0

    if current_pdf == new_pdf and current_req == new_req:
        print("Already integrated; no files changed.")
        return 0
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Backup first. Never overwrite the original backup path.
    for path, old in ((PDF, current_pdf), (REQ, current_req)):
        if old != (new_pdf if path == PDF else new_req):
            backup = path.with_name(path.name + ".pre_v717_" + stamp + ".bak")
            if backup.exists():
                raise CannotPatch("Backup path already exists; stopping to protect files.")
            backup.write_text(old, encoding="utf-8")
            print("Backup:", backup.name)
    if current_pdf != new_pdf:
        PDF.write_text(new_pdf, encoding="utf-8")
    if current_req != new_req:
        REQ.write_text(new_req, encoding="utf-8")
    print("V7.17 integration installed locally. Changes NOT committed, pushed or deployed.")
    print("Next: python -m unittest TEST_V7_17_ADVANCED_PDF -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
