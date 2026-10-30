"""V9.2 read-only admin views and idempotent expiry reminders.

All write decisions reuse V9.1 RPCs (review_request/revoke_access).
Never accepts age evidence over Telegram; does not perform age verification.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from adult_requests_v91 import _db, is_admin, pending_requests, review_request, revoke_access, AccessError

LOG = logging.getLogger(__name__)


def require_admin(admin_id):
    if not is_admin(admin_id):
        raise AccessError('Administrator access required')


def list_pending(admin_id, db=None, offset=0, size=8):
    require_admin(admin_id)
    offset = max(0, min(int(offset), 1000))
    size = max(1, min(int(size), 10))
    return ((db or _db()).table('study_adult_access_requests')
            .select('user_id,status,created_at,updated_at')
            .eq('status', 'pending').order('created_at', desc=False)
            .range(offset, offset + size - 1).execute().data or [])


def get_request(admin_id, uid, db=None):
    require_admin(admin_id)
    from adult_requests_v91 import _id
    uid = _id(uid)
    rows = ((db or _db()).table('study_adult_access_requests')
            .select('user_id,status,created_at,reviewed_at,reviewed_by')
            .eq('user_id', uid).limit(1).execute().data or [])
    return rows[0] if rows else None


def list_verified(admin_id, db=None, offset=0, size=8):
    require_admin(admin_id)
    offset = max(0, min(int(offset), 1000))
    size = max(1, min(int(size), 10))
    return ((db or _db()).table('study_verified_adults')
            .select('user_id,status,valid_until,verification_method')
            .eq('status', 'verified')
            .gt('valid_until', datetime.now(timezone.utc).isoformat())
            .order('valid_until', desc=False)
            .range(offset, offset + size - 1).execute().data or [])


def get_verified(admin_id, uid, db=None):
    require_admin(admin_id)
    from adult_requests_v91 import _id
    rows = ((db or _db()).table('study_verified_adults')
            .select('user_id,status,valid_until,verification_method')
            .eq('user_id', _id(uid)).limit(1).execute().data or [])
    return rows[0] if rows else None


def list_audit(admin_id, db=None, offset=0, size=8):
    require_admin(admin_id)
    offset = max(0, min(int(offset), 1000))
    size = max(1, min(int(size), 10))
    return ((db or _db()).table('study_adult_access_audit')
            .select('id,user_id,admin_id,action,valid_until,created_at')
            .order('created_at', desc=True)
            .range(offset, offset + size - 1).execute().data or [])


def claim_expiry_batch(db=None, batch_size=20):
    batch_size = max(1, min(int(batch_size), 50))
    response = (db or _db()).rpc('v92_claim_expiry_notifications',
                                {'p_limit': batch_size}).execute()
    return response.data or []


def mark_expiry_sent(event_id, claim_token, db=None):
    return (db or _db()).rpc('v92_mark_expiry_notification_sent', {
        'p_event_id': int(event_id), 'p_claim_token': str(claim_token),
    }).execute().data


def process_expiry_batch(bot, db=None, batch_size=20):
    """At-least-once notifications, safely leased through a database RPC.

    If Telegram sends successfully but marking fails, an eventual retry can
    duplicate a message. Never claim 'exactly once'.
    """
    events = claim_expiry_batch(db=db, batch_size=batch_size)
    sent = 0
    for event in events:
        try:
            milestone = event['milestone']
            target = int(event['user_id'])
            expiry = str(event['valid_until'])[:19].replace('T', ' ')
            if milestone == 'expired':
                msg = ('🔒 Your verified adult access has expired (UTC: ' + expiry
                       + '). You can send /verify_adult to request another independent review.')
            elif milestone == '1d':
                msg = ('⏳ Your verified adult access expires within 24 hours (UTC: '
                       + expiry + '). Contact the administrator for a renewal review.')
            elif milestone == '7d':
                msg = ('📅 Your verified adult access expires within 7 days (UTC: '
                       + expiry + '). Contact the administrator for a renewal review.')
            else:
                raise ValueError('Unrecognized milestone')
            bot.send_message(target, msg)
            ack = mark_expiry_sent(event['id'], event['claim_token'], db=db)
            if ack is not True:
                raise RuntimeError('Database did not acknowledge the notification lease')
            sent += 1
        except Exception:
            # Lease expiration permits retry without falsely recording delivery.
            LOG.exception('V9.2 expiry notification not delivered or not acknowledged; id=%s', event.get('id'))
    return {'claimed': len(events), 'sent': sent}
