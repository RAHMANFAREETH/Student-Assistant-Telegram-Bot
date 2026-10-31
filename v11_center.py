"""V11 Student Experience & Performance: an opt-in, light-weight Telegram navigator.

No provider/network calls occur when opening the menu or navigating pages.
Legacy V7–V10.1 handlers, Supabase schemas, quotas and age gates are unchanged.
"""
from __future__ import annotations
import importlib.util
import logging
import os
import secrets
import sys
import threading
import time
from collections import OrderedDict

import v11_metrics as metrics

LOG = logging.getLogger(__name__)
TRUTH = ('true', 'yes', '1')
BUTTON = '🚀 Study Center'
TOKEN_TTL = 300
TOKEN_LIMIT = 256
_LOCK = threading.RLock()
_TOKENS = OrderedDict()


def enabled():
    return os.getenv('V11_ENABLED', '').strip().lower() in TRUTH


def private(m):
    try:
        return m.chat.type == 'private' and int(m.chat.id) == int(m.from_user.id)
    except (AttributeError, TypeError, ValueError):
        return False


def admin(uid):
    try:
        user_id = int(uid)
        if user_id <= 0:
            return False
    except (TypeError, ValueError):
        return False
    ids = os.getenv('V91_ADMIN_USER_IDS', '').split(',')
    return any(x.strip().isdigit() and int(x.strip()) == user_id for x in ids)


def _bool(name):
    return 'ON' if os.getenv(name, '').strip().lower() in TRUTH else 'off'


def _new_token(uid, chat_id):
    now = time.monotonic()
    with _LOCK:
        for token, (_, _, stamp) in list(_TOKENS.items()):
            if now - stamp > TOKEN_TTL:
                _TOKENS.pop(token, None)
        token = secrets.token_urlsafe(7)
        _TOKENS[token] = (int(uid), int(chat_id), now)
        while len(_TOKENS) > TOKEN_LIMIT:
            _TOKENS.popitem(last=False)
        return token


def _redeem_token(token, uid, chat_id):
    now = time.monotonic()
    with _LOCK:
        item = _TOKENS.get(str(token))
        if not item:
            return False
        expected_uid, expected_chat, stamp = item
        if now - stamp > TOKEN_TTL:
            _TOKENS.pop(str(token), None)
            return False
        if expected_uid != int(uid) or expected_chat != int(chat_id):
            return False
        _TOKENS.pop(str(token), None)  # single-use button token
        return True


PAGES = {
    'docs': (
        '📚 Your document workflow\n\n'
        '1. /v10add — send PDF, DOCX or TXT\n'
        '2. /v10save — save prepared text privately\n'
        '3. /v10docs — list your documents\n'
        '4. /v10ask QUESTION — search and view source snippets\n'
        '5. /v10askai QUESTION → /v10confirm_ai — consented Gemini answer\n\n'
        'For scanned pages: /v101ocr → upload → /v101ocrconfirm → /v101ocrsave. '
        'OCR uses an external provider after separate consent.'
    ),
    'ai': (
        '🤖 Gemini tutor\n\n'
        '/v101chat QUESTION — chat with notes and short memory\n'
        '/v101explain Tamil | QUESTION — Tamil lesson (also Sinhala, Arabic, English)\n'
        '/v101compareai TOPIC — compare saved sources\n'
        '/v101check CLAIM — offline lexical source-overlap screening\n'
        '/v101confirm — review and consent to the pending Gemini request\n'
        '/v101forget — delete saved V10.1 tutor turns\n\n'
        'AI requests require verified-adult access and a daily quota. '
        'AI can be inaccurate; review document citations.'
    ),
    'practice': (
        '📝 Practice and review\n\n'
        '/v101viva TOPIC — AI question, then /v101answer ANSWER\n'
        '/v101voice — use voice in a viva after consent\n'
        '/v101mock TOPIC — 3-question practice exam; /v101submit A B C\n'
        '/v101cards TOPIC — AI flashcards; /v101cardsave\n'
        '/v10due — cards due; /v10card ID → /v10reveal → /v10rate good\n'
        '/v101plan 7 | Biology | 60 — learning plan; /v101myplan\n'
        'These are practice tools, not official exam marking.'
    ),
    'more': (
        '🧰 More study tools\n\n'
        '/v8 — Study Lab (past papers, quizzes, study planning and more)\n'
        '/v9 — Academic Toolkit (math, diagram reading, citations and more)\n'
        '/v10 — Learning Lab\n'
        '/v101 — All 12 advanced learning features\n'
        '/v101roomcreate GOAL — start an opt-in study room\n'
        '/v101audio TOPIC — consented audio summary\n\n'
        'Use each tool’s own menu for its complete instructions.'
    ),
    'access': (
        '🔐 Adult-access help\n\n'
        '/access_status — see current verification and expiry\n'
        '/verify_adult — request administrator review\n'
        '/access_help — access rules and help\n\n'
        'Only independently verified adults can access restricted study features. '
        'A self-declaration or Telegram account alone is not proof of age.'
    ),
    'errors': (
        '🛠 Troubleshooting\n\n'
        '• Menu missing: check the relevant V8/V9/V10/V101 feature switch.\n'
        '• Access denied: try /access_status; verified-adult record may be missing or expired.\n'
        '• Upload cannot be saved: check supported format, page/text limits and /v10save.\n'
        '• Gemini unavailable: confirm the feature switch, consent, provider quota and Render logs.\n'
        '• Pending upload or AI request stuck: try /studycancel, then restart.\n'
        '• Never paste API keys or service-role tokens into Telegram messages.\n\n'
        'V11 does not bypass any provider quota or verified-adult restriction.'
    ),
}

HOME_TEXT = (
    '🚀 Study Center — V11.0\n'
    'Fast navigation for existing Student Assistant tools.\n\n'
    'Choose a topic below or use /studyhelp. '
    'Menus do not contact Gemini or Supabase; restricted tools still require adult verification.\n'
    'To cancel pending V10/V10.1 actions: /studycancel.'
)


def status_text(uid, verifier=None):
    mode = os.getenv('STUDY_ACCESS_MODE', 'pilot').strip().lower()
    rows = [
        '📊 Study feature status',
        'V8: ' + _bool('V8_ENABLED'),
        'V9: ' + _bool('V9_ENABLED'),
        'V10: ' + _bool('V10_ENABLED'),
        'V10 Gemini: ' + _bool('V10_GEMINI_ENABLED'),
        'V10.1: ' + _bool('V101_ENABLED'),
        'V11: ' + _bool('V11_ENABLED'),
        'Adult access mode: ' + ('verified_adults' if mode == 'verified_adults' else 'not verified_adults'),
    ]
    if mode != 'verified_adults':
        rows.append('Verified-adult gate is not the active study access mode.')
    else:
        try:
            if verifier is None:
                from study_access_v9 import is_verified_adult
                verifier = is_verified_adult
            rows.append('Your adult verification: ' + ('active' if verifier(uid) else 'not confirmed'))
        except Exception:
            LOG.warning('V11 could not read verification status', exc_info=True)
            rows.append('Your adult verification: temporarily unavailable')
    rows.append('For expiry and requests, use /access_status. ON means configured, not provider-tested.')
    return '\n'.join(rows)


def diagnostic_text():
    names = ('v8_bot', 'v9_bot', 'v10_bot', 'v101_bot',
             'v91_access_bot', 'v92_admin_bot', 'v93_reliability_bot')
    rows = [
        '🛡 V11 local deployment diagnostics (admin only)',
        'Python: ' + '.'.join(map(str, sys.version_info[:3])),
        'V11: ' + _bool('V11_ENABLED'),
        'V10 Gemini: ' + _bool('V10_GEMINI_ENABLED'),
        'Adult access mode: ' + ('verified_adults' if os.getenv('STUDY_ACCESS_MODE', '').lower() == 'verified_adults' else 'other'),
    ]
    for name in names:
        rows.append(f'{name}: ' + ('present' if importlib.util.find_spec(name) else 'missing'))
    rows.append('Module presence is not a live API/SQL health check. Secrets and user data are not displayed.')
    return '\n'.join(rows)


def _keyboard(uid, chat_id, items):
    from telebot import types
    token = _new_token(uid, chat_id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(label, callback_data=f'v11:{token}:{code}')
               for label, code in items]
    kb.add(*buttons)
    return kb


HOME_BUTTONS = (
    ('📚 Documents', 'docs'), ('🤖 Gemini tutor', 'ai'),
    ('📝 Practice', 'practice'), ('🧰 All tools', 'more'),
    ('🔐 Adult access', 'access'), ('📊 My status', 'status'),
    ('🛠 Troubleshooting', 'errors'), ('❎ Cancel pending', 'cancel'),
)


def register_v11_handlers(bot):
    """Register before V10.1 and all older stateful handlers."""
    def send(chat, message, markup=None):
        bot.send_message(chat, str(message)[:3950], reply_markup=markup)

    def require_private(m):
        if not private(m):
            try: send(m.chat.id, '🔒 Use Study Center in a private Telegram chat with the bot.')
            except Exception: LOG.warning('V11 could not send private-chat notice')
            return False
        return True

    def run(action, fn, m):
        started = time.monotonic()
        try:
            if not enabled():
                send(m.chat.id, 'V11 Study Center is not enabled. Existing /v10 and /v101 tools are unchanged.')
                return
            if not require_private(m):
                return
            fn(m)
        except Exception:
            LOG.exception('V11 %s failed', action)
            try: send(m.chat.id, '⚠️ Study Center could not complete that action. Older study tools remain available.')
            except Exception: LOG.exception('V11 response failed')
        finally:
            metrics.record(action, (time.monotonic()-started)*1000)

    def show_home(m):
        send(m.chat.id, HOME_TEXT, _keyboard(m.from_user.id, m.chat.id, HOME_BUTTONS))

    def show_help(m):
        raw = str(getattr(m, 'text', '') or '').split(' ', 1)
        choice = raw[1].lower().strip() if len(raw) > 1 else ''
        if choice in PAGES:
            send(m.chat.id, PAGES[choice], _keyboard(m.from_user.id, m.chat.id, [('🏠 Home', 'home')]))
        else:
            send(m.chat.id, '📘 /studyhelp TOPIC\nTopics: docs, ai, practice, more, access, errors.\n'
                 'Use /study for interactive buttons.', _keyboard(m.from_user.id, m.chat.id, HOME_BUTTONS))

    def show_status(m):
        send(m.chat.id, status_text(m.from_user.id))

    def clear_uid(uid, chat_id):
        # V10 and V10.1 use independent in-memory pending states; do not erase stored documents.
        from v10_bot import _clear
        from v101_bot import cancel
        _clear(uid)
        cancel(uid)
        send(chat_id, '✅ Your temporary V10/V10.1 upload, AI consent or practice session was cleared. '
             'Stored documents, chat history and V8/V9 sessions are unchanged. '
             'Use /v101forget if you also want to delete stored V10.1 chat turns.')

    def clear_current(m):
        clear_uid(m.from_user.id, m.chat.id)

    def show_diag(m):
        if not admin(m.from_user.id):
            send(m.chat.id, '🔒 Administrator access required.')
            return
        send(m.chat.id, diagnostic_text())

    def show_perf(m):
        if not admin(m.from_user.id):
            send(m.chat.id, '🔒 Administrator access required.')
            return
        send(m.chat.id, metrics.report())

    @bot.message_handler(commands=['study', 'v11'])
    def cmd_home(m): run('home', show_home, m)

    @bot.message_handler(func=lambda m: getattr(m, 'text', None) == BUTTON)
    def menu_home(m): run('home', show_home, m)

    @bot.message_handler(commands=['studyhelp'])
    def cmd_help(m): run('help', show_help, m)

    @bot.message_handler(commands=['studystatus'])
    def cmd_status(m): run('status', show_status, m)

    @bot.message_handler(commands=['studycancel'])
    def cmd_cancel(m): run('cancel', clear_current, m)

    @bot.message_handler(commands=['studydiag'])
    def cmd_diag(m): run('admin', show_diag, m)

    @bot.message_handler(commands=['studyperf'])
    def cmd_perf(m): run('perf', show_perf, m)

    @bot.callback_query_handler(func=lambda call: str(getattr(call, 'data', '') or '').startswith('v11:'))
    def cb(call):
        started = time.monotonic()
        answer = 'Done'
        try:
            if not enabled():
                answer = 'Study Center is disabled.'
                return
            m = call.message
            if m.chat.type != 'private' or int(call.from_user.id) != int(m.chat.id):
                answer = 'Private chat only.'
                return
            parts = str(call.data).split(':', 2)
            if len(parts) != 3 or parts[2] not in {i[1] for i in HOME_BUTTONS} | {'home'}:
                answer = 'Invalid Study Center action.'
                return
            token, code = parts[1], parts[2]
            if not _redeem_token(token, call.from_user.id, m.chat.id):
                answer = 'Expired or already-used button. Send /study again.'
                return
            if code == 'home':
                send(m.chat.id, HOME_TEXT, _keyboard(call.from_user.id, m.chat.id, HOME_BUTTONS))
            elif code == 'status':
                send(m.chat.id, status_text(call.from_user.id), _keyboard(call.from_user.id, m.chat.id, [('🏠 Home', 'home')]))
            elif code == 'cancel':
                clear_uid(call.from_user.id, m.chat.id)
            else:
                send(m.chat.id, PAGES[code], _keyboard(call.from_user.id, m.chat.id, [('🏠 Home', 'home')]))
        except Exception:
            LOG.exception('V11 callback failed')
            answer = 'Could not complete. Try /study.'
        finally:
            # Always acknowledge callbacks (even stale/denied callbacks) to stop Telegram spinner.
            try: bot.answer_callback_query(call.id, text=answer[:190])
            except Exception: LOG.warning('V11 could not answer callback')
            metrics.record('button', (time.monotonic()-started)*1000)
