"""V9.2 Telegram inline-button admin dashboard.

Admin actions require the existing V91_ADMIN_USER_IDS allowlist, a private
chat, single-use expiring callback tokens, independent age attestation, and a
final confirmation. Database review writes reuse V9.1 atomic audited RPCs.
No identity documents or dates of birth are accepted through this workflow.
"""
from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from datetime import datetime, timezone

from adult_requests_v91 import AccessError, is_admin, review_request, revoke_access
from v92_admin_service import (list_pending, get_request, list_verified,
                               get_verified, list_audit, process_expiry_batch)
from v92_expiry_worker import start_worker_if_enabled

LOG = logging.getLogger(__name__)
TTL_SECONDS = 600
MAX_SESSIONS = 4096
_SESSIONS = {}
_SESSION_LOCK = threading.Lock()


def enabled():
    return os.getenv('V92_ADMIN_ENABLED', '').lower().strip() in ('true', '1', 'yes')


def _issue(uid, action, target=None, days=None, page=0):
    """Issue a one-shot, process-local callback. Restart invalidates safely."""
    with _SESSION_LOCK:
        now = time.monotonic()
        for key, record in list(_SESSIONS.items()):
            if record['expires'] < now:
                _SESSIONS.pop(key, None)
        if len(_SESSIONS) >= MAX_SESSIONS:
            # Fail closed on abuse / load, rather than evict active confirmations.
            raise AccessError('Too many active admin interactions. Try later.')
        token = secrets.token_urlsafe(12)
        _SESSIONS[token] = {'admin': int(uid), 'action': action,
                            'target': target, 'days': days,
                            'page': page, 'expires': now + TTL_SECONDS}
    return 'v92:' + token


def _consume(uid, data):
    if not isinstance(data, str) or not data.startswith('v92:'):
        return None
    with _SESSION_LOCK:
        key = data[4:]
        record = _SESSIONS.get(key)
        if not record or record['admin'] != int(uid):
            return None
        _SESSIONS.pop(key, None)
    return record if record['expires'] >= time.monotonic() else None


def _short(value):
    return str(value or '?')[:19].replace('T', ' ')


def _buttons(uid, rows):
    from telebot import types
    markup = types.InlineKeyboardMarkup(row_width=2)
    for row in rows:
        buttons = []
        for label, action, target, days, page in row:
            buttons.append(types.InlineKeyboardButton(
                text=label, callback_data=_issue(uid, action, target, days, page)))
        markup.row(*buttons)
    return markup


def register_v92_admin_handlers(bot):
    """Call once immediately after registering V9.1 handlers, before V8/V9."""

    def private(m):
        chat = getattr(m, 'chat', None)
        return (getattr(chat, 'type', None) == 'private'
                and int(getattr(chat, 'id', -1)) == int(m.from_user.id))

    def admin(m):
        return enabled() and private(m) and is_admin(m.from_user.id)

    def deliver(chat, text, markup=None, message_id=None):
        if message_id:
            try:
                return bot.edit_message_text(text, chat_id=chat,
                                             message_id=message_id,
                                             reply_markup=markup)
            except Exception:
                pass
        return bot.send_message(chat, text, reply_markup=markup)

    def show(uid, chat, text, rows, message_id=None):
        markup = _buttons(uid, rows)
        deliver(chat, text, markup, message_id=message_id)

    def dash(uid, chat, message_id=None):
        show(uid, chat,
             '🛡 V9.2 Adult Access Admin Center\n\n'
             'Review requests only after an independent, appropriate 18+ check '
             'outside Telegram. Do not collect identity documents in this bot.\n\n'
             'Legacy V9.1 admin commands remain available.',
             [[('📋 Pending requests', 'pending', None, None, 0)],
              [('✅ Active verified', 'verified', None, None, 0)],
              [('📜 Audit history', 'audit', None, None, 0)],
              [('🔔 Run expiry reminders', 'expiry_confirm', None, None, 0)]], message_id)

    def pending(uid, chat, page=0, message_id=None):
        items = list_pending(uid, offset=page * 8)
        rows = [[(f"👤 {r['user_id']}", 'request', int(r['user_id']), None, page)]
                for r in items]
        if page:
            rows.append([('⬅ Previous', 'pending', None, None, page - 1)])
        if len(items) == 8 and page < 124:
            rows.append([('Next ➡', 'pending', None, None, page + 1)])
        rows.append([('🏠 Dashboard', 'dash', None, None, 0)])
        lines = ['📋 Pending adult access requests (oldest first):']
        lines.extend(f"• {r['user_id']} · {_short(r.get('created_at'))} UTC" for r in items)
        if not items:
            lines.append('No pending requests on this page.')
        show(uid, chat, '\n'.join(lines), rows, message_id)

    def request(uid, chat, target, page=0, message_id=None):
        item = get_request(uid, target)
        if not item or item.get('status') != 'pending':
            show(uid, chat, 'This request is no longer pending.',
                 [[('⬅ Pending requests', 'pending', None, None, page)]], message_id)
            return
        rows = []
        if int(uid) != int(target):
            rows.append([('✅ Review for approval', 'attest', target, None, page)])
            rows.append([('❌ Reject request', 'reject_confirm', target, None, page)])
        else:
            rows.append([('🔒 Cannot review your own request', 'pending', None, None, page)])
        rows.append([('⬅ Pending requests', 'pending', None, None, page)])
        show(uid, chat,
             f"👤 Request: {target}\nStatus: pending\n"
             f"Requested: {_short(item.get('created_at'))} UTC\n\n"
             'The user has NOT been verified by submitting this request. '
             'Independently verify adult eligibility before approval.', rows, message_id)

    def verified(uid, chat, page=0, message_id=None):
        items = list_verified(uid, offset=page * 8)
        rows = [[(f"👤 {r['user_id']}", 'user', int(r['user_id']), None, page)]
                for r in items]
        if page:
            rows.append([('⬅ Previous', 'verified', None, None, page - 1)])
        if len(items) == 8 and page < 124:
            rows.append([('Next ➡', 'verified', None, None, page + 1)])
        rows.append([('🏠 Dashboard', 'dash', None, None, 0)])
        lines = ['✅ Active verified users (soonest expiry first):']
        lines.extend(f"• {r['user_id']} · expires {_short(r['valid_until'])} UTC" for r in items)
        if not items:
            lines.append('No active verified users on this page.')
        show(uid, chat, '\n'.join(lines), rows, message_id)

    def user(uid, chat, target, page=0, message_id=None):
        data = get_verified(uid, target)
        if not data:
            deliver(chat, 'No verification record was found.', message_id=message_id)
            return
        text = (f"👤 User: {target}\nStatus: {data.get('status')}\n"
                f"Expiry (UTC): {_short(data.get('valid_until'))}\n"
                f"Method: {data.get('verification_method')}\n\n"
                'Revoking will immediately disable verified-adult eligibility '
                '(subject to the existing short V9 cache).')
        rows = []
        if data.get('status') == 'verified' and int(uid) != int(target):
            rows.append([('🔒 Revoke access', 'revoke_confirm', target, None, page)])
        rows.append([('⬅ Verified users', 'verified', None, None, page)])
        show(uid, chat, text, rows, message_id)

    def audit(uid, chat, page=0, message_id=None):
        events = list_audit(uid, offset=page * 8)
        lines = ['📜 Recent access decisions (UTC):']
        lines.extend(f"• {_short(r.get('created_at'))}: {r['action']} user {r['user_id']} "
                     f"by admin {r['admin_id']}" for r in events)
        if not events:
            lines.append('No recorded decisions on this page.')
        rows = []
        if page:
            rows.append([('⬅ Previous', 'audit', None, None, page - 1)])
        if len(events) == 8 and page < 124:
            rows.append([('Next ➡', 'audit', None, None, page + 1)])
        rows.append([('🏠 Dashboard', 'dash', None, None, 0)])
        show(uid, chat, '\n'.join(lines), rows, message_id)

    @bot.message_handler(commands=['adult_admin', 'access_admin'])
    def cmd_admin(m):
        if not admin(m):
            bot.send_message(m.chat.id, '🔒 This dashboard requires an authorized administrator in a private chat.')
            return
        try:
            dash(m.from_user.id, m.chat.id)
        except Exception:
            LOG.exception('V9.2 admin dashboard failed')
            bot.send_message(m.chat.id, '⚠️ Admin dashboard is temporarily unavailable.')

    @bot.callback_query_handler(func=lambda call: str(getattr(call, 'data', '')).startswith('v92:'))
    def on_callback(call):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        m = getattr(call, 'message', None)
        chat_info = getattr(m, 'chat', None)
        # Callback.message.from_user is the *bot*, never the administrator.
        # Bind the clicker to their own private chat, with allowlist on EACH click.
        if not (enabled() and chat_info is not None
                and getattr(chat_info, 'type', None) == 'private'
                and int(chat_info.id) == int(call.from_user.id)
                and is_admin(call.from_user.id)):
            return
        uid = int(call.from_user.id)
        chat = int(m.chat.id)
        message_id = getattr(m, 'message_id', None)
        record = _consume(uid, call.data)
        if not record:
            deliver(chat, '⌛ This button expired or was already used. Open /adult_admin again.')
            return
        action, target, days, page = (record[k] for k in ('action', 'target', 'days', 'page'))
        try:
            if action == 'dash':
                dash(uid, chat, message_id)
            elif action == 'pending':
                pending(uid, chat, page, message_id)
            elif action == 'request':
                request(uid, chat, target, page, message_id)
            elif action == 'verified':
                verified(uid, chat, page, message_id)
            elif action == 'user':
                user(uid, chat, target, page, message_id)
            elif action == 'audit':
                audit(uid, chat, page, message_id)
            elif action == 'attest':
                if int(uid) == int(target) or get_request(uid, target).get('status') != 'pending':
                    raise AccessError('Self-review or stale request')
                show(uid, chat,
                     f"⚠️ Approval of {target} requires your own independent verification "
                     'that this person is at least 18 years old.\n\n'
                     'A Telegram claim, profile or typed birthdate alone is NOT '
                     'independent verification. Do not upload evidence to Telegram.\n\n'
                     'Have you independently completed the appropriate check?',
                     [[('✅ Yes, independently checked 18+', 'days', target, None, page)],
                      [('Cancel', 'request', target, None, page)]], message_id)
            elif action == 'days':
                if int(uid) == int(target) or get_request(uid, target).get('status') != 'pending':
                    raise AccessError('Self-review or stale request')
                show(uid, chat, f"Choose expiry for verified user {target}:",
                     [[(f'{x} days', 'approve_confirm', target, x, page)
                       for x in (30, 90)],
                      [(f'{x} days', 'approve_confirm', target, x, page)
                       for x in (180, 365)],
                      [('Cancel', 'request', target, None, page)]], message_id)
            elif action == 'approve_confirm':
                show(uid, chat,
                     f"FINAL CONFIRMATION\nApprove user {target} for {days} days?\n"
                     'Only confirm if you personally independently verified age 18+.',
                     [[('✅ Confirm approval', 'approve', target, days, page)],
                      [('Cancel', 'request', target, None, page)]], message_id)
            elif action == 'approve':
                if int(uid) == int(target):
                    raise AccessError('Cannot approve your own account')
                review_request(uid, target, 'approve', days=days)
                deliver(chat, f'✅ User {target} approved for {days} days.',
                        message_id=message_id)
                try:
                    bot.send_message(target, '✅ Your adult access was approved after independent review. '
                                     'Use /access_status, then /v8 or /v9.')
                except Exception:
                    LOG.info('Cannot notify approved user %s', target)
            elif action == 'reject_confirm':
                show(uid, chat, f"FINAL CONFIRMATION\nReject request for {target}?",
                     [[('❌ Confirm rejection', 'reject', target, None, page)],
                      [('Cancel', 'request', target, None, page)]], message_id)
            elif action == 'reject':
                if int(uid) == int(target):
                    raise AccessError('Cannot review your own account')
                review_request(uid, target, 'reject')
                deliver(chat, f'❌ Request for {target} rejected.', message_id=message_id)
                try:
                    bot.send_message(target, 'Your access request was declined. Contact the administrator for review.')
                except Exception:
                    LOG.info('Cannot notify rejected user %s', target)
            elif action == 'revoke_confirm':
                data = get_verified(uid, target)
                if int(uid) == int(target) or not data or data.get('status') != 'verified':
                    raise AccessError('Self-revocation or invalid record')
                show(uid, chat, f"FINAL CONFIRMATION\nRevoke adult access for {target}?",
                     [[('🔒 Confirm revoke', 'revoke', target, None, page)],
                      [('Cancel', 'user', target, None, page)]], message_id)
            elif action == 'revoke':
                if int(uid) == int(target):
                    raise AccessError('Cannot revoke yourself through dashboard')
                revoke_access(uid, target)
                deliver(chat, f'🔒 Adult access revoked for {target}.', message_id=message_id)
                try:
                    bot.send_message(target, '🔒 Your verified adult access was revoked. '
                                     'Contact the administrator for details.')
                except Exception:
                    LOG.info('Cannot notify revoked user %s', target)
            elif action == 'expiry_confirm':
                show(uid, chat, 'Run one expiry reminder batch now? '
                     'This may send reminders to eligible users.',
                     [[('🔔 Run once', 'expiry_run', None, None, 0)],
                      [('Cancel', 'dash', None, None, 0)]], message_id)
            elif action == 'expiry_run':
                outcome = process_expiry_batch(bot)
                deliver(chat, f"🔔 Expiry batch: claimed {outcome['claimed']}, "
                        f"delivered/recorded {outcome['sent']}.", message_id=message_id)
            else:
                deliver(chat, 'Unknown dashboard action. Open /adult_admin.')
        except (AccessError, ValueError, TypeError, AttributeError):
            deliver(chat, '⚠️ This action is no longer valid or is not permitted. Open /adult_admin.')
        except Exception:
            LOG.exception('V9.2 callback failed')
            deliver(chat, '⚠️ The action could not be completed. Check logs before retrying.')

    start_worker_if_enabled(bot)
