"""V7.0 — confirmed, private Markdown export of already saved AI Study notes.

This module intentionally performs no AI calls and no Supabase writes.  It
reuses the V6.9 owner-filtered loader and private-chat identity checks.
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone

COMMAND = 'studyexportmd'
CONFIRM = 'v70:md:confirm'
CANCEL = 'v70:md:cancel'
MAX_EXPORT_BYTES = 3_500_000
FILENAME = 'Student_Assistant_AI_Study_Notes.md'


class MarkdownExportLimitError(ValueError):
    """Export cannot be produced in full within the safe byte limit."""


def _heading(text):
    """A note title occupies exactly one Markdown heading line."""
    value = ' '.join(str(text or 'AI Study Note').split())
    # Neutralize heading/inline HTML injection from stored titles.
    return value.replace('\\', '\\\\').replace('<', '&lt;').replace('>', '&gt;')


def build_markdown_bytes(notes, now=None):
    """Build a full UTF-8 Markdown document in memory; no partial exports."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('UTC-aware timestamp required')
    if not isinstance(notes, (list, tuple)):
        raise ValueError('Expected list of notes')
    if len(notes) > 2000:
        raise MarkdownExportLimitError('Too many notes')
    output = bytearray(b'\xef\xbb\xbf')  # Helps Windows Notepad retain multilingual text.

    def add(text):
        chunk = text.encode('utf-8')
        if len(output) + len(chunk) > MAX_EXPORT_BYTES:
            raise MarkdownExportLimitError('Markdown export exceeds size limit')
        output.extend(chunk)

    add('# Student Assistant — Saved AI Study Notes\n\n'
        f'Exported (UTC): {now.astimezone(timezone.utc):%Y-%m-%d %H:%M}\n\n'
        f'Saved note count: **{len(notes)}**\n\n'
        '> Private study material. Share this file only if you intend to.\n\n')
    for idx, row in enumerate(notes, 1):
        if not isinstance(row, dict) or not str(row.get('title') or '').startswith('AI Study:'):
            raise ValueError('Unrecognized note type')
        title = _heading(row.get('title'))
        stamp = _heading(row.get('created_at') or 'Date unavailable')
        # A dynamically long fenced block keeps the original note body verbatim,
        # even when it contains Markdown headings, code fences, or HTML text.
        content = str(row.get('content') or '').strip()
        max_ticks = max((len(m.group()) for m in re.finditer(r'`+', content)), default=0)
        fence = '`' * max(3, max_ticks + 1)
        add(f'---\n\n## {idx}. {title}\n\nSaved: {stamp}\n\n'
            f'{fence}text\n{content}\n{fence}\n\n')
    return bytes(output)


def markdown_document(notes):
    output = io.BytesIO(build_markdown_bytes(notes))
    output.name = FILENAME
    return output


def register_study_markdown_v70_handlers(bot, db, types, load_notes, private_sender, private_callback):
    """Called by V6.9's existing registration; no new main.py patch needed."""

    @bot.message_handler(commands=[COMMAND])
    def v70_markdown_request(message):
        if not private_sender(message):
            bot.send_message(message.chat.id, '🔒 Export is available only in your own private bot chat.')
            return
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.row(types.InlineKeyboardButton('✅ Export Markdown', callback_data=CONFIRM),
               types.InlineKeyboardButton('❌ Cancel', callback_data=CANCEL))
        bot.send_message(message.chat.id,
                         '📝 Export Saved AI Notes as Markdown (.md)\n\n'
                         'Markdown is an editable text format. The file will include your saved AI Study notes '
                         'and may contain private information.\n\n'
                         'Maximum: 2,000 notes / 3.5 MB. No AI quota is used.\n\nExport now?',
                         reply_markup=kb)

    @bot.callback_query_handler(func=lambda call: getattr(call, 'data', None) in (CONFIRM, CANCEL))
    def v70_markdown_callback(call):
        if not private_callback(call):
            bot.answer_callback_query(call.id, 'Use your own private chat.', show_alert=True)
            return
        if call.data == CANCEL:
            bot.answer_callback_query(call.id, 'Export cancelled.')
            bot.send_message(call.message.chat.id, '❌ Markdown export cancelled. No file was created.')
            return
        bot.answer_callback_query(call.id, 'Preparing your Markdown backup…')
        try:
            notes = load_notes(db, int(call.from_user.id))
            if not notes:
                bot.send_message(call.message.chat.id,
                                 '📭 No saved AI Study notes to export. Save a study answer first.')
                return
            with markdown_document(notes) as document:
                bot.send_document(call.message.chat.id, document,
                                  caption=f'📝 Your {len(notes)} saved AI Study note(s), in Markdown. Keep it private.')
        except (MarkdownExportLimitError, ValueError) as exc:
            # V6.9 limit exceptions are ValueError subclasses, but don't expose contents.
            print('V7.0 Markdown export limit:', type(exc).__name__)
            bot.send_message(call.message.chat.id,
                             '⚠️ Your notes could not fit in a safe Markdown export. No partial file was sent.')
        except Exception as exc:
            print('V7.0 Markdown export failed:', type(exc).__name__)
            bot.send_message(call.message.chat.id,
                             '⚠️ Could not export your notes as Markdown. Please try again later.')
    return True
