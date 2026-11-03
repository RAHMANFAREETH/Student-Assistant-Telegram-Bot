"""V11.1: Telegram private-channel Book Library (pyTelegramBotAPI).

Register early (before older wildcard handlers); /start deep links are delegated
from the existing main.py /start handler by the companion installer.
No AI, OCR, or new Render service is required.
"""
from __future__ import annotations
import os
import re
import threading
import time
import uuid

from book_library_store import (add_book, search_books, latest_books, get_book,
                                deactivate_book, parse_caption, format_size)

BUTTON = '📚 Book Library'
_pending = {}              # (chat_id, user_id) -> expires; only non-sensitive state
_throttle = {}             # (chat_id, user_id) -> monotonic last request
_lock = threading.RLock()
_username = None


def _on(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def _ids(name):
    answer = set()
    for raw in os.getenv(name, '').split(','):
        try:
            answer.add(int(raw.strip()))
        except (ValueError, TypeError):
            pass
    return answer


def _enabled():
    return _on('BOOK_LIBRARY_ENABLED')


def _admin(uid):
    ids = _ids('BOOK_LIBRARY_ADMIN_IDS') or _ids('V91_ADMIN_USER_IDS')
    return bool(uid) and int(uid) in ids


def _allowed_group(chat_id):
    # Explicit opt-in: permit /book and /booklatest in any group containing the bot.
    # Automatic free-text group search remains OFF unless separately enabled.
    if _on('BOOK_LIBRARY_ALLOW_ALL_GROUPS', False):
        return True
    ids = _ids('BOOK_LIBRARY_GROUP_IDS')
    return bool(ids) and int(chat_id) in ids


def _verified(uid):
    if not _on('BOOK_LIBRARY_REQUIRE_VERIFIED_ADULT', False):
        return True
    try:
        from study_access_v9 import is_verified_adult
        return bool(is_verified_adult(int(uid)))
    except Exception:
        return False  # Fail closed when eligibility DB is unavailable.


def _is_private(m):
    return getattr(getattr(m, 'chat', None), 'type', None) == 'private'


def _is_group(m):
    return getattr(getattr(m, 'chat', None), 'type', None) in ('group', 'supergroup')


def _command_args(m):
    value = str(getattr(m, 'text', '') or '').strip()
    return value.split(' ', 1)[1].strip() if ' ' in value else ''


def _cooldown(chat_id, uid, seconds=8):
    key = (int(chat_id), int(uid))
    now = time.monotonic()
    with _lock:
        if len(_throttle) > 2000:
            _throttle.clear()
        before = _throttle.get(key, -1e15)
        if now - before < seconds:
            return True
        _throttle[key] = now
    return False


def _session_set(m):
    with _lock:
        if len(_pending) > 2000:
            _pending.clear()
        _pending[(m.chat.id, m.from_user.id)] = time.monotonic() + 180


def _session_take(m):
    key = (m.chat.id, m.from_user.id)
    with _lock:
        expiry = _pending.pop(key, 0)
    return expiry > time.monotonic()


def _session_active(m):
    with _lock:
        return _pending.get((m.chat.id, m.from_user.id), 0) > time.monotonic()


def _bot_username(bot):
    global _username
    if _username:
        return _username
    raw = (os.getenv('BOOK_LIBRARY_BOT_USERNAME', '') or '').lstrip('@').strip()
    if not raw:
        raw = (getattr(bot.get_me(), 'username', None) or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9_]{5,32}', raw):
        raise RuntimeError('Bot username is unavailable.')
    _username = raw
    return raw


def _adult_notice(bot, chat_id):
    bot.send_message(chat_id, '🔒 The Book Library is available to verified adults. '
                   'Start with /verify_adult, then check /access_status. '
                   'Open the book link again after approval.')


def _short(s, n):
    s = str(s or '').replace('\n', ' ').replace('\r', ' ')
    return s if len(s) <= n else s[:n-1] + '…'


def _results_markup(bot, books):
    from telebot import types
    markup = types.InlineKeyboardMarkup(row_width=1)
    username = _bot_username(bot)
    for item in books:
        bid = uuid.UUID(str(item['id'])).hex
        label = (f"📖 {_short(item.get('title'), 22)} · "
                 f"{_short(item.get('author'), 13)} · "
                 f"{_short(item.get('language'), 9)} · {format_size(item.get('file_size'))}")
        markup.add(types.InlineKeyboardButton(
            label[:64], url=f'https://t.me/{username}?start=book_{bid}'))
    return markup


def _search(bot, chat_id, query, group=False):
    query = (query or '').strip()
    if not 2 <= len(query) <= 100:
        bot.send_message(chat_id, '🔎 Enter at least 2 characters. Example: /book Ibn Kathir')
        return
    try:
        books = search_books(query)
        if not books:
            if not group:
                bot.send_message(chat_id, '📚 No matching books found. Try a different title or author.')
            return
        text = (f'📚 Book results for: {_short(query, 90)}\n'
                'Tap a book to open it privately with the bot.\n'
                'Only books the library administrator may lawfully share are permitted.')
        bot.send_message(chat_id, text, reply_markup=_results_markup(bot, books))
    except Exception:
        bot.send_message(chat_id, '⚠️ Book search is temporarily unavailable. Please try again later.')


def _latest(bot, chat_id):
    try:
        books = latest_books(limit=5)
        if books:
            bot.send_message(chat_id, f'📚 Latest Books ({len(books)} most recent uploads):',
                             reply_markup=_results_markup(bot, books))
        else:
            bot.send_message(chat_id, '📚 No books have been added yet.')
    except Exception:
        bot.send_message(chat_id, '⚠️ Book catalog unavailable. Please try later.')


def _menu(bot, m):
    if not _is_private(m):
        bot.send_message(m.chat.id, '📚 Search here with /book TITLE or show the newest five with /booklatest. Results link to private delivery.')
        return
    if not _verified(m.from_user.id):
        _adult_notice(bot, m.chat.id)
        return
    from telebot import types
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton('🔎 Search a Book', callback_data='lib:search'),
           types.InlineKeyboardButton('🆕 Latest Books', callback_data='lib:latest'))
    bot.send_message(m.chat.id, '📚 Book Library\nSearch by book title, author or language.\n'
                     'You can also send /book Ibn Kathir.', reply_markup=kb)


def handle_library_start(bot, message):
    """Called by main.py at the beginning of its EXISTING /start handler.

    Returns True only when the deep-link was handled.
    """
    if not _is_private(message):
        return False
    raw = str(getattr(message, 'text', '') or '').strip()
    bits = raw.split(maxsplit=1)
    if len(bits) != 2 or not bits[1].startswith('book_'):
        return False
    token = bits[1][5:]
    if not re.fullmatch(r'[a-fA-F0-9]{32}', token):
        bot.send_message(message.chat.id, '⚠️ Invalid book link.')
        return True
    if not _enabled():
        bot.send_message(message.chat.id, '📚 The Book Library is not available yet.')
        return True
    if not _verified(message.from_user.id):
        _adult_notice(bot, message.chat.id)
        return True
    try:
        item = get_book(str(uuid.UUID(hex=token)))
        if not item:
            bot.send_message(message.chat.id, '📚 This book is unavailable or has been removed.')
            return True
        bot.copy_message(chat_id=message.chat.id,
                         from_chat_id=int(item['channel_id']),
                         message_id=int(item['message_id']))
        bot.send_message(message.chat.id,
                         f"✅ Sent: {_short(item['title'], 160)}\n"
                         f"✍️ {_short(item['author'], 100)} · {_short(item['language'], 35)}")
    except Exception:
        bot.send_message(message.chat.id,
                         '⚠️ Could not deliver the file. Please contact the library administrator.')
    return True


def register_book_library_handlers(bot):
    """Register early, BEFORE old wildcard navigation and document handlers."""
    from telebot import types
    from telebot.handler_backends import ContinueHandling

    @bot.message_handler(commands=['book', 'booksearch', 'books'])
    def library_commands(m):
        if not _enabled():
            bot.send_message(m.chat.id, '📚 Book Library is not enabled yet.')
            return
        if _is_group(m) and not _allowed_group(m.chat.id):
            bot.send_message(m.chat.id, '🔒 Book search is not enabled in this group.')
            return
        if not (_is_private(m) or _is_group(m)):
            return
        if not _verified(m.from_user.id):
            if _is_private(m):
                _adult_notice(bot, m.chat.id)
            else:
                bot.send_message(m.chat.id, '🔒 Book search requires verified-adult access. Use /verify_adult in the bot’s private chat.')
            return
        query = _command_args(m)
        if not query:
            if _is_private(m):
                _menu(bot, m)
            else:
                if _cooldown(m.chat.id, m.from_user.id, 3):
                    return
                _latest(bot, m.chat.id)
        else:
            if _cooldown(m.chat.id, m.from_user.id, 3):
                return
            _search(bot, m.chat.id, query, group=_is_group(m))

    @bot.message_handler(commands=['booklatest', 'latestbooks'])
    def library_latest_command(m):
        if not _enabled():
            bot.send_message(m.chat.id, '📚 Book Library is not enabled yet.')
            return
        if _is_group(m) and not _allowed_group(m.chat.id):
            bot.send_message(m.chat.id, '🔒 Book search is not enabled in this group.')
            return
        if not (_is_private(m) or _is_group(m)):
            return
        if not _verified(m.from_user.id):
            if _is_private(m):
                _adult_notice(bot, m.chat.id)
            else:
                bot.send_message(m.chat.id, '🔒 Book Library access is restricted.')
            return
        if _cooldown(m.chat.id, m.from_user.id, 3):
            return
        _latest(bot, m.chat.id)

    @bot.message_handler(commands=['bookremove'])
    def library_remove(m):
        if not _enabled() or not _is_private(m) or not _admin(m.from_user.id):
            bot.send_message(m.chat.id, '🔒 Library administrator only.')
            return
        if not re.fullmatch(r'[a-fA-F0-9-]{32,36}', _command_args(m)):
            bot.send_message(m.chat.id, 'Usage: /bookremove BOOK_UUID')
            return
        try:
            removed = deactivate_book(_command_args(m))
            bot.send_message(m.chat.id, '✅ Book disabled.' if removed else 'No active book found.')
        except ValueError:
            bot.send_message(m.chat.id, 'Invalid book UUID.')
        except Exception:
            bot.send_message(m.chat.id, '⚠️ Database unavailable. No change confirmed.')

    @bot.message_handler(func=lambda m: getattr(m, 'text', None) == BUTTON,
                         content_types=['text'])
    def library_menu(m):
        if not _enabled():
            bot.send_message(m.chat.id, '📚 Book Library is not enabled yet.')
            return
        _menu(bot, m)

    @bot.callback_query_handler(func=lambda c: getattr(c, 'data', None) in ('lib:search', 'lib:latest'))
    def library_callback(c):
        # Inline controls exist ONLY in the user's private Library menu.
        if not _enabled() or not _is_private(c.message) or c.from_user.id != c.message.chat.id:
            bot.answer_callback_query(c.id, 'Open the bot privately.', show_alert=True)
            return
        if not _verified(c.from_user.id):
            bot.answer_callback_query(c.id, 'Adult verification required.', show_alert=True)
            return
        bot.answer_callback_query(c.id)
        if c.data == 'lib:search':
            with _lock:
                if len(_pending) > 2000:
                    _pending.clear()
                _pending[(c.message.chat.id, c.from_user.id)] = time.monotonic() + 180
            bot.send_message(c.message.chat.id, '🔎 Send a title or author now (or /book TITLE).')
        else:
            _latest(bot, c.message.chat.id)

    @bot.message_handler(content_types=['document'],
                         func=lambda m: _enabled() and _is_private(m)
                         and _admin(m.from_user.id)
                         and str(getattr(m, 'caption', '') or '').count('|') == 2)
    def admin_book_upload(m):
        """An approved admin sends a document with Title | Author | Language."""
        try:
            title, author, language = parse_caption(m.caption)
        except ValueError as exc:
            bot.send_message(m.chat.id, '⚠️ ' + str(exc))
            return
        doc = getattr(m, 'document', None)
        filename = str(getattr(doc, 'file_name', '') or '')
        if not filename.lower().endswith(('.pdf', '.epub', '.docx', '.txt')):
            bot.send_message(m.chat.id, '⚠️ Supported book files: PDF, EPUB, DOCX and TXT.')
            return
        try:
            limit = max(1, min(int(os.getenv('BOOK_LIBRARY_MAX_BYTES', '52428800')), 2*1024**3))
        except ValueError:
            bot.send_message(m.chat.id, '⚠️ Library upload size limit is misconfigured.')
            return
        file_size = int(getattr(doc, 'file_size', 0) or 0)
        if file_size < 0 or file_size > limit:
            bot.send_message(m.chat.id, f'⚠️ File exceeds library upload limit ({format_size(limit)}).')
            return
        raw_channel = os.getenv('BOOK_LIBRARY_CHANNEL_ID', '')
        try:
            channel = int(raw_channel)
            if channel >= 0:
                raise ValueError()
        except ValueError:
            bot.send_message(m.chat.id, '⚠️ Library storage channel is not configured.')
            return
        # Copy directly through Telegram. Never download/upload bytes on Render.
        try:
            copied = bot.copy_message(chat_id=channel, from_chat_id=m.chat.id,
                                      message_id=m.message_id)
            storage_mid = int(copied.message_id)
        except Exception:
            bot.send_message(m.chat.id, '⚠️ Could not store file in the channel. '
                             'Check that the bot is a channel admin with posting permission.')
            return
        try:
            rec = add_book(title=title, author=author, language=language,
                           channel_id=channel, message_id=storage_mid,
                           file_name=filename, file_size=file_size,
                           uploaded_by=m.from_user.id)
        except Exception:
            try:
                bot.delete_message(channel, storage_mid) # best-effort orphan cleanup
            except Exception:
                pass
            bot.send_message(m.chat.id, '⚠️ File copied but the catalog save failed. '
                             'Check Supabase migration and service credentials.')
            return
        bot.send_message(m.chat.id,
                         f'✅ Added to Book Library\n📖 {_short(title, 180)}\n'
                         f'✍️ {_short(author, 120)} · {_short(language, 40)}\n'
                         f'📦 {format_size(file_size)}\nID: {rec["id"]}')

    @bot.message_handler(content_types=['text'],
                         func=lambda m: _enabled() and _is_private(m)
                         and not str(getattr(m, 'text', '') or '').startswith('/')
                         and _session_active(m))
    def private_search(m):
        _session_take(m)
        if not _verified(m.from_user.id):
            _adult_notice(bot, m.chat.id)
            return
        if m.text in ('❌ Cancel', '↩️ All Categories', '🏠 Main Menu'):
            return ContinueHandling()
        _search(bot, m.chat.id, m.text)

    @bot.message_handler(content_types=['text'],
                         func=lambda m: _enabled() and _on('BOOK_LIBRARY_AUTO_GROUP_SEARCH')
                         and _is_group(m) and _allowed_group(m.chat.id)
                         and 3 <= len(str(getattr(m, 'text', '') or '').strip()) <= 100
                         and not str(getattr(m, 'text', '') or '').startswith('/')
                         and not str(getattr(m, 'text', '') or '').startswith('@'))
    def group_search(m):
        if not _verified(m.from_user.id):
            return ContinueHandling()
        if _cooldown(m.chat.id, m.from_user.id, 8):
            return ContinueHandling()
        try:
            books = search_books(m.text, limit=6)
            if not books:
                return ContinueHandling()
            bot.send_message(m.chat.id,
                             f'📚 Matching books for: {_short(m.text, 80)}\n'
                             'Tap to receive a copy in the bot’s private chat.',
                             reply_markup=_results_markup(bot, books))
        except Exception:
            # Silent on group auto-search failures; never spam groups with errors.
            return ContinueHandling()
