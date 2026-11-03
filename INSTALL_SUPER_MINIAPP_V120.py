"""Guarded V12 development preview integration. No automatic deployment, no git actions.

Usage: python INSTALL_SUPER_MINIAPP_V120.py --check
       python INSTALL_SUPER_MINIAPP_V120.py --apply

Copies no files; unpack all files into the project first. On apply, patches only
main.py after a recognized V8 app registration. Backs up original atomically.
"""
from __future__ import annotations
import argparse
import datetime as dt
import difflib
import os
from pathlib import Path
import shutil
import sys
import tempfile

HERE=Path(__file__).resolve().parent
MAIN=HERE/'main.py'
ANCHOR='register_v8_miniapp(app)'
START='# >>> V12.0 SUPER MINI APP integration (opt-in) >>>'
END='# <<< V12.0 SUPER MINI APP integration <<<' 
BLOCK=(START+'\nfrom super_miniapp_v120 import register_super_miniapp\nregister_super_miniapp(app)\n'+END)
REQUIRED=['super_miniapp_v120.py','super_miniapp_v120.html','super_miniapp_v120.css','super_miniapp_v120.js','super_miniapp_v120_tools.mjs']


def planned(src: str) -> str:
    if START in src:
        if BLOCK not in src or src.count(START)!=1 or src.count(END)!=1:
            raise ValueError('Existing V12 marker is damaged; refusing automatic rewrite.')
        return src
    if 'register_super_miniapp' in src:
        raise ValueError('Unrecognized V12 registration; inspect main.py manually.')
    if src.count(ANCHOR)!=1 or 'app = Flask(__name__)' not in src:
        raise ValueError('Expected Flask/V8 registration not found exactly once; no changes made.')
    # Keep all old routes, handlers, and registrations unchanged.
    return src.replace(ANCHOR,ANCHOR+'\n\n'+BLOCK,1)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--check',action='store_true');g.add_argument('--apply',action='store_true')
    args=ap.parse_args(argv)
    missing=[f for f in REQUIRED if not (HERE/f).is_file()]
    if missing:
        print('ERROR: Missing required V12 files: '+', '.join(missing),file=sys.stderr);return 2
    if not MAIN.is_file():
        print('ERROR: main.py not found in this folder.',file=sys.stderr);return 2
    original=MAIN.read_text(encoding='utf-8-sig')
    try:target=planned(original)
    except ValueError as exc:
        print('ERROR:',exc,file=sys.stderr);return 2
    changed=original!=target
    print('V12.0 Super Mini App PREVIEW (not a full production release)')
    print('  main.py:',MAIN)
    print('  changed:',changed)
    print('  feature flag: SUPER_MINIAPP_V120_ENABLED=false by default')
    if changed:
        print(''.join(difflib.unified_diff(original.splitlines(True),target.splitlines(True),fromfile='main.py (current)',tofile='main.py (proposed)')))
    if args.check or not changed:
        print('CHECK OK' if args.check else 'Already installed; no changes.')
        return 0
    backup=HERE / (f'V120_SUPER_MINIAPP_BACKUP_{dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")}')
    backup.mkdir(exist_ok=False)
    shutil.copy2(MAIN,backup/'main.py')
    fd,tempfile_name=tempfile.mkstemp(prefix='.v120_main_',suffix='.py',dir=HERE)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:f.write(target)
        # Never leave a half-written main.py.
        os.replace(tempfile_name,MAIN)
    finally:
        if os.path.exists(tempfile_name):os.unlink(tempfile_name)
    print('APPLIED. Backup:',backup/'main.py')
    print('Keep SUPER_MINIAPP_V120_ENABLED=false until local testing is complete.')
    return 0

if __name__=='__main__':raise SystemExit(main())
