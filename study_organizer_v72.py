"""V7.2: private organization for saved AI Study notes.

Cloudflare/Gemini are not called. Notes are not changed or deleted.
The optional organizer table persists favorite and subject metadata only.
"""
from __future__ import annotations

import re

TABLE = 'ai_note_organizer_v72'
MENU = '🗂 Organize AI Notes'
SUBJECTS = ('Science', 'Mathematics', 'Languages', 'History', 'Technology', 'General')
PAGE_SIZE = 8
MAX_ROWS = 200
ID_MAX = 10**18 - 1
# data never contains arbitrary user strings, to prevent callback ambiguity.
CALLBACK = re.compile(r'^v72:(o|f|s|r|v|g|t):([0-9]{1,3}|[1-9][0-9]{0,17})(?::([1-9][0-9]{0,17}))?$')


def _private(obj):
    sender = getattr(obj, 'from_user', None)
    msg = getattr(obj, 'message', obj)
    chat = getattr(msg, 'chat', None)
    uid = getattr(sender, 'id', None)
    return (isinstance(uid, int) and uid > 0
            and getattr(chat, 'type', None) == 'private'
            and getattr(chat, 'id', None) == uid)


def _id(value):
    if isinstance(value, bool):
        raise ValueError('Invalid ID')
    try:
        ident = int(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError('Invalid ID') from None
    if not 1 <= ident <= ID_MAX:
        raise ValueError('Invalid ID')
    return ident


def _rows(response):
    data = getattr(response, 'data', None)
    if not isinstance(data, list):
        raise RuntimeError('Unexpected Supabase response')
    return data


def note_organizer_keyboard(types, note_id):
    try:
        ident = _id(note_id)
    except ValueError:
        return None
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton('⭐ Favorite / 🏷 Subject', callback_data=f'v72:o:{ident}'))
    return keyboard


def read_metadata(db, uid, note_id):
    uid, note_id = _id(uid), _id(note_id)
    rows = _rows(db.table(TABLE).select('favorite,subject')
                 .eq('user_id', uid).eq('note_id', note_id).limit(1).execute())
    return rows[0] if rows else {'favorite': False, 'subject': None}


def save_metadata(db, uid, note_id, current, *, favorite=None, subject=None, change='favorite'):
    """No note writes. Current metadata is explicitly retained on the other dimension."""
    if change not in ('favorite', 'subject'):
        raise ValueError('Invalid update')
    uid, note_id = _id(uid), _id(note_id)
    if change == 'favorite':
        if type(favorite) is not bool:
            raise ValueError('Favorite must be boolean')
        fav = favorite
        sub = current.get('subject') or None
    else:
        if subject is not None and subject not in SUBJECTS:
            raise ValueError('Unknown subject')
        fav = current.get('favorite') is True
        sub = subject
    payload = {'user_id': uid, 'note_id': note_id, 'favorite': fav, 'subject': sub}
    # Composite primary key makes repeated saves safe; never trust the client to supply uid.
    db.table(TABLE).upsert(payload, on_conflict='user_id,note_id').execute()
    return payload


def load_organizer_notes(db, uid, *, favorite=False, subject=None):
    """Return user-owned AI Study note titles only; metadata is not ownership proof.

    Capped to 200 metadata rows, fetching note titles in chunks to avoid oversized URL filters.
    """
    uid = _id(uid)
    query = db.table(TABLE).select('note_id').eq('user_id', uid)
    if favorite:
        query = query.eq('favorite', True)
    if subject is not None:
        if subject not in SUBJECTS:
            raise ValueError('Unknown subject')
        query = query.eq('subject', subject)
    refs = _rows(query.order('note_id', desc=True).limit(MAX_ROWS).execute())
    ids = []
    for entry in refs:
        try:
            ident = _id(entry.get('note_id'))
        except ValueError:
            continue
        if ident not in ids:
            ids.append(ident)
    found = {}
    for pos in range(0, len(ids), 40):
        batch = ids[pos:pos+40]
        data = _rows(db.table('notes').select('id,title')
                     .eq('user_id', uid).ilike('title', 'AI Study:%')
                     .in_('id', batch).execute())
        for item in data:
            try:
                ident = _id(item.get('id'))
            except ValueError:
                continue
            if ident in batch and str(item.get('title') or '').startswith('AI Study:'):
                found[ident] = {'id': ident, 'title': item['title']}
    ordered = [found[ident] for ident in ids if ident in found]
    return ordered[:PAGE_SIZE], len(ordered), len(refs) >= MAX_ROWS


def _choose_note(bot, chat_id, notes, heading, types):
    if not notes:
        bot.send_message(chat_id, heading + '\n📭 No matching saved AI notes.')
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for note in notes:
        ident = _id(note['id'])
        title = ' '.join(str(note.get('title') or 'AI Study Note').split())[:43]
        kb.add(types.InlineKeyboardButton('📖 ' + title, callback_data=f'v72:o:{ident}'))
    bot.send_message(chat_id, heading + '\nTap a note to organize it.', reply_markup=kb)


def _show_recent(bot, db, uid, chat_id, load_ai_note_page, types, page=0):
    if not isinstance(page, int) or not 0 <= page <= 99:
        raise ValueError('Invalid page')
    notes, more = load_ai_note_page(db, uid, page)
    if not notes:
        bot.send_message(chat_id, '📭 No more saved AI notes.' if page else
                         '📭 No saved AI Study notes yet. Use /ai and 💾 Save AI Answer.')
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for note in notes:
        ident = _id(note['id'])
        title = ' '.join(str(note.get('title') or 'AI Study Note').split())[:43]
        kb.add(types.InlineKeyboardButton('📖 ' + title, callback_data=f'v72:o:{ident}'))
    nav = []
    if page:
        nav.append(types.InlineKeyboardButton('⬅️ Newer', callback_data=f'v72:r:{page-1}'))
    if more and page < 99:
        nav.append(types.InlineKeyboardButton('Older ➡️', callback_data=f'v72:r:{page+1}'))
    if nav:
        kb.row(*nav)
    bot.send_message(chat_id, f'🕒 Recently SAVED AI notes • Page {page+1}\n'
                     'This is save order, not recently viewed order. Tap to organize:',
                     reply_markup=kb)


def _show_subjects(bot, chat_id, types):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for ix, subject in enumerate(SUBJECTS):
        kb.add(types.InlineKeyboardButton('🏷 ' + subject, callback_data=f'v72:g:{ix}'))
    bot.send_message(chat_id, '🏷 Browse notes by subject. Choose a folder:', reply_markup=kb)


def _show_detail(bot, db, uid, chat_id, note_id, load_note, types):
    # Verify ownership from Notes on every request, even if the ID is from an old button.
    note = load_note(db, uid, _id(note_id))
    if not note:
        bot.send_message(chat_id, '⚠️ This AI Study note is unavailable.')
        return False
    meta = read_metadata(db, uid, note_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    is_fav = meta.get('favorite') is True
    kb.add(types.InlineKeyboardButton('☆ Remove favorite' if is_fav else '⭐ Add to favorites',
                                     callback_data=f'v72:f:{note_id}'))
    kb.add(types.InlineKeyboardButton('🏷 Change subject', callback_data=f'v72:s:{note_id}'))
    kb.add(types.InlineKeyboardButton('📖 Open full note', callback_data=f'v66:n:{note_id}'))
    title = ' '.join(str(note.get('title') or '').split())[:120]
    current_subject = meta.get('subject') if meta.get('subject') in SUBJECTS else 'Uncategorized'
    bot.send_message(chat_id,
                     f'🗂 {title}\n⭐ Favorite: {"Yes" if is_fav else "No"}\n🏷 Subject: {current_subject}',
                     reply_markup=kb)
    return True


def register_study_organizer_v72_handlers(bot, db, load_note, load_ai_note_page, types):
    """Register before wildcard handlers. Does not interfere with existing V7.1 callbacks."""

    @bot.message_handler(commands=['studyorganize', 'studyrecent'])
    @bot.message_handler(func=lambda m: getattr(m, 'text', None) == MENU)
    def v72_recent(message):
        if not _private(message):
            bot.send_message(message.chat.id, '🔒 Use your private chat with the bot.')
            return
        try:
            bot.send_message(message.chat.id,
                             '🗂 Study Organizer V7.2\n'
                             '⭐ /studyfavorites — favorited AI notes\n'
                             '🏷 /studysubjects — subject folders\n'
                             '🕒 /studyrecent — newest saved AI notes\n'
                             'All organizing actions are private and do not use AI quota.')
            _show_recent(bot, db, message.from_user.id, message.chat.id, load_ai_note_page, types)
        except Exception as exc:
            print('V7.2 recent notes failed:', type(exc).__name__)
            bot.send_message(message.chat.id, '⚠️ Cannot load your recent AI notes right now.')

    @bot.message_handler(commands=['studyfavorites'])
    def v72_favorites(message):
        if not _private(message):
            bot.send_message(message.chat.id, '🔒 Use your private chat with the bot.')
            return
        try:
            notes, count, capped = load_organizer_notes(db, message.from_user.id, favorite=True)
            extra = '\nShowing up to 8 favorites.' if count > PAGE_SIZE else ''
            if capped:
                extra += '\n⚠️ Recent 200 saved organization records only.'
            _choose_note(bot, message.chat.id, notes, '⭐ Your favorite AI notes' + extra, types)
        except Exception as exc:
            print('V7.2 favorites failed:', type(exc).__name__)
            bot.send_message(message.chat.id,
                             '⚠️ Favorites unavailable. Check that SQL_V7_2_NOTE_ORGANIZER.sql was run in Supabase.')

    @bot.message_handler(commands=['studysubjects'])
    def v72_subjects(message):
        if not _private(message):
            bot.send_message(message.chat.id, '🔒 Use your private chat with the bot.')
            return
        _show_subjects(bot, message.chat.id, types)

    @bot.callback_query_handler(func=lambda c: bool(CALLBACK.fullmatch(str(getattr(c,'data','') or ''))))
    def v72_organizer_callback(call):
        if not _private(call):
            bot.answer_callback_query(call.id, 'Use your private chat.', show_alert=True)
            return
        match = CALLBACK.fullmatch(str(getattr(call,'data','') or ''))
        if not match:
            return
        action, a, b = match.groups()
        chat_id, uid = call.message.chat.id, int(call.from_user.id)
        try:
            if action == 'r' and b is None:
                bot.answer_callback_query(call.id)
                _show_recent(bot, db, uid, chat_id, load_ai_note_page, types, int(a))
                return
            if action == 'v' and b is None:
                bot.answer_callback_query(call.id)
                notes, _, _ = load_organizer_notes(db, uid, favorite=True)
                _choose_note(bot, chat_id, notes, '⭐ Your favorite AI notes', types)
                return
            if action == 'g' and b is None and int(a) < len(SUBJECTS):
                bot.answer_callback_query(call.id)
                sub = SUBJECTS[int(a)]
                notes, count, capped = load_organizer_notes(db, uid, subject=sub)
                _choose_note(bot, chat_id, notes,
                             f'🏷 {sub} • {count} saved note(s)' +
                             ('\n⚠️ First 200 records searched.' if capped else ''), types)
                return
            if action in ('o','f','s') and b is None:
                note_id = _id(a)
                # Authorization must run before ANY metadata reads or writes.
                note = load_note(db, uid, note_id)
                if not note:
                    bot.answer_callback_query(call.id, 'Note unavailable.', show_alert=True)
                    return
                if action == 'o':
                    bot.answer_callback_query(call.id)
                    _show_detail(bot, db, uid, chat_id, note_id, load_note, types)
                    return
                if action == 'f':
                    meta = read_metadata(db, uid, note_id)
                    setting = not (meta.get('favorite') is True)
                    save_metadata(db, uid, note_id, meta, favorite=setting)
                    bot.answer_callback_query(call.id, 'Favorite saved.')
                    _show_detail(bot, db, uid, chat_id, note_id, load_note, types)
                    return
                kb = types.InlineKeyboardMarkup(row_width=2)
                for index, label in enumerate(SUBJECTS):
                    kb.add(types.InlineKeyboardButton(label,
                               callback_data=f'v72:t:{index}:{note_id}'))
                kb.add(types.InlineKeyboardButton('🧹 Clear subject', callback_data=f'v72:t:6:{note_id}'))
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id, '🏷 Choose a subject for this AI Study note:', reply_markup=kb)
                return
            if action == 't' and b is not None and 0 <= int(a) <= len(SUBJECTS):
                note_id = _id(b)
                if not load_note(db, uid, note_id):
                    bot.answer_callback_query(call.id, 'Note unavailable.', show_alert=True)
                    return
                meta = read_metadata(db, uid, note_id)
                subject = SUBJECTS[int(a)] if int(a) < len(SUBJECTS) else None
                save_metadata(db, uid, note_id, meta, subject=subject, change='subject')
                bot.answer_callback_query(call.id, 'Subject saved.')
                _show_detail(bot, db, uid, chat_id, note_id, load_note, types)
                return
            bot.answer_callback_query(call.id, 'Invalid action.', show_alert=True)
        except Exception as exc:
            print('V7.2 organizer action failed:', type(exc).__name__)
            bot.answer_callback_query(call.id, 'Organizer unavailable.', show_alert=True)
            bot.send_message(chat_id,
                             '⚠️ Could not save note organization. If not configured, run SQL_V7_2_NOTE_ORGANIZER.sql in Supabase.')
    return True
