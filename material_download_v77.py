"""V7.7 private export of ONE saved study material's extracted text.

No provider requests, storage writes, or original binary PDF/DOCX downloads.
Public handlers are registered by V7.7's guarded installer into the V7.5
material library. Saved files are created only in memory on confirmation.
"""
from __future__ import annotations

import io
import re
import secrets
import threading
import time

from material_library_v75 import clean_line, private_user

CONFIRM_SECONDS = 300
MAX_BYTES = 2 * 1024 * 1024
MAX_PENDING = 300
_PENDING = {}
_LOCK = threading.RLock()


def parse_material_id(value):
    try:
        if not str(value).isascii() or not str(value).isdigit():
            return None
        ident = int(value)
        return ident if 0 < ident <= 2**63 - 1 else None
    except (TypeError, ValueError):
        return None


def _safe_metadata(value, limit=120):
    """One line, no bidi/control characters in exported metadata."""
    value = clean_line(value, limit)
    return re.sub(r'[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]', '', value)


def _markdown_escape(value):
    return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', value)


def _accessible(material, user_id):
    return (isinstance(material, dict)
            and str(material.get('user_id', '')) == str(user_id))


def export_bytes(material, material_id, format_name):
    """Encode extracted text only; do not claim to export original document."""
    if format_name not in ('txt', 'md'):
        raise ValueError('Unsupported export format.')
    title = _safe_metadata(material.get('title') or material.get('file_name') or 'Untitled')
    original_name = _safe_metadata(material.get('file_name') or 'Unavailable')
    kind = _safe_metadata(material.get('file_type') or 'unknown', 20)
    content = str(material.get('extracted_text') or '').strip()
    if not content:
        raise ValueError('No extracted text is saved for this document. Try OCR or reuploading.')
    # Guard memory/Telegram size; no silently truncated exports.
    if len(content) > MAX_BYTES:
        raise ValueError('Extracted text is too large to export (2 MB limit).')
    if format_name == 'txt':
        body = (f'Student Assistant — Extracted Study Material\n'
                f'Title: {title}\nOriginal file: {original_name}\nType: {kind}\n'
                'Note: Exported extracted text only; NOT the original uploaded file.\n'
                '\n--- CONTENT ---\n' + content + '\n')
    else:
        body = (f'# {_markdown_escape(title)}\n\n'
                f'**Original file:** {_markdown_escape(original_name)}  \n'
                f'**File type:** {_markdown_escape(kind)}\n\n'
                '> Extracted text only — not the original uploaded file.\n\n'
                '---\n\n' + content + '\n')
    data = body.encode('utf-8')
    if len(data) > MAX_BYTES:
        raise ValueError('Export exceeds the 2 MB UTF-8 size limit. Nothing was sent.')
    filename = f'study_material_{material_id}_extracted.{format_name}'
    return filename, data


def register_material_download_handlers(bot, types_module, get_fn, material_state, *, clock=None):
    """Register independent handlers after V7.5, before catch-all upload handlers."""
    now = clock or time.monotonic

    def send(cid, text, markup=None):
        if markup is None:
            return bot.send_message(cid, text)
        return bot.send_message(cid, text, reply_markup=markup)

    def buttons():
        return types_module.InlineKeyboardMarkup(row_width=2)

    def btn(label, data):
        return types_module.InlineKeyboardButton(label, callback_data=data)

    def checked_row(uid, cid, mid):
        try:
            material = get_fn(uid, mid)
        except Exception as exc:
            print('V7.7 material export lookup failed:', type(exc).__name__)
            send(cid, '⚠️ Could not read your study material. Try again later.')
            return None
        if not _accessible(material, uid):
            send(cid, '🔒 Material not found or not accessible.')
            return None
        return material

    def request(uid, cid, mid, fmt):
        if fmt not in ('txt', 'md') or parse_material_id(mid) is None:
            send(cid, 'Usage: /materialdownload 12 or /materialdownloadmd 12')
            return
        mid = int(mid)
        material = checked_row(uid, cid, mid)
        if material is None:
            return
        try:
            filename, data = export_bytes(material, mid, fmt)
        except ValueError as exc:
            send(cid, f'⚠️ {exc}')
            return
        token = secrets.token_hex(8)
        with _LOCK:
            # Keep one pending request per user and expire old requests.
            for key, value in list(_PENDING.items()):
                if key == uid or now() - value['at'] > CONFIRM_SECONDS:
                    _PENDING.pop(key, None)
            if len(_PENDING) >= MAX_PENDING:
                send(cid, '⚠️ Export confirmations are temporarily busy. Try later.')
                return
            _PENDING[uid] = {'id': mid, 'format': fmt, 'token': token, 'at': now()}
        markup = buttons()
        markup.row(btn('✅ Download Extracted Text', f'v77:yes:{fmt}:{mid}:{token}'),
                   btn('❌ Cancel', f'v77:no:{fmt}:{mid}:{token}'))
        label = _safe_metadata(material.get('title') or material.get('file_name'), 80)
        send(cid, f'📥 Export extracted text from “{label}”?\n'
                  f'Format: {fmt.upper()} | Size: {len(data):,} bytes\n'
                  f'Filename: {filename}\n\n'
                  '🔒 Your file will be sent to this private chat only.\n'
                  '⚠️ This is NOT the original PDF/DOCX/TXT attachment. '
                  'The export includes only saved extracted text.', markup)

    def run_command(message, fmt):
        uid = private_user(message)
        cid = message.chat.id
        if uid is None or cid != uid:
            send(cid, '🔒 Material downloads are available only in your private chat.')
            return
        material_state.pop(cid, None)
        parts = (getattr(message, 'text', '') or '').split(maxsplit=1)
        mid = parse_material_id(parts[1]) if len(parts) > 1 else None
        if mid is None:
            send(cid, 'Usage: /materialdownload 12\nOr: /materialdownloadmd 12')
            return
        request(uid, cid, mid, fmt)

    @bot.message_handler(commands=['materialdownload'])
    def txt_command(message):
        run_command(message, 'txt')

    @bot.message_handler(commands=['materialdownloadmd'])
    def md_command(message):
        run_command(message, 'md')

    @bot.callback_query_handler(func=lambda c: str(getattr(c, 'data', '')).startswith('v77:'))
    def export_callback(call):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        uid = private_user(call)
        msg = getattr(call, 'message', None)
        cid = getattr(getattr(msg, 'chat', None), 'id', None)
        if cid is None:
            return
        if uid is None or cid != uid:
            send(cid, '🔒 Open a private chat with the bot.')
            return
        parts = str(getattr(call, 'data', '')).split(':')
        if len(parts) == 4 and parts[1] == 'req':
            fmt, mid = parts[2], parse_material_id(parts[3])
            if mid is not None:
                request(uid, cid, mid, fmt)
            return
        if len(parts) != 5 or parts[1] not in ('yes', 'no'):
            return
        action, fmt, mid, token = parts[1], parts[2], parse_material_id(parts[3]), parts[4]
        if mid is None or fmt not in ('txt', 'md'):
            return
        with _LOCK:
            pending = _PENDING.get(uid)
            if (not pending or pending['id'] != mid or pending['format'] != fmt
                    or not secrets.compare_digest(pending['token'], token)):
                send(cid, '⌛ This export confirmation is no longer valid. Open the material again.')
                return
            _PENDING.pop(uid, None)  # one-time token, even on failure
        if now() - pending['at'] > CONFIRM_SECONDS:
            send(cid, '⌛ Export confirmation expired. Request it again.')
            return
        if action == 'no':
            send(cid, '✅ Download cancelled; no file was sent.')
            return
        # Re-fetch and verify ownership at the moment of sending.
        material = checked_row(uid, cid, mid)
        if material is None:
            return
        try:
            filename, data = export_bytes(material, mid, fmt)
        except ValueError as exc:
            send(cid, f'⚠️ {exc}')
            return
        stream = io.BytesIO(data)
        stream.name = filename
        try:
            bot.send_document(cid, stream,
                              caption='📥 Extracted text only — not your original attachment.')
        except Exception as exc:
            print('V7.7 material export send failed:', type(exc).__name__)
            send(cid, '⚠️ Could not send the extracted text file. Please try again.')

    return {'request': request}
