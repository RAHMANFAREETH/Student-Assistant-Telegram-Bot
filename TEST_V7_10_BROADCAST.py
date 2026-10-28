"""Offline tests: no Telegram, Supabase, or provider requests."""
import os
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from broadcast_v710 import (
    AnnouncementService, MAX_RECIPIENTS, code_and_wait, is_private,
    register_broadcast_handlers,
)


class Result:
    def __init__(self, data=None):
        self.data = [] if data is None else data


class Query:
    def __init__(self, db):
        self.db = db
        self.filters = {}
        self.capacity = MAX_RECIPIENTS + 1
        self.payload = None

    def select(self, *a, **kw): return self
    def eq(self, key, value):
        self.filters[key] = value
        return self
    def limit(self, limit):
        self.capacity = limit
        return self
    def upsert(self, payload, **kwargs):
        self.payload = payload
        return self
    def execute(self):
        if self.db.fail:
            raise RuntimeError("Pretend DB error containing a secret")
        if self.payload is not None:
            row = self.payload
            self.db.users[row['user_id']] = dict(row)
            return Result([row])
        rows = list(self.db.users.values())
        for key, value in self.filters.items():
            rows = [row for row in rows if row.get(key) == value]
        return Result(rows[:self.capacity])


class DB:
    def __init__(self):
        self.users = {}
        self.fail = False

    def table(self, name):
        if name != 'bot_broadcast_subscribers':
            raise AssertionError('Unknown table')
        return Query(self)


class FakeBot:
    def __init__(self):
        self.messages = []
        self.handlers = {}
        self.fail_users = set()
        self.lock = threading.Lock()

    def send_message(self, chat_id, text, **kwargs):
        if chat_id in self.fail_users:
            exc = RuntimeError('forbidden')
            exc.error_code = 403
            raise exc
        with self.lock:
            self.messages.append((chat_id, text))

    def message_handler(self, commands):
        def decorator(fn):
            for cmd in commands:
                self.handlers[cmd] = fn
            return fn
        return decorator

    def last(self, chat_id):
        with self.lock:
            return [m[1] for m in self.messages if m[0] == chat_id][-1]


def message(uid=100, text='', private=True):
    return SimpleNamespace(text=text, from_user=SimpleNamespace(id=uid),
        chat=SimpleNamespace(id=uid if private else -1000,
                             type='private' if private else 'group'))


class BroadcastTests(unittest.TestCase):
    def setUp(self):
        self.bot, self.db = FakeBot(), DB()
        self.s = AnnouncementService(self.bot, self.db)
        self.env = patch.dict(os.environ, {'AI_OPS_ADMIN_IDS': '100'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def subscribe(self, uid):
        self.s.subscription(message(uid), True)

    def test_only_private_user_can_subscribe(self):
        self.s.subscription(message(200, private=False), True)
        self.assertFalse(self.db.users)
        self.subscribe(200)
        self.assertTrue(self.db.users[200]['subscribed'])
        self.assertEqual(self.db.users[200]['chat_id'], 200)

    def test_unsubscribe_is_saved(self):
        self.subscribe(200)
        self.s.subscription(message(200), False)
        self.assertFalse(self.db.users[200]['subscribed'])
        self.s.announcements(message(200))
        self.assertIn('OFF', self.bot.last(200))

    def test_subscription_error_does_not_claim_success(self):
        self.db.fail = True
        self.s.subscription(message(200), True)
        self.assertNotIn('subscribed to', self.bot.last(200))
        self.assertNotIn('Pretend DB error', self.bot.last(200))

    def test_nonadmin_cannot_start_broadcast(self):
        self.subscribe(200)
        self.s.preview(message(201, '/broadcast hello'))
        self.assertIn('administrators', self.bot.last(201))
        self.assertEqual({}, self.s._pending)

    def test_admin_cannot_command_from_group(self):
        self.s.preview(message(100, '/broadcast hello', private=False))
        self.assertFalse(self.s._pending)

    def test_no_admin_config_is_default_deny(self):
        os.environ['AI_OPS_ADMIN_IDS'] = ''
        self.s.preview(message(100, '/broadcast hello'))
        self.assertFalse(self.s._pending)

    def test_preview_requires_subscribers_and_text(self):
        self.s.preview(message(100, '/broadcast hello'))
        self.assertIn('No subscribers', self.bot.last(100))
        self.subscribe(200)
        self.s.preview(message(100, '/broadcast'))
        self.assertIn('Usage:', self.bot.last(100))
        self.s.preview(message(100, '/broadcast hi'))
        self.assertIn('PREVIEW', self.bot.last(100))
        self.assertFalse(any(msg == 'hi' for cid, msg in self.bot.messages if cid == 200))

    def test_cancel_prevents_delivery(self):
        self.subscribe(200)
        self.s.preview(message(100, '/broadcast hello'))
        self.s.cancel(message(100))
        self.assertFalse(self.s._pending)
        self.s.confirm(message(100))
        self.assertIn('No valid preview', self.bot.last(100))

    def test_preview_expiry(self):
        self.subscribe(200)
        self.s.preview(message(100, '/broadcast hello'))
        with self.s._lock:
            p = self.s._pending[100]
            self.s._pending[100] = type(p)(p.text, p.user_ids, time.monotonic() - 601)
        self.s.confirm(message(100))
        self.assertIn('No valid preview', self.bot.last(100))

    def test_opt_out_after_preview_not_delivered(self):
        self.subscribe(200)
        self.subscribe(300)
        self.s.preview(message(100, '/broadcast test-batch'))
        self.s.subscription(message(200), False)
        with patch('broadcast_v710.threading.Thread') as mock_thread:
            self.s.confirm(message(100))
            args = mock_thread.call_args.kwargs['args']
            self.assertEqual([300], args[2])
        self.assertNotIn(200, args[2])

    def test_new_subscriber_after_preview_not_delivered(self):
        self.subscribe(200)
        self.s.preview(message(100, '/broadcast test-batch'))
        self.subscribe(300)
        with patch('broadcast_v710.threading.Thread') as mock_thread:
            self.s.confirm(message(100))
            args = mock_thread.call_args.kwargs['args']
            self.assertEqual([200], args[2])

    def test_user_receives_plain_text_no_formatting(self):
        self.subscribe(200)
        with patch('broadcast_v710.time.sleep'):
            self.s._send_batch(100, '<b>hello</b>', [200])
        self.assertEqual('<b>hello</b>', self.bot.last(200))
        self.assertIn('Sent: 1', self.bot.last(100))

    def test_blocked_user_automatically_unsubscribed(self):
        self.subscribe(200)
        self.bot.fail_users.add(200)
        with patch('broadcast_v710.time.sleep'):
            self.s._send_batch(100, 'hello', [200])
        self.assertFalse(self.db.users[200]['subscribed'])
        self.assertIn('failed: 1', self.bot.last(100))

    def test_interrupted_db_does_not_deliver_to_unverified_user(self):
        self.subscribe(200)
        self.db.fail = True
        with patch('broadcast_v710.time.sleep'):
            self.s._send_batch(100, 'hello', [200])
        self.assertNotIn((200, 'hello'), self.bot.messages)

    def test_direct_message_to_subscribed_only(self):
        self.s.direct(message(100, '/messageuser 200 hello'))
        self.assertIn('not opted in', self.bot.last(100))
        self.subscribe(200)
        self.s.direct(message(100, '/messageuser 200 Hello user'))
        self.assertEqual('Hello user', self.bot.last(200))

    def test_direct_message_by_nonadmin_denied(self):
        self.subscribe(200)
        self.s.direct(message(300, '/messageuser 200 bad'))
        self.assertFalse(any(msg == 'bad' for _, msg in self.bot.messages))

    def test_batch_above_100_rejected(self):
        for i in range(200, 301):
            self.db.users[i] = dict(user_id=i, chat_id=i, subscribed=True)
        self.s.preview(message(100, '/broadcast hello'))
        self.assertIn('limit', self.bot.last(100))

    def test_only_one_active_broadcast(self):
        self.subscribe(200)
        self.s.preview(message(100, '/broadcast first'))
        self.s._active = True
        self.s.confirm(message(100))
        self.assertIn('already running', self.bot.last(100))
        self.assertIn(100, self.s._pending)

    def test_registers_each_command(self):
        register_broadcast_handlers(self.bot, self.db)
        self.assertEqual({'subscribe', 'unsubscribe', 'announcements', 'broadcastusers',
                          'broadcast', 'broadcastconfirm', 'broadcastcancel',
                          'broadcaststatus', 'messageuser'}, set(self.bot.handlers))

    def test_is_private_rejects_wrong_chat(self):
        m = message(200)
        m.chat.id = 201
        self.assertFalse(is_private(m))

    def test_structured_retry_after_capped(self):
        exc = RuntimeError('')
        exc.error_code = 429
        exc.result_json = {'parameters': {'retry_after': 999}}
        self.assertEqual((429, 15), code_and_wait(exc))


if __name__ == '__main__':
    unittest.main()
