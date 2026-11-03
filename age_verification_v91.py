"""V9.1 opt-in, fail-closed Yoti 18+ verification for Telegram users.

No images, identity documents, DOB, or provider API credentials are stored here.
Only the *server-authenticated provider result* can grant adult access.
This module requires a Yoti account/configuration and the SQL_V91 migration.
"""
from __future__ import annotations

import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import requests

YOTI_CREATE_URL = 'https://age.yoti.com/api/v1/sessions'
YOTI_VIEW_URL = 'https://age.yoti.com'
TRUE = ('true', '1', 'yes')
MAX_DAILY_SESSIONS = 3
VERIFY_TTL_SECONDS = 900
REVERIFY_DAYS = 90


class AgeVerificationError(Exception):
    """Safe error intended for the bot UI (no upstream payloads or credentials)."""


def enabled():
    return os.getenv('V91_AGE_VERIFY_ENABLED', 'false').strip().lower() in TRUE


def _utcnow():
    return datetime.now(timezone.utc)


def _parse_dt(value):
    try:
        val = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if val.tzinfo is None:
            return None
        return val.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _valid_uid(uid):
    if isinstance(uid, bool):
        raise AgeVerificationError('Invalid Telegram account.')
    try:
        uid = int(uid)
    except (ValueError, TypeError, OverflowError) as exc:
        raise AgeVerificationError('Invalid Telegram account.') from exc
    if uid < 1 or uid > 9223372036854775807:
        raise AgeVerificationError('Invalid Telegram account.')
    return uid


def _config():
    if not enabled():
        raise AgeVerificationError('Automatic adult verification is not enabled yet. Contact the bot administrator.')
    api_key = os.getenv('YOTI_AGE_API_KEY', '').strip()
    sdk_id = os.getenv('YOTI_AGE_SDK_ID', '').strip()
    base_url = os.getenv('V8_PUBLIC_URL', '').rstrip('/')
    parsed = urlsplit(base_url)
    if not api_key or not re.fullmatch(r'[0-9a-fA-F-]{36}', sdk_id):
        raise AgeVerificationError('Age verification provider is not configured. Contact the administrator.')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise AgeVerificationError('The public HTTPS URL is not configured correctly.')
    return api_key, sdk_id, base_url


def _headers(api_key, sdk_id):
    return {'Authorization': 'Bearer ' + api_key, 'Yoti-SDK-Id': sdk_id, 'Content-Type': 'application/json'}


def _db(client=None):
    if client is not None:
        return client
    from db import supabase
    return supabase


def _one(db, table, uid, fields='*'):
    result = (db.table(table).select(fields).eq('user_id', uid).limit(1).execute()).data or []
    return result[0] if result else None


def _access_row(db, uid):
    return _one(db, 'study_verified_adults', uid, 'status,valid_until,verification_method')


def _current_verified(row, now):
    return (bool(row) and row.get('status') == 'verified'
            and row.get('verification_method') in ('trusted_provider', 'manual_review')
            and (_parse_dt(row.get('valid_until')) or now) > now)


def _provider_json(response):
    try:
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError('Expected a JSON object')
        return data
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise AgeVerificationError('The verification provider is unavailable. Try again later.') from exc


def _session_link(session_id, sdk_id):
    # Both values are server-supplied UUIDs; no user-controlled host or redirection.
    return f'{YOTI_VIEW_URL}?sessionId={session_id}&sdkId={sdk_id}'


def start(uid, *, db=None, http=None, now=None):
    """Create/reuse a Yoti session tied to an authenticated Telegram user.

    Returns a Yoti-hosted link. This does *not* grant age eligibility.
    """
    uid = _valid_uid(uid)
    api_key, sdk_id, base_url = _config()
    db = _db(db)
    http = http or requests
    now = now or _utcnow()
    existing = _access_row(db, uid)
    if existing and existing.get('status') == 'revoked':
        raise AgeVerificationError('This account is restricted. Contact the administrator.')
    if _current_verified(existing, now):
        return None
    state = _one(db, 'study_age_sessions', uid)
    if state and state.get('status') == 'pending':
        expires = _parse_dt(state.get('expires_at'))
        if expires and expires > now and state.get('session_id'):
            return _session_link(state['session_id'], sdk_id)
    count = 0
    if state and str(state.get('count_date', ''))[:10] == now.date().isoformat():
        count = int(state.get('daily_count') or 0)
    if count >= MAX_DAILY_SESSIONS:
        raise AgeVerificationError('Daily verification attempts reached. Try again tomorrow.')
    if state:
        started = _parse_dt(state.get('created_at'))
        if started and now - started < timedelta(seconds=60):
            raise AgeVerificationError('Please wait a minute before requesting another verification.')
    reference = secrets.token_hex(16)  # Random, does not disclose Telegram ID.
    payload = {
        'type': 'OVER', 'ttl': VERIFY_TTL_SECONDS, 'reference_id': reference,
        'digital_id': {'allowed': True, 'threshold': 18},
        'doc_scan': {'allowed': True, 'threshold': 18, 'authenticity': 'AUTO', 'level': 'PASSIVE'},
        'age_estimation': {'allowed': False},
        'callback': {'auto': True, 'url': base_url + '/v91/age-return'},
        'cancel_url': base_url + '/v91/age-return',
        'synchronous_checks': True,
    }
    try:
        response = http.post(YOTI_CREATE_URL, headers=_headers(api_key, sdk_id), json=payload,
                             timeout=12, allow_redirects=False)
    except requests.RequestException as exc:
        raise AgeVerificationError('The age-verification service is temporarily unavailable.') from exc
    info = _provider_json(response)
    session_id = str(info.get('id', ''))
    try:
        uuid.UUID(session_id)
    except (ValueError, AttributeError) as exc:
        raise AgeVerificationError('The provider returned an invalid session.') from exc
    expires = _parse_dt(info.get('expires_at'))
    if not expires or not now < expires <= now + timedelta(seconds=VERIFY_TTL_SECONDS+60):
        raise AgeVerificationError('The provider returned an invalid session expiry.')
    row = {
        'user_id': uid, 'session_id': session_id, 'reference_id': reference,
        'status': 'pending', 'created_at': now.isoformat(), 'expires_at': expires.isoformat(),
        'daily_count': count+1, 'count_date': now.date().isoformat(),
    }
    try:
        db.table('study_age_sessions').upsert(row, on_conflict='user_id').execute()
    except Exception as exc:
        # Fail closed: no link is issued if the session cannot be bound to an account.
        raise AgeVerificationError('Could not save the verification request. Try again later.') from exc
    return _session_link(session_id, sdk_id)


def _checked_result(info, state):
    """Yoti's OVER session COMPLETE means threshold met; corroborate identity/data."""
    if info.get('status') != 'COMPLETE' or info.get('type') != 'OVER':
        return False
    if info.get('id') != state['session_id'] or info.get('reference_id') != state['reference_id']:
        return False
    if info.get('result') is False:
        return False
    age = info.get('age')
    if isinstance(age, bool):
        return False
    try:
        return int(age) >= 18
    except (ValueError, TypeError):
        return False


def status(uid, *, db=None, http=None, now=None):
    """Poll ONLY the server-recorded provider session; return status string.

    No webhook, URL parameter, or user-supplied result can grant eligibility.
    """
    uid = _valid_uid(uid)
    db = _db(db)
    now = now or _utcnow()
    row = _access_row(db, uid)
    if row and row.get('status') == 'revoked':
        return 'restricted'
    if _current_verified(row, now):
        return 'verified'
    state = _one(db, 'study_age_sessions', uid)
    if not state:
        return 'not_started'
    if state.get('status') != 'pending':
        return 'not_started' if state.get('status') == 'expired' else str(state['status'])
    expiry = _parse_dt(state.get('expires_at'))
    if not expiry or expiry <= now:
        db.table('study_age_sessions').update({'status':'expired'}).eq('user_id',uid).execute()
        return 'expired'
    api_key, sdk_id, _ = _config()
    http = http or requests
    session_id = str(state.get('session_id',''))
    try:
        uuid.UUID(session_id)
        response = http.get(f'{YOTI_CREATE_URL}/{session_id}/result',
                            headers=_headers(api_key,sdk_id), timeout=12, allow_redirects=False)
    except (requests.RequestException, ValueError, AttributeError) as exc:
        raise AgeVerificationError('Could not check verification status. Try again later.') from exc
    info = _provider_json(response)
    # Mismatched results are never accepted or stored.
    if info.get('id') != session_id or info.get('reference_id') != state.get('reference_id'):
        raise AgeVerificationError('Provider session mismatch. Please contact the administrator.')
    result_status = str(info.get('status', '')).upper()
    if result_status in ('PENDING','IN_PROGRESS','PROCESSING'):
        return 'pending'
    if result_status == 'COMPLETE':
        if not _checked_result(info, state):
            return 'unconfirmed'
        valid_until = now + timedelta(days=REVERIFY_DAYS)
        record = {'user_id':uid, 'status':'verified','verification_method':'trusted_provider',
                  'verified_at':now.isoformat(),'valid_until':valid_until.isoformat()}
        try:
            db.table('study_verified_adults').upsert(record,on_conflict='user_id').execute()
            db.table('study_age_sessions').update({'status':'complete'}).eq('user_id',uid).execute()
        except Exception as exc:
            raise AgeVerificationError('Verification was completed, but access could not be saved.') from exc
        try:
            import study_access_v9
            with study_access_v9._lock:
                study_access_v9._cache.pop(uid, None)
        except ImportError:
            pass
        return 'verified'
    if result_status in ('FAIL','CANCELLED','ERROR','EXPIRED'):
        db.table('study_age_sessions').update({'status':'expired' if result_status=='EXPIRED' else 'failed'}).eq('user_id',uid).execute()
        return 'expired' if result_status=='EXPIRED' else 'not_verified'
    return 'pending'  # Unknown provider status must never grant access.


MESSAGES = {
    'verified':'✅ Your adult verification is active. V8 and V9 access is available when enabled.',
    'restricted':'🔒 This account is restricted. Contact the administrator.',
    'not_started':'🔒 You have not completed adult verification. Send /verify_adult to begin.',
    'pending':'⏳ Your verification is still pending. Finish the provider check, then send /access_status again.',
    'expired':'⌛ Verification session expired. Send /verify_adult to try again.',
    'failed':'❌ Verification was not successful. Send /verify_adult to try again.',
    'not_verified':'❌ Adult eligibility was not confirmed. Access has not been granted.',
    'unconfirmed':'⚠️ The provider result could not be confirmed. Contact the administrator.',
}


def register_v91_age_handlers(bot):
    """Register BEFORE V8/V9 stateful handlers in main.py."""
    from telebot import types

    @bot.message_handler(commands=['verify_adult'])
    def v91_verify(m):
        if getattr(m.chat, 'type', None) != 'private':
            bot.reply_to(m, 'Please message the bot privately to verify age.')
            return
        try:
            if not enabled():
                bot.reply_to(m, MESSAGES['not_started']+' Provider setup is not enabled yet.')
                return
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton('🔐 Start 18+ verification', callback_data='v91_age_start'))
            bot.send_message(m.chat.id, 'You will be sent to an external age-verification provider (Yoti). '
                 'It may ask for a digital ID or document scan. Do not upload identity documents to this bot. '
                 'The bot stores only your verified eligibility and a short-lived session reference. '
                 'Verification may involve provider fees paid by the bot operator. Proceed only if you consent.', reply_markup=kb)
        except Exception:
            bot.reply_to(m, 'Verification is unavailable. Please contact the administrator.')

    @bot.message_handler(commands=['access_status'])
    def v91_status(m):
        if getattr(m.chat, 'type', None) != 'private':
            bot.reply_to(m, 'Please check access privately.')
            return
        try:
            bot.reply_to(m, MESSAGES.get(status(m.from_user.id), 'Access status unavailable.'))
        except AgeVerificationError as exc:
            bot.reply_to(m, str(exc))
        except Exception:
            bot.reply_to(m, 'Verification status is temporarily unavailable.')

    @bot.callback_query_handler(func=lambda c: getattr(c,'data', '') == 'v91_age_start')
    def v91_start_callback(c):
        try:
            bot.answer_callback_query(c.id)
        except Exception:
            pass
        if not c.message or getattr(c.message.chat,'type',None)!='private' or c.message.chat.id != c.from_user.id:
            return
        try:
            link = start(c.from_user.id)
            if link is None:
                bot.send_message(c.from_user.id, MESSAGES['verified'])
            else:
                kb=types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton('Open secure age check',url=link))
                bot.send_message(c.from_user.id,'🔐 Complete the check using this secure Yoti link (15 minutes). '
                    'Afterward, return to Telegram and send /access_status. Do not share this link.',reply_markup=kb)
        except AgeVerificationError as exc:
            bot.send_message(c.from_user.id,str(exc))
        except Exception:
            bot.send_message(c.from_user.id,'The verification request could not be started. Try again later.')


def register_v91_age_return(app):
    """Untrusted browser redirect only; NEVER grants access."""
    from flask import Response

    @app.route('/v91/age-return',methods=['GET'])
    def v91_age_return():
        msg = ('Age verification step finished. Return to your Telegram bot and send '
               '/access_status to securely retrieve the verification result.')
        return Response(msg,status=200,mimetype='text/plain',headers={
            'Cache-Control':'no-store','Referrer-Policy':'no-referrer',
            'Content-Security-Policy':"default-src 'none'",'X-Content-Type-Options':'nosniff'})
