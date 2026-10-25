"""V6.9 — Private export of a student's existing AI study notes.

Read-only Supabase query; no AI calls. Always requires private chat and
explicit confirmation before exporting. Never logs note contents.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from telebot import types

EXPORT_COMMAND = "studyexport"
PAGE_SIZE = 100
MAX_NOTES = 2000
MAX_EXPORT_BYTES = 3_500_000  # Small, bounded document upload on Render
CONFIRM = "v69:e:confirm"
CANCEL = "v69:e:cancel"


class ExportLimitError(ValueError):
    """Too many notes/bytes; never send a misleading partial export."""


def _private_sender(obj):
    """Only the Telegram account in its own private chat can export."""
    chat = getattr(obj, 'chat', None)
    user = getattr(obj, 'from_user', None)
    uid = getattr(user, 'id', None)
    return (getattr(chat, 'type', None) == 'private'
            and isinstance(uid, int) and uid > 0
            and getattr(chat, 'id', None) == uid)


def _private_callback(call):
    chat = getattr(getattr(call, 'message', None), 'chat', None)
    uid = getattr(getattr(call, 'from_user', None), 'id', None)
    return (getattr(chat, 'type', None) == 'private'
            and isinstance(uid, int) and uid > 0
            and getattr(chat, 'id', None) == uid)


def _rows(response):
    data = getattr(response, 'data', None)
    if not isinstance(data, list):
        raise RuntimeError('Invalid database response')
    return data


def load_export_notes(db, user_id):
    """Fetch all accessible AI-prefixed notes within safety limits; no writes.

    Returns newest-first notes. Raise before sending if complete export cannot fit.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError('Invalid user ID')
    result = []
    estimated_bytes = 1024
    for offset in range(0, MAX_NOTES + PAGE_SIZE, PAGE_SIZE):
        page = _rows(db.table('notes').select('id,title,content,created_at')
                     .eq('user_id', user_id).ilike('title', 'AI Study:%')
                     .order('id', desc=True)
                     .range(offset, offset + PAGE_SIZE - 1).execute())
        # Supabase's range is inclusive. Protect against an unsupported backend.
        if len(page) > PAGE_SIZE:
            raise RuntimeError('Unexpected export page size')
        for row in page:
            if not isinstance(row, dict):
                raise RuntimeError('Invalid note row')
            if not str(row.get('title') or '').startswith('AI Study:'):
                continue
            if len(result) >= MAX_NOTES:
                raise ExportLimitError('Too many notes')
            estimated_bytes += (len(str(row.get('title') or '').encode('utf-8'))
                                + len(str(row.get('content') or '').encode('utf-8'))
                                + len(str(row.get('created_at') or '').encode('utf-8')) + 200)
            if estimated_bytes > MAX_EXPORT_BYTES:
                raise ExportLimitError('Export exceeds size limit')
            result.append(row)
        if len(page) < PAGE_SIZE:
            break
    return result


def build_export_bytes(notes, now=None):
    """Unicode TXT with UTF-8 BOM for Windows Notepad/Tamil/Arabic compatibility."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Expected timezone-aware datetime')
    header = ('STUDENT ASSISTANT — SAVED AI STUDY NOTES\n'
              + 'Exported UTC: ' + now.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M') + '\n'
              + 'Note count: ' + str(len(notes)) + '\n'
              + 'This document may contain private study information.\n\n')
    output = bytearray(b'\xef\xbb\xbf')

    def append(text):
        encoded = text.encode('utf-8')
        if len(output) + len(encoded) > MAX_EXPORT_BYTES:
            raise ExportLimitError('Export exceeds size limit')
        output.extend(encoded)

    append(header)
    for n, row in enumerate(notes, 1):
        if not isinstance(row, dict) or not str(row.get('title') or '').startswith('AI Study:'):
            raise ValueError('Unrecognized note type')
        title = str(row.get('title') or 'AI Study Note').strip()
        created = str(row.get('created_at') or 'Date unavailable').strip()
        content = str(row.get('content') or '').strip()
        append(('=' * 48) + '\n'
               + f'{n}. {title}\n'
               + f'Saved: {created}\n'
               + ('-' * 48) + '\n'
               + content + '\n\n')
    return bytes(output)


def export_document(notes):
    """In-memory upload; avoids plaintext note files left on Render disk."""
    data = build_export_bytes(notes)
    file = io.BytesIO(data)
    file.name = 'Student_Assistant_AI_Study_Notes.txt'
    return file


def register_study_export_v69_handlers(bot, db):
    """Called from existing revision hub registration before wildcard handlers."""

    @bot.message_handler(commands=[EXPORT_COMMAND])
    def v69_export_request(message):
        if not _private_sender(message):
            bot.send_message(message.chat.id, '🔒 Export is available only in your own private bot chat.')
            return
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(types.InlineKeyboardButton('✅ Export My Notes', callback_data=CONFIRM),
               types.InlineKeyboardButton('❌ Cancel', callback_data=CANCEL))
        bot.send_message(message.chat.id,
                         '📤 Export Saved AI Study Notes\n\n'
                         'You will receive a UTF-8 .txt file containing your saved AI Study notes. '
                         'Only your own notes are included.\n\n'
                         '⚠️ The file may contain private information. Keep it safe.\n'
                         'Maximum: 2,000 notes / 3.5 MB. No AI quota is used.\n\n'
                         'Export now?', reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: getattr(c, 'data', None) in (CONFIRM, CANCEL))
    def v69_export_callback(call):
        if not _private_callback(call):
            bot.answer_callback_query(call.id, 'Use your own private chat.', show_alert=True)
            return
        if call.data == CANCEL:
            bot.answer_callback_query(call.id, 'Export cancelled.')
            bot.send_message(call.message.chat.id, '❌ Export cancelled. No file was created.')
            return
        bot.answer_callback_query(call.id, 'Preparing your private export…')
        try:
            notes = load_export_notes(db, int(call.from_user.id))
            if not notes:
                bot.send_message(call.message.chat.id,
                                 '📭 No saved AI Study notes to export. Save one using /ai first.')
                return
            with export_document(notes) as document:
                bot.send_document(call.message.chat.id, document,
                                  caption=f'📚 Your {len(notes)} saved AI Study note(s). Keep this file private.')
        except ExportLimitError:
            bot.send_message(call.message.chat.id,
                             '⚠️ Your notes exceed the safe export limit (2,000 notes / 3.5 MB). '
                             'No partial file was sent.')
        except Exception as exc:
            print('V6.9 private export failed:', type(exc).__name__)
            bot.send_message(call.message.chat.id,
                             '⚠️ Could not export your notes. Please try again later.')
    # V7.0 Private Markdown Export registration
    from study_markdown_v70 import register_study_markdown_v70_handlers
    register_study_markdown_v70_handlers(bot, db, types, load_export_notes,
                                         _private_sender, _private_callback)
    return True
