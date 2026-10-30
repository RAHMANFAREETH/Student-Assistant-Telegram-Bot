"""V9.2 offline tests: Telegram permissions, callback safety, DB, notifier.
Run: python -m unittest TEST_V92_SMART_ADMIN -q
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import v92_admin_service as service
import v92_admin_bot as ui
import v92_expiry_worker as worker
from INSTALL_V92_SMART_ADMIN import ANCHOR, edited, run


class FakeQuery:
    def __init__(self, db): self.db = db; self.calls = []
    def __getattr__(self, name):
        if name in ('select', 'eq', 'gt', 'order', 'range', 'limit'):
            def next_(*args, **kwargs):
                self.calls.append((name, args, kwargs))
                return self
            return next_
        raise AttributeError(name)
    def execute(self): return types.SimpleNamespace(data=self.db.rows)


class FakeDb:
    def __init__(self, rows=None, rpc_data=None):
        self.rows = rows or []
        self.rpc_data = rpc_data or []
        self.table_calls = []
        self.rpc_calls = []
        self.last_query = None
    def table(self, name):
        self.table_calls.append(name)
        self.last_query = FakeQuery(self)
        return self.last_query
    def rpc(self, name, args):
        self.rpc_calls.append((name,args))
        return types.SimpleNamespace(execute=lambda:types.SimpleNamespace(data=self.rpc_data))


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'V91_ADMIN_USER_IDS': '333,444'})
        self.env.start();self.addCleanup(self.env.stop)

    def test_nonadmin_list_denied(self):
        for fn in (service.list_pending, service.list_verified, service.list_audit):
            with self.subTest(fn=fn), self.assertRaises(service.AccessError):
                fn(999,db=FakeDb())

    def test_pending_read_scope_and_bounds(self):
        db = FakeDb([{'user_id':111,'status':'pending'}])
        service.list_pending(333,db=db,offset=9000,size=999)
        self.assertEqual(db.table_calls,['study_adult_access_requests'])
        self.assertIn(('eq',('status','pending'),{}),db.last_query.calls)
        self.assertIn(('range',(1000,1009),{}),db.last_query.calls)

    def test_verified_only_active(self):
        db=FakeDb()
        service.list_verified(333,db=db)
        self.assertEqual(db.table_calls,['study_verified_adults'])
        self.assertTrue(any(x[0]=='gt' and x[1][0]=='valid_until' for x in db.last_query.calls))

    def test_audit_is_read_only(self):
        db=FakeDb([{'id':1}]); self.assertEqual(service.list_audit(333,db=db)[0]['id'],1)
        self.assertEqual(db.table_calls,['study_adult_access_audit'])
        self.assertEqual(db.rpc_calls,[])

    def test_get_request_rejects_id_injection(self):
        with self.assertRaises(service.AccessError):
            service.get_request(333,'111; DROP TABLE')

    def test_claim_rpc_bound(self):
        db=FakeDb(rpc_data=[{'id':1}])
        self.assertEqual(service.claim_expiry_batch(db=db,batch_size=100),[{'id':1}])
        self.assertEqual(db.rpc_calls[0],('v92_claim_expiry_notifications',{'p_limit':50}))

    def test_mark_rpc_has_claim_token(self):
        db=FakeDb(rpc_data=True)
        service.mark_expiry_sent(7,'a-token',db=db)
        self.assertEqual(db.rpc_calls[0],('v92_mark_expiry_notification_sent',
                                          {'p_event_id':7,'p_claim_token':'a-token'}))

    def test_notifier_delivers_and_marks(self):
        events=[{'id':1,'user_id':111,'milestone':'7d','valid_until':'2027-01-10T12:00:00+00:00','claim_token':'token1'},
                {'id':2,'user_id':112,'milestone':'expired','valid_until':'2027-01-01T12:00:00+00:00','claim_token':'token2'}]
        db=FakeDb(rpc_data=events)
        bot=types.SimpleNamespace(send_message=MagicMock())
        with patch.object(service,'mark_expiry_sent',return_value=True) as ack:
            result=service.process_expiry_batch(bot,db=db)
        self.assertEqual(result,{'claimed':2,'sent':2})
        self.assertEqual(bot.send_message.call_count,2)
        self.assertEqual(ack.call_count,2)

    def test_notifier_failure_does_not_ack(self):
        event={'id':1,'user_id':111,'milestone':'1d','valid_until':'2027-01-02T12:00:00Z','claim_token':'x'}
        db=FakeDb(rpc_data=[event])
        bot=types.SimpleNamespace(send_message=MagicMock(side_effect=RuntimeError('blocked')))
        with patch.object(service,'mark_expiry_sent') as ack,patch.object(service.LOG,'exception'):
            outcome=service.process_expiry_batch(bot,db=db)
        self.assertEqual(outcome['sent'],0)
        ack.assert_not_called()

    def test_notifier_unknown_milestone_refused(self):
        event={'id':1,'user_id':111,'milestone':'unsafe','valid_until':'x','claim_token':'x'}
        with patch.object(service.LOG,'exception'),patch.object(service,'mark_expiry_sent') as ack:
            result=service.process_expiry_batch(types.SimpleNamespace(send_message=MagicMock()),db=FakeDb(rpc_data=[event]))
        self.assertEqual(result['sent'],0)
        ack.assert_not_called()


class InstallerTests(unittest.TestCase):
    def test_idempotent(self):
        s='begin\n'+ANCHOR+'\nend\n'
        once=edited(s)
        self.assertIn('register_v92_admin_handlers(bot)',once)
        self.assertEqual(edited(once),once)

    def test_missing_or_double_anchor_refused(self):
        for s in ('bad',ANCHOR+ANCHOR):
            with self.subTest(s=s),self.assertRaises(ValueError): edited(s)

    def test_check_and_apply_safe(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'main.py').write_text(ANCHOR+'\n')
            for name in ('v91_access_bot.py','adult_requests_v91.py',
                         'v92_admin_bot.py','v92_admin_service.py','v92_expiry_worker.py',
                         'SQL_V92_SMART_ADMIN.sql','TEST_V92_SMART_ADMIN.py'):
                (root/name).write_text('stub')
            run(root,apply=False)
            self.assertEqual((root/'main.py').read_text(),ANCHOR+'\n')
            run(root,apply=True)
            self.assertIn('register_v92_admin_handlers(bot)',(root/'main.py').read_text())
            run(root,apply=True)
            self.assertEqual(len(list(root.glob('V92_BACKUP_*'))),1)


class Button:
    def __init__(self,text,callback_data):
        self.text=text
        self.callback_data=callback_data

class Markup:
    def __init__(self, row_width=2): self.rows=[]
    def row(self,*items): self.rows.append(items)

class Bot:
    def __init__(self):
        self.commands=[];self.callbacks=[];self.rendered=[];self.sent=[]
        self.answers=[]; self.msg_id=10
    def message_handler(self,commands=None,**kw):
        def register(fn):self.commands.append((commands,fn));return fn
        return register
    def callback_query_handler(self,func=None,**kw):
        def register(fn):self.callbacks.append((func,fn));return fn
        return register
    def send_message(self,chat,text,reply_markup=None):
        self.rendered.append((chat,text,reply_markup))
        self.sent.append((chat,text))
    def edit_message_text(self,text,chat_id,message_id,reply_markup=None):
        self.rendered.append((chat_id,text,reply_markup))
    def answer_callback_query(self,id):self.answers.append(id)
    def command(self,uid=333,private=True):
        m=types.SimpleNamespace(
            chat=types.SimpleNamespace(type='private' if private else 'group',id=uid if private else -100),
            from_user=types.SimpleNamespace(id=uid))
        self.commands[0][1](m)
    def click(self,label,uid=333,call_data=None):
        if call_data is None:
            markup=self.rendered[-1][2]
            matches=[b.callback_data for row in markup.rows for b in row if b.text==label]
            assert matches, f'button {label!r} missing among {[b.text for r in markup.rows for b in r]}'
            call_data=matches[0]
        m=types.SimpleNamespace(chat=types.SimpleNamespace(type='private',id=333),
                                from_user=types.SimpleNamespace(id=99999),message_id=self.msg_id)
        call=types.SimpleNamespace(id='cb-1',from_user=types.SimpleNamespace(id=uid),
                                   message=m,data=call_data)
        self.callbacks[0][1](call)
        return call_data

class TelegramTests(unittest.TestCase):
    def setUp(self):
        ui._SESSIONS.clear()
        self.bot=Bot()
        self.mod=types.ModuleType('telebot')
        self.mod.types=types.SimpleNamespace(InlineKeyboardMarkup=Markup,InlineKeyboardButton=Button)
        self.pmod=patch.dict(sys.modules, {'telebot':self.mod})
        self.pmod.start();self.addCleanup(self.pmod.stop)
        self.env=patch.dict(os.environ,{'V92_ADMIN_ENABLED':'true','V91_ADMIN_USER_IDS':'333,444',
                                        'V92_EXPIRY_WORKER_ENABLED':'false'})
        self.env.start();self.addCleanup(self.env.stop)
        self.worker=patch.object(ui,'start_worker_if_enabled',return_value=False)
        self.worker.start();self.addCleanup(self.worker.stop)
        ui.register_v92_admin_handlers(self.bot)

    def test_no_access_for_non_admin(self):
        self.bot.command(uid=999)
        self.assertIn('authorized administrator',self.bot.sent[-1][1])

    def test_reject_group_admin(self):
        self.bot.command(uid=333,private=False)
        self.assertIn('private chat',self.bot.sent[-1][1])

    def test_off_flag_fails_closed(self):
        with patch.dict(os.environ, {'V92_ADMIN_ENABLED':'false'}):
            self.bot.command(uid=333)
        self.assertIn('requires',self.bot.sent[-1][1])

    def test_dashboard_shows_menus(self):
        self.bot.command()
        markup=self.bot.rendered[-1][2]
        self.assertIn('📋 Pending requests',[b.text for row in markup.rows for b in row])

    def test_callback_from_nonadmin_disallowed(self):
        self.bot.command()
        token=next(b.callback_data for row in self.bot.rendered[-1][2].rows for b in row)
        count=len(self.bot.rendered)
        self.bot.click('',uid=999,call_data=token)
        self.assertEqual(len(self.bot.rendered),count)
        self.assertIn(token[4:],ui._SESSIONS)

    def test_callback_token_single_use(self):
        self.bot.command()
        with patch.object(ui,'list_pending',return_value=[]):
            data=self.bot.click('📋 Pending requests')
            self.bot.click('any',call_data=data)
        self.assertIn('expired or was already used',self.bot.sent[-1][1])

    def test_callback_bound_to_issuer(self):
        self.bot.command()
        token=next(b.callback_data for row in self.bot.rendered[-1][2].rows for b in row)
        self.bot.click('',uid=444,call_data=token)
        self.assertIn(token[4:],ui._SESSIONS)
        self.assertEqual(len(self.bot.rendered),1)  # foreign chat cannot use token

    def test_expired_token(self):
        self.bot.command()
        token=next(b.callback_data for row in self.bot.rendered[-1][2].rows for b in row)
        with ui._SESSION_LOCK:
            ui._SESSIONS[token[4:]]['expires']=0
        self.bot.click('',call_data=token)
        self.assertIn('expired',self.bot.sent[-1][1])

    def test_full_approval_with_attestation_and_confirmation(self):
        self.bot.command()
        with (patch.object(ui,'list_pending',return_value=[{'user_id':111,'created_at':'2026-10-31T00:00:00Z'}]),
              patch.object(ui,'get_request',return_value={'user_id':111,'status':'pending','created_at':'2026-10-31T00:00:00Z'}),
              patch.object(ui,'review_request',return_value='approved') as approve):
            self.bot.click('📋 Pending requests')
            self.bot.click('👤 111')
            self.bot.click('✅ Review for approval')
            self.assertIn('independently completed',self.bot.rendered[-1][1])
            self.bot.click('✅ Yes, independently checked 18+')
            self.bot.click('180 days')
            self.assertIn('FINAL CONFIRMATION',self.bot.rendered[-1][1])
            self.bot.click('✅ Confirm approval')
        approve.assert_called_once_with(333,111,'approve',days=180)
        self.assertTrue(any('approved for 180' in msg for _,msg,_ in self.bot.rendered))

    def test_self_approval_blocked_even_if_token_manually_issued(self):
        self.bot.command()
        token=ui._issue(333,'approve',target=333,days=180)
        with patch.object(ui,'review_request') as approve:
            self.bot.click('any',call_data=token)
        approve.assert_not_called()

    def test_reject_requires_confirmation(self):
        self.bot.command()
        with (patch.object(ui,'list_pending',return_value=[{'user_id':111,'created_at':'x'}]),
              patch.object(ui,'get_request',return_value={'status':'pending','created_at':'x'}),
              patch.object(ui,'review_request',return_value='rejected') as review):
            self.bot.click('📋 Pending requests')
            self.bot.click('👤 111')
            self.bot.click('❌ Reject request')
            review.assert_not_called()
            self.bot.click('❌ Confirm rejection')
        review.assert_called_once_with(333,111,'reject')

    def test_revoke_requires_confirmation(self):
        self.bot.command()
        with (patch.object(ui,'list_verified',return_value=[{'user_id':111,'valid_until':'2027-05-01T00:00:00Z'}]),
              patch.object(ui,'get_verified',return_value={'status':'verified','valid_until':'2027-05-01T00:00:00Z','verification_method':'manual_review'}),
              patch.object(ui,'revoke_access',return_value='revoked') as revoker):
            self.bot.click('✅ Active verified')
            self.bot.click('👤 111')
            self.bot.click('🔒 Revoke access')
            revoker.assert_not_called()
            self.bot.click('🔒 Confirm revoke')
        revoker.assert_called_once_with(333,111)

    def test_audit_action_only_admin(self):
        self.bot.command()
        with patch.object(ui,'list_audit',return_value=[{'action':'approved','user_id':111,'admin_id':333,'created_at':'x'}]):
            self.bot.click('📜 Audit history')
        self.assertIn('approved user 111',self.bot.rendered[-1][1])

    def test_expiry_batch_requires_confirmation(self):
        self.bot.command()
        with patch.object(ui,'process_expiry_batch',return_value={'claimed':1,'sent':1}) as deliver:
            self.bot.click('🔔 Run expiry reminders')
            deliver.assert_not_called()
            self.bot.click('🔔 Run once')
        deliver.assert_called_once_with(self.bot)

    def test_telegram_callback_limit(self):
        data=ui._issue(333,'approve',target=111,days=365)
        self.assertLessEqual(len(data.encode()),64)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        worker._STARTED = False
    def tearDown(self):
        worker._STARTED = False

    def test_worker_disabled_by_default(self):
        with patch.dict(os.environ, {'V92_ADMIN_ENABLED':'false','V92_EXPIRY_WORKER_ENABLED':'true'}):
            self.assertFalse(worker.start_worker_if_enabled(MagicMock()))

    def test_worker_starts_only_once(self):
        with (patch.dict(os.environ,{'V92_ADMIN_ENABLED':'true','V92_EXPIRY_WORKER_ENABLED':'true'}),
              patch.object(worker.threading,'Thread') as thread):
            self.assertTrue(worker.start_worker_if_enabled(MagicMock()))
            self.assertFalse(worker.start_worker_if_enabled(MagicMock()))
            thread.assert_called_once()

    def test_worker_retry(self):
        stop=MagicMock()
        stop.is_set.side_effect=[False,False,True]
        with patch.object(worker,'process_expiry_batch',side_effect=[Exception('timeout'),{'claimed':0,'sent':0}]) as fun,patch.object(worker.LOG,'exception'):
            worker.run_worker(MagicMock(),stop=stop,interval_seconds=0)
        self.assertEqual(fun.call_count,2)


class SqlTests(unittest.TestCase):
    def test_additive_and_protected(self):
        sql=Path(__file__).with_name('SQL_V92_SMART_ADMIN.sql').read_text().upper()
        self.assertIn('ENABLE ROW LEVEL SECURITY',sql)
        self.assertIn('GRANT EXECUTE',sql)
        self.assertIn('TO SERVICE_ROLE',sql)
        self.assertIn('ON CONFLICT',sql)
        self.assertIn('P_CLAIM_TOKEN',sql)
        self.assertNotIn('DROP TABLE',sql)
        self.assertNotIn('TO ANON;',sql)
        self.assertNotIn('TO AUTHENTICATED;',sql)


if __name__ == '__main__': unittest.main()
