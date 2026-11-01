"""V11.8.8.2: opt-in admin-only one-document forwarding workflow.

No new storage or download path. Preview metadata before invoking V11.7 submit_media.
"""
from __future__ import annotations
import copy
import os
import threading
import time

import library_media_v117_store as store

_LOCK = threading.RLock()
_SESSIONS = {}
_TTL = 600
_LIMIT = 100
_RIGHTS = frozenset(('permission', 'public_domain', 'cc0', 'cc_by', 'cc_by_sa'))


def enabled():
    return os.getenv('LIBRARY_INDIVIDUAL_FORWARD_V11882_ENABLED', 'false').strip().lower() in ('1', 'true', 'yes', 'on')


def _send(bot, m, text):
    return bot.send_message(m.chat.id, text[:3900])


def _get(uid):
    with _LOCK:
        session = _SESSIONS.get(int(uid))
        if session and session['expires'] > time.monotonic():
            return session
        _SESSIONS.pop(int(uid), None)
        return None


def cancel(uid):
    with _LOCK:
        _SESSIONS.pop(int(uid), None)


def start(bot, m, *, api):
    uid=int(m.from_user.id)
    with _LOCK:
        if len(_SESSIONS) >= _LIMIT and uid not in _SESSIONS:
            for key, value in list(_SESSIONS.items()):
                if value['expires'] <= time.monotonic():
                    _SESSIONS.pop(key, None)
            if len(_SESSIONS) >= _LIMIT:
                return _send(bot,m,'⚠️ Too many forward sessions. Try again later.')
        _SESSIONS[uid]={'expires':time.monotonic()+_TTL, 'chat_id':int(m.chat.id), 'meta':None, 'file':None}
    api._state_set(uid,'forward',seconds=_TTL,remaining=1)
    return _send(bot,m,
        '📘 INDIVIDUAL FORWARD — V11.8.8.2\n'
        'Step 1: send /mediaforwardset TITLE | AUTHOR | LANGUAGE | CATEGORY | RIGHTS | COMMENT\n'
        'Step 2: forward ONE permitted PDF or other supported document from a Telegram channel.\n'
        'Step 3: review the preview; send /mediaforwardpublish to publish.\n'
        'To cancel: /mediaforwardcancel.\n'
        'Rights: permission / public_domain / cc0 / cc_by / cc_by_sa.\n'
        'Only declare rights you actually have. Session expires after 10 minutes.')


def parse(raw):
    items=[part.strip() for part in raw.split('|')]
    if len(items) != 6:
        raise ValueError('Use TITLE | AUTHOR | LANGUAGE | CATEGORY | RIGHTS | RIGHTS EXPLANATION.')
    title,author,language,category,rights=items[:5]
    rights=rights.lower()
    if rights not in _RIGHTS:
        raise ValueError('Rights must be permission, public_domain, cc0, cc_by, or cc_by_sa.')
    if not title or not author or not language or not category or not items[5]:
        raise ValueError('Title, author, language, category and rights explanation are required.')
    comment=items[5]
    caption=' | '.join((title,author,language,category,rights,comment))
    # Reuse existing parser/validation, including length and character limits.
    parsed=store.parse_caption(caption)
    if parsed['rights_statement']=='other':
        raise ValueError('A supported redistribution-rights declaration is required.')
    return caption,parsed


def configure(bot,m):
    uid=int(m.from_user.id)
    s=_get(uid)
    if not s or s['chat_id']!=int(m.chat.id):
        return _send(bot,m,'⚠️ Start /mediaforward first.')
    raw=str(getattr(m,'text','') or '').partition(' ')[2].strip()
    try:
        caption, meta = parse(raw)
    except ValueError as exc:
        return _send(bot,m,'⚠️ Metadata not saved: '+str(exc))
    with _LOCK:
        if _SESSIONS.get(uid) is not s:
            return _send(bot,m,'⚠️ Session expired. Start /mediaforward again.')
        s['meta']=(caption,meta)
        s['file']=None
    return _send(bot,m,
        '✅ Book details saved.\n'
        '📖 '+meta['title']+'\n'
        '✍️ '+meta['author']+'\n'
        '🌐 '+meta['language']+' · 📚 '+meta['category']+'\n'
        '📜 Rights: '+meta['rights_statement']+'\n'
        'Now forward ONE document from the channel. Do not send the details separately.')


def receive(bot,m,*,api):
    s=_get(m.from_user.id)
    if not s or s['chat_id']!=int(m.chat.id):
        return _send(bot,m,'⚠️ Session expired. Start /mediaforward again.')
    if not s['meta']:
        return _send(bot,m,'⚠️ Set book details first using /mediaforwardset.')
    if s['file'] is not None:
        return _send(bot,m,'⚠️ A file is awaiting review. Send /mediaforwardpublish or /mediaforwardcancel.')
    if not getattr(m,'document',None):
        return _send(bot,m,'⚠️ Forward one PDF/EPUB/DOCX/TXT document, not a photo or video.')
    try:
        info=store.detect_kind(m)
    except ValueError as exc:
        return _send(bot,m,'⚠️ '+str(exc))
    if info['kind'] not in ('pdf','epub','docx','txt'):
        return _send(bot,m,'⚠️ Only PDF, EPUB, DOCX and TXT are supported in this workflow.')
    if not info.get('unique_id'):
        return _send(bot,m,'⚠️ Telegram file identifier is missing.')
    with _LOCK:
        if _SESSIONS.get(int(m.from_user.id)) is not s:
            return _send(bot,m,'⚠️ Session expired.')
        s['file']=copy.copy(m)
    meta=s['meta'][1]
    return _send(bot,m,
        '🔎 REVIEW BEFORE PUBLISHING\n'
        '📖 Title: '+meta['title']+'\n'
        '✍️ Author: '+meta['author']+'\n'
        '🌐 Language: '+meta['language']+'\n'
        '📚 Category: '+meta['category']+'\n'
        '📜 Rights: '+meta['rights_statement']+'\n'
        '📎 Original file: '+str(info['name'])[:150]+'\n'
        'No file has been published yet.\n'
        '✅ /mediaforwardpublish — publish this file\n'
        '❌ /mediaforwardcancel — discard this session')


def publish(bot,m,*,api):
    uid=int(m.from_user.id)
    s=_get(uid)
    if not s or s['chat_id']!=int(m.chat.id) or not s['meta'] or s['file'] is None:
        return _send(bot,m,'⚠️ No reviewed document. Start /mediaforward, set details, and forward a file.')
    original=s['file']
    # Copy only the synthetic caption in memory; the original Telegram message stays intact.
    candidate=copy.copy(original)
    candidate.caption=s['meta'][0]
    # A failed DB write leaves the same source message eligible for retry.
    result=api.submit_media(bot,candidate,contributor=False)
    cancel(uid)
    api._state_cancel(uid)
    return _send(bot,m,'✅ Published in Library: '+result['title']+'\nID: '+str(result['id']))
