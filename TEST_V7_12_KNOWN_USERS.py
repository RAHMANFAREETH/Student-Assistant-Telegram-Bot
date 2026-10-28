"""V7.12 offline tests; no Telegram/Supabase or API traffic."""
from __future__ import annotations
import os
import unittest
from types import SimpleNamespace as O
from unittest.mock import patch

import broadcast_v710 as feature

ADMIN = 3001

class Response:
    def __init__(self, data): self.data = data

class FakeQuery:
    def __init__(self, db, table):
        self.db, self.name = db, table
        self.equals = {}
        self.members = {}
        self.cap = None
        self.payload = None
    def select(self, _): return self
    def order(self, *a, **k): return self
    def eq(self, field, value): self.equals[field] = value; return self
    def in_(self, field, values): self.members[field] = set(values); return self
    def limit(self, count): self.cap = count; return self
    def upsert(self, values, on_conflict=None): self.payload = values; return self
    def execute(self):
        if self.name in self.db.fail:
            raise RuntimeError('private database failure')
        if self.payload is not None:
            row = dict(self.payload)
            index = {r['user_id']: i for i, r in enumerate(self.db.tables.setdefault(self.name, []))}
            if row['user_id'] in index:
                self.db.tables[self.name][index[row['user_id']]].update(row)
            else: self.db.tables[self.name].append(row)
            return Response([row])
        rows = [dict(r) for r in self.db.tables.get(self.name, [])]
        for field, value in self.equals.items():
            rows = [r for r in rows if r.get(field) == value]
        for field, values in self.members.items():
            rows = [r for r in rows if r.get(field) in values]
        if self.cap is not None: rows = rows[:self.cap]
        return Response(rows)

class FakeDB:
    def __init__(self, users=None, prefs=None):
        self.tables = {
            'bot_known_users_v712': [{'user_id': u,'chat_id':u} for u in (users or [])],
            feature.TABLE: [{'user_id': k,'chat_id':k,'subscribed':v}
                            for k,v in (prefs or {}).items()],
        }
        self.fail = set()
    def table(self, name): return FakeQuery(self, name)

class FakeBot:
    def __init__(self): self.sent = []; self.handlers = []
    def send_message(self, chat_id, text, **kwargs): self.sent.append((chat_id,text))
    def message_handler(self, **kwargs):
        def decorator(fn): self.handlers.append((kwargs,fn)); return fn
        return decorator


def msg(uid=ADMIN, text='', private=True):
    return O(chat=O(id=uid if private else -2, type='private' if private else 'group'),
             from_user=O(id=uid, is_bot=False), text=text)

class KnownUsersTests(unittest.TestCase):
    def setUp(self):
        self.cfg=patch.dict(os.environ, {'AI_OPS_ADMIN_IDS':str(ADMIN)})
        self.cfg.start()
        self.addCleanup(self.cfg.stop)
        self.db=FakeDB(users=[ADMIN,4001,4002],prefs={4002:False})
        self.bot=FakeBot()
        self.s=feature.AnnouncementService(self.bot,self.db)
    def assertLast(self, part): self.assertIn(part, self.bot.sent[-1][1])

    def test_never_subscribed_are_included(self):
        self.assertEqual(self.s._known_user_rows(), {ADMIN:ADMIN,4001:4001})

    def test_explicit_unsubscribe_excluded(self):
        self.assertNotIn(4002,self.s._known_user_rows())
        self.assertFalse(self.s._known_user_eligible(4002))

    def test_unknown_user_not_eligible(self):
        self.assertFalse(self.s._known_user_eligible(99))

    def test_preferences_failure_aborts_preview(self):
        self.db.fail.add(feature.TABLE)
        self.s.preview_all(msg(text='/broadcastall Hello'))
        self.assertLast('Nothing was sent')
        self.assertFalse(self.s._pending)

    def test_known_users_failure_aborts_preview(self):
        self.db.fail.add('bot_known_users_v712')
        self.s.preview_all(msg(text='/broadcastall Hello'))
        self.assertLast('Nothing was sent')

    def test_limit_prevents_large_send(self):
        self.db=FakeDB(users=list(range(1,103)))
        self.s=feature.AnnouncementService(self.bot,self.db)
        self.s.preview_all(msg(text='/broadcastall Hello'))
        self.assertLast('Nothing was sent')

    def test_only_admin_can_preview(self):
        self.s.preview_all(msg(4001,'/broadcastall Hello'))
        self.assertLast('administrators only')
        self.assertFalse(self.s._pending)

    def test_group_cannot_preview(self):
        self.s.preview_all(msg(ADMIN,'/broadcastall Hello',private=False))
        self.assertLast('private bot chat')

    def test_inline_preview(self):
        self.s.preview_all(msg(text='/broadcastall Bot maintenance today'))
        self.assertLast('Recipients: 2')
        self.assertEqual(self.s._pending[ADMIN].audience,'all')

    def test_two_step_preview(self):
        self.s.preview_all(msg(text='/broadcastall'))
        self.assertLast('NEXT text message')
        self.assertTrue(self.s.pending_all_text(msg(text='Hi bot users!')))
        self.s.accept_all_text(msg(text='Hi bot users!'))
        self.assertLast('Recipients: 2')

    def test_general_command_not_swallowed(self):
        self.s.preview_all(msg(text='/broadcastall'))
        self.assertFalse(self.s.pending_all_text(msg(text='/help')))
        self.assertFalse(self.s.pending_all_text(msg(text='🏠 Main Menu')))

    def test_compose_cancel(self):
        self.s.preview_all(msg(text='/broadcastall'))
        self.s.cancel_all(msg(text='/broadcastallcancel'))
        self.assertFalse(self.s.pending_all_text(msg(text='test')))
        self.assertLast('Nothing was sent')

    def test_cancel_preview(self):
        self.s.preview_all(msg(text='/broadcastall Hello'))
        self.s.cancel_all(msg(text='/broadcastallcancel'))
        self.assertNotIn(ADMIN,self.s._pending)

    def test_standard_broadcast_does_not_confirm_all(self):
        self.s.preview_all(msg(text='/broadcastall Hello'))
        self.s.confirm(msg(text='/broadcastconfirm'))
        self.assertLast('No valid preview')
        self.assertEqual(self.s._pending[ADMIN].audience,'all')

    def test_confirm_expired(self):
        self.s._pending[ADMIN]=feature.Preview('Old',frozenset([4001]),0,'all')
        self.s.confirm_all(msg(text='/broadcastallconfirm'))
        self.assertLast('No valid known-users preview')

    def test_snapshot_excludes_new_users_after_preview(self):
        self.s.preview_all(msg(text='/broadcastall Important notice'))
        self.db.tables['bot_known_users_v712'].append({'user_id':5005,'chat_id':5005})
        class ImmediateThread:
            def __init__(self, target, args, **k): self.target=target; self.args=args
            def start(self): self.target(*self.args)
        with patch.object(feature.threading,'Thread',ImmediateThread), patch.object(feature.time,'sleep'):
            self.s.confirm_all(msg(text='/broadcastallconfirm'))
        recipients={c for c,t in self.bot.sent if t.startswith('Important notice')}
        self.assertEqual(recipients,{ADMIN,4001})
        self.assertNotIn(5005,recipients)

    def test_optout_after_preview_not_delivered(self):
        self.s.preview_all(msg(text='/broadcastall Important notice'))
        self.db.tables[feature.TABLE].append({'user_id':4001,'chat_id':4001,'subscribed':False})
        class ImmediateThread:
            def __init__(self, target, args, **k): self.target=target; self.args=args
            def start(self): self.target(*self.args)
        with patch.object(feature.threading,'Thread',ImmediateThread), patch.object(feature.time,'sleep'):
            self.s.confirm_all(msg(text='/broadcastallconfirm'))
        recipients={c for c,t in self.bot.sent if t.startswith('Important notice')}
        self.assertEqual(recipients,{ADMIN})

    def test_blocked_user_marked_opted_out(self):
        self.s.preview_all(msg(text='/broadcastall Notice'))
        oldsend=self.bot.send_message
        def send(cid, text, **kwargs):
            if cid==4001 and text.startswith('Notice'):
                e=Exception('fake block'); e.error_code=403; raise e
            return oldsend(cid,text,**kwargs)
        self.bot.send_message=send
        class ImmediateThread:
            def __init__(self,target,args,**k):self.target=target; self.args=args
            def start(self):self.target(*self.args)
        with patch.object(feature.threading,'Thread',ImmediateThread),patch.object(feature.time,'sleep'):
            self.s.confirm_all(msg(text='/broadcastallconfirm'))
        self.assertFalse(self.s._known_user_eligible(4001))

    def test_track_only_private_message(self):
        update=O(message=msg(4321,'/start'),callback_query=None)
        self.assertTrue(feature.track_known_private_user(update,self.db))
        self.assertIn(4321,[r['user_id'] for r in self.db.tables['bot_known_users_v712']])

    def test_tracking_group_not_allowed(self):
        update=O(message=msg(4321,'hello',private=False),callback_query=None)
        self.assertFalse(feature.track_known_private_user(update,self.db))

    def test_track_private_callback(self):
        cb=O(from_user=O(id=7345,is_bot=False),message=O(chat=O(type='private',id=7345)))
        self.assertTrue(feature.track_known_private_user(O(message=None,callback_query=cb),self.db))

    def test_tracking_does_not_store_message_text(self):
        update=O(message=msg(4321,'secret note'),callback_query=None)
        feature.track_known_private_user(update,self.db)
        self.assertNotIn('secret note',repr(self.db.tables))

    def test_tracking_errors_do_not_block_handler(self):
        self.db.fail.add('bot_known_users_v712')
        self.assertFalse(feature.track_known_private_user(O(message=msg(4321,'hello'),callback_query=None),self.db))

    def test_duplicate_track_preserves_one_record(self):
        update=O(message=msg(4321,'hi'),callback_query=None)
        feature.track_known_private_user(update,self.db)
        feature.track_known_private_user(update,self.db)
        self.assertEqual(sum(r['user_id']==4321 for r in self.db.tables['bot_known_users_v712']),1)

    def test_registers_both_existing_and_new_commands(self):
        service=feature.register_broadcast_handlers(self.bot,self.db)
        feature.register_known_broadcast_handlers(self.bot,service)
        registered=set()
        for kw,fn in self.bot.handlers: registered.update(kw.get('commands',[]))
        for name in ('broadcast','subscribe','broadcastall',
                     'broadcastallconfirm','broadcastallcancel','broadcastallusers'):
            self.assertIn(name, registered)

    def test_direct_nonadmin_denied(self):
        self.s.direct(msg(4001,'/messageuser 4001 Hello'))
        self.assertLast('administrators only')

if __name__=='__main__': unittest.main()
