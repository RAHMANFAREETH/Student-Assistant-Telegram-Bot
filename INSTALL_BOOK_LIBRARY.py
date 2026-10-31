"""Safe, idempotent V11.1 Book Library integration.

--check: show a preview without changing anything.
--apply: back up and change only main.py and navigation.py.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime, timezone
from pathlib import Path

START = (
    '    # V11.1: deliver a Book Library deep link before the existing /start menu.\n'
    '    from book_library_bot import handle_library_start\n'
    '    if handle_library_start(bot, message):\n'
    '        return\n'
)
REGISTER = (
    '# V11.1: Book Library handlers must precede older wildcard document/text handlers.\n'
    'from book_library_bot import register_book_library_handlers\n'
    'register_book_library_handlers(bot)\n\n'
)
BUTTON_ROW = '    ("📚 Book Library",),\n'
BUTTON_GLOBAL = 'GLOBAL_BUTTONS.add("📚 Book Library")\n'


def transform(name, text):
    if name == 'main.py':
        if 'if handle_library_start(bot, message):' not in text:
            anchor = 'def start(message):\n'
            if text.count(anchor) != 1:
                raise ValueError('Cannot find the existing /start handler. No files modified.')
            text = text.replace(anchor, anchor + START, 1)
        if 'register_book_library_handlers(bot)' not in text:
            anchors = (
                'broadcast_service = register_broadcast_handlers(bot)',
                'register_ui_v57_handlers(bot, show_main_menu)',
                'register_v11_handlers(bot)',
            )
            anchor = next((a for a in anchors if a in text), None)
            if not anchor:
                raise ValueError('Cannot find an early handler registration anchor. No files modified.')
            text = text.replace(anchor, REGISTER + anchor, 1)
        return text
    if name == 'navigation.py':
        if BUTTON_ROW not in text:
            anchor = '    (UI_FILES, UI_MORE),\n'
            if anchor not in text:
                raise ValueError('Cannot find V5.7 main menu row. No files modified.')
            text = text.replace(anchor, anchor + BUTTON_ROW, 1)
        if BUTTON_GLOBAL not in text:
            anchor = 'GLOBAL_BUTTONS.add("📝 Text → PDF")'
            if anchor in text:
                text = text.replace(anchor, BUTTON_GLOBAL + anchor, 1)
            else:
                anchor = 'NAVIGATION_BUTTONS = {'
                if anchor not in text:
                    raise ValueError('Cannot find the navigation index. No files modified.')
                text = text.replace(anchor, BUTTON_GLOBAL + '\n' + anchor, 1)
        return text
    raise ValueError('Unexpected target module.')


def integrate(root, apply=False, output=print):
    root = Path(root)
    planned = {}
    for name in ('main.py', 'navigation.py'):
        f = root / name
        if not f.is_file():
            raise FileNotFoundError(f'Missing required bot module: {f}')
        data = f.read_bytes()
        src = data.decode('utf-8-sig').replace('\r\n', '\n')
        dst = transform(name, src)
        prefix = b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b''
        if b'\r\n' in data:
            dst = dst.replace('\n', '\r\n')
        planned[name] = data, prefix + dst.encode('utf-8')
    changes = [name for name, (old, new) in planned.items() if old != new]
    if not changes:
        output('Book Library already integrated. No changes required.')
        return []
    if not apply:
        for name in changes:
            before, after = planned[name]
            output(''.join(difflib.unified_diff(
                before.decode('utf-8-sig').splitlines(True),
                after.decode('utf-8-sig').splitlines(True),
                fromfile=name + ':current', tofile=name + ':planned')))
        output('CHECK OK. No files changed.')
        return changes
    backup = root / ('BOOK_LIBRARY_BACKUP_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for name in changes:
        shutil.copy2(root / name, backup / name)
    try:
        for name in changes:
            (root / name).write_bytes(planned[name][1])
    except Exception:
        for name in changes:
            shutil.copy2(backup / name, root / name)
        raise
    output('V11.1 Book Library integrated. Backups: ' + str(backup))
    output('Updated: ' + ', '.join(changes))
    return changes


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    integrate(Path(__file__).resolve().parent, apply=args.apply)
