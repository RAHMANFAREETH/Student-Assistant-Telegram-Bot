"""Idempotent V11.6 installer; changes only main.py with a verified anchor."""
from __future__ import annotations
import argparse
import difflib
from pathlib import Path
from datetime import datetime
import shutil

MARK = '# V11.6: only public Book Library searches may execute in group chats.'
ANCHOR = 'install_group_ui_guard(bot)'
BLOCK = ("\n" + MARK + "\n"
         'from group_books_only_v116 import install_book_only_group_gate\n'
         'install_book_only_group_gate(bot)\n')


def transform(source):
    if MARK in source:
        if source.count(MARK) != 1:
            raise ValueError('V11.6 integration duplicated; no changes made.')
        return source
    if source.count(ANCHOR) != 1:
        raise ValueError('Exactly one V11.5 installation anchor is required; no changes made.')
    anchor = source.index(ANCHOR) + len(ANCHOR)
    if 'register_book_library_handlers(bot)' in source[:anchor]:
        raise ValueError('V11.6 must precede Book Library handler registration.')
    new_source = source[:anchor] + BLOCK + source[anchor:]
    compile(new_source, 'main.py', 'exec')
    return new_source


def integrate(root, *, apply=False):
    path = Path(root)/'main.py'
    source = path.read_text(encoding='utf-8')
    updated = transform(source)
    if updated == source:
        print('V11.6 already integrated. No changes needed.')
        return False
    if not apply:
        for line in difflib.unified_diff(source.splitlines(True), updated.splitlines(True),
                    fromfile='main.py:current', tofile='main.py:planned'):
            print(line, end='')
        print('CHECK OK. No files changed.')
        return True
    backup = Path(root)/('V116_GROUP_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    shutil.copy2(path, backup/'main.py')
    temporary = path.with_suffix('.py.v116temp')
    try:
        temporary.write_text(updated, encoding='utf-8', newline='')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    print('V11.6 integrated. Original main.py backed up in: ' + str(backup))
    return True

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    args=parser.parse_args()
    integrate(Path(__file__).resolve().parent, apply=args.apply)
