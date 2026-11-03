#!/usr/bin/env python3
"""Guarded, idempotent installation of optional group welcome in main.py."""
from __future__ import annotations
import argparse, ast, difflib, os, shutil, sys
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent
MAIN = ROOT / 'main.py'
MODULE = ROOT / 'group_welcome_v11884.py'
ANCHOR = 'install_book_only_group_gate(bot)\n'
INSERT = ('install_book_only_group_gate(bot)\n'
          '\n# V11.8.8.4: optional group join welcome; search and adult gates unchanged.\n'
          'from group_welcome_v11884 import install_group_welcome\n'
          'install_group_welcome(bot)\n')

def process():
    if not MAIN.is_file() or not MODULE.is_file():
        raise ValueError('main.py or group_welcome_v11884.py is missing.')
    old = MAIN.read_text(encoding='utf-8')
    if INSERT in old:
        return old, old
    if old.count(ANCHOR) != 1:
        raise ValueError('Missing/ambiguous V11.6 group gate anchor; no changes made.')
    new = old.replace(ANCHOR, INSERT)
    ast.parse(new, filename='main.py')
    ast.parse(MODULE.read_text(encoding='utf-8'), filename=MODULE.name)
    return old, new

def main():
    ap=argparse.ArgumentParser()
    choices=ap.add_mutually_exclusive_group(required=True)
    choices.add_argument('--check', action='store_true')
    choices.add_argument('--apply', action='store_true')
    args=ap.parse_args()
    try:
        old,new=process()
    except Exception as exc:
        print('STOP:',exc,file=sys.stderr)
        return 2
    if args.check:
        if old!=new:
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
                  fromfile='main.py:current',tofile='main.py:planned')))
        print('CHECK OK. '+('One production file would change.' if old!=new else 'Already integrated.')+' Nothing modified.')
        return 0
    if old==new:
        print('V11.8.8.4 already integrated; no changes.')
        return 0
    folder=ROOT/('V11884_GROUP_WELCOME_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir()
    shutil.copy2(MAIN, folder/MAIN.name)
    tmp=MAIN.with_suffix('.py.v11884_tmp')
    tmp.write_text(new,encoding='utf-8')
    os.replace(tmp,MAIN)
    print('V11.8.8.4 installed. Original main.py backed up:',folder)
    print('Feature is OFF unless GROUP_WELCOME_V11884_ENABLED=true on Render.')
    return 0

if __name__=='__main__':raise SystemExit(main())
