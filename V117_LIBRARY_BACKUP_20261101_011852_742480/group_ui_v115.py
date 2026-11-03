"""V11.5 optional group-menu isolation and 5-minute cleanup.

Additive: does not monkeypatch existing handlers' state, change book delivery,
or alter verified-adult access. The wrapper only modifies outgoing group menus.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import wraps
import logging
import os
import re
import threading
import time

LOG = logging.getLogger(__name__)
TABLE = 'bot_group_ephemeral_messages'
_GROUPS = set()
_LOCK = threading.RLock()
_LOCAL = {}  # fallback when Supabase temporarily fails; keyed by (chat, message)
_STARTED = set()


# Only PERSONAL navigation and student-workflow entry points are redirected.
# /book, /booklatest, book discovery, and group quiz battles remain untouched.
PUBLIC_BOOK_COMMANDS = frozenset({'book', 'books', 'booksearch', 'booklatest',
                                  'latestbooks', 'booksmart', 'bookbrowse'})

PERSONAL_COMMANDS = frozenset({
    'start', 'help', 'menu', 'categories', 'language', 'v8', 'v9', 'v10',
    'v101', 'study', 'studydiag', 'studyperf', 'adult_admin', 'access_admin',
    'access_status', 'verify_adult', 'v10add', 'v10docs', 'v10ask',
    'v10askai', 'v10viva', 'v10coach', 'v10due', 'v10save',
})
MENU_BUTTONS = frozenset({
    '📚 Book Library', '🌎 Languages', '🌐 Languages',
    '📦 More Tools', '↩️ All Categories', '🤖 AI & Questions', '📚 Study Tools',
    '📅 Plans & Reminders', '🧠 Practice & Quiz', '🌍 Languages',
    '📊 My Progress', '🎙 Voice & PDF', 'ℹ️ Help', '❓ Help & Tutorial',
    '🚀 Study Center', '🧰 V9 Academic Toolkit', '🚀 V8 Study Lab',
    '🧠 V10 Learning Lab', '📚 My documents', '🔎 Find a Tool',
    '⚙️ Settings', '🔐 Verify Adult Access',
})


def on(name: str, default: bool = False) -> bool:
    return str(os.getenv(name, str(default))).strip().lower() in ('true', '1', 'yes', 'on')


def seconds() -> int:
    try:
        return max(60, min(1800, int(os.getenv('GROUP_UI_DELETE_AFTER_SECONDS', '300'))))
    except (TypeError, ValueError):
        return 300


def group(chat) -> bool:
    return getattr(chat, 'type', None) in ('group', 'supergroup')


def navigation_input(text: str) -> bool:
    t = str(text or '').strip()
    if t in MENU_BUTTONS:
        return True
    if t.startswith('/'):
        cmd = t[1:].split(None, 1)[0].split('@', 1)[0].lower()
        return cmd in PERSONAL_COMMANDS
    return False


def book_url_keyboard(markup) -> bool:
    """Keep public book URL results. They are not session-specific callbacks."""
    buttons = [button for row in getattr(markup, 'keyboard', []) or
               getattr(markup, 'inline_keyboard', []) or [] for button in row]
    return bool(buttons) and all(
        bool(re.search(r'(?:\?|&)start=book_[0-9a-fA-F]{32}(?:&|$)',
                       str(getattr(b, 'url', '') or '')))
        for b in buttons
    )


def _library_group_response(text, markup) -> bool:
    msg = str(text or '').strip()
    return (book_url_keyboard(markup) or
            msg.startswith(('📚 Latest Books', '📚 Recently added books',
                            '📚 Book results', '🔎 Books matching',
                            '📖 Books matching', '📚 Book Library',
                            '📚 Search here', '📚 Choose a', '📚 Browse')))


def is_reply_menu(markup) -> bool:
    return getattr(markup, '__class__', object).__name__ == 'ReplyKeyboardMarkup'


def is_inline_menu(markup) -> bool:
    return getattr(markup, '__class__', object).__name__ == 'InlineKeyboardMarkup'


def personal_reply_menu(markup, text) -> bool:
    # Don't break group quiz / group voting reply keyboards. Only old
    # personal navigation layouts are replaced with private-chat links.
    if not is_reply_menu(markup):
        return False
    labels = [str(getattr(b, 'text', '') or '')
              for row in getattr(markup, 'keyboard', []) or [] for b in row]
    return (any(label in MENU_BUTTONS for label in labels) or
            str(text or '').startswith(('👋 Hello', '📦 More Tools',
                                          'Choose a category', 'Select a tool')))


def personal_inline_menu(markup, text) -> bool:
    return (is_inline_menu(markup) and
            str(text or '').startswith(('👋 Hello', '📦 More Tools',
                                         '🔐 Personal', '📚 Book Library',
                                         'Choose a category')))


def _db():
    from db import supabase
    return supabase


def _remember(bot, chat_id, message_id, *, kind='menu', db=None, now=None):
    """Persist only Telegram group/message IDs and expiry; no user contents."""
    if not on('GROUP_UI_TIMER_ENABLED', False):
        return
    cid, mid = int(chat_id), int(message_id)
    due = (now or datetime.now(timezone.utc)) + timedelta(seconds=seconds())
    with _LOCK:
        # Bound the fallback cache: database is authoritative when available.
        if len(_LOCAL) >= 2000:
            _LOCAL.clear()
        _LOCAL[(cid, mid)] = due.timestamp()
    try:
        (db or _db()).table(TABLE).upsert({
            'chat_id': cid, 'message_id': mid, 'message_type': kind,
            'delete_at': due.isoformat(), 'attempts': 0,
        }, on_conflict='chat_id,message_id').execute()
    except Exception as exc:
        LOG.warning('Group-menu cleanup DB queue unavailable (%s); using process-local fallback',
                    type(exc).__name__)


def _remove(bot, chat_id, message_id) -> bool:
    try:
        return bool(bot.delete_message(int(chat_id), int(message_id)))
    except Exception as exc:
        LOG.debug('Group menu not deleted (%s)', type(exc).__name__)
        return False


def cleanup_once(bot, *, db=None, now=None, claim_limit=30):
    """One bounded cleanup cycle; callable independently for tests."""
    now = (now or datetime.now(timezone.utc)).timestamp()
    done = 0
    d = db
    try:
        if d is None:
            d = _db()
        result = d.rpc('v115_claim_due_group_messages', {'p_limit': min(60, max(1, claim_limit))}).execute()
        rows = getattr(result, 'data', None) or []
        for row in rows:
            cid = int(row['out_chat_id'])
            mid = int(row['out_message_id'])
            success = _remove(bot, cid, mid)
            try:
                if success:
                    d.table(TABLE).delete().eq('chat_id', cid).eq('message_id', mid).execute()
                else:
                    d.rpc('v115_release_group_message', {'p_chat_id': cid, 'p_message_id': mid}).execute()
            except Exception as exc:
                LOG.warning('Group-menu cleanup finalize failed: %s', type(exc).__name__)
            with _LOCK:
                _LOCAL.pop((cid, mid), None)
            done += bool(success)
    except Exception as exc:
        LOG.debug('Group-menu cleanup DB poll unavailable (%s)', type(exc).__name__)
    with _LOCK:
        due = [(key, expiry) for key, expiry in _LOCAL.items() if expiry <= now][:40]
    for (cid, mid), expiry in due:
        if _remove(bot, cid, mid):
            done += 1
        with _LOCK:
            if _LOCAL.get((cid, mid)) == expiry:
                _LOCAL.pop((cid, mid), None)
        # DB lease may have failed; delete queue row best effort to avoid repeats.
        if d is not None:
            try:
                d.table(TABLE).delete().eq('chat_id', cid).eq('message_id', mid).execute()
            except Exception:
                pass
    return done


def _loop(bot):
    # Running in the existing Render service, not a separate bot or process.
    while on('GROUP_UI_PROTECTION_ENABLED', False) and on('GROUP_UI_TIMER_ENABLED', False):
        try:
            cleanup_once(bot)
        except Exception as exc:
            LOG.warning('Group-menu worker error: %s', type(exc).__name__)
        time.sleep(10)


def _start_worker(bot):
    if not on('GROUP_UI_TIMER_ENABLED', False):
        return
    with _LOCK:
        key = id(bot)
        if key in _STARTED:
            return
        _STARTED.add(key)
    threading.Thread(target=_loop, args=(bot,), name='group-menu-cleanup', daemon=True).start()


def _username(bot):
    raw = str(os.getenv('BOOK_LIBRARY_BOT_USERNAME', '') or '').strip().lstrip('@')
    if not raw:
        raw = str(os.getenv('BOT_USERNAME', '') or '').strip().lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9_]{5,32}', raw):
        return None
    return raw


def _link_markup(bot):
    from telebot import types
    username = _username(bot)
    if not username:
        return None
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton('🔐 Open My Private Bot',
                                      url=f'https://t.me/{username}?start=study'))
    return kb


def _notice(bot, raw_send, chat_id, *, reply_to=None):
    kwargs = {}
    if reply_to is not None:
        kwargs['reply_to_message_id'] = int(reply_to)
    kb = _link_markup(bot)
    username = _username(bot)
    text = ('🔐 This menu is private. Open your own bot session.\n'
            '📚 Public book search: /book TITLE or /booklatest.')
    if (reply_to is not None and username and
            on('GROUP_UI_CLOSE_REPLY_KEYBOARD', True)):
        # Telegram lets ReplyKeyboardRemove(selective=True) close the keyboard
        # for the user whose incoming message we reply to. A single markup
        # cannot be both ReplyKeyboardRemove and an inline button, so the
        # clickable bot link is placed in the message text instead.
        from telebot import types
        kwargs['reply_markup'] = types.ReplyKeyboardRemove(selective=True)
        text = (f'🔐 Your group menu is closed. Open your own bot: '
                f'https://t.me/{username}?start=study\n'
                '📚 Public book search: /book TITLE or /booklatest.')
    elif kb is not None:
        kwargs['reply_markup'] = kb
    try:
        result = raw_send(chat_id, text, **kwargs)
    except Exception:
        # Some groups reject replies to deleted messages; retry without
        # reply threading, with the inline link instead of selective removal.
        kwargs.pop('reply_to_message_id', None)
        kwargs.pop('reply_markup', None)
        if kb is not None:
            kwargs['reply_markup'] = kb
        result = raw_send(chat_id, '🔐 Open the bot privately for personal tools.\n'
                                   '📚 Public book search: /book TITLE.', **kwargs)
    mid = getattr(result, 'message_id', None)
    if mid:
        _remember(bot, chat_id, mid, kind='redirect')
    return result


def install_group_ui_guard(bot):
    """Must run ONCE immediately after TeleBot creation, before legacy handlers."""
    if getattr(bot, '_group_ui_v115_installed', False):
        return bot
    bot._group_ui_v115_installed = True
    raw_send = bot.send_message

    @wraps(raw_send)
    def group_safe_send(chat_id, text, *args, **kwargs):
        if not on('GROUP_UI_PROTECTION_ENABLED', False):
            return raw_send(chat_id, text, *args, **kwargs)
        try:
            cid = int(chat_id)
        except (ValueError, TypeError):
            return raw_send(chat_id, text, *args, **kwargs)
        with _LOCK:
            is_group_id = cid in _GROUPS
        if not is_group_id:
            return raw_send(chat_id, text, *args, **kwargs)
        markup = kwargs.get('reply_markup')
        if personal_reply_menu(markup, text) and on('GROUP_UI_PRIVATE_NAVIGATION', True):
            # Prevent the reply keyboard from appearing for everybody in a group.
            return _notice(bot, raw_send, cid)
        result = raw_send(chat_id, text, *args, **kwargs)
        if (_library_group_response(text, markup) or
            personal_inline_menu(markup, text) or
            str(text or '').startswith(('👋 Hello,', '📦 More Tools', '🔐 Open the bot privately'))):
            mid = getattr(result, 'message_id', None)
            if mid:
                _remember(bot, cid, mid, kind='book_links' if book_url_keyboard(markup) else 'menu')
        return result

    bot.send_message = group_safe_send

    from telebot.handler_backends import ContinueHandling

    @bot.message_handler(content_types=['text'],
                         func=lambda m: group(getattr(m, 'chat', None)))
    def v115_group_navigation_guard(message):
        if not on('GROUP_UI_PROTECTION_ENABLED', False):
            return ContinueHandling()
        with _LOCK:
            _GROUPS.add(int(message.chat.id))
        text = str(getattr(message, 'text', '') or '').strip()
        command = text[1:].split(None, 1)[0].split('@', 1)[0].lower() if text.startswith('/') else ''
        if command in PUBLIC_BOOK_COMMANDS:
            # Public book-search commands remain functional. If the bot has
            # Delete Messages permission, their text may expire with results.
            if on('GROUP_UI_EXPIRE_BOOK_COMMANDS', True):
                _remember(bot, message.chat.id, message.message_id, kind='menu')
            return ContinueHandling()
        if not on('GROUP_UI_PRIVATE_NAVIGATION', True) or not navigation_input(text):
            return ContinueHandling()
        _notice(bot, raw_send, message.chat.id, reply_to=getattr(message, 'message_id', None))
        if on('GROUP_UI_DELETE_NAV_INPUT', True):
            _remove(bot, message.chat.id, message.message_id)
        return None  # Stop routing to legacy navigation and stateful handlers.

    @bot.callback_query_handler(func=lambda c: (
        on('GROUP_UI_PROTECTION_ENABLED', False)
        and group(getattr(getattr(c, 'message', None), 'chat', None))
        and str(getattr(c, 'data', '') or '').startswith(
            ('lib:', 'lib2:', 'lib3:', 'v10:', 'v101:', 'v11:', 'nav:', 'ui:'))))
    def v115_group_personal_callback_guard(callback):
        # Existing personal callback menus in historical group messages are unsafe.
        # Public book URL buttons generate no callback, so remain unaffected.
        try:
            bot.answer_callback_query(callback.id,
                '🔐 Open the bot privately to use this personal menu.', show_alert=True)
        except Exception:
            pass
        if on('GROUP_UI_AUTODELETE_CALLBACK', True):
            _remove(bot, callback.message.chat.id, callback.message.message_id)
        return None

    _start_worker(bot)
    return bot
