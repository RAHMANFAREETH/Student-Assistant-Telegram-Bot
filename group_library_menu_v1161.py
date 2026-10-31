"""V11.6.1: a PUBLIC, time-limited Book Library menu inside Telegram groups.

Register BEFORE install_group_ui_guard() and install_book_only_group_gate().
The group menu exposes only book search instructions and latest five public books;
personal library/AI/admin workflows stay in private chat. It preserves all existing
book search/delivery routes and never accepts a supplied user_id as identity.
"""
from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from urllib.parse import quote

LOG = logging.getLogger(__name__)
_LOCK = threading.RLock()
_SESSIONS = {}  # nonce -> (group_id, original_message_id, owner_telegram_id, expires)
_LABEL = '📚 Book Library'
_MAX_SESSIONS = 1500
_MENU_TTL = 300


def _enabled():
    return (os.getenv('GROUP_LIBRARY_MENU_V1161_ENABLED', 'false').strip().lower()
            in ('true', 'yes', '1', 'on'))


def _group(message):
    return getattr(getattr(message, 'chat', None), 'type', None) in ('group', 'supergroup')


def _is_target(message):
    if not _group(message):
        return False
    raw = str(getattr(message, 'text', '') or '').strip()
    return raw == _LABEL or raw.split(' ', 1)[0].split('@', 1)[0].lower() in ('/bookmenu', '/library')


def _mentioned_other_bot(bot, message):
    raw = str(getattr(message, 'text', '') or '').split(' ', 1)[0]
    if not raw.startswith('/') or '@' not in raw:
        return False
    specified = raw.split('@', 1)[1].lower()
    from book_library_bot import _bot_username
    try:
        return specified != _bot_username(bot).lower()
    except Exception:
        return True


def _remember_group(group_id):
    # V11.5 usually discovers a group in its text handler. Because this handler
    # executes first, register the group before sending or scheduling our menu.
    import group_ui_v115 as previous
    with previous._LOCK:
        previous._GROUPS.add(int(group_id))


def _schedule(bot, chat_id, message_id):
    from group_ui_v115 import _remember
    _remember(bot, chat_id, message_id, kind='book_menu')


def _forget_after_delete(chat_id, message_id):
    import group_ui_v115 as previous
    with previous._LOCK:
        previous._LOCAL.pop((int(chat_id), int(message_id)), None)
    # Best effort cleanup of persistent queue; never block a UI callback on it.
    try:
        (previous._db().table(previous.TABLE).delete()
         .eq('chat_id', int(chat_id)).eq('message_id', int(message_id)).execute())
    except Exception:
        LOG.debug('Could not clear already-deleted group book menu from queue')


def _close(bot, group_id, message_id):
    from group_ui_v115 import _remove
    if _remove(bot, group_id, message_id):
        _forget_after_delete(group_id, message_id)
        return
    # If deletion is restricted, at least make the buttons unusable.
    try:
        bot.edit_message_reply_markup(chat_id=group_id, message_id=message_id,
                                      reply_markup=None)
    except Exception:
        LOG.debug('Could not remove old group-book-menu buttons')


def _answer(bot, callback, text, *, alert=False):
    try:
        bot.answer_callback_query(callback.id, text, show_alert=alert)
    except Exception:
        pass


def _session_new(group_id, owner_id):
    now = time.monotonic()
    token = secrets.token_hex(6)  # short callback_data, random and unguessable
    with _LOCK:
        if len(_SESSIONS) > _MAX_SESSIONS:
            for k, v in list(_SESSIONS.items()):
                if v[3] < now:
                    _SESSIONS.pop(k, None)
            if len(_SESSIONS) > _MAX_SESSIONS:
                _SESSIONS.clear()
        _SESSIONS[token] = [int(group_id), None, int(owner_id), now + _MENU_TTL]
    return token


def _session_bind(token, message_id):
    with _LOCK:
        if token in _SESSIONS:
            _SESSIONS[token][1] = int(message_id)


def _session_use(token, group_id, message_id, uid):
    now = time.monotonic()
    with _LOCK:
        row = _SESSIONS.get(token)
        if not row or row[3] < now:
            _SESSIONS.pop(token, None)
            return 'expired'
        if row[0] != int(group_id) or row[1] != int(message_id):
            return 'invalid'
        if row[2] != int(uid):
            return 'not-owner'
        _SESSIONS.pop(token, None)
    return 'ok'


def _show_menu(bot, message):
    from book_library_bot import _enabled as library_enabled, _allowed_group, _verified, _bot_username
    from telebot import types
    cid, uid = int(message.chat.id), int(message.from_user.id)
    if not library_enabled() or not _allowed_group(cid) or not _verified(uid):
        return None  # groups not approved; no public information disclosed
    _remember_group(cid)
    token = _session_new(cid, uid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(types.InlineKeyboardButton('🔎 Search a Book', callback_data=f'gbm1:s:{token}'),
           types.InlineKeyboardButton('🆕 Latest 5 Books', callback_data=f'gbm1:l:{token}'))
    try:
        username = _bot_username(bot)
        kb.row(types.InlineKeyboardButton('📚 Full Library in Private Bot',
               url=f'https://t.me/{quote(username)}?start=study'))
    except Exception:
        pass
    try:
        sent = bot.send_message(cid,
           '📚 Book Library — Group Search\n\n'
           '🔎 Type /book TITLE or just a matching title to search.\n'
           '🆕 Tap Latest 5 to see recent books.\n'
           '📩 Book links open the bot to deliver PDFs privately.\n'
           '⏳ This menu auto-deletes after 5 minutes.',
           reply_markup=kb)
    except Exception:
        with _LOCK:
            _SESSIONS.pop(token, None)
        raise
    mid = getattr(sent, 'message_id', None)
    if mid:
        _session_bind(token, mid)
        _schedule(bot, cid, mid)
    return sent


def install_group_library_menu(bot):
    """Install before V11.5 and V11.6 handlers, while the TeleBot is created."""
    if getattr(bot, '_group_library_menu_v1161_installed', False):
        return bot
    bot._group_library_menu_v1161_installed = True

    @bot.message_handler(content_types=['text'], func=_is_target)
    def v1161_public_library_group_menu(m):
        from telebot.handler_backends import ContinueHandling
        if not (_enabled() and os.getenv('GROUP_BOOK_ONLY_V116_ENABLED', '').lower() in ('true','1','yes','on')):
            return ContinueHandling()
        if _mentioned_other_bot(bot, m):
            return None
        from book_library_bot import _enabled as lib_enabled, _allowed_group, _verified
        if not lib_enabled() or not _allowed_group(m.chat.id) or not _verified(m.from_user.id):
            return None
        try:
            _show_menu(bot, m)
        except Exception:
            LOG.warning('Group Book Library menu failed', exc_info=True)
        from group_ui_v115 import _remove, on
        if on('GROUP_UI_DELETE_NAV_INPUT', False):
            _remove(bot, m.chat.id, m.message_id)
        return None

    @bot.callback_query_handler(func=lambda c: (
        _group(getattr(c, 'message', None)) and
        str(getattr(c, 'data', '') or '').startswith('gbm1:')))
    def v1161_public_library_group_callback(c):
        if not _enabled():
            _answer(bot, c, 'This menu is currently disabled.', alert=True)
            return None
        parts = str(c.data or '').split(':')
        if len(parts) != 3 or parts[1] not in ('s', 'l'):
            _answer(bot, c, 'Invalid menu action.', alert=True)
            return None
        cid = int(c.message.chat.id)
        mid = int(c.message.message_id)
        uid = int(c.from_user.id)
        status = _session_use(parts[2], cid, mid, uid)
        if status == 'not-owner':
            _answer(bot, c, 'This menu belongs to another user. Type /bookmenu to open yours.', alert=True)
            return None
        if status != 'ok':
            _answer(bot, c, 'Menu expired. Type /bookmenu for a new one.', alert=True)
            return None
        # Do not leave a usable group session after the owner's first selection.
        _close(bot, cid, mid)
        if parts[1] == 's':
            _answer(bot, c, 'Search in this group with /book TITLE (or type a matching title).', alert=True)
        else:
            _answer(bot, c, 'Showing the latest five books.')
            try:
                from book_library_bot import _latest
                _remember_group(cid)
                _latest(bot, cid)
            except Exception:
                LOG.warning('Latest books in group unavailable', exc_info=True)
        return None

    return bot
