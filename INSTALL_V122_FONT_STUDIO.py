"""Safe opt-in V12.2 Font Studio installer. --check (dry run), --apply (backup+patch)."""
from __future__ import annotations
import argparse
import difflib
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD=ROOT/'V122_FONT_STUDIO_PAYLOAD'
NEW_FILES = (
 'super_miniapp_v122_fonts.py', 'super_miniapp_v122_fonts.html',
 'super_miniapp_v122_fonts.css','super_miniapp_v122_fonts.js',
 'super_miniapp_v122_fonts.mjs','super_miniapp_v122_entry.mjs',
 'super_miniapp_v122_entry.css','TEST_V122_FONT_STUDIO.mjs',
 'TEST_V122_FONT_STUDIO.py','README_V122_FONT_STUDIO.md'
)

PY_ANCHOR='    register_v121_arcade(app)\n'
PY_PATCH='    from super_miniapp_v122_fonts import register_v122_fontstudio\n    register_v122_fontstudio(app)\n'
HTML_ANCHOR='<script type="module" src="/app/assets/arcade-entry.mjs"></script>'
HTML_PATCH='<script type="module" src="/app/assets/fontstudio-entry.mjs"></script>'

class LayoutError(RuntimeError):pass

def plan(root=ROOT, payload=PAYLOAD):
 for filename in NEW_FILES:
  file=payload/filename
  if not file.is_file():raise LayoutError(f'Missing payload: {file}')
 updates={}
 # Both modifications are minimal; no changes to existing JS engine, route order or Library.
 old=(root/'super_miniapp_v120.py').read_text(encoding='utf-8')
 if PY_PATCH not in old:
  if old.count(PY_ANCHOR)!=1:raise LayoutError('Unexpected super_miniapp_v120.py layout (missing V12.1 registration).')
  updates['super_miniapp_v120.py']=old.replace(PY_ANCHOR,PY_ANCHOR+PY_PATCH)
 old=(root/'super_miniapp_v120.html').read_text(encoding='utf-8')
 if HTML_PATCH not in old:
  if old.count(HTML_ANCHOR)!=1:raise LayoutError('Unexpected super_miniapp_v120.html layout (missing V12.1 entry).')
  updates['super_miniapp_v120.html']=old.replace(HTML_ANCHOR,HTML_ANCHOR+HTML_PATCH)
 for filename in NEW_FILES:
  dst=root/filename;data=(payload/filename).read_bytes()
  if dst.exists() and dst.read_bytes()!=data:raise LayoutError(f'Existing {filename} differs from payload. Refuse overwrite.')
 return updates

def execute(root=ROOT,payload=PAYLOAD,apply=False):
 updates=plan(root,payload)
 for filename,new in updates.items():
  old=(root/filename).read_text(encoding='utf-8')
  print(f'UPDATE {filename}')
  for line in difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile=filename+' old',tofile=filename+' V12.2',lineterm=''):
   print(line)
 for filename in NEW_FILES:
  if not (root/filename).exists():print(f'ADD    {filename}')
 if not apply:
  print('CHECK OK (dry run). Production settings and files unchanged.')
  return
 backup=None
 if updates:
  backup=root/('V122_FONT_STUDIO_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
  backup.mkdir()
  for name in updates:shutil.copy2(root/name,backup/name)
 try:
  for filename,text in updates.items():
   (root/filename).write_text(text,encoding='utf-8',newline='')
  for filename in NEW_FILES:
   dst=root/filename
   if not dst.exists():shutil.copy2(payload/filename,dst)
 except Exception:
  if backup:
   for name in updates:shutil.copy2(backup/name,root/name)
  raise
 print('APPLIED. New Studio remains disabled until the Render feature flag is enabled.')
 if backup:print('Original file backup:',backup)

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 modes=parser.add_mutually_exclusive_group(required=True)
 modes.add_argument('--check',action='store_true')
 modes.add_argument('--apply',action='store_true')
 a=parser.parse_args()
 try:execute(apply=a.apply)
 except (LayoutError,OSError) as exc:
  print('INSTALL REFUSED:',exc,file=sys.stderr);return 1
 return 0

if __name__=='__main__':raise SystemExit(main())
