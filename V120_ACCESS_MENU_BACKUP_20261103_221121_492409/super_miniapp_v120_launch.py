"""Opt-in Telegram private-chat launcher for the V12 Super Mini App.

This module does not change the BotFather menu or existing Library buttons.
Registration is safe while SUPER_MINIAPP_V120_ENABLED=false.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

_TRUE = {'true', '1', 'yes', 'on'}


def _on(key: str) -> bool:
    return os.getenv(key, '').strip().lower() in _TRUE


def mini_app_url() -> str | None:
    """Only return an HTTPS URL pointing to the expected /app endpoint."""
    explicit = os.getenv('SUPER_MINIAPP_V120_PUBLIC_URL', '').strip()
    if explicit:
        url = explicit.rstrip('/')
    else:
        base = (os.getenv('RENDER_EXTERNAL_URL', '') or os.getenv('BOOK_LIBRARY_PUBLIC_URL', '')).strip().rstrip('/')
        url = base + '/app' if base else ''
    if not url or any(c.isspace() for c in url) or '\\' in url:
        return None
    try:
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            return None
        if parsed.query or parsed.fragment or parsed.path != '/app':
            return None
        if parsed.port not in (None, 443):
            return None
        if parsed.hostname in ('localhost', '127.0.0.1', '::1'):
            return None
        return url
    except ValueError:
        return None


def pilot_user_ids() -> set[int]:
    result = set()
    for part in os.getenv('SUPER_MINIAPP_V120_PILOT_IDS', '').split(','):
        part = part.strip()
        if part.isdecimal() and 0 < len(part) <= 20:
            uid = int(part)
            if uid > 0:
                result.add(uid)
    return result


def pilot_access_allowed(uid: int) -> bool:
    """Server-side API pilot limit, when PILOT_IDS is configured.

    If unset, retain existing verified-adult-only API behavior and tests.
    This is NOT a substitute for Telegram HMAC or adult verification.
    """
    if type(uid) is not int or uid <= 0:
        return False
    if _on('SUPER_MINIAPP_V120_LAUNCH_PUBLIC'):
        return True
    raw = os.getenv('SUPER_MINIAPP_V120_PILOT_IDS', '').strip()
    return not raw or uid in pilot_user_ids()


def can_launch(uid: int) -> bool:
    """Release flag and pilot list are launcher controls, not API authorization."""
    if not (_on('SUPER_MINIAPP_V120_ENABLED') and _on('SUPER_MINIAPP_V120_LAUNCH_ENABLED')):
        return False
    if type(uid) is not int or uid <= 0:
        return False
    if not (_on('SUPER_MINIAPP_V120_LAUNCH_PUBLIC') or uid in pilot_user_ids()):
        return False
    try:
        from study_access_v9 import is_verified_adult
        return is_verified_adult(uid) is True
    except Exception:
        return False


def register_super_app_launcher(bot):
    """Register explicitly invoked commands early in main.py, no global menu override."""
    @bot.message_handler(commands=['superapp', 'app'])
    def v120_super_app_command(message):
        chat = getattr(message, 'chat', None)
        if getattr(chat, 'type', None) != 'private':
            return
        uid = getattr(getattr(message, 'from_user', None), 'id', None)
        chat_id = getattr(chat, 'id', None)
        if not isinstance(chat_id, int):
            return
        if not can_launch(uid):
            bot.send_message(chat_id, 'The V12 Mini App is not available for your account yet.')
            return
        url = mini_app_url()
        if not url:
            bot.send_message(chat_id, 'The V12 Mini App URL is not configured yet.')
            return
        from telebot import types
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton('🎓 Open Student Assistant Super App',
                                              web_app=types.WebAppInfo(url=url)))
        bot.send_message(chat_id, 'Open your secure Student Assistant Super Mini App:',
                         reply_markup=keyboard)
