"""Install V7.6 safely on top of the exact V7.5 Material Library structure.

Updates material_library_v75.py only. Makes an exact-byte backup first.
Run in the StudentAssistantBot project directory: python INSTALL_V7_6.py
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

TARGET = 'material_library_v75.py'
HELPER = 'material_filters_v76.py'
BACKUP = 'material_library_v75.py.before_v76.bak'
MENU_ANCHOR = "        markup.add(button('🔙 Materials Menu', 'v75:menu:0'))"
MENU_INSERT = "        markup.add(button('🧰 Filters & Stats', 'v76:menu'))\n"
RETURN_ANCHOR = "    return {'show_library': show_library, 'show_preview': show_preview}"
REGISTER = ('    from material_filters_v76 import register_material_filter_handlers\n'
            '    register_material_filter_handlers(\n'
            '        bot, types_module, list_fn, material_state, show_material_menu, show_library, clock=now\n'
            '    )\n\n')


class InstallationError(Exception):
    pass


def patch_code(text):
    marks = [MENU_INSERT.strip() in text, REGISTER.strip() in text]
    if all(marks):
        ast.parse(text)
        return text, False
    if any(marks):
        raise InstallationError('Partial V7.6 patch found; no change made.')
    if (text.count(MENU_ANCHOR) != 1 or text.count(RETURN_ANCHOR) != 1
            or 'def register_material_library_handlers(' not in text
            or "@bot.callback_query_handler(func=lambda c: str(getattr(c, 'data', '')).startswith('v75:'))" not in text):
        raise InstallationError('Unknown V7.5 Material Library version; no change made.')
    updated = text.replace(MENU_ANCHOR, MENU_INSERT + MENU_ANCHOR, 1)
    updated = updated.replace(RETURN_ANCHOR, REGISTER + RETURN_ANCHOR, 1)
    ast.parse(updated)
    return updated, True


def install(root=Path('.')):
    root = Path(root)
    target, helper, backup = root / TARGET, root / HELPER, root / BACKUP
    if not target.is_file() or not helper.is_file():
        raise InstallationError('Copy V7.6 Python files to the existing StudentAssistantBot folder first.')
    original = target.read_bytes()
    try:
        text = original.decode('utf-8').replace('\r\n', '\n')
    except UnicodeError:
        raise InstallationError('Material Library must be UTF-8.') from None
    updated, changed = patch_code(text)
    if not changed:
        print('V7.6 already installed; no files changed.')
        return False
    if backup.exists():
        raise InstallationError('Backup already exists; not overwriting it: ' + str(backup))
    ast.parse(helper.read_text(encoding='utf-8'))
    newline = '\r\n' if b'\r\n' in original else '\n'
    rewritten = updated.replace('\n', newline).encode('utf-8')
    backup.write_bytes(original)
    tmp = root / (TARGET + '.v76.tmp')
    try:
        tmp.write_bytes(rewritten)
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()
    print('V7.6 installed. Byte-for-byte backup: ' + BACKUP)
    return True


if __name__ == '__main__':
    try:
        install()
    except InstallationError as e:
        print('INSTALL BLOCKED:', e)
        sys.exit(1)
