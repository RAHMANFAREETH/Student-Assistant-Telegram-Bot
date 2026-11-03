"""V11.8.6.1: minimal search-status capability guard and V11.2 test isolation.

Run --check for a preview, --apply to install. No network calls.
"""
from __future__ import annotations
import argparse
import datetime
import difflib
import shutil
from pathlib import Path

MARK_MEDIA = '    editor=getattr(bot, "edit_message_text", None)  # V11.8.6.1'
MARK_UI = '    editor=getattr(bot, "edit_message_text", None)  # V11.8.6.1'
MARK_TEST = "'BOOK_LIBRARY_V113_ENABLED':'false',  # V11.8.6.1 isolate V11.2 tests"


def replace_once(source: str, before: str, after: str, name: str) -> str:
    count = source.count(before)
    if count != 1:
        raise ValueError(f'{name}: expected one matching block, found {count}; no changes made')
    return source.replace(before, after, 1)


def transform_media(source: str) -> str:
    name = 'library_media_v117_bot.py'
    if MARK_MEDIA in source:
        if source.count(MARK_MEDIA) != 1:
            raise ValueError(f'{name}: duplicate stabilization marker')
        return source
    if '# V11.8.6 user-visible search progress and zero-results feedback.' not in source:
        raise ValueError(f'{name}: V11.8.6 not installed; do not apply')
    before = '''    if mid is not None:
        try:
            updated=bot.edit_message_text(text, chat_id=chat_id, message_id=mid,
                                         reply_markup=markup)
'''
    after = '''    editor=getattr(bot, "edit_message_text", None)  # V11.8.6.1
    if mid is not None and callable(editor):
        try:
            updated=editor(text, chat_id=chat_id, message_id=mid,
                           reply_markup=markup)
'''
    output = replace_once(source, before, after, name)
    compile(output, name, 'exec')
    return output


def transform_ui(source: str) -> str:
    name = 'library_search_ui_v1183.py'
    if MARK_UI in source:
        if source.count(MARK_UI) != 1:
            raise ValueError(f'{name}: duplicate stabilization marker')
        return source
    if '# V11.8.6 edit the searching message into results.' not in source:
        raise ValueError(f'{name}: V11.8.6 not installed; do not apply')
    before = '''    mid=getattr(status_message, 'message_id', None)
    try:
        if mid is not None:
            try:
                updated=bot.edit_message_text(text, chat_id=chat_id,
                                              message_id=mid, reply_markup=kb)
'''
    after = '''    mid=getattr(status_message, 'message_id', None)
    editor=getattr(bot, "edit_message_text", None)  # V11.8.6.1
    try:
        if mid is not None and callable(editor):
            try:
                updated=editor(text, chat_id=chat_id,
                               message_id=mid, reply_markup=kb)
'''
    output = replace_once(source, before, after, name)
    before2 = '''        else:
            sent=_message(bot, chat_id, text, reply_markup=kb)
    except Exception:
        with _LOCK:
            _SESSIONS.pop(token, None)
'''
    after2 = '''        else:
            sent=_message(bot, chat_id, text, reply_markup=kb)
            # When a limited client cannot edit, try to remove its spinner.
            if mid is not None:
                try: bot.delete_message(chat_id, mid)
                except Exception: LOG.debug('Search progress cleanup unavailable')
    except Exception:
        with _LOCK:
            _SESSIONS.pop(token, None)
'''
    output = replace_once(output, before2, after2, name)
    compile(output, name, 'exec')
    return output


def transform_test(source: str) -> str:
    name = 'TEST_BOOK_LIBRARY_V112.py'
    if MARK_TEST in source:
        if source.count(MARK_TEST) != 1:
            raise ValueError(f'{name}: duplicate isolation marker')
        return source
    before = "'BOOK_LIBRARY_ENABLED':'true','BOOK_LIBRARY_V112_ENABLED':'true',"
    after = before + "\n            " + MARK_TEST
    output = replace_once(source, before, after, name)
    compile(output, name, 'exec')
    return output


def transform_legacy_test(source: str, name: str) -> str:
    """Block inherited V11.3 opt-in for legacy fake bots missing inline_handler."""
    if MARK_TEST in source:
        if source.count(MARK_TEST) != 1:
            raise ValueError(f'{name}: duplicate isolation marker')
        return source
    if name == 'TEST_BOOK_LIBRARY.py':
        before = "'BOOK_LIBRARY_ENABLED':'true','BOOK_LIBRARY_ADMIN_IDS':'7',"
    elif name == 'TEST_BOOK_PUBLIC_LATEST5.py':
        before = "'BOOK_LIBRARY_ENABLED': 'true',"
    else:
        raise ValueError(f'Unexpected test module {name}')
    after = before + "\n            " + MARK_TEST
    output = replace_once(source, before, after, name)
    compile(output, name, 'exec')
    return output


def plan(root: Path) -> dict[str, tuple[str, str]]:
    transformers = {
        'library_media_v117_bot.py': transform_media,
        'library_search_ui_v1183.py': transform_ui,
        'TEST_BOOK_LIBRARY_V112.py': transform_test,
        'TEST_BOOK_LIBRARY.py': lambda s: transform_legacy_test(s, 'TEST_BOOK_LIBRARY.py'),
        'TEST_BOOK_PUBLIC_LATEST5.py': lambda s: transform_legacy_test(s, 'TEST_BOOK_PUBLIC_LATEST5.py'),
    }
    changes = {}
    for name, transformer in transformers.items():
        path = root/name
        if not path.is_file():
            raise FileNotFoundError(f'Missing {name}; extract into your current project root')
        old = path.read_text(encoding='utf-8')
        new = transformer(old)
        if new != old:
            changes[name] = (old, new)
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check', action='store_true', help='Preview changes without writing')
    action.add_argument('--apply', action='store_true', help='Backup and apply verified changes')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    changes = plan(root)  # Validate all changes before touching anything.
    if not changes:
        print('V11.8.6.1 already installed. No files changed.')
        return
    if args.check:
        for name, (old, new) in changes.items():
            diff = difflib.unified_diff(old.splitlines(), new.splitlines(),
                                        fromfile=name+':current', tofile=name+':planned', lineterm='')
            print('\n'.join(diff))
        print('CHECK OK. No files changed.')
        return
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = root/('V11861_BACKUP_'+stamp)
    backup.mkdir(exist_ok=False)
    written = []
    try:
        for name in changes:
            shutil.copy2(root/name, backup/name)
        for name, (_, new) in changes.items():
            dest = root/name
            temp = root/(name+'.v11861.tmp')
            try:
                temp.write_text(new, encoding='utf-8')
                temp.replace(dest)
            finally:
                if temp.exists(): temp.unlink()
            written.append(name)
    except Exception:
        for name in written:
            shutil.copy2(backup/name, root/name)
        raise
    print('V11.8.6.1 installed. Backup:', backup)
    print('Updated:', ', '.join(changes))
    print('No database tables or feature flags changed.')

if __name__ == '__main__':
    main()
