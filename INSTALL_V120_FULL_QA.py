"""Guarded V12.0 Mini App client rebuild. No backend, Supabase, or environment modifications.

Usage: python INSTALL_V120_FULL_QA.py --check / --apply

Only replaces audited V12 frontend assets and associated tests. Refuses unexpected
local modifications; read and confirm the diff before using --apply.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile

FILES = {
    "super_miniapp_v120.js":"a2201ae13e8f211c31338ea7dea46eac9f1082843d791481290a20f62b3ee8c6",
    "super_miniapp_v120_tools.mjs":"572157fd3a4e5ae78119afdf191f5bd8a423a80a547585cb4e2f40ddda72ab9d",
    "TEST_SUPER_TOOLS_V120.mjs":"63a19dd7aa3e1a2a19227f4eb802a9815ca4e59a013b1f57c631ab0e206602d0",
    "TEST_SUPER_TOOLS_EXPANSION_V120.mjs":"06f50da29cdf27273c3be8c42872619bbe2cb28072f346c3615e5006912b7f9b",
    "TEST_SUPER_LOCALE_PLANNER_V120.mjs":"c7f9ae9263f1b06dc497bf68dd982bfaa3e48ffb5a087e78a3f01592839277a3",
}
ADDED = ("TEST_V120_REBUILT_TOOLS.mjs",)
BASE = Path(__file__).resolve().parent
PAYLOAD = BASE / "V120_TOOL_QA_PAYLOAD"

def digest(text: str)->str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def source_path(root:Path,name:str)->Path:
    path = root / name
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Unsafe nonregular file: {name}")
    return path

def examine(root:Path):
    actions=[]
    for name,old_hash in FILES.items():
        path=source_path(root,name)
        if not path.exists():
            raise ValueError(f"Required file is missing: {name}")
        current=path.read_text(encoding='utf-8')
        target=(PAYLOAD/name).read_text(encoding='utf-8')
        if current==target:
            actions.append((name,'UNCHANGED'))
        elif digest(current)==old_hash:
            actions.append((name,'UPDATE'))
        else:
            raise ValueError(f"Unexpected local version of {name} (SHA256 {digest(current)[:16]}); no files changed. Do not force a replacement. Share a diff or hash first.")
    for name in ADDED:
        path=source_path(root,name)
        if not path.exists():
            actions.append((name,'ADD'))
        elif path.read_text(encoding='utf-8')==(PAYLOAD/name).read_text(encoding='utf-8'):
            actions.append((name,'UNCHANGED'))
        else:
            raise ValueError(f"Unexpected existing file: {name}")
    return actions

def process(root:Path,apply:bool=False):
    root=Path(root)
    actions=examine(root)  # all-or-nothing validation before any writes
    for name,mode in actions:
        print(f"{mode:9s} {name}")
    updates=[name for name,mode in actions if mode in ('UPDATE','ADD')]
    if not apply:
        print(f"CHECK OK ({len(updates)} pending changes; no files written)")
        return actions
    if not updates:
        print('NO CHANGES (already installed)')
        return actions
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=root/f'V120_TOOL_QA_BACKUP_{stamp}'
    backup.mkdir(mode=0o700)
    for name in updates:
        path=root/name
        if path.exists():
            shutil.copy2(path,backup/name)
    completed=[]
    try:
        for name in updates:
            target=root/name
            payload=(PAYLOAD/name).read_bytes()
            # New files are written atomically on the same filesystem.
            with tempfile.NamedTemporaryFile(dir=root,delete=False,prefix='.v120qa_',suffix='.tmp') as tmp:
                temp=Path(tmp.name);tmp.write(payload)
            try:
                if target.exists():
                    shutil.copymode(target,temp)
                temp.replace(target)
            finally:
                temp.unlink(missing_ok=True)
            completed.append(name)
    except Exception:
        for name in reversed(completed):
            old=backup/name
            if old.exists():shutil.copy2(old,root/name)
            else:(root/name).unlink(missing_ok=True)
        raise
    print(f'APPLIED. Backup: {backup}')
    print('No changes to main.py, Flask APIs, Supabase, Render or current bot commands.')
    return actions

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try:process(BASE,apply=args.apply)
    except (ValueError,OSError,UnicodeError) as exc:
        print('STOP:',exc,file=sys.stderr)
        sys.exit(1)
