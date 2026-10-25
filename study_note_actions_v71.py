"""V7.1 — private quick actions for one existing AI Study note.

Reuses V6.9/V7.0 export encoders; no additional dependencies, AI calls,
Supabase writes, or Telegram-wide access. The note is fetched again by
current Telegram sender ID on EVERY callback, never trusted by callback id.
"""
from __future__ import annotations

import re

CALLBACK_PATTERN = re.compile(r'^v71:(txt|md|lib):([1-9][0-9]{0,17}|0)$')
MAX_NOTE_ID = 10**18 - 1


def note_actions_keyboard(types, note_id):
    """Create buttons for one saved AI note, or None for malformed IDs."""
    try:
        ident = int(note_id)
    except (TypeError, ValueError, OverflowError):
        return None
    if not 1 <= ident <= MAX_NOTE_ID:
        return None
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.row(types.InlineKeyboardButton('📄 Download TXT', callback_data=f'v71:txt:{ident}'),
           types.InlineKeyboardButton('📝 Download Markdown', callback_data=f'v71:md:{ident}'))
    kb.row(types.InlineKeyboardButton('📚 Back to Library', callback_data='v71:lib:0'))
    return kb


def _callback_private(call):
    """Verify sender is speaking in their own private chat; refuse forwarded callbacks."""
    chat = getattr(getattr(call, 'message', None), 'chat', None)
    sender = getattr(call, 'from_user', None)
    uid = getattr(sender, 'id', None)
    return (getattr(chat, 'type', None) == 'private'
            and isinstance(uid, int) and uid > 0
            and getattr(chat, 'id', None) == uid)


def single_note_document(note, note_id, fmt):
    """Prepare one full note in memory; no partial files, no disk writes."""
    import io
    if fmt not in ('txt', 'md'):
        raise ValueError('Unsupported format')
    if not isinstance(note, dict) or not str(note.get('title') or '').startswith('AI Study:'):
        raise ValueError('Not an AI Study note')
    # Never use untrusted note titles as filenames or filesystem paths.
    if fmt == 'txt':
        from study_export_v69 import build_export_bytes
        content = build_export_bytes([note])
    else:
        from study_markdown_v70 import build_markdown_bytes
        content = build_markdown_bytes([note])
    result = io.BytesIO(content)
    result.name = f'AI_Study_Note_{int(note_id)}.{fmt}'
    return result


def register_study_note_actions_v71_handlers(bot, db, load_note, send_study_library):
    """Register after revision navigation handlers, before legacy catchalls."""

    @bot.message_handler(commands=['studytips'])
    def v71_study_help(message):
        chat = getattr(message, 'chat', None)
        sender = getattr(message, 'from_user', None)
        if (getattr(chat, 'type', None) != 'private'
                or getattr(chat, 'id', None) != getattr(sender, 'id', None)):
            bot.send_message(message.chat.id, '🔒 Open your private bot chat to use Study Library.')
            return
        bot.send_message(message.chat.id,
                         '📚 AI Study Library — Quick Guide\n\n'
                         '1. /studylibrary — browse saved notes\n'
                         '2. /studysearch biology — search inside notes\n'
                         '3. /studyfind biology — search titles\n'
                         '4. Open a note to download only that lesson (TXT or Markdown)\n'
                         '5. /studyexport — full TXT backup\n'
                         '6. /studyexportmd — full Markdown backup\n'
                         '7. /studyhub — revision tools\n\n'
                         'Your saved notes are private. No AI quota is used.')

    @bot.callback_query_handler(func=lambda c: bool(CALLBACK_PATTERN.fullmatch(
        str(getattr(c, 'data', '') or ''))))
    def v71_note_action_callback(call):
        if not _callback_private(call):
            bot.answer_callback_query(call.id, 'Use your own private chat.', show_alert=True)
            return
        match = CALLBACK_PATTERN.fullmatch(str(call.data))
        if not match:
            return
        fmt, ident_text = match.groups()
        chat_id = call.message.chat.id
        uid = int(call.from_user.id)
        if fmt == 'lib':
            try:
                bot.answer_callback_query(call.id, 'Opening your study library…')
                send_study_library(bot, db, chat_id, uid, page=0)
            except Exception as exc:
                print('V7.1 note action library failed:', type(exc).__name__)
                bot.send_message(chat_id, '⚠️ Cannot open the library right now. Try /studylibrary.')
            return
        if ident_text == '0':
            bot.answer_callback_query(call.id, 'Invalid note.', show_alert=True)
            return
        try:
            # Owner check MUST happen at download time, even for old Telegram buttons.
            note = load_note(db, uid, int(ident_text))
            if not note:
                bot.answer_callback_query(call.id, 'Note unavailable.', show_alert=True)
                return
            bot.answer_callback_query(call.id, 'Preparing your private file…')
            with single_note_document(note, int(ident_text), fmt) as document:
                bot.send_document(chat_id, document,
                                  caption='📚 Your saved AI Study note. Keep it private.')
        except ValueError:
            bot.send_message(chat_id, '⚠️ This note is too large for a safe export. No partial file was sent.')
        except Exception as exc:
            print('V7.1 note export failed:', type(exc).__name__)
            bot.send_message(chat_id, '⚠️ Cannot export this note right now. Please try later.')
    return True
