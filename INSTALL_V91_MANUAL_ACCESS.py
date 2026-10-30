"""Apply a minimal V9.1 manual adult onboarding integration.

--check: unified diff, no file changes.
--apply: version-tolerant anchored edits, backups, and fail-closed behavior.
Run from the existing StudentAssistantBot project root with required new
modules already copied alongside this installer.
"""
from __future__ import annotations
import argparse
import difflib
from datetime import datetime
from pathlib import Path
import shutil

FILES = ('main.py','ui_v57.py','navigation.py')
NEEDED = ('adult_requests_v91.py','v91_access_bot.py','SQL_V91_MANUAL_ADULT_ACCESS.sql',
          'TEST_V91_MANUAL_ACCESS.py')

MAIN_ANCHOR = 'from v9_bot import register_v9_handlers\nregister_v9_handlers(bot, show_main_menu)'
MAIN_ADD = '''# V9.1 administrator-reviewed age eligibility (before V9 and V8 handlers).
from v91_access_bot import register_v91_access_handlers
register_v91_access_handlers(bot)

'''
UI_ANCHOR = 'ALL_UI_BUTTONS = (set(CATEGORY_FEATURES)'
UI_ADD = '''# V9.1: verification requests are available even before V8/V9 authorization.
import os as _v91_os
if _v91_os.getenv("V91_ACCESS_REQUESTS_ENABLED", "").lower() in ("true", "1", "yes"):
    CATEGORY_FEATURES[CAT_MORE].insert(0, "🔐 Verify Adult Access")

'''
NAV_ANCHOR = 'GLOBAL_BUTTONS.add("📝 Text → PDF")'
NAV_ADD = '''# V9.1: preserve the request action while legacy workflows are active.
import os as _v91_os
if _v91_os.getenv("V91_ACCESS_REQUESTS_ENABLED", "").lower() in ("true", "1", "yes"):
    GLOBAL_BUTTONS.add("🔐 Verify Adult Access")

'''


def edited(name: str, old: str) -> str:
    if name == 'main.py':
        anchor, added, position = MAIN_ANCHOR, MAIN_ADD, 'before'
    elif name == 'ui_v57.py':
        anchor, added, position = UI_ANCHOR, UI_ADD, 'before'
    elif name == 'navigation.py':
        anchor, added, position = NAV_ANCHOR, NAV_ADD, 'before'
    else:
        raise ValueError(name)
    if added in old:
        return old
    if old.count(anchor) != 1:
        raise ValueError(f'{name}: safe integration anchor missing/duplicated; STOP, do not overwrite')
    if name == 'main.py':
        return old.replace(anchor, added+anchor, 1)
    return old.replace(anchor, added+anchor, 1)


def run(root: Path, apply=False):
    for name in (*FILES, *NEEDED):
        if not (root/name).is_file():
            raise FileNotFoundError('Required file missing: '+name)
    original = {name:(root/name).read_text(encoding='utf8') for name in FILES}
    proposed = {name:edited(name,src) for name,src in original.items()}
    for name in FILES:
        if original[name]==proposed[name]:
            print(name+': already installed')
        else:
            print(''.join(difflib.unified_diff(original[name].splitlines(True),
                proposed[name].splitlines(True), fromfile=name+':current', tofile=name+':planned')))
    if not apply:
        print('CHECK OK. No files changed.')
        return
    changed=[n for n in FILES if original[n]!=proposed[n]]
    if not changed:
        print('Already installed. No files changed.')
        return
    backup=root/('V91_ACCESS_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(exist_ok=False)
    try:
        for name in changed:
            shutil.copy2(root/name,backup/name)
        for name in changed:
            (root/name).write_text(proposed[name],encoding='utf8',newline='\n')
    except Exception:
        for name in changed:
            if (backup/name).exists(): shutil.copy2(backup/name,root/name)
        raise
    print('Applied V9.1 request handler integration. Backup:',backup)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    run(Path(__file__).resolve().parent,apply=args.apply)
