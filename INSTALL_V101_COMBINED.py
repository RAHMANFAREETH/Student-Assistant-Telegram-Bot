"""Idempotent, minimal V10.1 integration into existing V10 Telegram bot.

--check: preview only. --apply: backup each modified file, then write. No Git/Supabase actions.
"""
from __future__ import annotations
import argparse,difflib,shutil
from datetime import datetime, timezone
from pathlib import Path

BUTTON='🧠 V10.1 All Features'
MAIN=(
    '# V10.1 combined study enhancements. Register before V10 and legacy stateful handlers.\n'
    'from v101_bot import register_v101_handlers\n'
    'register_v101_handlers(bot)\n\n'
)
UI=(
    '# V10.1 combined study menu: disabled until explicitly enabled.\n'
    'import os as _v101_os\n'
    'if _v101_os.getenv("V101_ENABLED", "").strip().lower() in ("true", "yes", "1"):\n'
    '    CATEGORY_FEATURES[CAT_MORE].insert(0, "🧠 V10.1 All Features")\n\n'
)
NAV=(
    '# V10.1 button bypasses older active feature sessions.\n'
    'import os as _v101_nav_os\n'
    'if _v101_nav_os.getenv("V101_ENABLED", "").strip().lower() in ("true", "yes", "1"):\n'
    '    GLOBAL_BUTTONS.add("🧠 V10.1 All Features")\n\n'
)

def transform(filename,text):
    if filename=='main.py':
        if 'register_v101_handlers(bot)' in text:return text
        anchor='register_v10_handlers(bot)'
        if anchor not in text:raise ValueError('Missing V10 registration; install V10 first.')
        return text.replace(anchor,MAIN+anchor,1)
    if filename=='ui_v57.py':
        if BUTTON in text:return text
        anchor='ALL_UI_BUTTONS ='
        if anchor not in text:raise ValueError('Missing UI set anchor.')
        return text.replace(anchor,UI+anchor,1)
    if filename=='navigation.py':
        if BUTTON in text:return text
        anchor='GLOBAL_BUTTONS.add("📝 Text → PDF")'
        if anchor not in text:raise ValueError('Missing navigation anchor.')
        return text.replace(anchor,NAV+anchor,1)
    raise ValueError('Unexpected target.')

def integrate(root,apply=False,output=print):
    root=Path(root)
    planned={}
    for name in ('main.py','ui_v57.py','navigation.py'):
        path=root/name
        if not path.is_file():raise FileNotFoundError(str(path))
        raw=path.read_bytes();source=raw.decode('utf-8-sig')
        dest=transform(name,source)
        if b'\r\n' in raw:dest=dest.replace('\r\n','\n').replace('\n','\r\n')
        prefix=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
        planned[name]=(raw,prefix+dest.encode('utf-8'))
    changed=[name for name,(x,y) in planned.items() if x!=y]
    if not changed:output('V10.1 already integrated. No files changed.');return []
    if not apply:
        for name in changed:
            before,after=planned[name]
            output(''.join(difflib.unified_diff(
                before.decode('utf-8-sig').splitlines(True),after.decode('utf-8-sig').splitlines(True),
                fromfile=f'{name}:current',tofile=f'{name}:planned')))
        output('CHECK OK. No files changed.');return changed
    backup=root/('V101_BACKUP_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for name in changed:shutil.copy2(root/name,backup/name)
    try:
        for name in changed:(root/name).write_bytes(planned[name][1])
    except Exception:
        for name in changed:shutil.copy2(backup/name,root/name)
        raise
    output('V10.1 integrated. Backups: '+str(backup))
    output('Updated: '+', '.join(changed))
    return changed

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    exclusive=parser.add_mutually_exclusive_group(required=True)
    exclusive.add_argument('--check',action='store_true')
    exclusive.add_argument('--apply',action='store_true')
    opts=parser.parse_args()
    integrate(Path(__file__).resolve().parent,apply=opts.apply)
