"""V11.8.8.4 optional welcome for people joining authorized Book Library groups.

Never sends unsolicited private messages, modifies group search, or bypasses eligibility.
"""
from __future__ import annotations
import logging
import os
import re
import threading
import time

LOG = logging.getLogger(__name__)
_LOCK = threading.RLock()
_SEEN = {}
_BOT_USER = 'Student_Sl_Assistant_bot'

def _on(name, default=False):
    return str(os.getenv(name, str(default))).strip().lower() in ('true', 'yes', '1', 'on')

def enabled():
    return _on('GROUP_WELCOME_V11884_ENABLED')

def _clean(value, maximum=80):
    value = re.sub(r'[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]', ' ', str(value or ''))
    return re.sub(r'\s+', ' ', value).strip()[:maximum]

def _name(user):
    username = _clean(getattr(user, 'username', ''), 32)
    if re.fullmatch(r'[A-Za-z0-9_]{5,32}', username):
        return '@' + username
    firstname = _clean(getattr(user, 'first_name', ''), 64)
    return firstname or 'New member'

def _allowed(cid):
    # Welcome only in groups where public book searching is already authorized.
    if not _on('GROUP_BOOK_ONLY_V116_ENABLED'):
        return False
    try:
        from book_library_bot import _enabled, _allowed_group
        return bool(_enabled() and _allowed_group(cid))
    except Exception:
        LOG.warning('Cannot verify Book Library group eligibility', exc_info=True)
        return False

def _first_time(chat_id, user_id, now=None):
    now = time.monotonic() if now is None else now
    key = (int(chat_id), int(user_id))
    with _LOCK:
        if len(_SEEN) >= 2000:
            for k, expiry in list(_SEEN.items()):
                if expiry <= now:
                    _SEEN.pop(k, None)
            if len(_SEEN) >= 2000:
                _SEEN.clear()
        if _SEEN.get(key, 0) > now:
            return False
        _SEEN[key] = now + 90
        return True

def _text(name):
    return (
        f'👋 Welcome to our Digital Library, {name}! 📚\n\n'
        '🔎 HOW TO SEARCH FOR BOOKS\n'
        '1️⃣ Send /book Quran to search by title.\n'
        '2️⃣ If plain-text search is enabled, you can also type Quran.\n'
        '3️⃣ Another example: /book The Psychology of Money\n'
        '4️⃣ Use /booklatest for recent books.\n\n'
        '📚 Search results show book files and language filters.\n'
        '📩 Tap a result to open the bot and receive the file privately.\n'
        f'🤖 Bot: https://t.me/{_BOT_USER}\n\n'
        '🔞 Service is for eligible users aged 18+. Access rules apply.\n'
        '💚 Please respect other members and share only material you may distribute.'
    )

def handle_join(bot, message):
    """Handle Telegram new_chat_members service message; return messages sent."""
    if not enabled():
        return 0
    chat = getattr(message, 'chat', None)
    if getattr(chat, 'type', None) not in ('group', 'supergroup'):
        return 0
    cid = getattr(chat, 'id', None)
    if cid is None or not _allowed(cid):
        return 0
    members = getattr(message, 'new_chat_members', None) or []
    sent_count = 0
    for member in members[:20]:  # bounded notifications for large joins
        if getattr(member, 'is_bot', False) or getattr(member, 'id', None) is None:
            continue
        if not _first_time(cid, member.id):
            continue
        try:
            sent = bot.send_message(cid, _text(_name(member)),
                                    disable_web_page_preview=True)
            sent_count += 1
            if _on('GROUP_WELCOME_AUTO_DELETE_V11884', True):
                try:
                    from group_ui_v115 import _remember
                    _remember(bot, cid, getattr(sent, 'message_id', None), kind='welcome') if getattr(sent, 'message_id', None) else None
                except Exception:
                    LOG.debug('Welcome message deletion queue unavailable', exc_info=True)
        except Exception:
            LOG.warning('Cannot send group welcome', exc_info=True)
    return sent_count

def install_group_welcome(bot):
    if getattr(bot, '_group_welcome_v11884_installed', False):
        return bot
    @bot.message_handler(content_types=['new_chat_members'])
    def v11884_group_member_welcome(message):
        return handle_join(bot, message)
    bot._group_welcome_v11884_installed = True
    return bot
