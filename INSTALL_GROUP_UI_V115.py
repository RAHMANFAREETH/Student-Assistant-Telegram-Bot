"""Fail-safe, idempotent integration of V11.5 into current main.py.

Only adds one block, BEFORE any Telegram message handlers. Preserves V11.4.
"""
from __future__ import annotations
import argparse
import difflib
from datetime import datetime
from pathlib import Path
import shutil
import re

MARK = '# V11.5: group menus are private, and temporary public book links expire.'
BLOCK = (MARK + '\n'
         'from group_ui_v115 import install_group_ui_guard\n'
         'install_group_ui_guard(bot)\n\n')
ANCHOR = re.compile(r'(?m)^app\s*=\s*Flask\(__name__\)\s*$')


def transform(code: str):
    if MARK in code:
        if code.count(MARK) != 1:
            raise ValueError('Duplicate V11.5 integration. Stop and review main.py.')
        return code
    hits = list(ANCHOR.finditer(code))
    if len(hits) != 1:
        raise ValueError('Expected Flask app anchor not found exactly once. No files changed.')
    # bot must already exist when install_group_ui_guard(bot) is called.
    if not re.search(r'(?m)^bot\s*=\s*telebot\.TeleBot\s*\(', code[:hits[0].start()]):
        raise ValueError('TeleBot must be created before Flask app. No files changed.')
    return code[:hits[0].start()] + BLOCK + code[hits[0].start():]


def integrate(root, *, apply=False):
    path = Path(root)/'main.py'
    source = path.read_text(encoding='utf-8')
    updated = transform(source)
    if updated == source:
        print('V11.5 already integrated; no files changed.')
        return False
    if not apply:
        for line in difflib.unified_diff(source.splitlines(True), updated.splitlines(True),
                                         fromfile='main.py:current', tofile='main.py:planned'):
            print(line, end='')
        print('CHECK OK. No files changed.')
        return True
    compile(updated, str(path), 'exec')
    backup = Path(root)/('V115_GROUP_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(exist_ok=False)
    shutil.copy2(path, backup/path.name)
    temp = path.with_suffix('.py.v115temp')
    try:
        temp.write_text(updated, encoding='utf-8')
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    print(f'V11.5 integrated. Original main.py: {backup/path.name}')
    return True


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check', action='store_true')
    action.add_argument('--apply', action='store_true')
    opts=parser.parse_args()
    integrate(Path(__file__).resolve().parent, apply=opts.apply)
