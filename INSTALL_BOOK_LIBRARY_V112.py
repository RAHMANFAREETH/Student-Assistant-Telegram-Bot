"""Safe, idempotent V11.2 integration; never replaces existing Telegram bot or storage.

--check: prints proposed changes, makes no writes
--apply: backs up and modifies ONLY book_library_bot.py and book_library_store.py
"""
from __future__ import annotations
import argparse
import difflib
import shutil
from datetime import datetime, timezone
from pathlib import Path

MARKER = '# V11.2 Advanced Library hooks.'


def _replace_once(text, old, new, *, target):
    if text.count(old) != 1:
        raise ValueError(f'Unexpected {target} structure: anchor missing or repeated; no changes made.')
    return text.replace(old, new, 1)


def transform(name, text):
    if MARKER in text:
        return text  # Never duplicate integration.
    if name == 'book_library_store.py':
        text = _replace_once(text,
            '             file_size, uploaded_by, db=None):',
            '             file_size, uploaded_by, db=None, category=None, isbn=None):', target=name)
        text = _replace_once(text,
            "                  uploaded_by=int(uploaded_by), active=True)\n    rows = _rows(",
            "                  uploaded_by=int(uploaded_by), active=True)\n"
            "    # V11.2 optional fields; omit until migration and feature flag are enabled.\n"
            "    if category is not None:\n"
            "        from book_library_v112_store import simple_text, normalize_isbn\n"
            "        values['category'] = simple_text(category, max_len=60)\n"
            "        values['isbn'] = normalize_isbn(isbn)\n"
            "    rows = _rows(", target=name)
        return text + '\n' + MARKER + '\n'
    if name != 'book_library_bot.py':
        raise ValueError('Not a permitted file.')
    # Only activate advanced database reads when the new schema is confirmed.
    text = _replace_once(text,
        'def _search(bot, chat_id, query, group=False):\n    query = (query or \'\').strip()',
        'def _search(bot, chat_id, query, group=False):\n'
        "    if _on('BOOK_LIBRARY_V112_ENABLED', False):\n"
        '        from book_library_v112_bot import show_search\n'
        '        return show_search(bot, chat_id, query, group=group)\n'
        "    query = (query or '').strip()", target=name)
    text = _replace_once(text,
        "    kb.add(types.InlineKeyboardButton('🔎 Search a Book', callback_data='lib:search'),\n"
        "           types.InlineKeyboardButton('🆕 Latest Books', callback_data='lib:latest'))\n"
        "    bot.send_message(m.chat.id, '📚 Book Library",
        "    kb.add(types.InlineKeyboardButton('🔎 Search a Book', callback_data='lib:search'),\n"
        "           types.InlineKeyboardButton('🆕 Latest Books', callback_data='lib:latest'))\n"
        "    if _on('BOOK_LIBRARY_V112_ENABLED', False):\n"
        "        from book_library_v112_bot import add_menu_buttons\n"
        "        add_menu_buttons(kb)\n"
        "    bot.send_message(m.chat.id, '📚 Book Library", target=name)
    text = _replace_once(text,
        'def handle_library_start(bot, message):\n    """Called by main.py at the beginning of its EXISTING /start handler.\n\n    Returns True only when the deep-link was handled.\n    """',
        'def handle_library_start(bot, message):\n    """Called by main.py at the beginning of its EXISTING /start handler.\n\n    Returns True only when the deep-link was handled.\n    """\n'
        "    if _on('BOOK_LIBRARY_V112_ENABLED', False):\n"
        '        from book_library_v112_bot import handle_preview_start\n'
        '        if handle_preview_start(bot, message):\n'
        '            return True', target=name)
    text = _replace_once(text,
        '        bot.copy_message(chat_id=message.chat.id,\n'
        "                         from_chat_id=int(item['channel_id']),\n"
        "                         message_id=int(item['message_id']))\n"
        '        bot.send_message(message.chat.id,',
        '        bot.copy_message(chat_id=message.chat.id,\n'
        "                         from_chat_id=int(item['channel_id']),\n"
        "                         message_id=int(item['message_id']))\n"
        "        # V11.2 delivery count is aggregate only; logging failure must not block a file.\n"
        "        if _on('BOOK_LIBRARY_V112_ENABLED', False):\n"
        '            try:\n'
        '                from book_library_v112_store import record_delivery\n'
        "                record_delivery(item['id'])\n"
        '            except Exception:\n'
        '                import logging\n'
        "                logging.getLogger(__name__).warning('V11.2 delivery count unavailable')\n"
        '        bot.send_message(message.chat.id,', target=name)
    text = _replace_once(text,
        "                         and str(getattr(m, 'caption', '') or '').count('|') == 2)",
        "                         and str(getattr(m, 'caption', '') or '').count('|') in (2, 3, 4)\n"
        "                         and (_on('BOOK_LIBRARY_V112_ENABLED', False) or\n"
        "                              str(getattr(m, 'caption', '') or '').count('|') == 2))", target=name)
    text = _replace_once(text,
        '        try:\n            title, author, language = parse_caption(m.caption)\n'
        '        except ValueError as exc:',
        "        try:\n"
        "            v112_extra = {}\n"
        "            if _on('BOOK_LIBRARY_V112_ENABLED', False):\n"
        "                from book_library_v112_store import parse_extended_caption\n"
        "                title, author, language, category, isbn = parse_extended_caption(m.caption)\n"
        "                v112_extra = dict(category=category, isbn=isbn)\n"
        "            else:\n"
        "                title, author, language = parse_caption(m.caption)\n"
        "        except ValueError as exc:", target=name)
    text = _replace_once(text,
        "                           uploaded_by=m.from_user.id)\n        except Exception:",
        "                           uploaded_by=m.from_user.id, **v112_extra)\n        except Exception:", target=name)
    text = _replace_once(text,
        "            books = search_books(m.text, limit=6)\n"
        "            if not books:\n"
        "                return ContinueHandling()\n"
        "            bot.send_message(m.chat.id,",
        "            if _on('BOOK_LIBRARY_V112_ENABLED', False):\n"
        "                from book_library_v112_bot import show_search\n"
        "                show_search(bot, m.chat.id, m.text, group=True)\n"
        "                return ContinueHandling()\n"
        "            books = search_books(m.text, limit=6)\n"
        "            if not books:\n"
        "                return ContinueHandling()\n"
        "            bot.send_message(m.chat.id,", target=name)
    # Remains inside register_book_library_handlers at 4-space indentation.
    text += "\n    # Register additional commands/callbacks while V11.2 is enabled.\n" \
            "    if _on('BOOK_LIBRARY_V112_ENABLED', False):\n" \
            "        from book_library_v112_bot import register_v112_handlers\n" \
            "        register_v112_handlers(bot)\n\n" + MARKER + '\n'
    return text


def integrate(root, apply=False, output=print):
    root=Path(root)
    plan={}
    for name in ('book_library_bot.py','book_library_store.py'):
        file=root/name
        if not file.exists():
            raise FileNotFoundError(str(file))
        raw=file.read_bytes()
        encoding='utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8'
        src=raw.decode(encoding).replace('\r\n','\n')
        dst=transform(name,src)
        if b'\r\n' in raw:
            dst=dst.replace('\n','\r\n')
        bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
        plan[name]=(raw,bom+dst.encode('utf-8'))
    changed=[name for name,(old,new) in plan.items() if old!=new]
    if not changed:
        output('V11.2 Book Library already integrated. No files changed.')
        return []
    if not apply:
        for name in changed:
            old,new=plan[name]
            output(''.join(difflib.unified_diff(
                old.decode('utf-8-sig').splitlines(True),
                new.decode('utf-8-sig').splitlines(True),
                fromfile=name+':current',tofile=name+':planned')))
        output('CHECK OK. No files changed.')
        return changed
    backup=root/('BOOK_V112_BACKUP_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    for name in changed:
        shutil.copy2(root/name, backup/name)
    try:
        for name in changed:
            (root/name).write_bytes(plan[name][1])
    except Exception:
        for name in changed:
            shutil.copy2(backup/name,root/name)
        raise
    output('V11.2 installed. Backups: '+str(backup))
    output('Updated: '+', '.join(changed))
    return changed

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    opts=parser.add_mutually_exclusive_group(required=True)
    opts.add_argument('--check',action='store_true')
    opts.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    integrate(Path(__file__).resolve().parent,apply=args.apply)
