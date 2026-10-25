"""V7.6 Study Materials filtering and summary views.

Registers next to V7.5's existing private library, without changing upload,
Supabase schema, content previews, or the original AI providers.
All totals and filters refer ONLY to the latest 100 documents returned by the
existing user-scoped get_materials() query, never all historical documents.
"""
from __future__ import annotations

from collections import Counter

from material_library_v75 import private_user, clean_line

PAGE_SIZE = 6
MAX_BROWSE = 100
ALLOWED_TYPES = frozenset({'pdf', 'docx', 'txt', 'other'})


def _type_of(row):
    raw = str(row.get('file_type') or '').lower().strip().lstrip('.')
    return raw if raw in {'pdf', 'docx', 'txt'} else 'other'


def _subject_of(row):
    value = row.get('subject_id')
    if value in (None, '', 0, '0'):
        return None
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def filter_materials(rows, *, kind, selector):
    """Filter already user-scoped rows. Does not request or expose document text."""
    if kind == 'type':
        if selector not in ALLOWED_TYPES:
            raise ValueError('Unsupported document type.')
        return [row for row in rows if _type_of(row) == selector]
    if kind == 'subject':
        if selector != 'none':
            try:
                selector = int(selector)
            except (TypeError, ValueError):
                raise ValueError('Invalid subject ID.') from None
            if selector < 1:
                raise ValueError('Invalid subject ID.')
        expected = None if selector == 'none' else selector
        return [row for row in rows if _subject_of(row) == expected]
    raise ValueError('Unknown filter.')


def library_stats(rows):
    counts = Counter(_type_of(row) for row in rows)
    subjects = Counter(_subject_of(row) for row in rows)
    chars = 0
    for row in rows:
        try:
            chars += max(0, int(row.get('extracted_chars') or 0))
        except (ValueError, TypeError):
            pass
    return {'total': len(rows), 'types': dict(counts), 'subjects': dict(subjects),
            'extracted_chars': chars}


def register_material_filter_handlers(bot, types_module, list_fn, material_state,
                                     show_material_menu, show_library, *, clock=None):
    """Register in V7.5 register_material_library_handlers, before stateful handlers."""

    def markup():
        return types_module.InlineKeyboardMarkup(row_width=2)

    def button(text, data):
        return types_module.InlineKeyboardButton(text, callback_data=data)

    def send(chat_id, text, buttons=None):
        if buttons is None:
            return bot.send_message(chat_id, text)
        return bot.send_message(chat_id, text, reply_markup=buttons)

    def fetch(uid, cid):
        try:
            fetched = list_fn(uid, limit=MAX_BROWSE)
            # Additional ownership defense, even if a supplied query accidentally
            # returns foreign rows. Never silently treat DB errors as empty results.
            return [r for r in (fetched or []) if isinstance(r, dict)
                    and str(r.get('user_id', '')) == str(uid)][:MAX_BROWSE]
        except Exception as exc:
            print('V7.6 material filter query failed:', type(exc).__name__)
            send(cid, '⚠️ Cannot load your study materials at the moment.')
            return None

    def open_menu(uid, cid):
        buttons = markup()
        buttons.row(button('📄 PDF', 'v76:t:pdf:0'), button('📝 DOCX', 'v76:t:docx:0'))
        buttons.row(button('📃 TXT', 'v76:t:txt:0'), button('📎 Other', 'v76:t:other:0'))
        buttons.row(button('🏷 Browse Subjects', 'v76:subjects'),
                    button('📊 Library Stats', 'v76:stats'))
        buttons.row(button('📚 All Materials', 'v76:all'),
                    button('🔙 Materials Menu', 'v76:home'))
        send(cid, '🧰 Study Materials Filters — V7.6\n'
                  'Browse your latest 100 saved materials by file type or subject.\n'
                  'These filters do not search document contents.', buttons)

    def show_subjects(uid, cid):
        rows = fetch(uid, cid)
        if rows is None:
            return
        counts = Counter(_subject_of(r) for r in rows)
        buttons = markup()
        for sub, count in sorted(counts.items(), key=lambda kv: (-kv[1], -1 if kv[0] is None else kv[0]))[:25]:
            code = 'none' if sub is None else str(sub)
            label = '⏩ No Subject' if sub is None else f'🏷 Subject #{sub}'
            buttons.add(button(f'{label} ({count})', f'v76:s:{code}:0'))
        buttons.add(button('⬅️ Filters', 'v76:menu'))
        send(cid, '🏷 Subjects in your most recent 100 materials\n'
                  'Subjects are shown by existing ID, without changing their names.\n'
                  'No documents? Upload one with ➕ Add Material.', buttons)

    def show_filtered(uid, cid, kind, selector, page=0):
        rows = fetch(uid, cid)
        if rows is None:
            return
        try:
            matches = filter_materials(rows, kind=kind, selector=selector)
        except ValueError as exc:
            send(cid, f'⚠️ {exc}')
            return
        pages = max(1, (len(matches) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, pages - 1))
        if kind == 'type':
            label = str(selector).upper()
            token = f'v76:t:{selector}'
        else:
            label = 'No Subject' if selector == 'none' else f'Subject #{selector}'
            token = f'v76:s:{selector}'
        buttons = markup()
        for row in matches[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
            try:
                material_id = int(row['id'])
                if material_id < 1:
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            # V7.5 preview re-checks ownership with a fresh DB query.
            title = clean_line(row.get('title') or row.get('file_name') or 'Untitled', 38)
            buttons.add(button(f'📄 #{material_id} {title}', f'v75:open:{material_id}'))
        nav = []
        if page > 0:
            nav.append(button('⬅️ Newer', f'{token}:{page - 1}'))
        if page + 1 < pages:
            nav.append(button('Older ➡️', f'{token}:{page + 1}'))
        if nav:
            buttons.row(*nav)
        buttons.row(button('🧰 Filters', 'v76:menu'),
                    button('📚 All Materials', 'v76:all'))
        message = (f'📚 Materials — {label}\n'
                   f'{len(matches)} matching saved document(s) in your latest {MAX_BROWSE}.\n'
                   f'Page {page + 1}/{pages}\n\n'
                   + ('Tap a document to preview it.' if matches else 'No saved documents match this filter.'))
        send(cid, message, buttons)

    def show_stats(uid, cid):
        rows = fetch(uid, cid)
        if rows is None:
            return
        info = library_stats(rows)
        counts = info['types']
        buttons = markup()
        buttons.row(button('🏷 Subjects', 'v76:subjects'), button('🧰 Filters', 'v76:menu'))
        send(cid, '\n'.join([
            '📊 Study Materials Snapshot — V7.6',
            f'Latest saved materials checked: {info["total"]} (maximum {MAX_BROWSE})',
            f'📄 PDF: {counts.get("pdf", 0)}',
            f'📝 DOCX: {counts.get("docx", 0)}',
            f'📃 TXT: {counts.get("txt", 0)}',
            f'📎 Other: {counts.get("other", 0)}',
            f'🏷 Distinct assigned subjects: {sum(k is not None for k in info["subjects"])}',
            f'⏩ No Subject: {info["subjects"].get(None, 0)}',
            f'🔡 Extracted characters (stored totals): {info["extracted_chars"]:,}',
            '',
            'ℹ️ This is not an all-time total; it covers only the latest 100 rows.',
            'No AI calls are made.',
        ]), buttons)

    def start(message, action, argument=None):
        uid = private_user(message)
        if uid is None:
            send(message.chat.id, '🔒 Study Materials filters work only in your private bot chat.')
            return
        material_state.pop(message.chat.id, None)
        cid = message.chat.id
        if action == 'menu':
            open_menu(uid, cid)
        elif action == 'stats':
            show_stats(uid, cid)
        elif action == 'type':
            name = (argument or '').strip().lower().lstrip('.')
            if name == 'all':
                show_library(cid, uid)
            elif name not in ALLOWED_TYPES:
                send(cid, 'Usage: /materialtype pdf\nAvailable: pdf, docx, txt, other, all.')
            else:
                show_filtered(uid, cid, 'type', name)
        elif action == 'subject':
            name = (argument or '').strip().lower()
            if not name:
                show_subjects(uid, cid)
            elif name == 'none' or (name.isdigit() and int(name) > 0):
                show_filtered(uid, cid, 'subject', name)
            else:
                send(cid, 'Usage: /materialsubject 12\nOr /materialsubject none')

    @bot.message_handler(commands=['materialfilters'])
    def filters_command(message):
        start(message, 'menu')

    @bot.message_handler(func=lambda m: getattr(m, 'text', None) == '🧰 Filter Materials')
    def filters_button(message):
        start(message, 'menu')

    @bot.message_handler(commands=['materialstats'])
    def stats_command(message):
        start(message, 'stats')

    @bot.message_handler(commands=['materialtype'])
    def type_command(message):
        parts = (getattr(message, 'text', '') or '').split(maxsplit=1)
        start(message, 'type', parts[1] if len(parts) > 1 else None)

    @bot.message_handler(commands=['materialsubject'])
    def subject_command(message):
        parts = (getattr(message, 'text', '') or '').split(maxsplit=1)
        start(message, 'subject', parts[1] if len(parts) > 1 else None)

    @bot.callback_query_handler(func=lambda c: str(getattr(c, 'data', '')).startswith('v76:'))
    def filter_callback(call):
        uid = private_user(call)
        msg = getattr(call, 'message', None)
        cid = getattr(getattr(msg, 'chat', None), 'id', None)
        if cid is None:
            return
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        if uid is None:
            send(cid, '🔒 Open a private chat with the bot for your study materials.')
            return
        material_state.pop(cid, None)
        parts = str(call.data).split(':')
        if len(parts) == 2:
            if parts[1] == 'menu':
                open_menu(uid, cid)
            elif parts[1] == 'subjects':
                show_subjects(uid, cid)
            elif parts[1] == 'stats':
                show_stats(uid, cid)
            elif parts[1] == 'all':
                show_library(cid, uid)
            elif parts[1] == 'home':
                show_material_menu(cid)
        elif len(parts) == 4 and parts[1] in ('t', 's'):
            try:
                page = int(parts[3])
            except ValueError:
                return
            if page < 0 or page > 100:
                return
            kind = 'type' if parts[1] == 't' else 'subject'
            selector = parts[2]
            if kind == 'type' and selector not in ALLOWED_TYPES:
                return
            if kind == 'subject' and not (selector == 'none' or (selector.isdigit() and int(selector) > 0)):
                return
            show_filtered(uid, cid, kind, selector, page)

    return {'show_filtered': show_filtered, 'show_stats': show_stats, 'show_subjects': show_subjects}
