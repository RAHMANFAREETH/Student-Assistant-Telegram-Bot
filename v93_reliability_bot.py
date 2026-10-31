"""V9.3 admin-only reliability diagnostics and public access guidance.

Deliberately read-only: no Telegram command in this module approves an adult,
changes access settings, or exposes credentials or user records.
"""
from __future__ import annotations

import logging
import os

LOG = logging.getLogger(__name__)
TRUTHY = frozenset(('true', '1', 'yes'))


def on(name):
    return os.getenv(name, '').strip().lower() in TRUTHY


def _private(m):
    chat = getattr(m, 'chat', None)
    sender = getattr(m, 'from_user', None)
    try:
        return (getattr(chat, 'type', None) == 'private'
                and int(chat.id) == int(sender.id))
    except (TypeError, ValueError, AttributeError):
        return False


def diagnose(db=None):
    """Return non-sensitive deployment/DB information; never print secrets or rows.

    Each table test is a read-only 0/1-row query. Bad DB connections are reported
    as unavailable without exposing exception details to the Telegram chat.
    """
    if db is None:
        from adult_requests_v91 import _db
        db = _db()
    results = {}
    for label, table in (
        ('Verified registry', 'study_verified_adults'),
        ('Request queue', 'study_adult_access_requests'),
        ('Audit history', 'study_adult_access_audit'),
        ('Reminder queue', 'study_adult_expiry_notifications'),
    ):
        if label == 'Reminder queue' and not on('V92_EXPIRY_WORKER_ENABLED'):
            results[label] = 'not checked (worker off)'
            continue
        try:
            db.table(table).select('user_id' if label != 'Audit history' else 'id').limit(1).execute()
            results[label] = 'reachable'
        except Exception:
            LOG.exception('V9.3 DB diagnostic: %s unavailable', label)
            results[label] = 'unavailable'
    return results


def summary(db=None):
    mode = os.getenv('STUDY_ACCESS_MODE', 'pilot').strip().lower()
    if mode not in ('pilot', 'verified_adults'):
        mode_label = 'unsupported (access denied)'
    else:
        mode_label = mode
    checks = diagnose(db=db)
    lines = [
        '🩺 V9.3 Access System Health (administrator only)',
        f'V8: {"enabled" if on("V8_ENABLED") else "disabled"}',
        f'V9: {"enabled" if on("V9_ENABLED") else "disabled"}',
        f'Access mode: {mode_label}',
        f'V9.1 requests: {"enabled" if on("V91_ACCESS_REQUESTS_ENABLED") else "disabled"}',
        f'V9.2 dashboard: {"enabled" if on("V92_ADMIN_ENABLED") else "disabled"}',
        f'Expiry worker: {"enabled" if on("V92_EXPIRY_WORKER_ENABLED") else "disabled"}',
        f'Atomic requests: {"enabled" if on("V93_REQUEST_RPC_ENABLED") else "legacy mode"}',
        '', 'Supabase read checks:',
    ]
    lines += [f'• {label}: {state}' for label, state in checks.items()]
    lines += ['', 'No database rows or environment secrets are displayed.',
              'For user-specific eligibility, ask the user to send /access_status.']
    return '\n'.join(lines)


def register_v93_reliability_handlers(bot):
    """Register after V9.2 and before the older V8/V9 stateful handlers."""
    from adult_requests_v91 import is_admin

    @bot.message_handler(commands=['access_help'])
    def help_cmd(m):
        if not _private(m):
            bot.send_message(m.chat.id, '🔒 Send /access_help in a private chat with the bot.')
            return
        bot.send_message(m.chat.id,
                         '🔐 Adult access guide\n\n'
                         '1. Send /verify_adult to request an independent review.\n'
                         '2. Use /access_status to check progress.\n'
                         '3. An authorized administrator must independently confirm 18+ eligibility '
                         'before approval; your request does not verify age.\n'
                         '4. Once approved, open /v8 or /v9 if those tools are enabled.\n\n'
                         'Do not send identity documents or dates of birth to this bot. '
                         'Access expires on the date shown in /access_status.')

    @bot.message_handler(commands=['access_health'])
    def health_cmd(m):
        if not _private(m) or not on('V93_ENABLED') or not is_admin(m.from_user.id):
            bot.send_message(m.chat.id, '🔒 This diagnostic requires an authorized administrator in a private chat.')
            return
        try:
            bot.send_message(m.chat.id, summary())
        except Exception:
            LOG.exception('V9.3 health command failed')
            bot.send_message(m.chat.id, '⚠️ Diagnostic currently unavailable. Review Render logs.')
