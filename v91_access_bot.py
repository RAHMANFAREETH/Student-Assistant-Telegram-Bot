"""Private Telegram enrollment + verified-adult admin review for V8/V9.

Only administrators on V91_ADMIN_USER_IDS may review requests. Users are not
asked to upload identifying documents through Telegram. Age verification must
occur independently outside this bot and be attested by the human reviewer.
"""
from __future__ import annotations
import os
from adult_requests_v91 import (AccessError, is_admin, create_request,
                                request_status, pending_requests,
                                review_request, revoke_access)

BUTTON = '🔐 Verify Adult Access'

def enabled():
    return os.getenv('V91_ACCESS_REQUESTS_ENABLED', '').lower() in ('true','1','yes')


def register_v91_access_handlers(bot):
    """Register before legacy V8/V9 stateful handlers."""

    def send(chat_id, text):
        bot.send_message(chat_id, text)

    def private(m):
        return getattr(getattr(m, 'chat', None), 'type', None) == 'private'

    def status(m):
        if not private(m):
            send(m.chat.id, '🔒 Adult access status is available only in a private chat.')
            return
        if not enabled():
            send(m.chat.id, 'Adult access requests are not enabled yet. Contact the bot administrator.')
            return
        try:
            data = request_status(m.from_user.id)
            st = data.get('status', 'unknown')
            msgs = {
                'verified': '✅ Your adult access is verified. Open /v8 or /v9 if those features are enabled.',
                'pending': '⏳ Your access request is pending independent administrator review.',
                'rejected': '❌ Your previous request was declined. Contact the administrator if this is an error.',
                'revoked': '🔒 Your access has been revoked. Contact the administrator.',
                'cancelled': 'Your request was cancelled. You may submit a new request.',
                'inactive': '⚠️ Your previous approval is not currently active. It may have expired or become unavailable. Contact the administrator or request a new review.',
                'not_requested': 'No access request found. Send /verify_adult to request review.',
            }
            message = msgs.get(st, 'Your access status is temporarily unavailable.')
            if st == 'verified' and data.get('valid_until'):
                message += '\nExpiry (UTC): ' + str(data['valid_until'])[:19]
            send(m.chat.id, message)
        except Exception:
            send(m.chat.id, '⚠️ Verification status is temporarily unavailable. Please try later.')

    @bot.message_handler(commands=['access_status'])
    def cmd_status(m):
        status(m)

    @bot.message_handler(commands=['verify_adult'])
    @bot.message_handler(func=lambda m: getattr(m, 'text', '') == BUTTON)
    def cmd_request(m):
        if not private(m):
            send(m.chat.id, '🔒 Send /verify_adult privately to the bot.')
            return
        if not enabled():
            send(m.chat.id, 'Adult verification enrollment is not enabled yet.')
            return
        try:
            result = create_request(m.from_user.id)
        except Exception:
            send(m.chat.id, '⚠️ Unable to save your access request. Please try again later.')
            return
        if result == 'created':
            send(m.chat.id, '✅ Request submitted for administrator review. This does NOT verify your age. '
                 'An administrator must check your eligibility independently. '
                 'Do not send identity documents or birthdates to this bot. Check /access_status.')
            for raw in os.getenv('V91_ADMIN_USER_IDS', '').split(','):
                if raw.strip().isdigit():
                    try:
                        bot.send_message(int(raw.strip()),
                            '🔐 New adult access request from Telegram user ID '
                            f'{int(m.from_user.id)}. Use /access_requests in private chat.')
                    except Exception:
                        pass
        elif result == 'pending':
            send(m.chat.id, '⏳ Your request is already pending review. Use /access_status.')
        elif result == 'verified':
            send(m.chat.id, '✅ Your account is already verified.')
        else:
            send(m.chat.id, '⏳ Please wait at least 24 hours after the last review before reapplying.')

    def require_admin(m):
        if not private(m):
            send(m.chat.id, '🔒 Admin commands must be used in a private chat with the bot.')
            return False
        if not enabled() or not is_admin(m.from_user.id):
            send(m.chat.id, '🔒 Administrator access is unavailable.')
            return False
        return True

    @bot.message_handler(commands=['access_requests'])
    def cmd_requests(m):
        if not require_admin(m):
            return
        try:
            items = pending_requests(limit=10)
            if not items:
                send(m.chat.id, 'No pending adult access requests.')
            else:
                lines = ['🔐 Pending requests (oldest first):']
                lines.extend(f"• {r['user_id']} (requested {str(r.get('created_at','?'))[:16]})" for r in items)
                lines.append('After independently verifying age, use:')
                lines.append('/access_approve USER_ID verified_offline 180')
                lines.append('Or deny with /access_reject USER_ID')
                send(m.chat.id, '\n'.join(lines))
        except Exception:
            send(m.chat.id, '⚠️ Unable to read the request queue. Check database access.')

    @bot.message_handler(commands=['access_approve'])
    def cmd_approve(m):
        if not require_admin(m):
            return
        parts = (getattr(m,'text','') or '').split()
        if len(parts) not in (3,4) or parts[2] != 'verified_offline':
            send(m.chat.id, 'Usage: /access_approve USER_ID verified_offline [DAYS]\n'
                 'Only use after independently verifying the user is 18+. '
                 'Never approve based only on a self-declaration.')
            return
        try:
            days = int(parts[3]) if len(parts) == 4 else 180
            result = review_request(m.from_user.id, parts[1], 'approve', days)
            send(m.chat.id, f'✅ Request {parts[1]} {result}; access expires in {days} days.')
            try: send(int(parts[1]), '✅ Adult access approved after review. Check /access_status and open /v8 or /v9.')
            except Exception: pass
        except (AccessError, ValueError):
            send(m.chat.id, '❌ Invalid request, review confirmation, or expiry (1–365 days).')
        except Exception:
            send(m.chat.id, '⚠️ Approval did not complete. Check SQL RPC setup and logs; do not retry blindly.')

    @bot.message_handler(commands=['access_reject'])
    def cmd_reject(m):
        if not require_admin(m):
            return
        parts = (getattr(m,'text','') or '').split()
        if len(parts) != 2:
            send(m.chat.id, 'Usage: /access_reject USER_ID')
            return
        try:
            review_request(m.from_user.id, parts[1], 'reject')
            send(m.chat.id, 'Request rejected.')
            try: send(int(parts[1]), 'Your adult access request was not approved. Contact the administrator.')
            except Exception: pass
        except (AccessError, ValueError):
            send(m.chat.id, 'Invalid request or administrator access.')
        except Exception:
            send(m.chat.id, '⚠️ Unable to reject request. Check logs.')

    @bot.message_handler(commands=['access_revoke'])
    def cmd_revoke(m):
        if not require_admin(m):
            return
        parts = (getattr(m,'text','') or '').split()
        if len(parts) != 2:
            send(m.chat.id, 'Usage: /access_revoke USER_ID')
            return
        try:
            revoke_access(m.from_user.id, parts[1])
            send(m.chat.id, '🔒 Verified-adult access revoked.')
            try: send(int(parts[1]), 'Your adult access has been revoked. Contact the administrator.')
            except Exception: pass
        except AccessError:
            send(m.chat.id, 'Invalid request or administrator access.')
        except Exception:
            send(m.chat.id, '⚠️ Unable to revoke access. Check logs.')

