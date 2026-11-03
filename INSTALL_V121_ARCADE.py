"""V12.1 Study/Mind Arcade guarded additive installer.

Adds a new self-contained Arcade alongside V12.0.2 rather than replacing any
V12.0.2 JS/CSS/tools or the Book Library. Python stdlib only.

Usage: python INSTALL_V121_ARCADE.py --check
       python INSTALL_V121_ARCADE.py --apply
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / 'V121_ARCADE_PAYLOAD'
FILES = (
    'super_miniapp_v121.py',
    'super_miniapp_v121.html',
    'super_miniapp_v121.css',
    'super_miniapp_v121_entry.css',
    'super_miniapp_v121_entry.mjs',
    'super_miniapp_v121_app.mjs',
    'super_miniapp_v121_data.mjs',
    'super_miniapp_v121_engine.mjs',
    'super_miniapp_v121_study.mjs',
    'super_miniapp_v121_mind.mjs',
    'super_miniapp_v121_helpers.mjs',
    'TEST_V121_ARCADE.py',
    'TEST_V121_ARCADE.mjs',
)
PYTHON = 'super_miniapp_v120.py'
HTML = 'super_miniapp_v120.html'
PY_NEEDLE = '    register_v120_exports(app)\n'
PY_ADD = ('    from super_miniapp_v121 import register_v121_arcade\n'
          '    register_v121_arcade(app)\n')
HTML_NEEDLE = '<script type="module" src="/app/assets/app.js"></script>'
HTML_ADD = '<script type="module" src="/app/assets/arcade-entry.mjs"></script>'


def regular(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def plan(root: Path, payload: Path):
    if not payload.is_dir() or payload.is_symlink():
        raise RuntimeError('Missing or unsafe V121_ARCADE_PAYLOAD directory.')
    actions = {}
    for name in FILES:
        source, target = payload / name, root / name
        if not regular(source):
            raise RuntimeError('Missing payload: ' + name)
        if target.is_symlink() or target.is_dir():
            raise RuntimeError('Unsafe target: ' + name)
        data = source.read_bytes()
        if target.exists():
            if target.read_bytes() != data:
                raise RuntimeError('Existing V12.1 file differs: ' + name + '. No changes made.')
            actions[name] = None
        else:
            if name.endswith('.py'):
                compile(data, name, 'exec')
            actions[name] = data

    source = root / PYTHON
    if not regular(source):
        raise RuntimeError('Missing or unsafe super_miniapp_v120.py; install V12.0.2 first.')
    # Preserve exact CRLF/LF line endings: Windows Git checkouts may use CRLF.
    src = source.read_bytes().decode('utf-8')
    newline = '\r\n' if '\r\n' in src else '\n'
    needle = PY_NEEDLE.replace('\n', newline)
    addition = PY_ADD.replace('\n', newline)
    if 'def register_super_miniapp(app):' not in src or needle not in src:
        raise RuntimeError('V12.0.2 export registration hook missing; no files modified.')
    if src.count(needle) != 1:
        raise RuntimeError('Expected one V12.0.2 hook; preserve customized code.')
    if 'register_v121_arcade(app)' in src:
        if src.count('register_v121_arcade(app)') != 1 or addition not in src:
            raise RuntimeError('Unknown V12.1 Python integration; do not overwrite.')
        actions[PYTHON] = None
    else:
        text = src.replace(needle, needle + addition, 1)
        compile(text, PYTHON, 'exec')
        actions[PYTHON] = text.encode('utf-8')

    source = root / HTML
    if not regular(source):
        raise RuntimeError('Missing or unsafe V12.0.2 HTML.')
    src = source.read_bytes().decode('utf-8')
    if 'id="app-shell"' not in src or src.count(HTML_NEEDLE) != 1:
        raise RuntimeError('Unknown V12.0.2 HTML layout; preserve original file.')
    if HTML_ADD in src:
        if src.count(HTML_ADD) != 1 or HTML_NEEDLE + HTML_ADD not in src:
            raise RuntimeError('Unrecognized existing V12.1 HTML integration.')
        actions[HTML] = None
    else:
        actions[HTML] = src.replace(HTML_NEEDLE, HTML_NEEDLE + HTML_ADD, 1).encode('utf-8')
    return actions


def install(root: Path, actions):
    todo = {name: contents for name, contents in actions.items() if contents is not None}
    if not todo:
        return None
    backup = root / ('V121_ARCADE_BACKUP_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(exist_ok=False)
    original = {}
    applied = []
    try:
        for name in todo:
            target = root / name
            if target.exists():
                original[name] = target.read_bytes()
                shutil.copy2(target, backup / name)
            else:
                original[name] = None
        for name, data in todo.items():
            target = root / name
            temp = root / (name + '.v121tmp')
            if temp.exists() or temp.is_symlink():
                raise RuntimeError('Unsafe leftover temporary file: ' + temp.name)
            try:
                with temp.open('xb') as f:
                    f.write(data)
                os.replace(temp, target)
                applied.append(name)
            finally:
                if temp.exists():
                    temp.unlink()
    except BaseException:
        for name in reversed(applied):
            target = root / name
            old = original[name]
            if old is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(old)
        raise
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    actions = plan(ROOT, PAYLOAD)
    for name, data in actions.items():
        print(('UNCHANGED ' if data is None else 'ADD ' if not (ROOT/name).exists() else 'UPDATE ') + name)
    if args.check:
        print('CHECK OK; no files modified.')
        return
    backup = install(ROOT, actions)
    if backup is None:
        print('NO CHANGES (already installed).')
    else:
        print('APPLIED. Backup:', backup)
    print('V12.1 ships DISABLED. Set SUPER_ARCADE_V121_ENABLED=true only after all tests and deployment.')
    print('Existing V12 tools, /library, main.py and Supabase are not changed.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(2)
