"""Idempotent V11.3 installer with byte-for-byte source backups.
Check before apply; modifies book_library_bot.py, book_library_store.py and main.py only.
Requires V11.2 existing integration and its SQL migration.
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime, timezone
from pathlib import Path

MARK='V11.3 Advanced Library integration'


def _one(text,old,new,name):
    if text.count(old)!=1:
        raise ValueError(f'Unknown {name} code layout. Required anchor missing or repeated; no changes made.')
    return text.replace(old,new,1)


def transform(name,src):
    if MARK in src:return src
    if name=='book_library_store.py':
        src=_one(src,
            '             file_size, uploaded_by, db=None, category=None, isbn=None):',
            '             file_size, uploaded_by, db=None, category=None, isbn=None,\n'
            '             file_unique_id=None, sha256=None):',name)
        src=_one(src,
            "        values['isbn'] = normalize_isbn(isbn)\n    rows = _rows(",
            "        values['isbn'] = normalize_isbn(isbn)\n"
            "    if os.getenv('BOOK_LIBRARY_V113_ENABLED', 'false').lower() in ('true', '1', 'yes'):\n"
            "        if file_unique_id: values['file_unique_id'] = str(file_unique_id)[:200]\n"
            "        if sha256: values['sha256'] = str(sha256)[:64]\n"
            '    rows = _rows(',name)
        return src+'\n# '+MARK+'\n'
    if name=='book_library_bot.py':
        src=_one(src,
            "def _search(bot, chat_id, query, group=False):\n    if _on('BOOK_LIBRARY_V112_ENABLED', False):",
            "def _search(bot, chat_id, query, group=False):\n"
            "    if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
            "        from book_library_v113_bot import show_smart_search\n"
            "        return show_smart_search(bot, chat_id, query, group=group)\n"
            "    if _on('BOOK_LIBRARY_V112_ENABLED', False):", name)
        src=_one(src,
            '        add_menu_buttons(kb)\n    bot.send_message(m.chat.id,',
            '        add_menu_buttons(kb)\n'
            "    if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
            '        from book_library_v113_bot import add_v113_menu_buttons\n'
            '        add_v113_menu_buttons(kb)\n'
            '    bot.send_message(m.chat.id,',name)
        src=_one(src,
            '        bot.send_message(message.chat.id,\n'
            '                         f"✅ Sent:',
            "        if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
            "            try:\n"
            "                from book_library_v113_store import record_metric\n"
            "                record_metric('deliveries')\n"
            "            except Exception:\n"
            "                import logging\n"
            "                logging.getLogger(__name__).warning('V11.3 delivery metrics unavailable')\n"
            '        bot.send_message(message.chat.id,\n'
            '                         f"✅ Sent:',name)
        src=_one(src,
            "        raw_channel = os.getenv('BOOK_LIBRARY_CHANNEL_ID', '')",
            "        # V11.3 checks duplicates before copying the file into Telegram storage.\n"
            '        v113_extra = {}\n'
            "        if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
            '            from book_library_v113_bot import check_admin_upload\n'
            '            try:\n'
            '                duplicate, file_unique_id, sha256 = check_admin_upload(\n'
            "                    bot, m, isbn=v112_extra.get('isbn'))\n"
            '            except Exception:\n'
            "                bot.send_message(m.chat.id, '⚠️ Duplicate check is unavailable; upload was not published.')\n"
            '                return\n'
            '            if duplicate: return\n'
            '            v113_extra = dict(file_unique_id=file_unique_id, sha256=sha256)\n'
            "        raw_channel = os.getenv('BOOK_LIBRARY_CHANNEL_ID', '')",name)
        src=_one(src,
            '                           uploaded_by=m.from_user.id, **v112_extra)',
            '                           uploaded_by=m.from_user.id, **v112_extra, **v113_extra)',name)
        src=_one(src,
            '        bot.send_message(m.chat.id,\n'
            "                         f'✅ Added to Book Library",
            "        if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
            '            from book_library_v113_bot import post_admin_upload\n'
            '            post_admin_upload(bot, rec)\n'
            '        bot.send_message(m.chat.id,\n'
            "                         f'✅ Added to Book Library",name)
        src=_one(src,
            "        register_v112_handlers(bot)\n\n# V11.2 Advanced Library hooks.",
            "        register_v112_handlers(bot)\n"
            "    if _on('BOOK_LIBRARY_V113_ENABLED', False):\n"
            '        from book_library_v113_bot import register_v113_handlers\n'
            '        register_v113_handlers(bot)\n'
            '\n# V11.2 Advanced Library hooks.',name)
        return src+'\n# '+MARK+'\n'
    if name=='main.py':
        src=_one(src,'app = Flask(__name__)',
            'app = Flask(__name__)\n\n'
            '# '+MARK+'\n'
            "if os.getenv('BOOK_LIBRARY_V113_ENABLED', 'false').lower() in ('true','1','yes'):\n"
            '    from book_library_v113_web import register_book_library_web\n'
            '    from book_library_v113_notify import start_worker_if_enabled\n'
            '    register_book_library_web(app, bot)\n'
            '    start_worker_if_enabled(bot)',name)
        return src
    raise ValueError('Not an allowed file: '+name)


def integrate(root,apply=False,output=print):
    root=Path(root)
    names=('book_library_bot.py','book_library_store.py','main.py')
    plan={}
    for name in names:
        path=root/name
        raw=path.read_bytes()
        bom=raw.startswith(b'\xef\xbb\xbf')
        sep='\r\n' if b'\r\n' in raw else '\n'
        src=raw.decode('utf-8-sig').replace('\r\n','\n')
        dst=transform(name,src)
        if sep=='\r\n':dst=dst.replace('\n','\r\n')
        rendered=(b'\xef\xbb\xbf' if bom else b'')+dst.encode('utf-8')
        plan[name]=(raw,rendered)
    changed=[n for n,(a,b) in plan.items() if a!=b]
    if not changed:
        output('V11.3 already integrated; no files changed.')
        return []
    if not apply:
        for name in changed:
            old,new=plan[name]
            output(''.join(difflib.unified_diff(
                old.decode('utf-8-sig').splitlines(True),new.decode('utf-8-sig').splitlines(True),
                fromfile=name+':current',tofile=name+':planned')))
        output('CHECK OK. No files changed.')
        return changed
    folder=root/('BOOK_V113_BACKUP_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir(exist_ok=False)
    for n in changed: shutil.copy2(root/n,folder/n)
    try:
        for n in changed:(root/n).write_bytes(plan[n][1])
    except Exception:
        for n in changed:shutil.copy2(folder/n,root/n)
        raise
    output('V11.3 integrated. Backup: '+str(folder))
    output('Updated: '+', '.join(changed))
    return changed


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    flags=parser.add_mutually_exclusive_group(required=True)
    flags.add_argument('--check',action='store_true')
    flags.add_argument('--apply',action='store_true')
    options=parser.parse_args()
    integrate(Path(__file__).resolve().parent,apply=options.apply)
