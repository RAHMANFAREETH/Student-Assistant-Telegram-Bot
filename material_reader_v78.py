"""V7.8: private, read-only paginated material reader and in-document search.

Works only with the extracted_text already stored for a study material.
No AI requests, Supabase writes, or original-file access.
"""
from __future__ import annotations

import re

from material_library_v75 import clean_line, private_user

PAGE_CHARS = 2500
SEARCH_SCAN_CHARS = 500_000
MAX_SEARCH_RESULTS = 5
MAX_QUERY_CHARS = 80
MAX_MATERIAL_ID = 2**63 - 1


def parse_positive_id(value):
    """Accept only ASCII positive decimal IDs in a signed-64-bit range."""
    raw = str(value or '')
    if not raw.isascii() or not raw.isdigit() or len(raw) > 19:
        return None
    number = int(raw)
    return number if 1 <= number <= MAX_MATERIAL_ID else None


def _title(row):
    return clean_line(row.get('title') or row.get('file_name') or 'Untitled', 80)


def _text(row):
    return str(row.get('extracted_text') or '').strip()


def read_page(text, requested=0):
    """Return exact, lossless slices from the trimmed text; no omitted pages."""
    text = str(text or '').strip()
    if not text:
        raise ValueError('No extracted text is saved for this document. Try OCR or reuploading.')
    total = max(1, (len(text) + PAGE_CHARS - 1) // PAGE_CHARS)
    page = max(0, min(int(requested), total - 1))
    start = page * PAGE_CHARS
    return page, total, text[start:start + PAGE_CHARS]


def search_extracted_text(text, query):
    """Bounded Unicode-aware search. Clearly labels partial scans."""
    query = str(query or '').strip()
    if not 2 <= len(query) <= MAX_QUERY_CHARS or re.search(r'[\x00-\x1f\x7f]', query):
        raise ValueError('Search must contain 2–80 characters on one line.')
    text = str(text or '').strip()
    if not text:
        raise ValueError('No extracted text is saved for this document. Try OCR or reuploading.')
    scanned = text[:SEARCH_SCAN_CHARS]
    matches = []
    count = 0
    # Python re.IGNORECASE maintains offsets into the original Unicode text.
    for match in re.finditer(re.escape(query), scanned, flags=re.IGNORECASE):
        count += 1
        if len(matches) < MAX_SEARCH_RESULTS:
            left, right = max(0, match.start() - 85), min(len(scanned), match.end() + 85)
            snippet = re.sub(r'\s+', ' ', scanned[left:right]).strip()
            prefix = '…' if left else ''
            suffix = '…' if right < len(scanned) else ''
            matches.append(f'{len(matches) + 1}. {prefix}{snippet}{suffix}')
    return {
        'results': matches,
        'count': count,
        'partial': len(text) > SEARCH_SCAN_CHARS,
        'scanned': len(scanned),
        'total_chars': len(text),
    }


def register_material_reader_handlers(bot, types_module, get_fn, material_state,
                                      show_library, show_preview):
    """Register after V7.7, before Study Materials stateful catch-all handlers."""
    def reply(cid, message, markup=None):
        if markup is None:
            return bot.send_message(cid, message)
        return bot.send_message(cid, message, reply_markup=markup)

    def markup():
        return types_module.InlineKeyboardMarkup(row_width=2)

    def button(label, code):
        return types_module.InlineKeyboardButton(label, callback_data=code)

    def verified(uid, cid, material_id):
        try:
            row = get_fn(uid, material_id)
        except Exception as exc:
            print('V7.8 material read lookup failed:', type(exc).__name__)
            reply(cid, '⚠️ Could not load this material. Please try again.')
            return None
        if (not isinstance(row, dict)
                or str(row.get('user_id', '')) != str(uid)
                or parse_positive_id(row.get('id')) != material_id):
            reply(cid, '🔒 Material not found or not accessible.')
            return None
        return row

    def read(uid, cid, material_id, page=0):
        material = verified(uid, cid, material_id)
        if material is None:
            return
        try:
            number, total, content = read_page(_text(material), page)
        except ValueError as exc:
            reply(cid, f'⚠️ {exc}')
            return
        keys = markup()
        nav = []
        if number:
            nav.append(button('⬅️ Previous', f'v78:read:{material_id}:{number - 1}'))
        if number + 1 < total:
            nav.append(button('Next ➡️', f'v78:read:{material_id}:{number + 1}'))
        if nav:
            keys.row(*nav)
        keys.row(button('🔎 Search Inside', f'v78:hint:{material_id}'),
                 button('📖 Preview', f'v78:preview:{material_id}'))
        keys.add(button('📚 Material Library', 'v78:library'))
        reply(cid,
              f'📖 {_title(material)}\nPage {number + 1}/{total} • Extracted text only\n\n'
              f'{content}\n\n'
              'ℹ️ Pages are consecutive sections of the saved text, not PDF page numbers.',
              keys)

    def search(uid, cid, material_id, query):
        material = verified(uid, cid, material_id)
        if material is None:
            return
        try:
            result = search_extracted_text(_text(material), query)
        except ValueError as exc:
            reply(cid, f'⚠️ {exc}')
            return
        scope = (f'Only the first {result["scanned"]:,} of {result["total_chars"]:,} '
                 'characters were searched.' if result['partial']
                 else 'Entire saved extracted text searched.')
        samples = ('\n\n'.join(result['results']) if result['results']
                   else 'No matches in the scanned text.')
        keys = markup()
        keys.row(button('📖 Read Material', f'v78:read:{material_id}:0'),
                 button('📚 Library', 'v78:library'))
        reply(cid, f'🔎 Inside: {_title(material)}\n'
                   f'Matches in scanned text: {result["count"]}\n{scope}\n\n{samples}', keys)

    def authenticated(message):
        uid = private_user(message)
        cid = getattr(getattr(message, 'chat', None), 'id', None)
        if uid is None or cid != uid:
            if cid is not None:
                reply(cid, '🔒 Open your private chat with the bot to read study materials.')
            return None
        return uid

    @bot.message_handler(commands=['materialread'])
    def read_command(message):
        uid = authenticated(message)
        if uid is None:
            return
        material_state.pop(message.chat.id, None)
        args = (getattr(message, 'text', '') or '').split()
        material_id = parse_positive_id(args[1]) if len(args) == 2 else None
        if material_id is None:
            reply(uid, '📖 Usage: /materialread 12\nRead saved extracted text page by page.')
            return
        read(uid, uid, material_id)

    @bot.message_handler(commands=['materialinside'])
    def search_command(message):
        uid = authenticated(message)
        if uid is None:
            return
        material_state.pop(message.chat.id, None)
        command = (getattr(message, 'text', '') or '').strip()
        args = command.split(maxsplit=2)
        mid = parse_positive_id(args[1]) if len(args) >= 2 else None
        if mid is None or len(args) != 3:
            reply(uid, '🔎 Usage: /materialinside 12 photosynthesis\nSearch inside one saved document.')
            return
        search(uid, uid, mid, args[2])

    @bot.callback_query_handler(func=lambda c: str(getattr(c, 'data', '')).startswith('v78:'))
    def read_callback(call):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        uid = private_user(call)
        cid = getattr(getattr(getattr(call, 'message', None), 'chat', None), 'id', None)
        if cid is None:
            return
        if uid is None or cid != uid:
            reply(cid, '🔒 Open your private chat with the bot.')
            return
        parts = str(getattr(call, 'data', '')).split(':')
        action = parts[1] if len(parts) > 1 else ''
        if action == 'library' and len(parts) == 2:
            show_library(cid, uid)
            return
        if action not in ('read', 'preview', 'hint'):
            return
        if (action == 'read' and len(parts) != 4) or (action != 'read' and len(parts) != 3):
            return
        mid = parse_positive_id(parts[2])
        if mid is None:
            return
        if action == 'read':
            page_str = parts[3]
            if not page_str.isascii() or not page_str.isdigit() or len(page_str) > 8:
                return
            read(uid, cid, mid, int(page_str))
        elif action == 'preview':
            # The existing V7.5 preview performs a fresh owner-scoped lookup.
            show_preview(cid, uid, mid)
        elif action == 'hint':
            # Avoid revealing even document metadata without checking ownership.
            if verified(uid, cid, mid) is not None:
                reply(cid, f'🔎 To search inside this document, send:\n/materialinside {mid} photosynthesis\n'
                           'Replace “photosynthesis” with your own word or phrase.')

    return {'read': read, 'search': search}
