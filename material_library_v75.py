"""V7.5 private, read-only Study Materials browser with confirmed deletion.

Uses the existing `study_materials` Supabase helpers. Never sends contents to AI.
Original PDF/DOCX/TXT binary files are not stored in the current table;
previews use extracted_text only.
"""
from __future__ import annotations

import re
import secrets
import time

PAGE_SIZE = 6
MAX_BROWSE = 100
PREVIEW_CHARS = 950
CONFIRM_SECONDS = 300
SEARCH_SECONDS = 600
_PENDING = {}
_SEARCH = {}


def private_user(message):
    chat = getattr(message, 'chat', None)
    if chat is None:
        chat = getattr(getattr(message, 'message', None), 'chat', None)
    user = getattr(message, 'from_user', None)
    if chat is None or user is None or getattr(chat, 'type', 'private') != 'private':
        return None
    return int(user.id)


def clean_line(value, max_length=100):
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    return text[:max_length]


def search_metadata(rows, query):
    query = str(query or '').strip().casefold()
    if not 2 <= len(query) <= 80:
        raise ValueError('Search must be between 2 and 80 characters.')
    return [row for row in rows if query in (' '.join([
        str(row.get('title') or ''), str(row.get('file_name') or '')
    ])).casefold()]


def preview_text(material):
    extracted = str(material.get('extracted_text') or '').strip()
    name = clean_line(material.get('title') or material.get('file_name') or 'Untitled', 100)
    kind = clean_line(material.get('file_type') or 'document', 12).upper()
    content = extracted[:PREVIEW_CHARS]
    ending = '\n\n…Preview shortened. Use 📖 Read Material for the full extracted text.' if len(extracted) > PREVIEW_CHARS else ''
    if not content:
        content = '(No extracted text is stored for this material.)'
    return f'📄 {name}\nType: {kind} | Extracted characters: {len(extracted):,}\n\n{content}{ending}\n\nℹ️ This is an extracted-text preview, not the original file.'


def _pagination(total, requested):
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(int(requested), pages - 1))
    return page, pages


def _from_callback(data):
    parts = str(data or '').split(':')
    if len(parts) < 3 or parts[0] != 'v75':
        return None
    return parts


def register_material_library_handlers(bot, show_material_menu, material_state, *,
                                       types_module=None, list_fn=None, get_fn=None,
                                       delete_fn=None, clock=None):
    """Register before Study Materials' catch-all state handler.

    Optional dependencies are for isolated offline tests, not needed in the bot.
    """
    if types_module is None:
        from telebot import types as types_module
    if list_fn is None or get_fn is None or delete_fn is None:
        from study_materials import get_materials, get_material, delete_material
        list_fn = list_fn or get_materials
        get_fn = get_fn or get_material
        delete_fn = delete_fn or delete_material
    now = clock or time.monotonic

    def keyboard():
        return types_module.InlineKeyboardMarkup(row_width=2)

    def button(label, data):
        return types_module.InlineKeyboardButton(label, callback_data=data)

    def reply(chat_id, text, markup=None):
        if markup is None:
            return bot.send_message(chat_id, text)
        return bot.send_message(chat_id, text, reply_markup=markup)

    def safe_list(user_id, chat_id):
        try:
            return list_fn(user_id, limit=MAX_BROWSE)
        except Exception as error:
            print('V7.5 library list failed:', type(error).__name__)
            reply(chat_id, '⚠️ Cannot load your study materials right now.')
            return None

    def show_library(chat_id, user_id, page=0, query=None):
        if query is not None:
            try:
                search_metadata([], query)  # validate before database lookup
            except ValueError as error:
                reply(chat_id, f'⚠️ {error}')
                return
            # Keep only short-lived private search state for pagination.
            for key in list(_SEARCH):
                if _SEARCH[key][1] + SEARCH_SECONDS < now():
                    _SEARCH.pop(key, None)
            _SEARCH[user_id] = (query, now())
        rows = safe_list(user_id, chat_id)
        if rows is None:
            return
        if query is not None:
            try:
                rows = search_metadata(rows, query)
            except ValueError as error:
                reply(chat_id, f'⚠️ {error}')
                return
        page, pages = _pagination(len(rows), page)
        heading = '🔎 Material search' if query is not None else '📚 Material Library'
        if not rows:
            reply(chat_id, heading + '\n\nNo matching saved materials found.\nUse ➕ Add Material to upload one.')
            return
        markup = keyboard()
        for item in rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
            try:
                material_id = int(item['id'])
            except (TypeError, ValueError, KeyError):
                continue
            name = clean_line(item.get('title') or item.get('file_name') or 'Untitled', 43)
            markup.add(button(f'📄 #{material_id} {name}', f'v75:open:{material_id}'))
        paging = []
        kind = 'page' if query is None else 'search'
        if page > 0:
            paging.append(button('⬅️ Newer', f'v75:{kind}:{page - 1}'))
        if page + 1 < pages:
            paging.append(button('Older ➡️', f'v75:{kind}:{page + 1}'))
        if paging:
            markup.row(*paging)
        markup.add(button('🧰 Filters & Stats', 'v76:menu'))
        markup.add(button('🔙 Materials Menu', 'v75:menu:0'))
        if query is None:
            text = f'{heading}\nSaved materials: {len(rows)} (latest {MAX_BROWSE} maximum)\nPage {page + 1}/{pages}\n\nTap a document to preview it.'
        else:
            text = f'{heading}: {clean_line(query, 80)}\nMatches: {len(rows)} of your latest {MAX_BROWSE} saved materials.\n\nTap to preview.'
        reply(chat_id, text, markup)

    def show_preview(chat_id, user_id, material_id):
        try:
            material = get_fn(user_id, material_id)
        except Exception as error:
            print('V7.5 material preview failed:', type(error).__name__)
            reply(chat_id, '⚠️ Material preview unavailable. Please try again.')
            return
        if not material or int(material.get('user_id', -1)) != user_id:
            reply(chat_id, '🔒 Material not found or not accessible.')
            return
        markup = keyboard()
        markup.row(button('📖 Read Full Text', f'v78:read:{material_id}:0'),
                   button('🔎 Search Inside', f'v78:hint:{material_id}'))
        markup.row(button('📥 TXT Extract', f'v77:req:txt:{material_id}'),
                   button('📝 Markdown Extract', f'v77:req:md:{material_id}'))
        markup.row(button('🗑 Delete (confirm)', f'v75:del:{material_id}'),
                   button('📚 Library', 'v75:page:0'))
        reply(chat_id, preview_text(material), markup)

    @bot.message_handler(commands=['materiallibrary'])
    def library_command(message):
        user_id = private_user(message)
        if user_id is None:
            reply(message.chat.id, '🔒 Study Materials Library is available in private chat only.')
            return
        material_state.pop(message.chat.id, None)
        show_library(message.chat.id, user_id)

    @bot.message_handler(func=lambda m: getattr(m, 'text', None) == '📚 Material Library')
    def library_button(message):
        library_command(message)

    @bot.message_handler(commands=['materialfind'])
    def find_command(message):
        user_id = private_user(message)
        if user_id is None:
            reply(message.chat.id, '🔒 Search works in private chat only.')
            return
        material_state.pop(message.chat.id, None)
        text = (getattr(message, 'text', '') or '').strip()
        terms = text.split(maxsplit=1)
        if len(terms) < 2:
            reply(message.chat.id, '🔎 Usage: /materialfind Biology\nSearches document titles and filenames. For text inside documents, use 🔎 Search Materials.')
            return
        show_library(message.chat.id, user_id, query=terms[1])

    @bot.message_handler(commands=['materialpreview'])
    def preview_command(message):
        user_id = private_user(message)
        if user_id is None:
            reply(message.chat.id, '🔒 Document preview works in private chat only.')
            return
        material_state.pop(message.chat.id, None)
        parts = (getattr(message, 'text', '') or '').split(maxsplit=1)
        if len(parts) != 2 or not parts[1].isdigit():
            reply(message.chat.id, 'Usage: /materialpreview 12')
            return
        show_preview(message.chat.id, user_id, int(parts[1]))

    @bot.callback_query_handler(func=lambda c: str(getattr(c, 'data', '')).startswith('v75:'))
    def library_callback(call):
        user_id = private_user(call)
        chat_id = getattr(getattr(call, 'message', None), 'chat', None)
        chat_id = getattr(chat_id, 'id', None)
        if chat_id is None:
            return
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        if user_id is None:
            reply(chat_id, '🔒 Open your private chat with the bot.')
            return
        parts = _from_callback(getattr(call, 'data', ''))
        if parts is None:
            return
        action = parts[1]
        if action == 'menu':
            material_state.pop(chat_id, None)
            show_material_menu(chat_id)
            return
        if action in ('page', 'search', 'open', 'del', 'no') and len(parts) == 3:
            try:
                number = int(parts[2])
                if number < 0:
                    return
            except ValueError:
                return
            if action == 'page':
                show_library(chat_id, user_id, number)
                return
            if action == 'search':
                saved = _SEARCH.get(user_id)
                if not saved or now() - saved[1] > SEARCH_SECONDS:
                    reply(chat_id, '⌛ Search expired. Send /materialfind followed by a keyword again.')
                    return
                show_library(chat_id, user_id, number, query=saved[0])
                return
            if action == 'open':
                show_preview(chat_id, user_id, number)
                return
            if action == 'no':
                _PENDING.pop((user_id, number), None)
                reply(chat_id, '✅ Deletion cancelled.')
                return
            if action == 'del':
                try:
                    material = get_fn(user_id, number)
                except Exception as error:
                    print('V7.5 material deletion check failed:', type(error).__name__)
                    reply(chat_id, '⚠️ Material cannot be checked right now.')
                    return
                if not material or int(material.get('user_id', -1)) != user_id:
                    reply(chat_id, '🔒 Material not found or not accessible.')
                    return
                token = secrets.token_hex(8)
                # Limit short-lived pending confirmations per user to avoid unbounded growth.
                for key in list(_PENDING):
                    if key[0] == user_id or _PENDING[key][1] + CONFIRM_SECONDS < now():
                        _PENDING.pop(key, None)
                _PENDING[(user_id, number)] = (token, now())
                markup = keyboard()
                markup.row(button('✅ Yes, delete', f'v75:yes:{number}:{token}'),
                           button('❌ Cancel', f'v75:no:{number}'))
                reply(chat_id, f'⚠️ Permanently delete material #{number} ({clean_line(material.get("title"), 80)})?\nThis deletes the saved database record, including extracted text. It cannot be undone.', markup)
                return
        if action == 'yes' and len(parts) == 4:
            try:
                number = int(parts[2]); token = parts[3]
            except ValueError:
                return
            saved = _PENDING.get((user_id, number))
            if not saved or not secrets.compare_digest(saved[0], token) or now() - saved[1] > CONFIRM_SECONDS:
                reply(chat_id, '⌛ Confirmation expired or invalid. Reopen the material to delete it.')
                return
            _PENDING.pop((user_id, number), None)
            try:
                material = get_fn(user_id, number)
                if not material or int(material.get('user_id', -1)) != user_id:
                    reply(chat_id, '🔒 Material not found or not accessible.')
                    return
                deleted = delete_fn(user_id, number)
            except Exception as error:
                print('V7.5 material delete failed:', type(error).__name__)
                reply(chat_id, '⚠️ Could not delete this material. Try again later.')
                return
            reply(chat_id, '✅ Material deleted.' if deleted else '⚠️ Material was not deleted.')
            return

    from material_filters_v76 import register_material_filter_handlers
    register_material_filter_handlers(
        bot, types_module, list_fn, material_state, show_material_menu, show_library, clock=now
    )

    from material_download_v77 import register_material_download_handlers
    register_material_download_handlers(bot, types_module, get_fn, material_state, clock=now)

    from material_reader_v78 import register_material_reader_handlers
    register_material_reader_handlers(
        bot, types_module, get_fn, material_state, show_library, show_preview
    )

    return {'show_library': show_library, 'show_preview': show_preview}
