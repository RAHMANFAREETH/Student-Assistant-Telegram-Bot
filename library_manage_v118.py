"""V11.8 private, administrator-only management of V11.1 PDFs and V11.7 media.

No new tables or credentials. Hard-delete is fail-closed: hide, request
Telegram deletion, and only then remove the catalog row. Telegram's Bot API
cannot delete messages older than 48h; manual channel deletion and explicitly
attested catalog cleanup are supported as a separate action.
"""
from __future__ import annotations

import logging
import os
import re
import secrets
import threading
import time
import uuid

LOG = logging.getLogger(__name__)
_LOCK = threading.RLock()
_CONFIRM = {}  # token -> (uid, kind, record_uuid, method, expires)
_TOKEN_TTL = 180


def enabled():
    return os.getenv('LIBRARY_MANAGE_V118_ENABLED', 'false').strip().lower() in ('true', 'yes', '1', 'on')


def _api():
    import library_media_v117_bot as api
    return api


def _store():
    import library_media_v117_store as media
    return media


def _books():
    import book_library_store as books
    return books


def _admin_user(obj):
    api = _api()
    uid = getattr(getattr(obj, 'from_user', None), 'id', 0)
    chat = getattr(obj, 'chat', None) or getattr(obj, 'message', None) and getattr(obj.message, 'chat', None)
    if not chat or getattr(chat, 'type', None) != 'private' or getattr(chat, 'id', None) != uid:
        return False
    from book_library_bot import _admin
    return bool(uid and _admin(uid))


def _clean_uuid(value):
    return str(uuid.UUID(str(value)))


def _kind(code):
    if code not in ('b', 'm'):
        raise ValueError('Unknown catalog type.')
    return code


def _record(code, key, *, db=None):
    code = _kind(code)
    key = _clean_uuid(key)
    d = db or _store()._db()
    if code == 'm':
        rows = _store()._rows(d.table('library_media_v117').select('*').eq('id', key).limit(1).execute())
        if rows and rows[0].get('status') not in ('approved', 'hidden'):
            return None
    else:
        rows = _store()._rows(d.table('book_library_items').select('*').eq('id', key).limit(1).execute())
    return rows[0] if rows else None


def _is_visible(code, record):
    return bool(record['active']) if code == 'b' else record['status'] == 'approved'


def _destination(code, record):
    if code == 'b':
        return record.get('channel_id'), record.get('message_id')
    return record.get('storage_channel_id'), record.get('storage_message_id')


def _audit(uid, verb, code, key, detail=''):
    try:
        _store().audit(uid, 'manage '+verb, key, f'{code}: {detail}'[:490])
    except Exception:
        LOG.warning('Admin action succeeded but audit insert failed: %s', verb, exc_info=True)


def _rows_for(code, term='', limit=9, *, db=None):
    d = db or _store()._db()
    name, stamp = ('book_library_items', 'added_at') if code == 'b' else ('library_media_v117', 'created_at')
    q = d.table(name).select('*')
    if code == 'm':
        q = q.in_('status', ['approved', 'hidden'])
    if term:
        # No SQL or PostgREST filter fragments from user-supplied text.
        # Wildcards are refused rather than silently interpreted.
        if len(term) > 90 or any(c in term for c in '%_*\\(){}'):
            raise ValueError('Use plain words (up to 90 characters) for a title search.')
        q = q.ilike('title', f'%{term}%')
    return _store()._rows(q.order(stamp, desc=True).limit(limit).execute())


def find(query='', *, db=None):
    """Search both catalogs by title, or locate an exact UUID regardless of age.

    Prefix a UUID with b: or m: when a catalog is known. Old hidden PDFs and
    hidden V11.7 items remain available to administrators for restoration.
    """
    q = str(query or '').strip()
    m = re.fullmatch(r'(?:(b|m):)?([0-9a-fA-F-]{32,36})', q)
    if m:
        try:
            key = _clean_uuid(m.group(2))
        except ValueError:
            raise ValueError('Invalid file UUID.')
        kinds = [m.group(1)] if m.group(1) else ['b', 'm']
        return [(k, row) for k in kinds if (row := _record(k, key, db=db))]
    if q and (len(q) < 2 or len(q) > 90):
        raise ValueError('Search by 2–90 characters or an exact UUID.')
    rows = []
    for code in ('b', 'm'):
        rows += [(code, r) for r in _rows_for(code, q, db=db)]
    return rows[:18]


def change_visibility(code, key, show, uid, *, db=None):
    code = _kind(code)
    key = _clean_uuid(key)
    rec = _record(code, key, db=db)
    if not rec:
        raise ValueError('File not found in the catalog.')
    d = db or _store()._db()
    if _is_visible(code, rec) == bool(show):
        return 'Already published.' if show else 'Already hidden.'
    if code == 'b':
        rows = _store()._rows(d.table('book_library_items').update({'active': bool(show)})
                              .eq('id', key).eq('active', not bool(show)).execute())
    else:
        target = 'approved' if show else 'hidden'
        old = 'hidden' if show else 'approved'
        rows = _store()._rows(d.table('library_media_v117').update({'status': target})
                              .eq('id', key).eq('status', old).execute())
    if not rows:
        raise RuntimeError('Visibility change not confirmed; refresh and try again.')
    _audit(uid, 'restore' if show else 'hide', code, key, rec.get('title', ''))
    return 'Restored to public library.' if show else 'Hidden from public searches and deliveries.'


def rename(code, key, title, uid, *, db=None):
    code = _kind(code)
    key = _clean_uuid(key)
    title = _store().clean(title, 180)
    row = _record(code, key, db=db)
    if not row:
        raise ValueError('File not found.')
    table = 'book_library_items' if code == 'b' else 'library_media_v117'
    updated = _store()._rows((db or _store()._db()).table(table).update({'title': title})
                             .eq('id', key).execute())
    if not updated:
        raise RuntimeError('Title update not confirmed.')
    _audit(uid, 'rename', code, key, f'{row.get("title", "")} -> {title}'[:400])
    return title


def _referenced_elsewhere(code, key, cid, mid, *, db=None):
    """Never remove a shared Telegram message that another catalog entry uses."""
    d = db or _store()._db()
    old = _store()._rows(d.table('book_library_items').select('id')
                          .eq('channel_id', cid).eq('message_id', mid).limit(10).execute())
    new = _store()._rows(d.table('library_media_v117').select('id')
                          .eq('storage_channel_id', cid).eq('storage_message_id', mid).limit(10).execute())
    return any(str(x['id']) != str(key) or code != 'b' for x in old) or \
           any(str(x['id']) != str(key) or code != 'm' for x in new)


def _remove_catalog(code, key, uid, *, db=None):
    row = _record(code, key, db=db)
    if not row:
        raise ValueError('Catalog record already removed.')
    # Reject deleting a published record while storage has not been hidden.
    if _is_visible(code, row):
        raise RuntimeError('Hide the item before clearing its catalog record.')
    table = 'book_library_items' if code == 'b' else 'library_media_v117'
    rows = _store()._rows((db or _store()._db()).table(table).delete().eq('id', key).execute())
    if not rows:
        raise RuntimeError('Catalog deletion was not confirmed. Item remains hidden.')
    _audit(uid, 'catalog purged', code, key, row.get('title', ''))
    return True


def _issue_token(uid, code, key, method):
    if method not in ('delete', 'manual'):
        raise ValueError('Invalid confirmation.')
    token = secrets.token_urlsafe(12)
    now = time.monotonic()
    with _LOCK:
        for k, val in list(_CONFIRM.items()):
            if val[-1] < now:
                del _CONFIRM[k]
        if len(_CONFIRM) > 300:
            _CONFIRM.clear()
        _CONFIRM[token] = (int(uid), _kind(code), _clean_uuid(key), method, now + _TOKEN_TTL)
    return token


def _take_token(uid, token):
    with _LOCK:
        data = _CONFIRM.pop(token, None)
    if not data or data[0] != int(uid) or data[-1] < time.monotonic():
        raise ValueError('This confirmation expired or belongs to another admin. Start again.')
    return data[1], data[2], data[3]


def delete(bot, code, key, uid, *, manually_removed=False, db=None):
    """Require positive Telegram deletion, or admin attestation, before DB purge.

    Raises a descriptive error while leaving the row hidden if Telegram refuses
    deletion (including >48h old storage-channel messages).
    """
    row = _record(code, key, db=db)
    if not row:
        raise ValueError('File already deleted or no longer exists.')
    cid, mid = _destination(code, row)
    if cid is None or mid is None:
        raise ValueError('Storage message reference missing. Resolve manually; no changes made.')
    cid, mid = int(cid), int(mid)
    if cid >= 0 or mid <= 0:
        raise ValueError('Invalid private channel reference; no changes made.')
    # Fail closed on shared copies. Deleting the catalog row (without deleting
    # storage) is still possible only after the admin removes other references.
    if _referenced_elsewhere(code, key, cid, mid, db=db):
        raise ValueError('This storage message is used by another library item. Hide it, then resolve duplicates first.')
    change_visibility(code, key, False, uid, db=db)
    if not manually_removed:
        try:
            result = bot.delete_message(cid, mid)
            if result is False:
                raise RuntimeError('Telegram did not confirm deletion.')
        except Exception as exc:
            LOG.warning('Telegram cannot delete storage message (%s,%s)', cid, mid, exc_info=True)
            raise RuntimeError('File is HIDDEN but Telegram could not delete its stored message '
                               f'(channel {cid}, message {mid}). For older messages Telegram may refuse '
                               'deletion. Delete it manually in the private storage channel, then use '
                               '"I removed the channel file — Purge catalog". No catalog data was purged.') from exc
    _remove_catalog(code, key, uid, db=db)
    if manually_removed:
        _audit(uid, 'manual channel removal attested', code, key, f'channel {cid} message {mid}')
    else:
        _audit(uid, 'telegram file deleted', code, key, f'channel {cid} message {mid}')
    return f'Permanently removed from the library catalog. Channel message: {cid}/{mid}.'


def _keyboard():
    from telebot import types
    return types.InlineKeyboardMarkup(row_width=2)


def _button(text, data):
    from telebot import types
    return types.InlineKeyboardButton(text, callback_data=data)


def _send(bot, cid, text, markup=None):
    opts = {'reply_markup': markup} if markup else {}
    return bot.send_message(cid, text[:3990], **opts)


def _answer(bot, call, value='OK', alert=False):
    try:
        bot.answer_callback_query(call.id, str(value)[:190], show_alert=alert)
    except Exception:
        LOG.warning('Could not answer callback query')


def list_panel(bot, uid, cid, query=''):
    items = find(query)
    if not items:
        return _send(bot, cid, '📁 No matching files. Try /librarymanage TITLE or the exact UUID.')
    kb = _keyboard()
    for code, item in items:
        name = str(item.get('title', 'Untitled'))[:43]
        state = '✅' if _is_visible(code, item) else '🙈'
        badge = '📄' if code == 'b' else _store().BADGES.get(item.get('media_kind'), '📦')
        kb.add(_button(f'{state} {badge} {name}', f'v118:i:{code}:{uuid.UUID(str(item["id"])).hex}'))
    heading = '📁 Manage Library Files — Admin only\n'
    heading += f'Search: {query[:100]}\n' if query else 'Recent books and media\n'
    heading += '✅ Public · 🙈 Hidden\nSelect a file to preview, rename, hide, restore or delete.\n'
    heading += 'Search: /librarymanage TITLE\nExact ID: /librarymanage b:UUID or m:UUID'
    return _send(bot, cid, heading, kb)


def item_panel(bot, cid, code, key):
    row = _record(code, key)
    if not row:
        return _send(bot, cid, '📁 This file has been removed or is unavailable.')
    visible = _is_visible(code, row)
    ident = uuid.UUID(str(row['id'])).hex
    cid_storage, mid_storage = _destination(code, row)
    kind = 'PDF' if code == 'b' else row.get('media_kind', '?').upper()
    text = (f'📁 {row.get("title", "Untitled")}\n📦 {kind} — {"Public" if visible else "Hidden"}\n'
            f'✍️ {row.get("author", "Unknown")} · 🌐 {row.get("language", "-")}\n'
            f'ID: {row["id"]}\n'
            f'Original file: {str(row.get("file_name", ""))[:100]}\n'
            f'Storage message: {cid_storage} / {mid_storage}\n'
            'Rename changes the library title, not the original Telegram filename.')
    kb = _keyboard()
    kb.add(_button('👁 Preview original', f'v118:v:{code}:{ident}'))
    kb.add(_button('✏️ Rename title', f'v118:n:{code}:{ident}'))
    kb.add(_button('🙈 Hide' if visible else '✅ Restore', f'v118:h:{code}:{ident}' if visible else f'v118:s:{code}:{ident}'))
    kb.add(_button('🗑️ Delete permanently', f'v118:d:{code}:{ident}'))
    if not visible:
        kb.add(_button('⚠️ I removed channel file — Purge catalog', f'v118:p:{code}:{ident}'))
    return _send(bot, cid, text, kb)


def _confirm_panel(bot, uid, cid, code, key, method):
    row = _record(code, key)
    if not row:
        return _send(bot, cid, 'This file is no longer in the library.')
    token = _issue_token(uid, code, key, method)
    if method == 'delete':
        instruction = ('⚠️ IRREVERSIBLE DELETE\n'
                       'The file will first be hidden, then the bot will try to delete the original '
                       'Telegram channel message and remove the catalog entry.\n'
                       'Telegram may reject deletion of messages older than 48 hours. '
                       'In that case the item stays hidden.\n')
    else:
        instruction = ('⚠️ CONFIRM MANUAL STORAGE REMOVAL\n'
                       'Use this ONLY after you personally deleted the original file message from '
                       'the private Telegram storage channel. The bot cannot verify this and will '
                       'permanently erase its catalog entry.\n')
    kb = _keyboard()
    kb.add(_button('✅ Confirm irreversible delete', 'v118:ok:'+token))
    kb.add(_button('↩️ Cancel', 'v118:cancel'))
    return _send(bot, cid, instruction+'\nFile: '+str(row.get('title'))+'\nID: '+key, kb)


def register_manage_handlers(bot):
    if getattr(bot, '_library_manage_v118_registered', False):
        return
    bot._library_manage_v118_registered = True
    from telebot.handler_backends import ContinueHandling

    @bot.message_handler(commands=['librarymanage', 'libraryfiles', 'librarysettitle'])
    def manage_command(message):
        if not enabled():
            return ContinueHandling()
        if not _admin_user(message):
            return _send(bot, message.chat.id, '🔒 Library management works only for authorized admins in private chat.')
        try:
            cmd = str(message.text).split()[0].split('@')[0].lower()
            arg = str(message.text).partition(' ')[2].strip()
            if cmd == '/librarysettitle':
                match = re.fullmatch(r'([bm]):([0-9a-fA-F-]{32,36})\s*\|\s*(.+)', arg, re.S)
                if not match:
                    raise ValueError('Use /librarysettitle b:UUID | New Catalog Title (m: for newer media).')
                result = rename(match[1], match[2], match[3].strip(), message.from_user.id)
                return _send(bot, message.chat.id, '✅ Catalog title updated: '+result)
            return list_panel(bot, message.from_user.id, message.chat.id, arg)
        except ValueError as exc:
            return _send(bot, message.chat.id, '⚠️ '+str(exc)[:350])
        except Exception:
            LOG.exception('Manage command failed')
            return _send(bot, message.chat.id, '⚠️ Admin management is unavailable. Check Supabase/Render logs.')

    @bot.callback_query_handler(func=lambda c: str(getattr(c, 'data', '') or '').startswith('v118:'))
    def actions(call):
        if not enabled():
            return ContinueHandling()
        if not _admin_user(call):
            return _answer(bot, call, 'Admins only, in your own private bot chat.', True)
        uid = call.from_user.id
        cid = call.message.chat.id
        data = str(call.data)
        if data == 'v118:cancel':
            return _answer(bot, call, 'Cancelled. No file was deleted.')
        try:
            if data.startswith('v118:ok:'):
                code, key, method = _take_token(uid, data[8:])
                result = delete(bot, code, key, uid, manually_removed=(method == 'manual'))
                _answer(bot, call, 'Completed.')
                return _send(bot, cid, '✅ '+result)
            parts = data.split(':')
            if len(parts) != 4:
                raise ValueError('Unrecognized admin action.')
            _, action, code, raw = parts
            code = _kind(code)
            key = str(uuid.UUID(hex=raw))
            rec = _record(code, key)
            if rec is None:
                raise ValueError('The file is not available in this catalog.')
            _answer(bot, call)
            if action == 'i':
                return item_panel(bot, cid, code, key)
            if action == 'v':
                channel, msg = _destination(code, rec)
                if channel is None or msg is None:
                    raise ValueError('Storage reference missing.')
                bot.copy_message(cid, int(channel), int(msg))
                return _send(bot, cid, '👁 Original file copied privately for admin preview.')
            if action == 'n':
                return _send(bot, cid, f'✏️ Rename title using:\n/librarysettitle {code}:{key} | New Catalog Title')
            if action in ('h', 's'):
                result = change_visibility(code, key, action == 's', uid)
                _send(bot, cid, '✅ '+result)
                return item_panel(bot, cid, code, key)
            if action in ('d', 'p'):
                return _confirm_panel(bot, uid, cid, code, key, 'delete' if action == 'd' else 'manual')
            raise ValueError('Unknown action.')
        except ValueError as exc:
            return _answer(bot, call, str(exc)[:180], True)
        except RuntimeError as exc:
            LOG.warning('Delete or manage operation halted safely: %s', exc)
            return _send(bot, cid, '⚠️ '+str(exc)[:1000])
        except Exception:
            LOG.exception('Admin management failed')
            return _send(bot, cid, '⚠️ Operation could not finish; check status in /librarymanage and Render logs.')
