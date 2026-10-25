"""Guarded V7.8 installer for a V7.7 material_library_v75.py.

Run from the StudentAssistantBot project root: python INSTALL_V7_8.py
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

TARGET = 'material_library_v75.py'
HELPER = 'material_reader_v78.py'
BACKUP = 'material_library_v75.py.before_v78.bak'
BUTTON_ANCHOR = "        markup.row(button('📥 TXT Extract', f'v77:req:txt:{material_id}'),"
BUTTON_INSERT = ("        markup.row(button('📖 Read Full Text', f'v78:read:{material_id}:0'),\n"
                 "                   button('🔎 Search Inside', f'v78:hint:{material_id}'))\n")
RETURN_ANCHOR = "    return {'show_library': show_library, 'show_preview': show_preview}"
REGISTER = ("    from material_reader_v78 import register_material_reader_handlers\n"
            "    register_material_reader_handlers(\n"
            "        bot, types_module, get_fn, material_state, show_library, show_preview\n"
            "    )\n\n")


class InstallationError(Exception):
    pass


def patch_code(source):
    source = source.replace('\r\n', '\n')
    flags = (BUTTON_INSERT.strip() in source, REGISTER.strip() in source)
    if all(flags):
        if source.count(BUTTON_INSERT.strip()) != 1 or source.count(REGISTER.strip()) != 1:
            raise InstallationError('Duplicate V7.8 integration detected.')
        ast.parse(source)
        return source, False
    if any(flags):
        raise InstallationError('Partial V7.8 integration detected; restore your backup.')
    if (source.count(BUTTON_ANCHOR) != 1
            or source.count(RETURN_ANCHOR) != 1
            or source.count('register_material_download_handlers(') != 1
            or 'register_material_filter_handlers(' not in source
            or source.count('def show_preview(chat_id, user_id, material_id):') != 1):
        raise InstallationError('Expected V7.7 material library structure not found; unchanged.')
    patched = source.replace(BUTTON_ANCHOR, BUTTON_INSERT + BUTTON_ANCHOR, 1)
    patched = patched.replace(RETURN_ANCHOR, REGISTER + RETURN_ANCHOR, 1)
    ast.parse(patched)
    return patched, True


def install(root=Path('.')):
    root = Path(root)
    target, helper, backup = root / TARGET, root / HELPER, root / BACKUP
    if not target.is_file() or not helper.is_file():
        raise InstallationError('Copy the V7.8 files into the StudentAssistantBot folder first.')
    original_bytes = target.read_bytes()
    try:
        text = original_bytes.decode('utf-8')
    except UnicodeError:
        raise InstallationError('Expected a UTF-8 Python source file.') from None
    patched, changed = patch_code(text)
    if not changed:
        print('V7.8 already installed; no files changed.')
        return False
    if backup.exists():
        raise InstallationError(f'Existing {BACKUP} would be overwritten.')
    ast.parse(helper.read_text(encoding='utf-8'))
    data = patched.replace('\n', '\r\n' if b'\r\n' in original_bytes else '\n').encode('utf-8')
    backup.write_bytes(original_bytes)
    temp = root / (TARGET + '.v78.tmp')
    try:
        temp.write_bytes(data)
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    print('V7.8 installed. Original saved byte-for-byte in ' + BACKUP)
    return True


if __name__ == '__main__':
    try:
        install()
    except InstallationError as error:
        print('INSTALL BLOCKED:', error)
        sys.exit(1)
