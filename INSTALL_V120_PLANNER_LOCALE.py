"""Protected V12.0 planner + trilingual UI development upgrade.

Usage:
  python INSTALL_V120_PLANNER_LOCALE.py --check
  python INSTALL_V120_PLANNER_LOCALE.py --apply

Only the named development assets/tests are touched. Existing bot, library, DB,
Render configuration, and production feature flag are never edited here.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
PAYLOAD=ROOT/'V120_PLANNER_LOCALIZATION_PAYLOAD'
BASE_HASHES={
 'super_miniapp_v120.py':'436b8508fe7d6fcb67b411e4715f340f666a62d07b62cf3a2115136c7950b881',
 'super_miniapp_v120.html':'1da39f7fbee782e12ec091aa6e295391583cbd5520787b95f7ec555af09dca33',
 'super_miniapp_v120.css':'a40d9c8201a4e7c704babe7bbed6d230e6515223a2cdcef3870c9a919b67d4db',
 'super_miniapp_v120.js':'04a2d75a7d8d20242802060ffc4c07cb9a85cbcc65a50a3e8832f8de4f0ed14d',
 'super_miniapp_v120_tools.mjs':'6e0461153a487079b89637e8e90e87b9ef5de89a324317c781c2d3c26ba40032',
 'TEST_SUPER_MINIAPP_V120.py':'559dcefd027d4af4c3163334997fe586cca207c3af000a1107130af28eb11bdf',
}
NEW_FILES=('TEST_SUPER_PLANNER_V120.py','TEST_SUPER_LOCALE_PLANNER_V120.mjs')
FILES=tuple(BASE_HASHES)+NEW_FILES

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def planned(root=ROOT,payload=PAYLOAD):
 root,payload=Path(root),Path(payload)
 main=root/'main.py'
 if not main.is_file() or 'register_super_miniapp(app)' not in main.read_text(encoding='utf-8'):
  raise ValueError('V12 preview not registered in main.py; run the existing V12 installer first.')
 result=[]
 for name in FILES:
  source=payload/name;dest=root/name
  if not source.is_file() or source.is_symlink():raise ValueError('Missing or unsafe package file: '+name)
  if dest.is_symlink():raise ValueError('Refusing symlink: '+name)
  if dest.is_file():
   current=digest(dest)
   if current==digest(source):action='UNCHANGED'
   elif name in BASE_HASHES and current==BASE_HASHES[name]:action='UPDATE'
   else:raise ValueError('Local changes found in '+name+'; review manually. No files changed.')
  elif name in BASE_HASHES:raise ValueError('Missing installed 50-tool baseline asset: '+name)
  elif dest.exists():raise ValueError('Not a regular file: '+name)
  else:action='ADD'
  result.append((name,action))
 return result

def apply(root=ROOT,payload=PAYLOAD):
 actions=planned(root,payload)
 changes=[(name,kind) for name,kind in actions if kind!='UNCHANGED']
 if not changes:return actions,None
 root,payload=Path(root),Path(payload)
 backup=root/('V120_PLANNER_LOCALE_BACKUP_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
 backup.mkdir(exist_ok=False)
 replaced={}
 try:
  for name,kind in changes:
   dest=root/name;source=payload/name
   replaced[name]=dest.read_bytes() if dest.is_file() else None
   if dest.is_file():shutil.copy2(dest,backup/name)
   temp=root/('.v120_next_'+name)
   try:
    shutil.copy2(source,temp)
    os.replace(temp,dest)
   finally:temp.unlink(missing_ok=True)
 except Exception:
  for name,data in replaced.items():
   dest=root/name
   if data is None:dest.unlink(missing_ok=True)
   else:dest.write_bytes(data)
  raise
 return actions,backup

def main():
 parser=argparse.ArgumentParser(description='Guarded V12.0 planner + localization development upgrade')
 group=parser.add_mutually_exclusive_group(required=True)
 group.add_argument('--check',action='store_true');group.add_argument('--apply',action='store_true')
 args=parser.parse_args()
 try:
  if args.check:actions=planned();backup=None
  else:actions,backup=apply()
 except (OSError,ValueError) as exc:parser.exit(1,'ERROR: '+str(exc)+'\n')
 print('V12.0 planner + multilingual forms development patch (production flag remains OFF)')
 for name,kind in actions:print(f'  {kind:9} {name}')
 if args.check:print('CHECK OK. No changes applied.')
 else:
  print('APPLIED.' if backup else 'ALREADY APPLIED.')
  if backup:print('Backup:',backup)
  print('Run focused Python, Node, and full regression tests before further steps.')
 print('Keep SUPER_MINIAPP_V120_ENABLED=false. No database migration required.')

if __name__=='__main__':main()
