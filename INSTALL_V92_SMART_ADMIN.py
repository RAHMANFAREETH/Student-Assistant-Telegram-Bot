"""Safe, idempotent V9.2 installer. One targeted edit: main.py.

--check prints unified diff without modifying anything.
--apply backs up main.py and adds V9.2 immediately after V9.1 registration.
"""
from __future__ import annotations

import argparse
import difflib
import shutil
from datetime import datetime
from pathlib import Path

ANCHOR = 'register_v91_access_handlers(bot)'
INTEGRATION = '''\n\n# V9.2 optional, administrator-only dashboard. Register before V9/V8 handlers.\nfrom v92_admin_bot import register_v92_admin_handlers\nregister_v92_admin_handlers(bot)'''
NEEDED = ('v92_admin_bot.py', 'v92_admin_service.py', 'v92_expiry_worker.py',
          'SQL_V92_SMART_ADMIN.sql', 'TEST_V92_SMART_ADMIN.py')


def edited(old):
    if INTEGRATION.strip() in old:
        return old
    if old.count(ANCHOR) != 1:
        raise ValueError('Missing/ambiguous V9.1 handler anchor in main.py. Stop; do not overwrite.')
    return old.replace(ANCHOR, ANCHOR + INTEGRATION, 1)


def run(root: Path, apply=False):
    for filename in ('main.py', 'v91_access_bot.py', 'adult_requests_v91.py', *NEEDED):
        if not (root / filename).is_file():
            raise FileNotFoundError('Missing dependency: ' + filename)
    path = root / 'main.py'
    old = path.read_text(encoding='utf-8')
    new = edited(old)
    if old == new:
        print('V9.2 already integrated; no files changed.')
        return
    print(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                       fromfile='main.py:current', tofile='main.py:planned')))
    if not apply:
        print('CHECK OK. No files changed.')
        return
    backup = root / ('V92_BACKUP_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    shutil.copy2(path, backup / 'main.py')
    try:
        path.write_text(new, encoding='utf-8', newline='\n')
    except Exception:
        shutil.copy2(backup / 'main.py', path)
        raise
    print('V9.2 integrated. Backed up original main.py to:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check', action='store_true')
    modes.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    run(Path(__file__).resolve().parent, apply=args.apply)
