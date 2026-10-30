"""Offline authorization, SQL, installer and Telegram routing tests for V9.1."""
import os
import sys
import types
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import adult_requests_v91 as service
import v91_access_bot as handlers
from INSTALL_V91_MANUAL_ACCESS import edited, MAIN_ANCHOR, UI_ANCHOR, NAV_ANCHOR, run

class DbFake:
    def __init__(self, row=None):
        self.row = row
        self.inserted=[]
        self.rpc_calls=[]
    def table(self, name):
        assert name == service.REQUEST_TABLE
        return QueryFake(self)
    def rpc(self, name, params):
        self.rpc_calls.append((name,params))
        return types.SimpleNamespace(execute=lambda:types.SimpleNamespace(data='ok'))

class QueryFake:
    def __init__(self, db): self.db=db; self.is_upsert=False
    def select(self,*args,**kwargs): return self
    def eq(self,*args,**kwargs): return self
    def limit(self,*args,**kwargs): return self
    def order(self,*args,**kwargs): return self
    def upsert(self, data, on_conflict=None):
        assert on_conflict == 'user_id'
        self.is_upsert=True
        self.db.inserted.append(data)
        return self
    def execute(self):
        if self.is_upsert:return types.SimpleNamespace(data=self.db.inserted)
        return types.SimpleNamespace(data=([self.db.row] if self.db.row else []))

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.active = patch('study_access_v9.is_verified_adult',return_value=False)
        self.active.start()
        self.addCleanup(self.active.stop)
        self.admin = patch.dict(os.environ,{'V91_ADMIN_USER_IDS':'333,444'})
        self.admin.start();self.addCleanup(self.admin.stop)
    def test_new_request(self):
        db=DbFake()
        self.assertEqual(service.create_request(111,db),'created')
        self.assertEqual(db.inserted[0]['status'],'pending')
        self.assertEqual(db.inserted[0]['user_id'],111)
    def test_pending_idempotent(self):
        db=DbFake({'status':'pending','updated_at':datetime.now(timezone.utc).isoformat()})
        self.assertEqual(service.create_request(111,db),'pending')
        self.assertFalse(db.inserted)
    def test_recent_rejection_cooldown(self):
        db=DbFake({'status':'rejected','updated_at':datetime.now(timezone.utc).isoformat()})
        self.assertEqual(service.create_request(111,db),'cooldown')
    def test_old_rejection_reapply(self):
        db=DbFake({'status':'rejected','updated_at':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()})
        self.assertEqual(service.create_request(111,db),'created')
    def test_missing_date_fails_closed(self):
        db=DbFake({'status':'rejected','updated_at':None})
        self.assertEqual(service.create_request(111,db),'cooldown')
    def test_verified_does_not_create_request(self):
        with patch('study_access_v9.is_verified_adult',return_value=True):
            self.assertEqual(service.create_request(111,DbFake()),'verified')
    def test_non_admin_cannot_approve(self):
        with self.assertRaises(service.AccessError):service.review_request(111,222,'approve',db=DbFake())
    def test_admin_cannot_self_approve(self):
        with self.assertRaises(service.AccessError):service.review_request(333,333,'approve',db=DbFake())
    def test_days_bounded(self):
        for days in (0, 366, -2, 'bad'):
            with self.subTest(days=days):
                with self.assertRaises(service.AccessError):service.review_request(333,111,'approve',days,db=DbFake())
    def test_admin_record_review_rpc(self):
        db=DbFake()
        with patch('study_access_v9._cache',{111:(999,False)}):
            self.assertEqual(service.review_request(333,111,'approve',180,db),'approved')
            self.assertEqual(db.rpc_calls[0],('v91_review_adult_request',{
                'p_target_user_id':111,'p_admin_user_id':333,'p_action':'approve','p_valid_days':180}))
    def test_admin_revokes(self):
        db=DbFake();self.assertEqual(service.revoke_access(333,111,db),'revoked')
        self.assertEqual(db.rpc_calls[0][0],'v91_revoke_adult_access')
    def test_invalid_ids_rejected(self):
        for uid in (0, -1, '1; drop table',None,999999999999999999999):
            with self.subTest(uid=uid):
                with self.assertRaises(service.AccessError): service._id(uid)
    def test_admin_ids_separated(self):
        self.assertTrue(service.is_admin(333));self.assertFalse(service.is_admin(999))
    def test_status_unverified(self):
        self.assertEqual(service.request_status(111,DbFake())['status'],'not_requested')

class InstallerTests(unittest.TestCase):
    def test_anchors(self):
        for name, anchor in [('main.py',MAIN_ANCHOR),('ui_v57.py',UI_ANCHOR),('navigation.py',NAV_ANCHOR)]:
            with self.subTest(name=name):
                updated=edited(name,anchor)
                self.assertEqual(updated,edited(name,updated))
                self.assertIn('V9.1',updated)
    def test_refuses_unexpected_anchor(self):
        for n in ('main.py','ui_v57.py','navigation.py'):
            with self.subTest(n=n),self.assertRaises(ValueError):edited(n,'outdated template')
    def test_check_no_modify(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for n in ('main.py','ui_v57.py','navigation.py'):
                (root/n).write_text({'main.py':MAIN_ANCHOR,'ui_v57.py':UI_ANCHOR,'navigation.py':NAV_ANCHOR}[n],encoding='utf8')
            for n in ('adult_requests_v91.py','v91_access_bot.py','SQL_V91_MANUAL_ADULT_ACCESS.sql','TEST_V91_MANUAL_ACCESS.py'):
                (root/n).write_text('placeholder',encoding='utf8')
            before=(root/'main.py').read_text()
            run(root,False)
            self.assertEqual(before,(root/'main.py').read_text())
            run(root,True)
            self.assertIn('register_v91_access_handlers',(root/'main.py').read_text())
            run(root,True)

class BotFake:
    def __init__(self):self.handlers=[];self.sent=[]
    def message_handler(self,commands=None,func=None,**kwargs):
        def d(fn):self.handlers.append((commands,func,fn));return fn
        return d
    def send_message(self,chat_id,text):self.sent.append((chat_id,text))
    def dispatch(self,text,uid=111,private=True):
        message=types.SimpleNamespace(text=text,chat=types.SimpleNamespace(id=uid if private else -101,type='private' if private else 'group'),from_user=types.SimpleNamespace(id=uid))
        for commands,func,handler in self.handlers:
            if commands and text.split()[0].lstrip('/') in commands:
                handler(message);return
            if func and func(message):
                handler(message);return
        raise AssertionError('No matching handler for '+text)

class BotTests(unittest.TestCase):
    def setUp(self):
        self.bot=BotFake()
        self.fake_telebot=types.ModuleType('telebot')
        self.fake_handlers=types.ModuleType('telebot.handler_backends')
        self.fake_handlers.ContinueHandling=type('ContinueHandling',(),{})
        self.modules=patch.dict(sys.modules,{'telebot':self.fake_telebot,'telebot.handler_backends':self.fake_handlers})
        self.modules.start();self.addCleanup(self.modules.stop)
        self.env=patch.dict(os.environ,{'V91_ACCESS_REQUESTS_ENABLED':'true','V91_ADMIN_USER_IDS':'333'})
        self.env.start();self.addCleanup(self.env.stop)
        handlers.register_v91_access_handlers(self.bot)
    def test_user_can_request(self):
        with patch.object(handlers,'create_request',return_value='created') as c:
            self.bot.dispatch('/verify_adult')
            c.assert_called_once_with(111)
        self.assertIn('Request submitted',self.bot.sent[0][1])
    def test_no_id_proof_in_bot(self):
        self.bot.dispatch('/verify_adult',private=False)
        self.assertIn('privately',self.bot.sent[-1][1])
    def test_unauthorized_admin_denied(self):
        self.bot.dispatch('/access_requests',uid=111)
        self.assertIn('unavailable',self.bot.sent[-1][1])
    def test_approval_requires_exact_attestation(self):
        self.bot.dispatch('/access_approve 111 yes',uid=333)
        self.assertIn('verified_offline',self.bot.sent[-1][1])
    def test_self_approval_rejected(self):
        with patch.object(handlers,'review_request',side_effect=service.AccessError('self')):
            self.bot.dispatch('/access_approve 333 verified_offline 180',uid=333)
        self.assertIn('Invalid request',self.bot.sent[-1][1])
    def test_admin_can_approve(self):
        with patch.object(handlers,'review_request',return_value='approved') as a:
            self.bot.dispatch('/access_approve 111 verified_offline 180',uid=333)
            a.assert_called_once_with(333,'111','approve',180)
        self.assertIn('approved',self.bot.sent[0][1])
    def test_admin_revoke(self):
        with patch.object(handlers,'revoke_access',return_value='revoked'):
            self.bot.dispatch('/access_revoke 111',uid=333)
        self.assertIn('revoked',self.bot.sent[0][1])
    def test_disabled_request_denied(self):
        with patch.dict(os.environ,{'V91_ACCESS_REQUESTS_ENABLED':'false'}):
            self.bot.dispatch('/verify_adult')
        self.assertIn('not enabled',self.bot.sent[-1][1])
    def test_status_pending(self):
        with patch.object(handlers,'request_status',return_value={'status':'pending'}):
            self.bot.dispatch('/access_status')
        self.assertIn('pending',self.bot.sent[-1][1])

if __name__=='__main__':unittest.main()
