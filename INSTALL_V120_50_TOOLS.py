"""V12.0 50-tools development expansion. No production feature flags or routes changed.

Usage: python INSTALL_V120_50_TOOLS.py --check | --apply
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / 'V120_50_TOOLS_PAYLOAD'
FILES = ('super_miniapp_v120.html', 'super_miniapp_v120.css', 'super_miniapp_v120.js', 'super_miniapp_v120_tools.mjs', 'TEST_SUPER_TOOLS_V120.mjs', 'TEST_SUPER_TOOLS_EXPANSION_V120.mjs')
BASE_HASHES = {'super_miniapp_v120.html': '1a1366bd47e207d536c93025f4a57fcb16e4350b494448daee2d7417e2f1565a', 'super_miniapp_v120.css': '68dd17759bbdfb37a789fa8f7ae20921882e2628aa959854110bf4e5c73f1106', 'super_miniapp_v120.js': '8726ae05ffec611ba900be5b3b0ddb810de00c19da4c01ad7947a130cd2f8aa2', 'super_miniapp_v120_tools.mjs': '7f577abcb398a2bebad66ffcd47dc69db59b7ce22a197f4be9aedc48233232f8', 'TEST_SUPER_TOOLS_V120.mjs': '1497eb539537ddc5096c016f6e5b5ddbc2d9aeffc45de10b7c695e47ee81b055'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def planned(root=ROOT, payload=PAYLOAD):
    root, payload = Path(root), Path(payload)
    main = root / 'main.py'
    if not main.exists() or 'register_super_miniapp(app)' not in main.read_text(encoding='utf-8'):
        raise ValueError('V12.0 preview registration missing in main.py. Install and test the existing preview first.')
    changes=[]
    for name in FILES:
        source = payload / name
        dest = root / name
        if not source.is_file():raise ValueError('Missing package file: '+name)
        if dest.is_symlink():raise ValueError('Refusing to overwrite a symbolic link: '+name)
        if not dest.exists():
            if name in BASE_HASHES:raise ValueError('Existing preview file missing: '+name)
            changes.append((name, 'ADD'))
        elif digest(dest)==digest(source):
            changes.append((name, 'UNCHANGED'))
        elif name in BASE_HASHES and digest(dest)==BASE_HASHES[name]:
            changes.append((name, 'UPDATE'))
        else:raise ValueError('Local file differs from the tested preview: '+name+'; manual review required. No files changed.')
    return changes

def apply(root=ROOT, payload=PAYLOAD):
    changes=planned(root,payload)
    if all(status=='UNCHANGED' for _,status in changes):return changes, None
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    backup=Path(root)/('V120_50_TOOLS_BACKUP_'+stamp)
    backup.mkdir(exist_ok=False)
    original={}
    try:
        for name,status in changes:
            if status=='UNCHANGED':continue
            dest=Path(root)/name;source=Path(payload)/name
            if dest.exists():
                original[name]=dest.read_bytes()
                shutil.copy2(dest,backup/name)
            else:original[name]=None
            temp=dest.with_name('.v120_next_'+name)
            try:
                shutil.copy2(source,temp)
                os.replace(temp,dest)
            finally:
                temp.unlink(missing_ok=True)
    except Exception:
        for name,old in original.items():
            dest=Path(root)/name
            if old is None:dest.unlink(missing_ok=True)
            else:dest.write_bytes(old)
        raise
    return changes, backup

def main():
    parser=argparse.ArgumentParser(description='V12.0 protected Mini App tool expansion')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    args=parser.parse_args()
    try:
        if args.check:changes=planned();backup=None
        else:changes,backup=apply()
    except (OSError,ValueError) as e:
        parser.exit(1,'ERROR: '+str(e)+'\n')
    print('V12.0 50-tool development expansion (production flag remains OFF)')
    for name,status in changes:print(f'  {status:9} {name}')
    if args.check:print('CHECK OK. No changes applied.')
    else:
        print('APPLIED.' if backup else 'NO CHANGES. Already installed.')
        if backup:print('Backup:',backup)
        print('Run Python tests, Node tests, and full regression before any deployment.')
        print('Keep SUPER_MINIAPP_V120_ENABLED=false in Render.')

if __name__=='__main__':main()
