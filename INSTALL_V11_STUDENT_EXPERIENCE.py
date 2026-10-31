"""V11 idempotent installer. --check is read-only; --apply backs up then edits 3 files.

Avoids changing older bot modules, SQL, API configuration and secrets.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime, timezone
from pathlib import Path

BUTTON = '🚀 Study Center'
MAIN = (
    '# V11 Study Center: fast optional navigation before V10.1 and older stateful handlers.\n'
    'from v11_center import register_v11_handlers\n'
    'register_v11_handlers(bot)\n\n'
)
UI = (
    '# V11 lightweight Study Center menu entry.\n'
    'import os as _v11_os\n'
    'if _v11_os.getenv("V11_ENABLED", "").strip().lower() in ("true", "yes", "1"):\n'
    '    CATEGORY_FEATURES[CAT_MORE].insert(0, "🚀 Study Center")\n\n'
)
NAV = (
    '# V11 Study Center must bypass older in-progress text workflows.\n'
    'import os as _v11_nav_os\n'
    'if _v11_nav_os.getenv("V11_ENABLED", "").strip().lower() in ("true", "yes", "1"):\n'
    '    GLOBAL_BUTTONS.add("🚀 Study Center")\n\n'
)


def transform(filename, text):
    if filename == 'main.py':
        if 'register_v11_handlers(bot)' in text:
            return text
        anchor = 'register_v101_handlers(bot)'
        if anchor not in text:
            raise ValueError('Missing V10.1 registration. V11 needs the installed V10.1 release.')
        return text.replace(anchor, MAIN + anchor, 1)
    if filename == 'ui_v57.py':
        if BUTTON in text:
            return text
        anchor = 'ALL_UI_BUTTONS ='
        if anchor not in text:
            raise ValueError('Missing UI button index anchor.')
        return text.replace(anchor, UI + anchor, 1)
    if filename == 'navigation.py':
        if BUTTON in text:
            return text
        anchor = 'GLOBAL_BUTTONS.add("📝 Text → PDF")'
        if anchor not in text:
            raise ValueError('Missing navigation button anchor.')
        return text.replace(anchor, NAV + anchor, 1)
    raise ValueError('Unexpected integration file: ' + filename)


def integrate(root, apply=False, output=print):
    root = Path(root)
    planned = {}
    for name in ('main.py', 'ui_v57.py', 'navigation.py'):
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f'Missing existing bot module: {path}')
        original = path.read_bytes()
        src = original.decode('utf-8-sig')
        dst = transform(name, src)
        # Preserve CRLF and UTF-8 BOM in Windows source trees.
        if b'\r\n' in original:
            dst = dst.replace('\r\n', '\n').replace('\n', '\r\n')
        bom = b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
        planned[name] = (original, bom + dst.encode('utf-8'))
    changed = [k for k, (before, after) in planned.items() if before != after]
    if not changed:
        output('V11 already integrated. No files changed.')
        return []
    if not apply:
        for name in changed:
            before, after = planned[name]
            output(''.join(difflib.unified_diff(
                before.decode('utf-8-sig').splitlines(True),
                after.decode('utf-8-sig').splitlines(True),
                fromfile=name + ':current', tofile=name + ':planned')))
        output('CHECK OK. No files changed.')
        return changed
    backup = root / ('V11_BACKUP_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for name in changed:
        shutil.copy2(root / name, backup / name)
    try:
        for name in changed:
            (root / name).write_bytes(planned[name][1])
    except Exception:
        for name in changed:
            shutil.copy2(backup / name, root / name)
        raise
    output('V11 integrated. Backups: ' + str(backup))
    output('Updated: ' + ', '.join(changed))
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument('--check', action='store_true')
    command.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    integrate(Path(__file__).resolve().parent, apply=args.apply)
