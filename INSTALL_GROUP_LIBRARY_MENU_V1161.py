"""Safe V11.6.1 add-on installer: one early handler block in main.py."""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime
from pathlib import Path

MARK = '# V11.6.1: Book Library-only group menu before V11.5 navigation guard.'
ANCHOR = 'from group_ui_v115 import install_group_ui_guard'
NEW_BLOCK = (MARK + '\n'
             'from group_library_menu_v1161 import install_group_library_menu\n'
             'install_group_library_menu(bot)\n\n')


def transform(source: str) -> str:
    if MARK in source:
        if source.count(MARK) != 1 or source.count('install_group_library_menu(bot)') != 1:
            raise ValueError('V11.6.1 integration is duplicated or incomplete. No changes made.')
        return source
    if source.count(ANCHOR) != 1:
        raise ValueError('V11.5 registration anchor missing or duplicated. No changes made.')
    if 'install_book_only_group_gate(bot)' not in source:
        raise ValueError('V11.6 Book Library-only group gate is missing. No changes made.')
    if 'install_group_library_menu(bot)' in source:
        raise ValueError('V11.6.1 appears partially installed. No changes made.')
    idx = source.index(ANCHOR)
    updated = source[:idx] + NEW_BLOCK + source[idx:]
    compile(updated, 'main.py', 'exec')
    return updated


def integrate(root: Path, *, apply=False) -> bool:
    path = root/'main.py'
    source = path.read_text(encoding='utf-8')
    updated = transform(source)
    if source == updated:
        print('V11.6.1 group library menu already integrated; no files changed.')
        return False
    if not apply:
        print(''.join(difflib.unified_diff(source.splitlines(True), updated.splitlines(True),
            fromfile='main.py:current', tofile='main.py:planned')), end='')
        print('CHECK OK. No files changed.')
        return True
    backup = root/('V1161_MENU_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    shutil.copy2(path, backup/'main.py')
    tmp = root/'main.py.v1161_tmp'
    try:
        tmp.write_text(updated, encoding='utf-8', newline='')
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    print('V11.6.1 integrated. Original main.py backed up to:', backup)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    integrate(Path(__file__).resolve().parent, apply=args.apply)
