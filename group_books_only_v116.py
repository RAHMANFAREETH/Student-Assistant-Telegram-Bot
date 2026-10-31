"""V11.6: group messages execute only public Book Library search/delivery routes.

Installs immediately AFTER V11.5 and BEFORE legacy Telegram handlers. Does not
alter private-chat handlers, Supabase book records, AI gates, or previous releases.
"""
from __future__ import annotations
import logging
import os
import re
from functools import wraps

LOG = logging.getLogger(__name__)
BOOK_COMMANDS = frozenset({'book', 'booksearch', 'books', 'booklatest', 'latestbooks',
                            'booksmart', 'bookbrowse'})
LATEST_COMMANDS = frozenset({'books', 'booklatest', 'latestbooks'})
PRIVATE_LIBRARY_COMMANDS = frozenset({
    'bookcats', 'bookauthors', 'booklangs', 'bookcat', 'bookauthor', 'booklang',
    'bookisbn', 'bookdetails', 'bookpreview', 'bookfav', 'bookfavs', 'bookstats',
    'bookmanage', 'bookedit', 'bookcover', 'bookremove', 'bookreading',
    'bookprogress', 'bookchallenge', 'bookchallengecheck', 'bookcollections',
    'bookcollection', 'bookcollectionadd', 'bookcollectionview', 'bookreview',
    'bookreviews', 'bookalert', 'bookalerts', 'bookrequest', 'bookreport',
    'booksubmit', 'bookmeta', 'bookmetafill', 'bookedition', 'bookdescription',
    'booklicense', 'bookrelated', 'bookseries', 'bookinfo',
})
FOOTER = '\n\n📩 Tap a book to receive the PDF privately.\n⏳ This result auto-deletes after 5 minutes.'


def active():
    return os.getenv('GROUP_BOOK_ONLY_V116_ENABLED', 'false').lower().strip() in ('true', '1', 'yes', 'on')


def _group(m):
    return getattr(getattr(m, 'chat', None), 'type', None) in ('group', 'supergroup')


def _command(text):
    part = str(text or '').strip().split(maxsplit=1)[0] if text and str(text).strip() else ''
    if not part.startswith('/'):
        return None, '', None
    token = part[1:]
    pieces = token.split('@', 1)
    args = str(text).strip().split(maxsplit=1)
    return pieces[0].lower(), args[1].strip() if len(args) > 1 else '', pieces[1].lower() if len(pieces) > 1 else None


def _targeted_elsewhere(bot, mention):
    if mention is None:
        return False
    from group_ui_v115 import _username
    ours = _username(bot)
    return bool(ours) and mention.lower() != ours.lower()


def _ephemeral(bot, chat_id, text, *, reply_to=None):
    from group_ui_v115 import _remember
    opts = {}
    if reply_to:
        opts['reply_to_message_id'] = int(reply_to)
    try:
        sent = bot.send_message(chat_id, text, **opts)
    except Exception:
        opts.pop('reply_to_message_id', None)
        sent = bot.send_message(chat_id, text, **opts)
    mid = getattr(sent, 'message_id', None)
    if mid:
        _remember(bot, chat_id, mid, kind='redirect')
    return sent


def _private_notice(bot, m, *, delete_input=False):
    from group_ui_v115 import _username, _remove, on
    name = _username(bot)
    link = f'https://t.me/{name}?start=study' if name else 'your bot private chat'
    _ephemeral(bot, m.chat.id,
        f'🔐 Only Book Library search works in groups. Open {link} for other tools.\n'
        '📚 Search here: /book TITLE or /booklatest.')
    if delete_input and on('GROUP_UI_DELETE_NAV_INPUT', True):
        _remove(bot, m.chat.id, m.message_id)


def _book_search(bot, m, query):
    from book_library_bot import _search, _cooldown
    if _cooldown(m.chat.id, m.from_user.id, 3):
        return
    answer = _search(bot, m.chat.id, query, group=True, requester_id=m.from_user.id)
    if answer is False:
        _ephemeral(bot, m.chat.id, '📚 No matching book found. Try another title or author.\n'
                   '⏳ This message auto-deletes after 5 minutes.')


def _book_latest(bot, m):
    from book_library_bot import _latest, _cooldown
    if _cooldown(m.chat.id, m.from_user.id, 3):
        return
    _latest(bot, m.chat.id)


def _is_book_match(text):
    """Check for an actual catalog match before answering ordinary group chat."""
    from book_library_bot import _on
    if _on('BOOK_LIBRARY_V113_ENABLED', False):
        from book_library_v113_store import smart_search
        return bool(smart_search(text, limit=1))
    from book_library_store import search_books
    return bool(search_books(text, limit=1))


def route_group_text(bot, m):
    """Return None to STOP old handlers. Groups can only use book search."""
    from book_library_bot import _enabled, _allowed_group, _verified, _on
    text = str(getattr(m, 'text', '') or '').strip()
    command, args, mention = _command(text)
    if _targeted_elsewhere(bot, mention):
        return None
    if command:
        if command in BOOK_COMMANDS:
            if not _enabled() or not _allowed_group(m.chat.id) or not _verified(m.from_user.id):
                _ephemeral(bot, m.chat.id, '📚 Book Library is unavailable in this group.')
                return None
            if command in LATEST_COMMANDS or not args:
                _book_latest(bot, m)
            else:
                _book_search(bot, m, args)
            return None
        # Personal library functions (including favorites and admin controls),
        # every AI / PDF / quiz command and unknown bot commands: private only.
        _private_notice(bot, m, delete_input=True)
        return None
    # Never treat old reply-keyboard selections, @mentions, or ordinary documents
    # as private workflows in a shared group.
    if not (active() and _enabled() and _on('BOOK_LIBRARY_AUTO_GROUP_SEARCH', False)
            and _allowed_group(m.chat.id) and _verified(m.from_user.id)):
        return None
    if not 3 <= len(text) <= 100 or text.startswith('@') or text.startswith('📚'):
        return None
    try:
        if _is_book_match(text):
            _book_search(bot, m, text)
    except Exception:
        LOG.warning('V11.6 group catalog lookup unavailable', exc_info=True)
    return None


def install_book_only_group_gate(bot):
    """Call after install_group_ui_guard and before other handlers."""
    if getattr(bot, '_group_books_only_v116_installed', False):
        return bot
    if not getattr(bot, '_group_ui_v115_installed', False):
        raise RuntimeError('Install V11.5 group guard before V11.6.')
    bot._group_books_only_v116_installed = True
    old_send = bot.send_message

    @wraps(old_send)
    def send_with_book_footer(chat_id, text, *args, **kwargs):
        if active():
            try:
                import group_ui_v115 as previous
                cid = int(chat_id)
                markup = kwargs.get('reply_markup')
                if (cid in previous._GROUPS and previous.book_url_keyboard(markup)
                        and previous.on('GROUP_UI_TIMER_ENABLED', False)
                        and FOOTER.strip() not in str(text)):
                    text = str(text)[:4096 - len(FOOTER)] + FOOTER
            except (TypeError, ValueError):
                pass
        return old_send(chat_id, text, *args, **kwargs)

    bot.send_message = send_with_book_footer

    @bot.message_handler(content_types=['text'], func=_group)
    def group_books_only_text(m):
        if not active():
            from telebot.handler_backends import ContinueHandling
            return ContinueHandling()
        return route_group_text(bot, m)

    @bot.message_handler(content_types=[
        'document', 'photo', 'video', 'audio', 'voice', 'video_note', 'animation',
        'sticker', 'contact', 'location', 'venue', 'poll'], func=_group)
    def group_books_only_media(m):
        if not active():
            from telebot.handler_backends import ContinueHandling
            return ContinueHandling()
        return None

    @bot.callback_query_handler(func=lambda c: _group(getattr(c, 'message', None)))
    def group_books_only_callback(c):
        if not active():
            from telebot.handler_backends import ContinueHandling
            return ContinueHandling()
        try:
            bot.answer_callback_query(c.id,
                '🔐 Use personal buttons in the bot private chat. Book PDF links open privately.',
                show_alert=True)
        except Exception:
            pass
        # Existing public book URL buttons are not callbacks. Don't delete
        # shared results just because someone clicked an old interactive menu.
        return None

    return bot
