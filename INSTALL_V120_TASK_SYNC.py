"""Guarded V12.0 task sync + partial result localization preview patch.

python INSTALL_V120_TASK_SYNC.py --check  # no writes
python INSTALL_V120_TASK_SYNC.py --apply  # backup + copy only named files

Never touches main.py, original /library, old database tables, or feature flags.
Supabase SQL is copied to disk for manual review, NOT executed.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / 'V120_TASK_SYNC_PAYLOAD'
BASE_HASHES = {
 'super_miniapp_v120.py':'bc0b6fd159d0627e308313691ca0a77fdae2439433b9fb13208bbf1f7e654805',
 'super_miniapp_v120.html':'066d274e1da3a0368d265d921bceec01a03dab1814cb570004b8bd588197caf6',
 'super_miniapp_v120.js':'ed5a9e91bd78a78912d00fd72e8e27617ab5eee6e361abed7f839b845c1a1ffd',
 'super_miniapp_v120_tools.mjs':'4763de74493a0c33b3af43a88d2fd1e8cbb5f396c3879fc3f21aebd511a83e06',
 'TEST_SUPER_MINIAPP_V120.py':'b1cdceb144d70f81946fd8c8d7a2ead0a8794926f3584ca3e7b5174e79e5145d',
}
NEW_FILES = (
 'super_miniapp_v120_tasks.py',
 'super_miniapp_v120_results.mjs',
 'TEST_SUPER_TASK_SYNC_V120.py',
 'TEST_SUPER_TASK_SYNC_V120.mjs',
 'SQL_V120_QUICK_TASKS.sql',
)
FILES = tuple(BASE_HASHES) + NEW_FILES


def digest(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def planned(root=ROOT,payload=PAYLOAD):
 root,payload=Path(root),Path(payload)
 main=root/'main.py'
 if not main.is_file() or 'register_super_miniapp(app)' not in main.read_text(encoding='utf-8'):
  raise ValueError('V12 Super Mini App must already be registered in main.py.')
 if not (root/'TEST_SUPER_PLANNER_V120.py').is_file() or not (root/'TEST_SUPER_LOCALE_PLANNER_V120.mjs').is_file():
  raise ValueError('Install the earlier V12 planner/localization patch first.')
 output=[]
 for name in FILES:
  source=payload/name; dest=root/name
  if not source.is_file() or source.is_symlink():raise ValueError('Missing or unsafe payload: '+name)
  if dest.is_symlink():raise ValueError('Refusing symbolic link: '+name)
  if dest.is_file():
   if digest(dest)==digest(source):status='UNCHANGED'
   elif name in BASE_HASHES and digest(dest)==BASE_HASHES[name]:status='UPDATE'
   else:raise ValueError('Unexpected local changes in '+name+'; do not overwrite. No files changed.')
  elif name in BASE_HASHES:raise ValueError('Missing V12 baseline asset: '+name)
  elif dest.exists():raise ValueError('Destination is not a regular file: '+name)
  else:status='ADD'
  output.append((name,status))
 return output


def apply(root=ROOT,payload=PAYLOAD):
 actions=planned(root,payload)
 changes=[(name,status) for name,status in actions if status!='UNCHANGED']
 if not changes:return actions,None
 root,payload=Path(root),Path(payload)
 backup=root/('V120_TASK_SYNC_BACKUP_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
 backup.mkdir(exist_ok=False)
 previous={}
 try:
  for name,_ in changes:
   src=payload/name;dst=root/name
   previous[name]=dst.read_bytes() if dst.is_file() else None
   if dst.is_file():shutil.copy2(dst,backup/name)
   tmp=root/('.v120_task_next_'+name)
   try:
    shutil.copy2(src,tmp)
    os.replace(tmp,dst)
   finally:tmp.unlink(missing_ok=True)
 except Exception:
  for name,data in previous.items():
   dst=root/name
   if data is None:dst.unlink(missing_ok=True)
   else:dst.write_bytes(data)
  raise
 return actions,backup


def main():
 p=argparse.ArgumentParser(description='V12 preview: secure task sync and results localization')
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument('--check',action='store_true');g.add_argument('--apply',action='store_true')
 opts=p.parse_args()
 try:
  actions,backup=(planned(),None) if opts.check else apply()
 except (OSError,ValueError) as exc:p.exit(1,'ERROR: '+str(exc)+'\n')
 print('V12.0 Task Sync DEVELOPMENT PATCH (keep feature flag OFF)')
 for name,action in actions:print(f' {action:9} {name}')
 if opts.check:print('CHECK OK. No files changed.')
 else:
  print('APPLIED.' if backup else 'ALREADY APPLIED.')
  if backup:print('Backup:',backup)
  print('SQL file copied only. No database migration was executed.')
  print('Do not publicly deploy. Keep SUPER_MINIAPP_V120_ENABLED=false.')

if __name__=='__main__':main()
