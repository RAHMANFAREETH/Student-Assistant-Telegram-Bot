"""V11.8.6.2: isolate legacy Book Library tests from newer live feature flags.

Changes four TEST_*.py files only. Usage: --check or --apply.
No network/database calls, credentials, or production modules are modified.
"""
from __future__ import annotations
import argparse
import difflib
import datetime as dt
from pathlib import Path
import shutil

MARK = "# V11.8.6.2 legacy-only test environment"
RULES = {
    'TEST_BOOK_LIBRARY.py': (
        "            'BOOK_LIBRARY_ENABLED':'true','BOOK_LIBRARY_ADMIN_IDS':'7',",
        "            'LIBRARY_MEDIA_V117_ENABLED':'false', 'BOOK_LIBRARY_V112_ENABLED':'false',\n"
        "            'BOOK_LIBRARY_ALLOW_ALL_GROUPS':'false',\n"
        "            'BOOK_LIBRARY_PRIVATE_GROUP_RESULTS':'false',  " + MARK + "\n",
    ),
    'TEST_BOOK_LIBRARY_V112.py': (
        "            'BOOK_LIBRARY_ENABLED':'true','BOOK_LIBRARY_V112_ENABLED':'true',",
        "            'LIBRARY_MEDIA_V117_ENABLED':'false',\n"
        "            'BOOK_LIBRARY_PRIVATE_GROUP_RESULTS':'false',  " + MARK + "\n",
    ),
    'TEST_BOOK_LIBRARY_PRIVACY_V114.py': (
        "          'BOOK_LIBRARY_V113_ENABLED':'false', 'BOOK_LIBRARY_AUTO_GROUP_SEARCH':'true',",
        "          'LIBRARY_MEDIA_V117_ENABLED':'false',  " + MARK + "\n",
    ),
    'TEST_BOOK_PUBLIC_LATEST5.py': (
        "            'BOOK_LIBRARY_ENABLED': 'true',",
        "            'LIBRARY_MEDIA_V117_ENABLED':'false', 'BOOK_LIBRARY_V112_ENABLED':'false',\n"
        "            'BOOK_LIBRARY_PRIVATE_GROUP_RESULTS':'false',  " + MARK + "\n",
    ),
}

def transform(name: str, before: str) -> str:
    anchor, addition = RULES[name]
    if MARK in before:
        if before.count(MARK) != 1:
            raise ValueError(f'{name}: unexpected duplicate patch marker')
        return before
    if before.count(anchor) != 1:
        raise ValueError(f'{name}: expected one known source anchor; found {before.count(anchor)}. Aborting.')
    new = before.replace(anchor, anchor + '\n' + addition, 1)
    compile(new, name, 'exec')
    return new

def plan(root: Path):
    changes = {}
    for name in RULES:
        path = root/name
        if not path.exists():
            raise FileNotFoundError(f'{name} missing. Place patch next to your TEST_*.py modules.')
        old = path.read_text(encoding='utf-8')
        new = transform(name, old)
        if new != old:
            changes[name] = (old, new)
    return changes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    opts=p.add_mutually_exclusive_group(required=True)
    opts.add_argument('--check', action='store_true')
    opts.add_argument('--apply', action='store_true')
    args=p.parse_args()
    root=Path(__file__).resolve().parent
    changes=plan(root)
    if not changes:
        print('V11.8.6.2 already installed; no files changed.')
        return
    if args.check:
        for name, (old,new) in changes.items():
            print('\n'.join(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile=name+':current',tofile=name+':planned',lineterm='')))
        print('CHECK OK. No files changed.')
        return
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=root/('V11862_TEST_BACKUP_'+stamp)
    backup.mkdir(exist_ok=False)
    written=[]
    try:
        for name in changes:
            shutil.copy2(root/name,backup/name)
        for name, (_,new) in changes.items():
            temp=root/(name+'.v11862.tmp')
            try:
                temp.write_text(new,encoding='utf-8')
                temp.replace(root/name)
            finally:
                if temp.exists():temp.unlink()
            written.append(name)
    except BaseException:
        for name in written:
            shutil.copy2(backup/name,root/name)
        raise
    print('V11.8.6.2 legacy test isolation installed.')
    print('Backup:', backup)
    print('Updated TEST files:', ', '.join(changes))
    print('Production code, database, and Render settings unchanged.')

if __name__=='__main__':
    main()
