"""V11.8.3 — paginated, filterable, privacy-preserving Telegram search results.

No new database objects. The group gate delegates ONLY ``ls83:`` filter callbacks;
file buttons are the existing bot deep links and continue to preview privately.
Search sessions are transient/bounded and expire with the group result message.
"""
from __future__ import annotations

import logging
import secrets
import threading
import time
from collections import OrderedDict

LOG = logging.getLogger(__name__)
_LOCK = threading.RLock()
_SESSIONS = OrderedDict()
_MAX_SESSIONS = 250
_PER_PAGE = 5
_TTL_GROUP = 300
_TTL_PRIVATE = 900
_PREFIX = 'ls83:'
_FILTERS = (('language', '🌐 Language'), ('media_kind', '📄 Format'),
            ('category', '🗂 Category'))
_SORTS = (('relevance', '⭐ Relevance'), ('newest', '🆕 Newest'),
          ('smallest', '📦 Smallest'), ('largest', '📦 Largest'))


def _prune(now):
    for key, value in list(_SESSIONS.items()):
        if value['expires'] <= now:
            _SESSIONS.pop(key, None)
    while len(_SESSIONS) >= _MAX_SESSIONS:
        _SESSIONS.popitem(last=False)


def _create(chat_id, items, heading, *, group, requester_id):
    now = time.monotonic()
    with _LOCK:
        _prune(now)
        token = secrets.token_hex(6)
        session = dict(chat_id=int(chat_id), user_id=int(requester_id) if requester_id else None,
                       group=bool(group), expires=now + (_TTL_GROUP if group else _TTL_PRIVATE),
                       items=[dict(x) for x in items], heading=str(heading),
                       filters={}, sort='relevance', page=0, menu=None)
        _SESSIONS[token] = session
    return token, session


def _button(label, data=None, url=None):
    from telebot import types
    if url:
        return types.InlineKeyboardButton(str(label)[:64], url=url)
    return types.InlineKeyboardButton(str(label)[:64], callback_data=data)


def _keyboard():
    from telebot import types
    return types.InlineKeyboardMarkup(row_width=3)


def _value(item, key):
    if key == 'media_kind':
        return str(item.get(key) or 'pdf').strip().lower()
    if key == 'category':
        return str(item.get(key) or 'General').strip()
    return str(item.get(key) or 'Unknown').strip()


def _options(items, key):
    values = {}
    for item in items:
        val = _value(item, key)
        values[val] = values.get(val, 0) + 1
    # V11.8.5 paired language selector.
    if key == 'language':
        from library_language_picker_v1185 import language_counts
        return language_counts(values.items())
    return sorted(values.items(), key=lambda x: x[0].casefold())[:30]


def _filtered(s):
    rows = [r for r in s['items'] if all(_value(r, key).casefold() == val.casefold()
            for key, val in s['filters'].items())]
    if s['sort'] == 'newest':
        rows.sort(key=lambda r: str(r.get('approved_at') or r.get('created_at') or ''), reverse=True)
    elif s['sort'] in ('smallest', 'largest'):
        rows.sort(key=lambda r: int(r.get('file_size') or 0), reverse=s['sort'] == 'largest')
    return rows


def _format_size(item):
    from book_library_store import format_size
    return format_size(item.get('file_size'))


def _file_button(bot, item):
    from library_media_v117_bot import _link
    title = ' '.join(str(item.get('title') or 'Untitled').split())
    language = _value(item, 'language')
    kind = _value(item, 'media_kind')
    badges = {'pdf': '📄', 'image': '🖼️', 'audio': '🎧', 'video': '🎬', 'zip': '📦'}
    label = f'{badges.get(kind, "📁")} {language} · {title} · {_format_size(item)}'
    return _button(label[:63], url=_link(bot, item))


def _display(bot, token, s):
    kb = _keyboard()
    if s['menu']:
        mode = s['menu']
        title = dict(_FILTERS).get(mode, '🔃 Sort')
        if mode == 'sort':
            opts = list(_SORTS)
            choices = [(code, name) for code, name in opts]
        else:
            opts = _options(s['items'], mode)
            choices = [(str(i), f'{val} ({count})') for i, (val, count) in enumerate(opts)]
        all_label = '⭐ Relevance' if mode == 'sort' else f'🌍 All {mode.replace("_", " ")}s'
        kb.add(_button(all_label, f'{_PREFIX}{token}:x'))
        if mode == 'language':
            # Two buttons per row, just like the requested Telegram selector.
            for i in range(0, len(choices), 2):
                kb.add(*[_button(label, f'{_PREFIX}{token}:v:{code}')
                         for code, label in choices[i:i+2]])
            kb.add(_button('↩️ Back to Files', f'{_PREFIX}{token}:b'))
        else:
            for code, label in choices:
                kb.add(_button(label, f'{_PREFIX}{token}:v:{code}'))
            kb.add(_button('⬅️ Back to results', f'{_PREFIX}{token}:b'))
        text = s['heading'].split('\n', 1)[0] + ('\n🌐 SELECT LANGUAGE — choose an option\n'
              'Counts show indexed files in this search. (0) means unavailable.'
              if mode == 'language' else '\n' + title + ' — choose an option')
        return text, kb

    rows = _filtered(s)
    max_page = max(0, (len(rows) - 1) // _PER_PAGE)
    s['page'] = min(max(0, s['page']), max_page)
    selected = ' · '.join(f'{k.replace("_", " ")}: {v}' for k,v in s['filters'].items())
    extras = f'\n🔎 {len(rows)} results'
    if selected:
        extras += '\n🎯 ' + selected[:150]
    # V11.8.5: show an actual language-filtered file listing after choice.
    if s['filters'].get('language'):
        lang = s['filters']['language']
        text = (s['heading'].split('\n', 1)[0]
                + f'\n📚 {lang.upper()} FILES'
                + f'\n🔎 {len(rows)} matching files · page {s["page"]+1}/{max_page+1}'
                + '\nTap a file to receive it privately.')
    else:
        text = s['heading'] + extras
    kb.add(_button('📚 Show All', f'{_PREFIX}{token}:z'))
    kb.add(_button('🌐 Language', f'{_PREFIX}{token}:l'),
           _button('📄 Format', f'{_PREFIX}{token}:f'),
           _button('🗂 Category', f'{_PREFIX}{token}:c'))
    kb.add(_button('🔃 Sort', f'{_PREFIX}{token}:o'))
    current = rows[s['page']*_PER_PAGE:(s['page']+1)*_PER_PAGE]
    for item in current:
        kb.add(_file_button(bot, item))
    if not current:
        text += '\n📭 No indexed files for this filter. Try another language.'
    if s['filters'].get('language'):
        kb.add(_button('🌐 Change Language', f'{_PREFIX}{token}:l'))
    kb.add(_button('◀ Previous', f'{_PREFIX}{token}:p:{max(0, s["page"] - 1)}'),
           _button(f'{s["page"] + 1} / {max_page + 1}', f'{_PREFIX}{token}:n'),
           _button('Next ▶', f'{_PREFIX}{token}:p:{min(max_page, s["page"] + 1)}'))
    return text, kb


# V11.8.6 edit the searching message into results.
def send_search_results(bot, chat_id, heading, items, *, group=False, requester_id=None,
                        status_message=None):
    """Called only by unified_search; prior latest/favorites menus stay unchanged."""
    from library_media_v117_bot import _message
    token, session = _create(chat_id, items, heading, group=group, requester_id=requester_id)
    text, kb = _display(bot, token, session)
    mid=getattr(status_message, 'message_id', None)
    editor=getattr(bot, "edit_message_text", None)  # V11.8.6.1
    try:
        if mid is not None and callable(editor):
            try:
                updated=editor(text, chat_id=chat_id,
                               message_id=mid, reply_markup=kb)
                if updated is False:
                    raise RuntimeError('Telegram did not confirm result edit')
                sent=status_message
            except Exception:
                LOG.warning('Cannot replace progress; sending new results', exc_info=True)
                sent=_message(bot, chat_id, text, reply_markup=kb)
                try: bot.delete_message(chat_id, mid)
                except Exception: LOG.debug('Search progress cleanup unavailable')
        else:
            sent=_message(bot, chat_id, text, reply_markup=kb)
            # When a limited client cannot edit, try to remove its spinner.
            if mid is not None:
                try: bot.delete_message(chat_id, mid)
                except Exception: LOG.debug('Search progress cleanup unavailable')
    except Exception:
        with _LOCK:
            _SESSIONS.pop(token, None)
        raise
    # Mixed URL and callback buttons are NOT identified by V11.5's URL-only
    # keyboard recognizer. Queue this group message explicitly for cleanup.
    if group and getattr(sent, 'message_id', None):
        try:
            from group_ui_v115 import _remember
            _remember(bot, chat_id, sent.message_id, kind='book_links')
        except Exception:
            LOG.warning('Could not queue search result expiry', exc_info=True)
    return sent


def _answer(bot, callback, text, *, alert=False):
    try:
        bot.answer_callback_query(callback.id, text[:180], show_alert=alert)
    except Exception:
        pass


def handle_callback(bot, callback, *, group=False):
    """Handle filters only; do not deliver, copy, or forward any files."""
    from book_library_bot import _allowed_group, _verified
    from library_media_v117_bot import enabled
    message = getattr(callback, 'message', None)
    chat = getattr(message, 'chat', None)
    uid = getattr(getattr(callback, 'from_user', None), 'id', None)
    cid = getattr(chat, 'id', None)
    if (not enabled() or uid is None or cid is None or
        not _verified(uid) or (group and not _allowed_group(cid)) or
        (group and getattr(chat, 'type', '') not in ('group', 'supergroup')) or
        (not group and (getattr(chat, 'type', '') != 'private' or int(cid) != int(uid)))):
        return _answer(bot, callback, 'Library access is unavailable.', alert=True)
    parts = str(getattr(callback, 'data', '') or '').split(':')
    if len(parts) < 3 or len(parts) > 4 or parts[0] != 'ls83':
        return _answer(bot, callback, 'Invalid search action.', alert=True)
    token, action = parts[1], parts[2]
    with _LOCK:
        _prune(time.monotonic())
        s = _SESSIONS.get(token)
        if not s or s['chat_id'] != int(cid) or s['group'] != bool(group):
            return _answer(bot, callback, 'Search expired. Send /book TITLE again.', alert=True)
        if s['user_id'] is not None and s['user_id'] != int(uid):
            return _answer(bot, callback, 'Only the person who searched can change these filters.', alert=True)
        if action in ('l','f','c','o') and len(parts) == 3:
            s['menu'] = {'l':'language','f':'media_kind','c':'category','o':'sort'}[action]
        elif action == 'b' and len(parts) == 3:
            s['menu'] = None
        elif action == 'z' and len(parts) == 3:
            s['menu'] = None; s['filters'] = {}; s['sort'] = 'relevance'; s['page'] = 0
        elif action == 'x' and len(parts) == 3 and s['menu']:
            if s['menu'] == 'sort':
                s['sort'] = 'relevance'
            else:
                s['filters'].pop(s['menu'], None)
            s['menu'] = None; s['page'] = 0
        elif action == 'v' and len(parts) == 4 and s['menu']:
            selection = parts[3]
            if s['menu'] == 'sort':
                if selection not in dict(_SORTS):
                    return _answer(bot, callback, 'Unknown sorting choice.', alert=True)
                s['sort'] = selection
            else:
                opts = _options(s['items'], s['menu'])
                try:
                    n = int(selection)
                    if not 0 <= n < len(opts): raise ValueError()
                except ValueError:
                    return _answer(bot, callback, 'Unknown filter choice.', alert=True)
                s['filters'][s['menu']] = opts[n][0]
            s['menu'] = None; s['page'] = 0
        elif action == 'p' and len(parts) == 4 and not s['menu']:
            try: s['page'] = min(100, max(0, int(parts[3])))
            except ValueError: return _answer(bot, callback, 'Invalid page.', alert=True)
        elif action == 'n' and len(parts) == 3:
            return _answer(bot, callback, 'Choose Previous or Next.')
        else:
            return _answer(bot, callback, 'Invalid search action.', alert=True)
        text, markup = _display(bot, token, s)
    try:
        bot.edit_message_text(text, chat_id=int(cid), message_id=message.message_id,
                              reply_markup=markup)
    except Exception as exc:
        if 'not modified' not in str(exc).casefold():
            LOG.warning('Search results could not be refreshed: %s', type(exc).__name__)
            return _answer(bot, callback, 'Could not refresh. Search again.', alert=True)
    return _answer(bot, callback, 'Updated')


def register_private_handlers(bot):
    """Public group callbacks are handled earlier by the V11.6 group gate."""
    if getattr(bot, '_library_search_v1183_registered', False):
        return
    bot._library_search_v1183_registered = True

    @bot.callback_query_handler(func=lambda c: str(getattr(c, 'data', '') or '').startswith(_PREFIX))
    def private_search_callback(callback):
        if getattr(getattr(getattr(callback, 'message', None), 'chat', None), 'type', None) != 'private':
            return _answer(bot, callback, 'Open the bot privately.', alert=True)
        return handle_callback(bot, callback, group=False)
