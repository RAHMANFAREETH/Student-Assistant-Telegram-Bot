"""Safe V11.4 Book Library privacy update installer.

Does not touch Render, GitHub, Supabase, age verification, or non-library modules.
Uses exact-context UTF-8 patches. Fails closed on unexpected file layouts.
"""
from __future__ import annotations
import argparse
import difflib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

NAMES=('book_library_bot.py', 'book_library_v112_bot.py', 'book_library_v113_bot.py')
MARKER='# V11.4 Book Library privacy integration'


def _anchor_variant(name, src, patch):
    """Recognize the V11.3 smart-search insertion without replacing its handler.

    Legacy V11.2 and installed V11.3 both remain supported; all other
    unmatched source layouts still abort before any project file changes.
    """
    old, new = patch['old'], patch['new']
    if name != 'book_library_bot.py' or 'def _search(bot, chat_id' not in old:
        return old, new
    v112_head = ("def _search(bot, chat_id, query, group=False):\n"
                 "    if _on('BOOK_LIBRARY_V112_ENABLED', False):")
    v112_new_head = ("def _search(bot, chat_id, query, group=False, requester_id=None):\n"
                     "    if _on('BOOK_LIBRARY_V112_ENABLED', False):")
    v113_head = ("def _search(bot, chat_id, query, group=False):\n"
                 "    if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
                 "        from book_library_v113_bot import show_smart_search\n"
                 "        return show_smart_search(bot, chat_id, query, group=group)\n"
                 "    if _on('BOOK_LIBRARY_V112_ENABLED', False):")
    v113_new_head = ("def _search(bot, chat_id, query, group=False, requester_id=None):\n"
                     "    if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
                     "        from book_library_v113_bot import show_smart_search\n"
                     "        return show_smart_search(bot, chat_id, query, group=group)\n"
                     "    if _on('BOOK_LIBRARY_V112_ENABLED', False):")
    if src.count(old) == 1:
        return old, new
    if old.count(v112_head) != 1 or new.count(v112_new_head) != 1:
        return old, new
    alternate_old = old.replace(v112_head, v113_head, 1)
    alternate_new = new.replace(v112_new_head, v113_new_head, 1)
    if src.count(alternate_old) == 1:
        return alternate_old, alternate_new
    return old, new


def transform(name, src, ops):
    if name not in NAMES:
        raise ValueError('Disallowed filename: '+name)
    if MARKER in src:
        return src
    if 'V11.3 Advanced Library integration' not in src and name == 'book_library_bot.py':
        raise ValueError('V11.3 Book Library is required. Not patching older version.')
    if name == 'book_library_v113_bot.py' and not 'V11.3:' in src:
        raise ValueError('V11.3 Book Library module is missing.')
    for patch in ops[name]:
        old,new=_anchor_variant(name,src,patch)
        if not old or src.count(old)!=1:
            raise ValueError(f'{name}: expected integration anchor missing/duplicated. No files changed.')
        src=src.replace(old,new,1)
    return src.rstrip('\n')+'\n\n'+MARKER+'\n'


def integrate(root, apply=False, output=print):
    root=Path(root)
    ops=json.loads((Path(__file__).resolve().parent/'V114_PATCH_OPS.json').read_text(encoding='utf-8'))
    prepared={}
    for name in NAMES:
        file=root/name
        raw=file.read_bytes()
        bom=raw.startswith(b'\xef\xbb\xbf')
        crlf=b'\r\n' in raw
        src=raw.decode('utf-8-sig').replace('\r\n','\n')
        dst=transform(name,src,ops)
        if crlf:dst=dst.replace('\n','\r\n')
        rendered=(b'\xef\xbb\xbf' if bom else b'')+dst.encode('utf-8')
        prepared[name]=(raw,rendered)
    changed=[name for name,(old,new) in prepared.items() if old!=new]
    if not changed:
        output('V11.4 privacy patch already installed; no files changed.')
        return []
    if not apply:
        for name in changed:
            before,after=prepared[name]
            output(''.join(difflib.unified_diff(
                before.decode('utf-8-sig').splitlines(True),
                after.decode('utf-8-sig').splitlines(True),
                fromfile=name+':current',tofile=name+':planned')))
        output('CHECK OK. No files changed.')
        return changed
    backup=root/('BOOK_PRIVACY_V114_BACKUP_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for name in changed:shutil.copy2(root/name,backup/name)
    try:
        for name in changed:(root/name).write_bytes(prepared[name][1])
    except Exception:
        for name in changed:shutil.copy2(backup/name,root/name)
        raise
    output('V11.4 privacy patch installed. Backups: '+str(backup))
    output('Updated: '+', '.join(changed))
    return changed


if __name__=='__main__':
    p=argparse.ArgumentParser()
    mx=p.add_mutually_exclusive_group(required=True)
    mx.add_argument('--check',action='store_true');mx.add_argument('--apply',action='store_true')
    args=p.parse_args()
    integrate(Path(__file__).resolve().parent,apply=args.apply)
