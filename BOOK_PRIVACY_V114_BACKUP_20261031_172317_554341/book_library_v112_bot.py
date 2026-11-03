"""V11.2 advanced public Book Library: browse/filter/preview/favorites/stats/admin edits.

Add-on to V11.1: registered by register_book_library_handlers() only while
BOOK_LIBRARY_V112_ENABLED=true. Existing storage and deep-link delivery retained.
"""
from __future__ import annotations
import os
import re
import secrets
import threading
import time
import uuid
import logging

from book_library_v112_store import (
    browse_books, facets, get_details, update_metadata, set_cover,
    toggle_favorite, list_favorites, top_downloaded, recently_uploaded, parse_extended_caption,
    normalize_isbn, record_delivery, book_uuid)

log = logging.getLogger(__name__)
TOKEN_TTL = 600
PAGE_SIZE = 5
_sessions = {}
_covers = {}
_lock = threading.RLock()


def enabled():
    import book_library_bot as lib
    return lib._enabled() and lib._on('BOOK_LIBRARY_V112_ENABLED', False)


def _allowed(m):
    import book_library_bot as lib
    if not enabled():
        return False
    if lib._is_group(m) and not lib._allowed_group(m.chat.id):
        return False
    if not (lib._is_private(m) or lib._is_group(m)):
        return False
    return lib._verified(m.from_user.id)


def _types():
    from telebot import types
    return types


def _button(label, **kwargs):
    return _types().InlineKeyboardButton(label, **kwargs)


def _keyboard():
    return _types().InlineKeyboardMarkup(row_width=1)


def _short(text, size=65):
    value = str(text or '').replace('\n',' ').replace('\r',' ')
    return value if len(value) <= size else value[:size-1] + '…'


def add_menu_buttons(kb):
    """Called by V11.1 library menu, after existing Search/Latest buttons."""
    if not enabled():
        return
    kb.add(_button('🗂 Categories', callback_data='lib2:fac:category'),
           _button('✍️ Authors', callback_data='lib2:fac:author'))
    kb.add(_button('🌐 Languages', callback_data='lib2:fac:language'),
           _button('❤️ My Favorites', callback_data='lib2:favs'))
    kb.add(_button('📚 Browse All', callback_data='lib2:browse'))


def _save_session(chat_id, params, owner=None):
    with _lock:
        now = time.monotonic()
        for k, v in list(_sessions.items()):
            if v['expires'] < now:
                del _sessions[k]
        if len(_sessions) >= 500:
            oldest = min(_sessions, key=lambda x: _sessions[x]['expires'])
            del _sessions[oldest]
        token = secrets.token_hex(6)
        _sessions[token] = dict(chat_id=int(chat_id), owner=owner,
                                expires=now+TOKEN_TTL, params=dict(params))
        return token


def _session(token, chat_id, user_id):
    with _lock:
        item = _sessions.get(token)
        if (not item or item['expires'] < time.monotonic() or
            item['chat_id'] != int(chat_id) or
            (item['owner'] is not None and item['owner'] != int(user_id))):
            return None
        return dict(item)


def _book_markup(bot, books, *, chat_id, token=None, page=0, has_more=False, private=False):
    import book_library_bot as lib
    username = lib._bot_username(bot)
    markup = _keyboard()
    for item in books:
        identifier = uuid.UUID(str(item['id'])).hex
        title = _short(item.get('title'), 35)
        markup.add(_button(f'📥 {title}', url=f'https://t.me/{username}?start=book_{identifier}'))
        markup.add(_button('🖼 Cover / Details',
                           url=f'https://t.me/{username}?start=preview_{identifier}'))
    if token:
        nav = []
        if page:
            nav.append(_button('◀️ Previous', callback_data=f'lib2:pg:{token}:{page-1}'))
        if has_more and page < 99:
            nav.append(_button('Next ▶️', callback_data=f'lib2:pg:{token}:{page+1}'))
        if nav:
            markup.row(*nav)
    return markup


def _list_page(bot, chat_id, params, *, page=0, token=None, owner=None, group=False, edit=None):
    """One page of 5; an extra DB row tells us whether Next is available."""
    kind = params.get('kind', 'browse')
    if kind == 'favorites':
        if owner is None or int(chat_id) != owner:
            raise ValueError('Favorites are private.')
        books, more = list_favorites(owner, page=page, page_size=PAGE_SIZE)
        heading = '❤️ My Favorite Books'
    else:
        books, more = browse_books(query=params.get('query'), category=params.get('category'),
                                   author=params.get('author'), language=params.get('language'),
                                   isbn=params.get('isbn'), page=page, page_size=PAGE_SIZE)
        heading = params.get('title', '📚 Browse Books')
    if not books:
        if page == 0 and group and kind == 'browse' and params.get('query'):
            return False   # Avoid spamming groups for unrelated text.
        bot.send_message(chat_id, '📚 No matching books found.' if page == 0 else '📚 No more books on this page.')
        return True
    if token is None:
        token = _save_session(chat_id, params, owner=owner)
    text = (f'{heading}\nPage {page+1} · showing {len(books)} books\n'
            'Tap 📥 to receive a book privately, or 🖼 to preview its cover.')
    markup = _book_markup(bot, books, chat_id=chat_id, token=token, page=page,
                          has_more=more, private=not group)
    if edit is not None:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=edit,
                                  reply_markup=markup)
            return True
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)
    return True


def show_search(bot, chat_id, query, *, group=False):
    q = str(query or '').strip()
    if not 2 <= len(q) <= 100:
        if not group:
            bot.send_message(chat_id, '🔎 Search needs 2–100 characters. Example: /book Ibn Kathir')
        return False
    try:
        return _list_page(bot, chat_id,
                          {'kind':'browse','query':q,'title':f'🔎 Results for: {_short(q,75)}'},
                          group=group)
    except Exception:
        if not group:
            bot.send_message(chat_id, '⚠️ Book search unavailable. Please try again.')
        log.exception('V11.2 search failed')
        return False


def _detail_markup(bot, book_id, user_id):
    import book_library_bot as lib
    hexid = uuid.UUID(book_id).hex
    markup = _keyboard()
    markup.add(_button('📥 Get Book', url=f'https://t.me/{lib._bot_username(bot)}?start=book_{hexid}'))
    markup.add(_button('❤️ Add / Remove Favorite', callback_data='lib2:f:' + hexid))
    return markup


def show_preview(bot, chat_id, book_id, *, user_id=None):
    book = get_details(book_id)
    if not book:
        bot.send_message(chat_id, '📚 Book not found or removed.')
        return False
    title = _short(book.get('title'), 125)
    text = (f'📖 {title}\n✍️ {_short(book.get("author"), 110)}\n'
            f'🌐 {_short(book.get("language"), 40)} · 🗂 {_short(book.get("category"), 50)}\n'
            f'ISBN: {book.get("isbn") or "Not listed"}\n'
            f'📥 Deliveries: {int(book.get("download_count") or 0)}')
    markup = _detail_markup(bot, str(book['id']), user_id)
    if book.get('cover_file_id'):
        try:
            bot.send_photo(chat_id, book['cover_file_id'], caption=text[:1024], reply_markup=markup)
            return True
        except Exception:
            log.warning('V11.2 cover unavailable for book %s', book_id)
    bot.send_message(chat_id, text, reply_markup=markup)
    return True


def handle_preview_start(bot, message):
    """Handle /start preview_UUID; leave book_UUID delivery to V11.1."""
    import book_library_bot as lib
    raw = str(getattr(message, 'text', '') or '').strip()
    words = raw.split(maxsplit=1)
    if len(words) != 2 or not words[1].startswith('preview_'):
        return False
    if not enabled():
        bot.send_message(message.chat.id, '📚 Cover previews are currently unavailable.')
        return True
    if not lib._is_private(message) or not lib._verified(message.from_user.id):
        bot.send_message(message.chat.id, 'Open the library in a private bot chat.')
        return True
    token = words[1][8:]
    if not re.fullmatch(r'[0-9a-fA-F]{32}', token):
        bot.send_message(message.chat.id, '⚠️ Invalid preview link.')
        return True
    try:
        show_preview(bot, message.chat.id, str(uuid.UUID(hex=token)), user_id=message.from_user.id)
    except Exception:
        log.exception('V11.2 preview failed')
        bot.send_message(message.chat.id, '⚠️ Preview is currently unavailable.')
    return True


def _require_admin(bot, m):
    import book_library_bot as lib
    if not lib._is_private(m) or not lib._admin(m.from_user.id):
        bot.send_message(m.chat.id, '🔒 Library administrators only. Use a private chat.')
        return False
    return True


def register_v112_handlers(bot):
    """Called once from V11.1 handler registration, before older wildcard handlers."""
    import book_library_bot as lib

    @bot.message_handler(commands=['bookbrowse','bookcat','bookauthor','booklang','bookisbn'])
    def library_v112_browse(m):
        if not _allowed(m):
            bot.send_message(m.chat.id, '📚 Library not enabled in this chat.')
            return
        command = str(getattr(m, 'text', '') or '').split()[0].split('@')[0].lower()
        val = lib._command_args(m)
        names = {'/bookcat':('category','🗂 Category'), '/bookauthor':('author','✍️ Author'),
                 '/booklang':('language','🌐 Language'), '/bookisbn':('isbn','🔢 ISBN')}
        if command in names and not val:
            bot.send_message(m.chat.id, 'Usage: ' + command + ' VALUE')
            return
        params = {'kind':'browse','title':'📚 Browse Books'}
        if command in names:
            key, head = names[command]
            params[key] = val
            params['title'] = f'{head}: {_short(val,75)}'
        if command == '/bookbrowse' and val:
            params['query'] = val
            params['title'] = f'🔎 {_short(val,75)}'
        try:
            _list_page(bot, m.chat.id, params, group=lib._is_group(m))
        except ValueError as e:
            bot.send_message(m.chat.id, '⚠️ ' + str(e))
        except Exception:
            log.exception('V11.2 browse failed')
            bot.send_message(m.chat.id, '⚠️ Catalog currently unavailable.')

    @bot.message_handler(commands=['bookcats','bookauthors','booklangs'])
    def library_v112_facets(m):
        if not _allowed(m):
            bot.send_message(m.chat.id, '📚 Library not enabled in this chat.')
            return
        cmd = str(m.text or '').split()[0].split('@')[0].lower()
        kind = {'/bookcats':'category','/bookauthors':'author','/booklangs':'language'}[cmd]
        _send_facets(bot, m.chat.id, kind)

    @bot.message_handler(commands=['bookdetails','bookpreview'])
    def library_v112_details(m):
        if not _allowed(m):
            bot.send_message(m.chat.id, '📚 Library not enabled in this chat.')
            return
        if not lib._is_private(m):
            bot.send_message(m.chat.id, '🔐 Open the bot privately to preview book covers.')
            return
        try:
            show_preview(bot, m.chat.id, book_uuid(lib._command_args(m)), user_id=m.from_user.id)
        except ValueError:
            bot.send_message(m.chat.id, 'Usage: /bookpreview BOOK_UUID')
        except Exception:
            log.exception('V11.2 preview command failed')
            bot.send_message(m.chat.id, '⚠️ Preview unavailable.')

    @bot.message_handler(commands=['bookfav','bookfavs'])
    def library_v112_favs(m):
        if not _allowed(m) or not lib._is_private(m):
            bot.send_message(m.chat.id, '🔐 Favorites are available only in your private bot chat.')
            return
        command = str(m.text or '').split()[0].split('@')[0].lower()
        if command == '/bookfavs':
            try:
                _list_page(bot, m.chat.id, {'kind':'favorites'}, owner=m.from_user.id)
            except Exception:
                log.exception('V11.2 favorites list failed')
                bot.send_message(m.chat.id, '⚠️ Favorites unavailable.')
            return
        try:
            status = toggle_favorite(m.from_user.id, book_uuid(lib._command_args(m)))
            bot.send_message(m.chat.id, '❤️ Saved to favorites.' if status else '✅ Removed from favorites.')
        except ValueError:
            bot.send_message(m.chat.id, 'Usage: /bookfav BOOK_UUID')
        except Exception:
            log.exception('V11.2 favorite update failed')
            bot.send_message(m.chat.id, '⚠️ Could not update favorites.')

    @bot.message_handler(commands=['bookstats'])
    def library_v112_stats(m):
        if not _require_admin(bot, m):
            return
        try:
            books = top_downloaded(limit=10)
            lines = ['📊 Book Library — Top Deliveries']
            for i, b in enumerate(books,1):
                lines.append(f'{i}. {_short(b.get("title"),55)} — {int(b.get("download_count") or 0)}')
            if len(lines) == 1:
                lines.append('No books in the catalog.')
            bot.send_message(m.chat.id, '\n'.join(lines)[:3500])
        except Exception:
            log.exception('V11.2 stats failed')
            bot.send_message(m.chat.id, '⚠️ Statistics unavailable.')

    @bot.message_handler(commands=['bookmanage'])
    def library_v112_manage(m):
        if not _require_admin(bot, m):
            return
        try:
            items = recently_uploaded(limit=10)
            lines = ['🛠 Recent Books — Admin IDs']
            for item in items:
                lines.append(f'{_short(item.get("title"), 55)}\nID: {item["id"]}')
            if len(lines) == 1:
                lines.append('No active books found.')
            lines.append('Use /bookedit UUID | Title | Author | Language | Category | ISBN-or--')
            bot.send_message(m.chat.id, '\n\n'.join(lines)[:3800])
        except Exception:
            log.exception('V11.2 admin list failed')
            bot.send_message(m.chat.id, '⚠️ Could not load book IDs.')

    @bot.message_handler(commands=['bookedit'])
    def library_v112_edit(m):
        if not _require_admin(bot, m):
            return
        raw = lib._command_args(m)
        bits = [x.strip() for x in raw.split('|')]
        if len(bits) != 6:
            bot.send_message(m.chat.id, 'Usage: /bookedit UUID | Title | Author | Language | Category | ISBN-or--')
            return
        try:
            key = book_uuid(bits[0])
            status = update_metadata(key, title=bits[1], author=bits[2],
                                     language=bits[3], category=bits[4], isbn=bits[5])
            bot.send_message(m.chat.id, '✅ Book metadata updated.' if status else '📚 No active book with that ID.')
        except ValueError as e:
            bot.send_message(m.chat.id, '⚠️ ' + str(e))
        except Exception:
            log.exception('V11.2 admin metadata update failed')
            bot.send_message(m.chat.id, '⚠️ Update not confirmed. Check logs.')

    @bot.message_handler(commands=['bookcover'])
    def library_v112_cover_cmd(m):
        if not _require_admin(bot, m):
            return
        args = lib._command_args(m).split()
        if not args:
            bot.send_message(m.chat.id, 'Usage: /bookcover BOOK_UUID [clear], then send a photo.')
            return
        try:
            key = book_uuid(args[0])
            if len(args) == 2 and args[1].lower() == 'clear':
                success = set_cover(key, None)
                bot.send_message(m.chat.id, '✅ Cover cleared.' if success else 'Book not found.')
                return
            if len(args) != 1 or not get_details(key):
                bot.send_message(m.chat.id, '📚 Book not found, or invalid command.')
                return
            with _lock:
                _covers[int(m.from_user.id)] = (key, time.monotonic()+180)
            bot.send_message(m.chat.id, '🖼 Send the cover as a Telegram photo within 3 minutes. /bookcover UUID clear removes it.')
        except ValueError:
            bot.send_message(m.chat.id, 'Usage: /bookcover BOOK_UUID [clear]')
        except Exception:
            log.exception('V11.2 cover command failed')
            bot.send_message(m.chat.id, '⚠️ Cover operation unavailable.')

    @bot.message_handler(content_types=['photo'],
                         func=lambda m: enabled() and lib._is_private(m) and
                         lib._admin(m.from_user.id) and _cover_active(m.from_user.id))
    def library_v112_cover_photo(m):
        with _lock:
            info = _covers.pop(int(m.from_user.id), None)
        if not info or info[1] < time.monotonic():
            bot.send_message(m.chat.id, '⏱ Cover session expired. Try /bookcover BOOK_UUID again.')
            return
        photos = list(getattr(m, 'photo', []) or [])
        if not photos:
            bot.send_message(m.chat.id, '⚠️ Please send a Telegram photo.')
            return
        try:
            success = set_cover(info[0], photos[-1].file_id)
            bot.send_message(m.chat.id, '✅ Book cover saved.' if success else 'Book not found.')
        except Exception:
            log.exception('V11.2 cover photo failed')
            bot.send_message(m.chat.id, '⚠️ Could not save cover.')

    @bot.callback_query_handler(func=lambda c: str(getattr(c, 'data', '') or '').startswith('lib2:'))
    def library_v112_callback(c):
        def reply(text='', alert=False):
            bot.answer_callback_query(c.id, text, show_alert=alert)
        m = getattr(c, 'message', None)
        if m is None or not hasattr(m, 'chat'):
            reply('Open the bot and try again.', True)
            return
        if not enabled() or not _allowed(_callback_message(m, c.from_user)):
            reply('Book Library unavailable in this chat.', True)
            return
        parts = str(c.data).split(':')
        action = parts[1] if len(parts)>1 else ''
        try:
            if action == 'fac' and len(parts)==3:
                if parts[2] not in ('category','author','language'):
                    reply('Invalid filter.',True); return
                reply(); _send_facets(bot,m.chat.id,parts[2]); return
            if action == 'filter' and len(parts)==3:
                session = _session(parts[2],m.chat.id,c.from_user.id)
                if not session:
                    reply('Expired. Open the library again.',True); return
                reply(); _list_page(bot,m.chat.id,session['params'],
                                    owner=session['owner'],group=lib._is_group(m)); return
            if action == 'pg' and len(parts)==4:
                session = _session(parts[2],m.chat.id,c.from_user.id)
                if not session:
                    reply('Page expired. Search again.',True); return
                page = int(parts[3]);
                if not 0<=page<=99: raise ValueError('Invalid page.')
                reply(); _list_page(bot,m.chat.id,session['params'],page=page,
                                    token=parts[2],owner=session['owner'],
                                    group=lib._is_group(m),edit=m.message_id); return
            if action == 'browse' and len(parts)==2:
                reply(); _list_page(bot,m.chat.id,{'kind':'browse'},group=lib._is_group(m)); return
            if action == 'favs' and len(parts)==2:
                if not lib._is_private(m) or m.chat.id != c.from_user.id:
                    reply('Favorites are private.',True); return
                reply(); _list_page(bot,m.chat.id,{'kind':'favorites'},owner=c.from_user.id); return
            if action == 'f' and len(parts)==3:
                if not lib._is_private(m) or m.chat.id != c.from_user.id:
                    reply('Favorites are private.',True); return
                status = toggle_favorite(c.from_user.id,str(uuid.UUID(hex=parts[2])))
                reply('❤️ Saved' if status else 'Removed from favorites.'); return
            reply('This button is no longer valid.',True)
        except Exception:
            log.exception('V11.2 library callback failed')
            reply('Library unavailable. Please retry.',True)


def _callback_message(m, user):
    from types import SimpleNamespace
    return SimpleNamespace(chat=m.chat, from_user=user)


def _cover_active(user_id):
    with _lock:
        pending = _covers.get(int(user_id))
    return bool(pending and pending[1] > time.monotonic())


def _send_facets(bot, chat_id, kind):
    try:
        values = facets(kind)
        if not values:
            bot.send_message(chat_id,'📚 No entries yet.'); return
        kb = _keyboard()
        for item in values[:30]:
            name = str(item.get('value') or '').strip()
            if not name:
                continue
            context = {'kind':'browse','title':f'📚 {kind.title()}: {_short(name,70)}',kind:name}
            token = _save_session(chat_id,context)
            kb.add(_button(f'{_short(name,35)} ({int(item.get("book_count") or 0)})',
                           callback_data=f'lib2:filter:{token}'))
        bot.send_message(chat_id,f'📚 Choose a {kind}:',reply_markup=kb)
    except Exception:
        log.exception('V11.2 list facets failed')
        bot.send_message(chat_id, '⚠️ Filters currently unavailable.')
