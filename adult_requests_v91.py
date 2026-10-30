"""V9.1 age-eligibility request queue and administrator review service.

Does NOT verify a user's age. An authorized human must verify eligibility
independently before calling approve_request. No ID images, birthdates, proof
or other sensitive evidence should be sent to the Telegram bot or stored here.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import os

REQUEST_TABLE = 'study_adult_access_requests'
MAX_DAYS = 365
REAPPLY_COOLDOWN = timedelta(hours=24)

class AccessError(Exception):
    """Safe application-level access error."""


def _db():
    from db import supabase
    return supabase


def _id(value):
    try:
        number = int(value)
        if str(number) != str(value) or number <= 0 or number > 9223372036854775807:
            raise ValueError
        return number
    except (ValueError, TypeError, OverflowError):
        raise AccessError('Invalid Telegram user ID.') from None


def _utc(dt=None):
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _parse_ts(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else None
    if not isinstance(value, str):
        return None
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return date if date.tzinfo else None
    except ValueError:
        return None


def is_admin(uid, env=None):
    uid = str(_id(uid))
    raw = (env if env is not None else os.getenv('V91_ADMIN_USER_IDS', ''))
    return uid in {item.strip() for item in raw.split(',') if item.strip().isdigit()}


def request_status(uid, db=None):
    uid = _id(uid)
    from study_access_v9 import is_verified_adult
    active = is_verified_adult(uid)
    db = db or _db()
    if active:
        # The established eligibility predicate remains authoritative.
        # Read expiry for display only; never infer eligibility from this query.
        rows = (db.table('study_verified_adults').select('valid_until')
                .eq('user_id', uid).limit(1).execute()).data or []
        return {'status': 'verified', 'valid_until': rows[0].get('valid_until') if rows else None}
    rows = (db.table(REQUEST_TABLE).select('status,created_at,updated_at')
            .eq('user_id', uid).limit(1).execute()).data or []
    if rows and rows[0].get('status') == 'approved':
        return {'status': 'inactive', 'updated_at': rows[0].get('updated_at')}
    return rows[0] if rows else {'status': 'not_requested'}


def create_request(uid, db=None, now=None):
    """Return created/pending/verified/cooldown; fail closed on DB errors."""
    uid = _id(uid)
    from study_access_v9 import is_verified_adult
    if is_verified_adult(uid):
        return 'verified'
    db = db or _db()
    now = _utc(now)
    rows = (db.table(REQUEST_TABLE).select('status,updated_at')
            .eq('user_id', uid).limit(1).execute()).data or []
    if rows:
        current = rows[0]
        if current.get('status') == 'pending':
            return 'pending'
        last = _parse_ts(current.get('updated_at'))
        # A missing timestamp is not evidence that a cooldown has passed.
        if last is None or now - last.astimezone(timezone.utc) < REAPPLY_COOLDOWN:
            return 'cooldown'
    (db.table(REQUEST_TABLE).upsert({
        'user_id': uid, 'status': 'pending',
        'created_at': now.isoformat(), 'updated_at': now.isoformat(),
        'reviewed_at': None, 'reviewed_by': None,
    }, on_conflict='user_id').execute())
    return 'created'


def pending_requests(db=None, limit=10):
    db = db or _db()
    return (db.table(REQUEST_TABLE).select('user_id,created_at')
            .eq('status', 'pending').order('created_at', desc=False)
            .limit(min(int(limit), 20)).execute()).data or []


def review_request(admin_uid, target_uid, decision, days=180, db=None):
    if not is_admin(admin_uid):
        raise AccessError('Administrator access required.')
    admin_uid, target_uid = _id(admin_uid), _id(target_uid)
    if admin_uid == target_uid:
        raise AccessError('An administrator cannot approve their own request.')
    if decision not in ('approve', 'reject'):
        raise AccessError('Invalid decision.')
    try:
        days = int(days)
    except (ValueError, TypeError):
        raise AccessError('Invalid expiry days.') from None
    if not 1 <= days <= MAX_DAYS:
        raise AccessError('Expiry must be between 1 and 365 days.')
    # RPC performs request review, verified-registry changes, and audit atomically.
    (db or _db()).rpc('v91_review_adult_request', {
        'p_target_user_id': target_uid, 'p_admin_user_id': admin_uid,
        'p_action': decision, 'p_valid_days': days,
    }).execute()
    from study_access_v9 import _cache, _lock
    with _lock:
        _cache.pop(target_uid, None)
    return 'approved' if decision == 'approve' else 'rejected'


def revoke_access(admin_uid, target_uid, db=None):
    if not is_admin(admin_uid):
        raise AccessError('Administrator access required.')
    admin_uid, target_uid = _id(admin_uid), _id(target_uid)
    (db or _db()).rpc('v91_revoke_adult_access', {
        'p_target_user_id': target_uid, 'p_admin_user_id': admin_uid,
    }).execute()
    from study_access_v9 import _cache, _lock
    with _lock:
        _cache.pop(target_uid, None)
    return 'revoked'
