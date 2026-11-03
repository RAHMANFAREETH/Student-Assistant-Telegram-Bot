"""Guarded additive V12 Telegram command/URL pilot gate integration.

Only modifies main.py and super_miniapp_v120.py in the project directory.
Source/test/SQL files are distributed by the ZIP extraction, not mutated here.
"""
from __future__ import annotations

import argparse
import difflib
from datetime import datetime
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE / 'main.py'
APP = HERE / 'super_miniapp_v120.py'
MARKER = '# >>> V12.0 PRIVATE SUPER APP LAUNCH >>>'
AUTH_MARKER = '    # V12.0 optional server-side pilot gate; HMAC and adult checks run first.'
MAIN_ANCHOR = '# ==================================================\n# /HELP\n# =================================================='
MAIN_INSERT = '''# >>> V12.0 PRIVATE SUPER APP LAUNCH >>>
# Opt-in /superapp and /app commands. Do not replace current BotFather menu.
from super_miniapp_v120_launch import register_super_app_launcher
register_super_app_launcher(bot)
# <<< V12.0 PRIVATE SUPER APP LAUNCH <<<

'''
APP_ANCHOR = '    return uid\n\n\ndef register_super_miniapp(app):'
APP_REPLACEMENT = '''    # V12.0 optional server-side pilot gate; HMAC and adult checks run first.
    from super_miniapp_v120_launch import pilot_access_allowed
    if not pilot_access_allowed(uid):
        raise PermissionError("V12 pilot access is restricted.")
    return uid


def register_super_miniapp(app):'''


def plan(main: str, app: str) -> tuple[str, str]:
    if 'register_super_miniapp(app)' not in main:
        raise ValueError('V12 route integration is not present in main.py. Stop.')
    if MARKER in main:
        if main.count(MARKER) != 1 or 'register_super_app_launcher(bot)' not in main:
            raise ValueError('Existing V12 launcher marker is incomplete. Stop.')
        new_main = main
    else:
        if main.count(MAIN_ANCHOR) != 1:
            raise ValueError('Could not identify unique HELP registration anchor. Stop.')
        new_main = main.replace(MAIN_ANCHOR, MAIN_INSERT + MAIN_ANCHOR, 1)
    if AUTH_MARKER in app:
        if app.count(AUTH_MARKER) != 1 or 'if not pilot_access_allowed(uid)' not in app:
            raise ValueError('Existing V12 auth marker is incomplete. Stop.')
        new_app = app
    else:
        if app.count(APP_ANCHOR) != 1 or 'def verify_super_session' not in app:
            raise ValueError('Could not identify unique session authorization anchor. Stop.')
        new_app = app.replace(APP_ANCHOR, APP_REPLACEMENT, 1)
    compile(new_main, str(MAIN), 'exec')
    compile(new_app, str(APP), 'exec')
    return new_main, new_app


def run(apply: bool = False):
    for p in (MAIN, APP):
        if not p.is_file() or p.is_symlink():
            raise ValueError(f'Missing or symlinked file: {p.name}. Stop.')
    if not (HERE / 'super_miniapp_v120_launch.py').is_file():
        raise ValueError('Missing super_miniapp_v120_launch.py from ZIP extraction.')
    originals = (MAIN.read_text(encoding='utf-8'), APP.read_text(encoding='utf-8'))
    updated = plan(*originals)
    changes = [(p, original, new) for p, original, new in zip((MAIN, APP), originals, updated) if original != new]
    print('V12 Telegram launch PILOT PATCH (production flags remain OFF)')
    for p, old, new in changes:
        print('UPDATE', p.name)
        print(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                           fromfile=p.name+' (current)', tofile=p.name+' (proposed)')))
    if not changes:
        print('NO CHANGES (already applied)')
        return
    if not apply:
        print('CHECK OK (no files written)')
        return
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = HERE / ('V120_TELEGRAM_LAUNCH_BACKUP_' + stamp)
    backup.mkdir(mode=0o700)
    for p, _, _ in changes:
        shutil.copy2(p, backup / p.name)
    try:
        for p, _, new in changes:
            p.write_text(new, encoding='utf-8', newline='')
    except Exception:
        for p, _, _ in changes:
            shutil.copy2(backup / p.name, p)
        raise
    print('APPLIED. Backup:', backup)
    print('Keep SUPER_MINIAPP_V120_ENABLED=false and SUPER_MINIAPP_V120_LAUNCH_ENABLED=false.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    opts = parser.parse_args()
    try:
        run(opts.apply)
    except (OSError, ValueError, SyntaxError) as exc:
        print('STOP:', exc, file=sys.stderr)
        sys.exit(1)
