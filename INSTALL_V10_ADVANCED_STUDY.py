"""Idempotent, narrow V10 integration for existing StudentAssistantBot.

--check prints proposed diff, never writes. --apply backs up touched files.
"""
from __future__ import annotations
import argparse, difflib, shutil
from pathlib import Path
from datetime import datetime, timezone

LABEL='🧠 V10 Learning Lab'
MAIN_SNIP=(
    '# V10.0 opt-in Learning Lab. Register before V9/V8 state handlers.\n'
    'from v10_bot import register_v10_handlers\n'
    'register_v10_handlers(bot)\n\n'
)
UI_SNIP=(
    '# V10.0 optional Learning Lab: feature is hidden unless explicitly enabled.\n'
    'import os as _v10_os\n'
    'if _v10_os.getenv("V10_ENABLED", "").strip().lower() in ("true", "yes", "1"):\n'
    '    CATEGORY_FEATURES[CAT_MORE].insert(0, "🧠 V10 Learning Lab")\n\n'
)
NAV_SNIP=(
    '# V10.0 optional Learning Lab button should pass through legacy states.\n'
    'import os as _v10_nav_os\n'
    'if _v10_nav_os.getenv("V10_ENABLED", "").strip().lower() in ("true", "yes", "1"):\n'
    '    GLOBAL_BUTTONS.add("🧠 V10 Learning Lab")\n\n'
)


def transform(name,source):
    if name=='main.py':
        if 'register_v10_handlers(bot)' in source:return source
        for anchor in ['register_v93_reliability_handlers(bot)',
                       'register_v92_admin_handlers(bot)',
                       'register_v91_access_handlers(bot)']:
            if anchor in source:
                idx=source.index(anchor)+len(anchor)
                # Insert after existing registration, preserving the following newline.
                return source[:idx]+'\n\n'+MAIN_SNIP.rstrip('\n')+source[idx:]
        anchor='from v9_bot import register_v9_handlers'
        if anchor in source:return source.replace(anchor,MAIN_SNIP+anchor,1)
        raise ValueError('Missing expected V9 or V9.1/V9.2/V9.3 main.py registration anchor; no edits made.')
    if name=='ui_v57.py':
        if '🧠 V10 Learning Lab' in source:return source
        anchor='ALL_UI_BUTTONS ='
        if anchor not in source:raise ValueError('Missing UI button-set anchor.')
        return source.replace(anchor,UI_SNIP+anchor,1)
    if name=='navigation.py':
        if '🧠 V10 Learning Lab' in source:return source
        anchor='GLOBAL_BUTTONS.add("📝 Text → PDF")'
        if anchor not in source:raise ValueError('Missing navigation global-button anchor.')
        return source.replace(anchor,NAV_SNIP+anchor,1)
    raise ValueError('Unexpected filename')


def integrate(root,apply=False,output=print):
    root=Path(root)
    files=['main.py','ui_v57.py','navigation.py']
    planned={}
    for fname in files:
        path=root/fname
        if not path.is_file():raise FileNotFoundError(str(path))
        raw=path.read_bytes()
        src=raw.decode('utf-8-sig')
        dst=transform(fname,src)
        eol='\r\n' if b'\r\n' in raw else '\n'
        if eol=='\r\n':
            dst=dst.replace('\r\n','\n').replace('\n','\r\n')
        prefix=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
        written=prefix+dst.encode('utf-8')
        planned[fname]=(raw,written)
    changed=[f for f,(before,after) in planned.items() if before!=after]
    if not changed:
        output('V10 already integrated. No files changed.');return []
    if not apply:
        for fname in changed:
            original,replaced=planned[fname]
            diff=difflib.unified_diff(original.decode('utf-8-sig').splitlines(True),
                                      replaced.decode('utf-8-sig').splitlines(True),
                                      fromfile=f'{fname}:current',tofile=f'{fname}:planned')
            output(''.join(diff))
        output('CHECK OK. No files changed.');return changed
    backup=root/('V10_BACKUP_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(exist_ok=False)
    for fname in changed:shutil.copy2(root/fname,backup/fname)
    try:
        for fname in changed:(root/fname).write_bytes(planned[fname][1])
    except Exception:
        for fname in changed:shutil.copy2(backup/fname,root/fname)
        raise
    output('V10 integrated. Backups: '+str(backup))
    output('Updated: '+', '.join(changed))
    return changed


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    integrate(Path(__file__).resolve().parent,apply=args.apply)
