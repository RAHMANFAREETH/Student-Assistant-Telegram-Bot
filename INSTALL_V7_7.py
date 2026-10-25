"""Safely add V7.7 private extracted-text exports on top of V7.6.
Run: python INSTALL_V7_7.py from the StudentAssistantBot project root.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

TARGET = 'material_library_v75.py'
HELPER = 'material_download_v77.py'
BACKUP = 'material_library_v75.py.before_v77.bak'
BUTTON_ANCHOR = "        markup.row(button('🗑 Delete (confirm)', f'v75:del:{material_id}'),"
BUTTON_INSERT = ("        markup.row(button('📥 TXT Extract', f'v77:req:txt:{material_id}'),\n"
                 "                   button('📝 Markdown Extract', f'v77:req:md:{material_id}'))\n")
RETURN_ANCHOR = "    return {'show_library': show_library, 'show_preview': show_preview}"
REGISTER = ("    from material_download_v77 import register_material_download_handlers\n"
            "    register_material_download_handlers(bot, types_module, get_fn, material_state, clock=now)\n\n")

class InstallationError(Exception):
    pass


def patch_code(text):
    text = text.replace('\r\n', '\n')
    present = (BUTTON_INSERT.strip() in text, REGISTER.strip() in text)
    if all(present):
        if text.count(BUTTON_INSERT.strip()) != 1 or text.count(REGISTER.strip()) != 1:
            raise InstallationError('Duplicate V7.7 code detected.')
        ast.parse(text)
        return text, False
    if any(present):
        raise InstallationError('Partial V7.7 installation. Restore backup before retrying.')
    if (text.count(BUTTON_ANCHOR) != 1 or text.count(RETURN_ANCHOR) != 1
            or "register_material_filter_handlers(" not in text
            or 'def show_preview(chat_id, user_id, material_id):' not in text
            or "get_fn(user_id, material_id)" not in text):
        raise InstallationError('Expected V7.6 material library structure not found; no changes made.')
    updated = text.replace(BUTTON_ANCHOR, BUTTON_INSERT + BUTTON_ANCHOR, 1)
    updated = updated.replace(RETURN_ANCHOR, REGISTER + RETURN_ANCHOR, 1)
    ast.parse(updated)
    return updated, True


def install(root=Path('.')):
    root = Path(root)
    target, helper, backup = root / TARGET, root / HELPER, root / BACKUP
    if not target.is_file() or not helper.is_file():
        raise InstallationError('Copy V7.7 files into the existing project folder first.')
    original = target.read_bytes()
    try:
        source = original.decode('utf-8')
    except UnicodeError:
        raise InstallationError('Expected UTF-8 material library source.') from None
    updated, changed = patch_code(source)
    if not changed:
        print('V7.7 already installed; no files changed.')
        return False
    if backup.exists():
        raise InstallationError('Existing backup would be overwritten: ' + BACKUP)
    ast.parse(helper.read_text(encoding='utf-8'))
    data = updated.replace('\n', '\r\n' if b'\r\n' in original else '\n').encode('utf-8')
    backup.write_bytes(original)
    tmp = root / (TARGET + '.v77.tmp')
    try:
        tmp.write_bytes(data)
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()
    print('V7.7 installed. Original saved byte-for-byte in ' + BACKUP)
    return True

if __name__ == '__main__':
    try:
        install()
    except InstallationError as exc:
        print('INSTALL BLOCKED:', exc)
        sys.exit(1)
