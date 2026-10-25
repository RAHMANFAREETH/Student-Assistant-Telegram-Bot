"""Safe, repeatable V7.5 patch for existing Study Materials registration.

Run from your StudentAssistantBot project folder: python INSTALL_V7_5.py
"""
from __future__ import annotations
import ast
import os
import sys
from pathlib import Path

TARGET = 'study_materials.py'
HELPER = 'material_library_v75.py'
BACKUP = 'study_materials.py.before_v75.bak'
IMPORT = 'from material_library_v75 import register_material_library_handlers\n'
MENU_OLD = '            types.KeyboardButton(\n                "📂 My Materials"\n            ),'
MENU_NEW = '            types.KeyboardButton(\n                "📚 Material Library"\n            ),\n' + MENU_OLD
REG_ANCHOR = '    def show_material_list(\n'
REG = '    register_material_library_handlers(bot, show_material_menu, material_state)\n\n'

class InstallationError(Exception):
    pass


def patch_code(text):
    already = [IMPORT.strip() in text, '"📚 Material Library"' in text, REG.strip() in text]
    if all(already):
        ast.parse(text)
        return text, False
    if any(already):
        raise InstallationError('Partial V7.5 installation detected; no changes made.')
    if 'def register_study_material_handlers(' not in text or MENU_OLD not in text or text.count(REG_ANCHOR) != 1:
        raise InstallationError('Unknown Study Materials version; no changes made.')
    if text.count('from navigation import GLOBAL_BUTTONS') != 1 or text.count(MENU_OLD) != 1:
        raise InstallationError('Unexpected patch anchors; no changes made.')
    text = text.replace('from navigation import GLOBAL_BUTTONS\n',
                        'from navigation import GLOBAL_BUTTONS\n'+IMPORT, 1)
    text = text.replace(MENU_OLD, MENU_NEW, 1)
    text = text.replace(REG_ANCHOR, REG+REG_ANCHOR, 1)
    ast.parse(text)
    return text, True


def install(root=Path('.')):
    root = Path(root)
    path = root / TARGET
    helper = root / HELPER
    backup = root / BACKUP
    if not path.is_file() or not helper.is_file():
        raise InstallationError('Copy the V7.5 files directly into your existing StudentAssistantBot folder.')
    original = path.read_bytes()
    newline = '\r\n' if b'\r\n' in original else '\n'
    try:
        text = original.decode('utf-8').replace('\r\n', '\n')
    except UnicodeError:
        raise InstallationError('study_materials.py must use UTF-8 encoding.')
    updated, changed = patch_code(text)
    if not changed:
        print('V7.5 already installed; no files changed.')
        return False
    if backup.exists():
        raise InstallationError(f'Backup already exists: {backup}. No changes made.')
    ast.parse(helper.read_text(encoding='utf-8'))
    output = updated.replace('\n', newline).encode('utf-8')
    backup.write_bytes(original)
    tmp = root / (TARGET + '.v75.tmp')
    try:
        tmp.write_bytes(output)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    print('V7.5 installed into study_materials.py; original backed up as', BACKUP)
    return True


if __name__ == '__main__':
    try:
        install()
    except InstallationError as e:
        print('INSTALL BLOCKED:', e)
        sys.exit(1)
