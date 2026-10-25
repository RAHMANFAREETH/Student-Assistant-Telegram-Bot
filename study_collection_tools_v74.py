"""V7.4 — owner-scoped collection search, stats, and confirmed Markdown export.

Read-only Supabase operations, no AI calls or provider changes. Uses the V7.3
collections and memberships and V7.0 Markdown writer. Registration is added to
V7.3's existing function by the version-guarded installer.
"""
from __future__ import annotations

import io
import re
from collections import Counter

from study_collections_v73 import (_id, _private, _rows, get_collection,
                                   list_collections, COLLECTIONS, ITEMS,
                                   MAX_COLLECTIONS, MAX_NOTES_PER_COLLECTION)
from study_markdown_v70 import build_markdown_bytes, MarkdownExportLimitError, _heading

MENU = '📊 Collection Tools'
CALLBACK = re.compile(r'^v74:(menu|stats|request|e|n):([1-9][0-9]{0,17}|0)$')
STATS_PAGE_SIZE = 500
MAX_MEMBERSHIPS = MAX_COLLECTIONS * MAX_NOTES_PER_COLLECTION
BATCH = 20


class CollectionExportError(ValueError):
    """Refuse an incomplete or oversized collection export."""


def _term(value):
    if not isinstance(value, str):
        raise ValueError('Search term required')
    term = ' '.join(value.split()).strip()
    if not 2 <= len(term) <= 60 or any(ord(c) < 32 or ord(c) == 127 for c in term):
        raise ValueError('Search term must contain 2–60 printable characters')
    return term


def search_collections(db, uid, term):
    """Unicode-aware literal substring search, never a user-controlled SQL filter."""
    term = _term(term).casefold()
    return [entry for entry in list_collections(db, _id(uid))
            if term in str(entry.get('name') or '').casefold()]


def collection_stats(db, uid):
    """Count links across all own collections; bounded and page-safe.

    Counts memberships, including potentially stale links, not current accessible
    note content. The export path independently rechecks note ownership.
    """
    uid = _id(uid)
    collections = list_collections(db, uid)
    own_ids = {_id(row['id']) for row in collections}
    counts = Counter()
    note_ids = set()
    for start in range(0, MAX_MEMBERSHIPS + STATS_PAGE_SIZE, STATS_PAGE_SIZE):
        rows = _rows(db.table(ITEMS).select('collection_id,note_id')
                     .eq('user_id', uid)
                     .order('collection_id')
                     .range(start, start + STATS_PAGE_SIZE - 1).execute())
        if len(rows) > STATS_PAGE_SIZE:
            raise RuntimeError('Unexpected result page size')
        if start + len(rows) > MAX_MEMBERSHIPS:
            raise RuntimeError('Collection membership limit exceeded')
        for row in rows:
            cid, nid = _id(row.get('collection_id')), _id(row.get('note_id'))
            if cid in own_ids:
                counts[cid] += 1
                note_ids.add(nid)
        if len(rows) < STATS_PAGE_SIZE:
            break
    return {'collections': collections,
            'links': sum(counts.values()),
            'unique_note_ids': len(note_ids),
            'counts': dict(counts)}


def collection_export_notes(db, uid, collection_id):
    """Load all and ONLY accessible AI Study notes linked to an owned collection.

    One bounded membership request, then batches of 20 owner-filtered note reads.
    If a membership is stale or not the student's AI note, export is rejected;
    never silently send a misleading partial backup.
    """
    uid, cid = _id(uid), _id(collection_id)
    collection = get_collection(db, uid, cid)
    if not collection:
        raise ValueError('Collection not found')
    memberships = _rows(db.table(ITEMS).select('note_id').eq('user_id', uid)
                        .eq('collection_id', cid).order('note_id', desc=True)
                        .limit(MAX_NOTES_PER_COLLECTION + 1).execute())
    if len(memberships) > MAX_NOTES_PER_COLLECTION:
        raise CollectionExportError('Collection exceeds 100 notes')
    ids = [_id(row['note_id']) for row in memberships]
    if len(ids) != len(set(ids)):
        raise CollectionExportError('Duplicate membership records')
    if not ids:
        return collection, []
    results = {}
    for start in range(0, len(ids), BATCH):
        batch = ids[start:start + BATCH]
        rows = _rows(db.table('notes').select('id,title,content,created_at')
                     .eq('user_id', uid).in_('id', batch).limit(BATCH).execute())
        for row in rows:
            rid = _id(row.get('id'))
            if rid not in batch or rid in results:
                raise RuntimeError('Unexpected note lookup result')
            if not str(row.get('title') or '').startswith('AI Study:'):
                raise CollectionExportError('Collection contains unavailable AI Study notes')
            results[rid] = row
    if len(results) != len(ids):
        raise CollectionExportError('Some notes are unavailable; no partial export was sent')
    return collection, [results[nid] for nid in ids]


def collection_markdown_document(collection, notes):
    """Private in-memory Markdown, reuse existing V7.0 writer and 3.5 MB cap."""
    base = build_markdown_bytes(notes)
    original = b'# Student Assistant \xe2\x80\x94 Saved AI Study Notes\n\n'
    label = _heading(collection.get('name') or 'Untitled')
    replacement = ('# Student Assistant — Collection Export\n\n'
                   f'Collection: **{label}**\n\n').encode('utf-8')
    if original not in base:
        raise RuntimeError('Markdown export format changed')
    result = base.replace(original, replacement, 1)
    from study_markdown_v70 import MAX_EXPORT_BYTES
    if len(result) > MAX_EXPORT_BYTES:
        raise MarkdownExportLimitError('Collection export exceeds size limit')
    doc = io.BytesIO(result)
    doc.name = f'Student_Assistant_Collection_{_id(collection["id"])}.md'
    return doc


def register_study_collection_tools_v74_handlers(bot, db, types):
    """Register after V7.3 callbacks; BEFORE general/wildcard handlers."""
    def tools(chat_id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton('📊 Collection Statistics', callback_data='v74:stats:0'))
        kb.add(types.InlineKeyboardButton('📁 Browse My Collections', callback_data='v73:list:0'))
        bot.send_message(chat_id,
                         '📊 Collection Tools — V7.4\n\n'
                         '🔎 Search: /collectionsearch biology\n'
                         '📊 Statistics: /collectionstats\n'
                         '📤 Export one collection: /collectionexport 12\n'
                         '📁 Browse or create: /collections\n\n'
                         'Export is private, confirmed, and read-only. It makes no AI requests.',
                         reply_markup=kb)

    def show_stats(chat_id, uid):
        summary = collection_stats(db, uid)
        rows = summary['collections']
        lines = [f'📊 Collection Statistics — {len(rows)}/{MAX_COLLECTIONS} collections',
                 f'Collection note links: {summary["links"]}',
                 f'Distinct linked note IDs: {summary["unique_note_ids"]}',
                 '', 'Links are not a count of currently accessible notes.']
        for entry in rows[:MAX_COLLECTIONS]:
            cid = _id(entry['id'])
            label = ' '.join(str(entry.get('name') or 'Untitled').split())[:45]
            lines.append(f'• #{cid} {label} — {summary["counts"].get(cid, 0)} link(s)')
        if not rows:
            lines.append('📭 No collections yet. Try /collectioncreate Biology Revision')
        bot.send_message(chat_id, '\n'.join(lines)[:3850])

    def request_export(chat_id, uid, cid):
        row = get_collection(db, uid, cid)
        if not row:
            raise ValueError('Collection not found')
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(types.InlineKeyboardButton('✅ Export Markdown', callback_data=f'v74:e:{cid}'),
               types.InlineKeyboardButton('❌ Cancel', callback_data=f'v74:n:{cid}'))
        name = ' '.join(str(row.get('name') or 'Untitled').split())[:60]
        bot.send_message(chat_id,
                         f'📤 Export collection #{cid}: {name}\n\n'
                         'A private .md file will contain all accessible saved AI notes in this collection. '
                         'No partial export is sent if any linked note is unavailable or the file is too large.\n\n'
                         'Maximum: 100 notes / 3.5 MB. Confirm export?',
                         reply_markup=kb)

    @bot.message_handler(commands=['collectiontools'])
    @bot.message_handler(func=lambda m: getattr(m, 'text', None) == MENU)
    def v74_menu(message):
        if not _private(message):
            bot.send_message(message.chat.id, '🔒 Collection tools work only in your private chat.')
            return
        tools(message.chat.id)

    @bot.message_handler(commands=['collectionsearch'])
    def v74_search(message):
        if not _private(message):
            bot.send_message(message.chat.id, '🔒 Use your own private bot chat.')
            return
        term = (getattr(message,'text','') or '').partition(' ')[2]
        try:
            matches = search_collections(db, message.from_user.id, term)
            kb = types.InlineKeyboardMarkup(row_width=1)
            for row in matches:
                cid = _id(row['id'])
                name = ' '.join(str(row.get('name') or 'Untitled').split())[:40]
                kb.add(types.InlineKeyboardButton('📁 ' + name, callback_data=f'v73:c:{cid}'))
            bot.send_message(message.chat.id,
                             f'🔎 Found {len(matches)} collection(s) for “{_term(term)}”.\n'
                             + ('Tap a collection to open it.' if matches else 'No matches. Try another name.'),
                             reply_markup=kb if matches else None)
        except ValueError as exc:
            bot.send_message(message.chat.id, f'⚠️ {exc}\nUsage: /collectionsearch biology')
        except Exception as exc:
            print('V7.4 search failed:', type(exc).__name__)
            bot.send_message(message.chat.id, '⚠️ Collection search is unavailable. Try again later.')

    @bot.message_handler(commands=['collectionstats'])
    def v74_stats(message):
        if not _private(message):
            bot.send_message(message.chat.id, '🔒 Use your own private bot chat.')
            return
        try:
            show_stats(message.chat.id, message.from_user.id)
        except Exception as exc:
            print('V7.4 statistics failed:', type(exc).__name__)
            bot.send_message(message.chat.id, '⚠️ Collection statistics unavailable. Please try later.')

    @bot.message_handler(commands=['collectionexport'])
    def v74_export(message):
        if not _private(message):
            bot.send_message(message.chat.id, '🔒 Use your own private bot chat.')
            return
        try:
            cid = _id((getattr(message,'text','') or '').partition(' ')[2].strip())
            request_export(message.chat.id, message.from_user.id, cid)
        except ValueError:
            bot.send_message(message.chat.id, '⚠️ Usage: /collectionexport 12 — get your ID from /collections')
        except Exception as exc:
            print('V7.4 export confirmation failed:', type(exc).__name__)
            bot.send_message(message.chat.id, '⚠️ Could not prepare collection export.')

    @bot.callback_query_handler(func=lambda call: bool(CALLBACK.fullmatch(str(getattr(call,'data','') or ''))))
    def v74_callback(call):
        if not _private(call):
            bot.answer_callback_query(call.id, 'Open your private bot chat.', show_alert=True)
            return
        action, id_text = CALLBACK.fullmatch(str(call.data)).groups()
        uid, chat_id = call.from_user.id, call.message.chat.id
        try:
            if action == 'menu' and id_text == '0':
                bot.answer_callback_query(call.id)
                tools(chat_id)
            elif action == 'stats' and id_text == '0':
                bot.answer_callback_query(call.id)
                show_stats(chat_id, uid)
            elif action == 'n':
                bot.answer_callback_query(call.id, 'Export cancelled.')
                bot.send_message(chat_id, '❌ Collection export cancelled. No file was created.')
            elif action == 'request':
                cid = _id(id_text)
                bot.answer_callback_query(call.id)
                request_export(chat_id, uid, cid)
            elif action == 'e':
                cid = _id(id_text)
                bot.answer_callback_query(call.id, 'Preparing private Markdown export…')
                collection, notes = collection_export_notes(db, uid, cid)
                if not notes:
                    bot.send_message(chat_id, '📭 This collection has no notes to export.')
                    return
                with collection_markdown_document(collection, notes) as document:
                    bot.send_document(chat_id, document,
                                      caption=f'📤 Collection #{cid}: {len(notes)} saved note(s). Keep private.')
            else:
                bot.answer_callback_query(call.id, 'Invalid action.', show_alert=True)
        except (ValueError, MarkdownExportLimitError) as exc:
            print('V7.4 export or callback rejected:', type(exc).__name__)
            bot.send_message(chat_id, '⚠️ Collection is unavailable, has inaccessible notes, or exceeds the export limit. No partial file sent.')
        except Exception as exc:
            print('V7.4 callback failed:', type(exc).__name__)
            bot.send_message(chat_id, '⚠️ Collection tool temporarily unavailable. No file sent.')
    return True
