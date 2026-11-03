"""Safe, idempotent installer for V11.8.3 search UI.

Requires library_search_ui_v1183.py to be in the same project directory.
Only two existing files are changed; this installer never runs the bot.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime
from pathlib import Path

FLAG = '# V11.8.3 interactive search results.'


def replace_once(text, old, new, *, filename):
    if text.count(old) != 1:
        raise ValueError(f'{filename}: expected exactly one verified anchor: {old[:80]!r}; found {text.count(old)}')
    return text.replace(old, new, 1)


def transform_media(text):
    if FLAG in text:
        if text.count(FLAG) != 1 or 'send_search_results(' not in text:
            raise ValueError('V11.8.3 media integration is incomplete or duplicated.')
        return text
    path = 'library_media_v117_bot.py'
    text = replace_once(text,
        '    old=_legacy_filtered(_book_rows(query,limit=8),filt)\n',
        '    old=_legacy_filtered(_book_rows(query,limit=min(10,limit)),filt)\n', filename=path)
    text = replace_once(text, '        items=union_search(q)\n',
                        '        items=union_search(q,limit=30)\n', filename=path)
    text = replace_once(text,
        '        return _send_results(bot,chat_id,heading,items,group=group)\n',
        (f'        {FLAG}\n'
         '        if group and requester_id is None:\n'
         '            # Unknown requester: retain existing group URL-only keyboard.\n'
         '            return _send_results(bot,chat_id,heading,items,group=group)\n'
         '        from library_search_ui_v1183 import send_search_results\n'
         '        return send_search_results(bot,chat_id,heading,items,group=group,\n'
         '                                   requester_id=requester_id)\n'), filename=path)
    text = replace_once(text,
        '    from library_manage_v118 import register_manage_handlers\n    register_manage_handlers(bot)\n',
        '    from library_manage_v118 import register_manage_handlers\n    register_manage_handlers(bot)\n'
        '    from library_search_ui_v1183 import register_private_handlers\n'
        '    register_private_handlers(bot)\n',filename=path)
    compile(text, path, 'exec')
    return text


def transform_group(text):
    flag = '# V11.8.3 group-only search filters.'
    if flag in text:
        if text.count(flag) != 1 or 'handle_callback(bot,c,group=True)' not in text:
            raise ValueError('V11.8.3 group integration is incomplete or duplicated.')
        return text
    path = 'group_books_only_v116.py'
    anchor = ('    def group_books_only_callback(c):\n'
              '        if not active():\n'
              '            from telebot.handler_backends import ContinueHandling\n'
              '            return ContinueHandling()\n')
    replacement = (anchor +
        f'        {flag}\n'
        "        if str(getattr(c, 'data', '') or '').startswith('ls83:'):\n"
        '            from library_search_ui_v1183 import handle_callback\n'
        '            return handle_callback(bot,c,group=True)\n')
    text = replace_once(text,anchor,replacement,filename=path)
    compile(text,path,'exec')
    return text


def integrate(root: Path, *, apply=False):
    root = Path(root)
    helper = root/'library_search_ui_v1183.py'
    if not helper.is_file():
        raise FileNotFoundError('Missing library_search_ui_v1183.py. Copy the full patch ZIP contents first.')
    compile(helper.read_text(encoding='utf-8'),str(helper),'exec')
    transforms = {'library_media_v117_bot.py': transform_media,
                  'group_books_only_v116.py': transform_group}
    changes = {}
    for filename,transform in transforms.items():
        original = (root/filename).read_text(encoding='utf-8')
        new = transform(original)
        if original != new:
            changes[filename] = (original,new)
    if not changes:
        print('V11.8.3 already integrated. Nothing to change.')
        return False
    if not apply:
        for filename,(old,new) in changes.items():
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
                  fromfile=filename+':current',tofile=filename+':planned')))
        print('CHECK OK. No files changed.')
        return True
    backup = root/('V1183_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(exist_ok=False)
    try:
        for filename in changes:
            shutil.copy2(root/filename,backup/filename)
        for filename,(_,new) in changes.items():
            temp = root/(filename+'.v1183.tmp')
            try:
                temp.write_text(new,encoding='utf-8',newline='')
                temp.replace(root/filename)
            finally:
                temp.unlink(missing_ok=True)
    except Exception:
        for filename in changes:
            saved=backup/filename
            if saved.exists():shutil.copy2(saved,root/filename)
        raise
    print('V11.8.3 installed; original source saved to:',backup)
    return True


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check',action='store_true')
    g.add_argument('--apply',action='store_true')
    args=p.parse_args()
    integrate(Path(__file__).resolve().parent,apply=args.apply)
