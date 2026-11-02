"""V11.8.8 — private administrator smart bulk catalog sessions.

All file transfers delegate to V11.7 submit_media() (Telegram copy_message), so
permissions, database consistency, duplicate checks, and OCR/download limits stay
with the existing production implementation. Sessions are process-local only.
"""
from __future__ import annotations

import copy
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import PurePath

import library_media_v117_store as store

LOG = logging.getLogger(__name__)
_LOCK = threading.RLock()
_SESSIONS = {}
_MAX_SESSIONS = 100
# Unlimited number of files; no fixed session timeout for authenticated admins.
# Core V11.7 state accepts infinity as both seconds and remaining counter.
MAX_ATTEMPTS = float('inf')
SESSION_SECONDS = float('inf')
RIGHTS = frozenset({'permission', 'public_domain', 'cc0', 'cc_by', 'cc_by_sa'})


@dataclass
class Session:
    chat_id: int
    expires_at: float
    progress_id: int | None = None
    config: dict | None = None
    attempted: int = 0
    approved: int = 0
    duplicates: int = 0
    failed: int = 0
    failures: list = field(default_factory=list)


def enabled():
    return os.getenv('LIBRARY_SMART_BULK_V1188_ENABLED', 'false').strip().lower() in (
        'true', 'yes', '1', 'on')


def _session(user_id):
    uid = int(user_id)
    with _LOCK:
        s = _SESSIONS.get(uid)
        if s and s.expires_at > time.monotonic():
            return s
        _SESSIONS.pop(uid, None)
        return None


def _plain(text, maxlen, *, minimum=2):
    return store.clean(str(text or '').strip(), maxlen, minimum=minimum)


def _report(s, *, finished=False):
    prefix = '✅ BULK UPLOAD FINISHED' if finished else '📦 SMART BULK UPLOAD'
    text = (f'{prefix}\n'
            f'📁 Processed: {s.attempted}\n'
            f'✅ Published: {s.approved}\n'
            f'⏭️ Duplicates skipped: {s.duplicates}\n'
            f'⚠️ Failed: {s.failed}')
    if s.config:
        text += (f'\n🌐 Language: {s.config["language"]}'
                 f' · 📚 Category: {s.config["category"]}')
    if s.failures:
        text += '\nRecent issues:\n' + '\n'.join(s.failures[-5:])
    if not finished:
        text += '\n/mediabulkstatus · /mediabulkdone'
    return text[:3800]


def _send(bot, chat_id, text):
    return bot.send_message(chat_id, text[:3990])


def _update(bot, s, *, force=False):
    # Telegram edits are cheap; fall back to occasional progress updates only.
    if s.progress_id is not None:
        edit = getattr(bot, 'edit_message_text', None)
        if callable(edit):
            try:
                result = edit(_report(s), chat_id=s.chat_id,
                              message_id=s.progress_id)
                if result is not False:
                    return
            except Exception:
                LOG.debug('Cannot edit bulk progress', exc_info=True)
        # Avoid retrying edits after a missing/failed edit method.
        s.progress_id = None
    if force or s.attempted == 1 or s.attempted % 10 == 0:
        _send(bot, s.chat_id, _report(s))


def begin(bot, m):
    """Start after caller has checked admin/private permission and set V11.7 state."""
    uid = int(m.from_user.id)
    chat_id = int(m.chat.id)
    with _LOCK:
        if len(_SESSIONS) >= _MAX_SESSIONS:
            now = time.monotonic()
            for old_id, old in list(_SESSIONS.items()):
                if old.expires_at <= now:
                    _SESSIONS.pop(old_id, None)
            if len(_SESSIONS) >= _MAX_SESSIONS and uid not in _SESSIONS:
                raise ValueError('Too many active bulk sessions. Try again later.')
        s = Session(chat_id=chat_id, expires_at=time.monotonic() + SESSION_SECONDS)
        _SESSIONS[uid] = s
    instruction = (
        '📦 SMART BULK UPLOAD — V11.8.8\n'
        'Step 1: confirm shared metadata AND your right to distribute these files:\n'
        '/mediabulkset Tamil | Education | permission | Unknown | Distribution rights verified\n\n'
        'Step 2: In Telegram Desktop, attach multiple files as Documents and send.\n'
        'Each file receives its own title from its filename. Captions with full metadata override shared values.\n'
        'No per-session file limit or fixed timer. Finish with /mediabulkdone.\n'
        'Duplicates are skipped. Large files are copied inside Telegram.\n'
        'Use /mediabulkstatus or /mediabulkdone when finished.\n'
        '⛔ Only upload files you are authorized to distribute.\n'
        'ZIP archives still follow the existing small, safe ZIP-import rules.'
    )
    try:
        sent = _send(bot, chat_id, instruction)
    except Exception:
        with _LOCK:
            _SESSIONS.pop(uid, None)
        raise
    # Don't edit instructions; status will be a separate message after setup.
    return sent


def configure(bot, m):
    s = _session(m.from_user.id)
    if not s:
        return _send(bot, m.chat.id, '⚠️ No active smart bulk session. Start /mediabulk first.')
    raw = str(getattr(m, 'text', '') or '').partition(' ')[2].strip()
    fields = [x.strip() for x in raw.split('|')]
    if len(fields) not in (3, 4, 5):
        return _send(bot, m.chat.id,
                     '⚠️ Use /mediabulkset LANGUAGE | CATEGORY | RIGHTS | AUTHOR | COMMENT\n'
                     'Example: /mediabulkset Tamil | Education | permission | Unknown | Distribution rights verified')
    try:
        language = _plain(fields[0], 40)
        category = _plain(fields[1], 70)
        rights = fields[2].strip().lower()
        if rights not in RIGHTS:
            raise ValueError('Rights must be permission, public_domain, cc0, cc_by, or cc_by_sa.')
        author = _plain(fields[3] if len(fields) >= 4 and fields[3] else 'Unknown', 120)
        comment = _plain(fields[4] if len(fields) == 5 and fields[4] else
                         'Distribution rights verified by library administrator', 700)
        # Validate the same seven-column caption that submit_media() will parse.
        example = 'Example title | ' + author + ' | ' + language + ' | ' + category + ' | ' + rights + ' | ' + comment
        store.parse_caption(example)
        config = dict(language=language, category=category, rights=rights,
                      author=author, comment=comment)
    except ValueError as exc:
        return _send(bot, m.chat.id, '⚠️ Batch metadata not saved: ' + str(exc)[:250])
    with _LOCK:
        if _SESSIONS.get(int(m.from_user.id)) is not s:
            return _send(bot, m.chat.id, '⚠️ Session expired. Start /mediabulk again.')
        s.config = config
    sent = _send(bot, m.chat.id,
                 '✅ Shared metadata saved. Send multiple PDF/EPUB/DOCX/TXT or other supported files now.\n'
                 f'Language: {language} · Category: {category}\n'
                 f'Rights: {rights} · Author: {author}\n'
                 'File titles will come from filenames. Finish with /mediabulkdone.')
    # Create progress message separately, never overwrite instructions.
    progress = _send(bot, m.chat.id, _report(s))
    with _LOCK:
        s.progress_id = getattr(progress, 'message_id', None)
    return sent


def _filename_title(m):
    info = store.detect_kind(m)
    name = str(info['name'])
    basename = name.rsplit('.', 1)[0] if '.' in name else name
    # Preserve Unicode Tamil/Arabic names; prevent caption field separators.
    title = ' '.join(basename.replace('_', ' ').replace('|', ' ').split()).strip()
    return _plain(title[:180] if title else 'Untitled file', 180), info


def _caption(m, config):
    title, info = _filename_title(m)
    # V11.8.8.1: channel-forward text is not a library rights declaration.
    # Trust admin-confirmed shared metadata and the actual document filename.
    # Individually authored admin uploads keep existing caption overrides.
    forwarded = bool(getattr(m, 'forward_origin', None) or
                     getattr(m, 'forward_from_chat', None) or
                     getattr(m, 'forward_date', None))
    original = '' if forwarded else str(getattr(m, 'caption', '') or '').strip()
    if '|' in original:
        # Explicit full metadata provided for this single file; do not hide
        # errors in it by quietly using the shared batch authorization.
        store.parse_caption(original, default_name=title)
        return original, info
    if original:
        # A simple caption is a per-file title override, not a rights declaration.
        title = _plain(original.replace('|', ' ')[:180], 180)
    pieces = [title, config['author'], config['language'], config['category'],
              config['rights'], config['comment']]
    return ' | '.join(pieces), info


def accept_file(bot, m, *, api):
    """True means handled. False means legacy V11.7 handler should process it."""
    s = _session(m.from_user.id)
    if not s or not s.config:
        return False
    # ZIP extraction must use the old, strictly size-limited import path.
    doc = getattr(m, 'document', None)
    if doc and str(getattr(doc, 'file_name', '') or '').lower().endswith('.zip'):
        return False
    uid = int(m.from_user.id)
    with _LOCK:
        s.attempted += 1
    name = 'file'
    try:
        caption, info = _caption(m, s.config)
        name = info['name'][:90]
        # Do NOT alter the actual incoming Telegram message or download media.
        copied = copy.copy(m)
        copied.caption = caption
        api.submit_media(bot, copied, contributor=False)
        with _LOCK:
            s.approved += 1
    except ValueError as exc:
        msg = str(exc)
        with _LOCK:
            if msg.startswith('Duplicate file already exists:'):
                s.duplicates += 1
            else:
                s.failed += 1
                s.failures.append(f'{name[:35]}: {msg[:95]}')
    except Exception:
        LOG.exception('Smart bulk file upload failed')
        with _LOCK:
            s.failed += 1
            s.failures.append(f'{name[:35]}: upload or catalog save failed')
    _update(bot, s)
    # Keep accepting files until /mediabulkdone or /mediacancel.
    return True


def status(bot, m):
    s = _session(m.from_user.id)
    return _send(bot, m.chat.id, _report(s) if s else
                 'ℹ️ No active smart bulk upload. Use /mediabulk to start.')


def finish(bot, m, *, api):
    uid = int(m.from_user.id)
    with _LOCK:
        s = _SESSIONS.pop(uid, None)
    api._state_cancel(uid)
    if s:
        return _send(bot, m.chat.id, _report(s, finished=True))
    return _send(bot, m.chat.id, '✅ No active smart bulk upload.')


def cancel(user_id):
    with _LOCK:
        _SESSIONS.pop(int(user_id), None)
