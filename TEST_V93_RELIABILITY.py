"""V9.3 offline regressions: permissions, diagnostics, RPC, installer idempotence.
Run: python -m unittest TEST_V93_RELIABILITY -q
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import v93_reliability_bot as diag
from INSTALL_V93_RELIABILITY import (edit_main, edit_requests, edit_v91_bot,
                                      changes, run, REGISTRATION_ANCHOR,
                                      RPC_ANCHOR, OLD_APPROVAL_ERROR)


class Query:
    def __init__(self, fail=False): self.fail = fail; self.called = []
    def select(self, fields): self.called.append(('select', fields)); return self
    def limit(self, n): self.called.append(('limit', n)); return self
    def execute(self):
        if self.fail: raise RuntimeError('private DB credential DO NOT SHOW')
        return types.SimpleNamespace(data=[])


class FakeDb:
    def __init__(self, fail_on=()):
        self.fail_on = set(fail_on)
        self.tables = []
        self.rpc_calls = []
        self.result = 'created'
        self.explode = False
    def table(self, name):
        self.tables.append(name)
        return Query(name in self.fail_on)
    def rpc(self, name, args):
        self.rpc_calls.append((name, args))
        if self.explode: raise RuntimeError('simulated database outage')
        return types.SimpleNamespace(execute=lambda: types.SimpleNamespace(data=self.result))


class FakeBot:
    def __init__(self): self.commands = {}; self.sent = []
    def message_handler(self, commands=None, **kwargs):
        def register(fn):
            for command in commands or []: self.commands[command] = fn
            return fn
        return register
    def send_message(self, chat, msg): self.sent.append((chat, msg))
    def invoke(self, command, uid=333, chat_type='private', chat=None):
        if chat is None: chat = uid if chat_type == 'private' else -100
        message = types.SimpleNamespace(
            from_user=types.SimpleNamespace(id=uid),
            chat=types.SimpleNamespace(type=chat_type, id=chat),
            text='/' + command,
        )
        self.commands[command](message)
        return self.sent[-1][1]


class DiagnosticsTests(unittest.TestCase):
    def test_all_reads_no_rows_returned(self):
        db=FakeDb()
        with patch.dict(os.environ, {'V92_EXPIRY_WORKER_ENABLED':'true'}):
            r=diag.diagnose(db=db)
        self.assertEqual(len(db.tables), 4)
        self.assertEqual(set(r.values()), {'reachable'})

    def test_worker_disabled_skips_optional_table(self):
        db=FakeDb()
        with patch.dict(os.environ, {'V92_EXPIRY_WORKER_ENABLED':'false'}):
            r=diag.diagnose(db=db)
        self.assertEqual(len(db.tables), 3)
        self.assertIn('not checked', r['Reminder queue'])

    def test_db_errors_are_sanitized(self):
        db=FakeDb({'study_verified_adults'})
        with patch.object(diag.LOG, 'exception'):
            output=diag.summary(db=db)
        self.assertIn('Verified registry: unavailable', output)
        self.assertNotIn('DO NOT SHOW', output)
        self.assertNotIn('KEY=', output)

    def test_invalid_mode_reported_and_never_inferred(self):
        with patch.dict(os.environ, {'STUDY_ACCESS_MODE':'unknown','V92_EXPIRY_WORKER_ENABLED':'false'}):
            self.assertIn('unsupported (access denied)', diag.summary(db=FakeDb()))

    def test_correct_mode_and_flags(self):
        with patch.dict(os.environ, {'STUDY_ACCESS_MODE':'verified_adults', 'V93_REQUEST_RPC_ENABLED':'true',
                                     'V8_ENABLED':'true','V9_ENABLED':'true',
                                     'V92_EXPIRY_WORKER_ENABLED':'false'}):
            data=diag.summary(db=FakeDb())
        for needle in ('verified_adults','V8: enabled','V9: enabled','Atomic requests: enabled'):
            self.assertIn(needle, data)


class TelegramTests(unittest.TestCase):
    def setUp(self):
        self.bot=FakeBot()
        self.env=patch.dict(os.environ, {'V91_ADMIN_USER_IDS':'333,444','V93_ENABLED':'true'})
        self.env.start(); self.addCleanup(self.env.stop)
        fake_access=types.ModuleType('adult_requests_v91')
        fake_access.is_admin=lambda uid: str(uid) in {'333', '444'}
        self.access_mock=patch.dict(sys.modules, {'adult_requests_v91': fake_access})
        self.access_mock.start(); self.addCleanup(self.access_mock.stop)
        diag.register_v93_reliability_handlers(self.bot)

    def test_nonadmin_denied(self):
        msg=self.bot.invoke('access_health',uid=22)
        self.assertIn('authorized administrator',msg)

    def test_admin_in_group_denied(self):
        msg=self.bot.invoke('access_health',uid=333,chat_type='group')
        self.assertIn('private chat',msg)

    def test_chat_sender_mismatch_denied(self):
        msg=self.bot.invoke('access_health',uid=333,chat=444)
        self.assertIn('authorized administrator',msg)

    def test_disabled_denied(self):
        with patch.dict(os.environ, {'V93_ENABLED':'false'}):
            msg=self.bot.invoke('access_health',uid=333)
        self.assertIn('authorized administrator',msg)

    def test_private_admin_gets_read_only_summary(self):
        with patch.object(diag,'summary',return_value='HEALTHY') as value:
            self.assertEqual(self.bot.invoke('access_health',uid=333),'HEALTHY')
        value.assert_called_once_with()

    def test_health_failure_no_exception_detail_to_user(self):
        with patch.object(diag,'summary',side_effect=RuntimeError('private credential')), \
             patch.object(diag.LOG,'exception'):
            response=self.bot.invoke('access_health',uid=333)
        self.assertIn('Diagnostic currently unavailable',response)
        self.assertNotIn('credential',response)

    def test_access_help_for_private_user(self):
        response=self.bot.invoke('access_help',uid=999)
        self.assertIn('/access_status',response)
        self.assertIn('independently',response)
        self.assertIn('Do not send identity documents',response)

    def test_access_help_rejects_group(self):
        self.assertIn('private chat',self.bot.invoke('access_help',uid=999,chat_type='group'))


class RequestRPCIntegrationTests(unittest.TestCase):
    """Execute just the patched real V9.1 module inside a fresh module namespace."""
    @classmethod
    def setUpClass(cls):
        p = Path(__file__).resolve().parent
        # V9.1 source is expected beside this file in the real bot. During
        # local V9.3 package testing, a fixture is created by the test runner.
        cls.v91 = p / 'adult_requests_v91.py'

    def test_rpc_called_only_when_enabled(self):
        if not self.v91.exists():
            self.skipTest('Integrated V9.1 source unavailable; run after copy into bot root')
        code=edit_requests(self.v91.read_text(encoding='utf-8'))
        module=types.ModuleType('v91_under_test')
        exec(compile(code,str(self.v91),'exec'),module.__dict__)
        db=FakeDb()
        with patch.dict(os.environ, {'V93_REQUEST_RPC_ENABLED':'true'}):
            self.assertEqual(module.create_request(123,db=db),'created')
            self.assertEqual(db.rpc_calls,[('v93_submit_adult_request',{'p_user_id':123})])
            db.result='pending'
            self.assertEqual(module.create_request(123,db=db),'pending')
            db.result='verified'
            self.assertEqual(module.create_request(123,db=db),'verified')
            db.result='cooldown'
            self.assertEqual(module.create_request(123,db=db),'cooldown')

    def test_rpc_fail_closed_no_old_upsert(self):
        if not self.v91.exists():
            self.skipTest('Integrated V9.1 source unavailable; run after copy into bot root')
        code=edit_requests(self.v91.read_text(encoding='utf-8'))
        module=types.ModuleType('v91_under_test')
        exec(compile(code,str(self.v91),'exec'),module.__dict__)
        db=FakeDb(); db.explode=True
        with patch.dict(os.environ,{'V93_REQUEST_RPC_ENABLED':'true'}):
            with self.assertRaises(RuntimeError): module.create_request(123,db=db)
        self.assertEqual(db.tables,[])

    def test_invalid_rpc_output_denied(self):
        if not self.v91.exists():
            self.skipTest('Integrated V9.1 source unavailable; run after copy into bot root')
        code=edit_requests(self.v91.read_text(encoding='utf-8'))
        module=types.ModuleType('v91_under_test')
        exec(compile(code,str(self.v91),'exec'),module.__dict__)
        db=FakeDb();db.result='approved'
        with patch.dict(os.environ,{'V93_REQUEST_RPC_ENABLED':'true'}):
            with self.assertRaises(module.AccessError):module.create_request(123,db=db)

    def test_invalid_user_id_rejected_before_rpc(self):
        if not self.v91.exists(): self.skipTest('V9.1 source unavailable')
        code=edit_requests(self.v91.read_text(encoding='utf-8'))
        module=types.ModuleType('v91_under_test')
        exec(compile(code,str(self.v91),'exec'),module.__dict__)
        db=FakeDb()
        with patch.dict(os.environ,{'V93_REQUEST_RPC_ENABLED':'true'}):
            with self.assertRaises(module.AccessError):module.create_request('1;SELECT',db=db)
        self.assertEqual(db.rpc_calls, [])


class InstallerTests(unittest.TestCase):
    def test_registration_idempotent(self):
        old=REGISTRATION_ANCHOR+'\nother\n'
        new=edit_main(old)
        self.assertIn('register_v93_reliability_handlers(bot)',new)
        self.assertEqual(edit_main(new),new)

    def test_requests_idempotent(self):
        original='def create_request(uid, db=None, now=None):\n'+RPC_ANCHOR+'    return 1\n'
        changed=edit_requests(original)
        self.assertIn('v93_submit_adult_request', changed)
        self.assertEqual(edit_requests(changed),changed)

    def test_errors_differentiated(self):
        original='x\n'+OLD_APPROVAL_ERROR+'y\n'
        changed=edit_v91_bot(original)
        self.assertIn('except AccessError as exc',changed)
        self.assertEqual(edit_v91_bot(changed),changed)

    def test_ambiguous_missing_anchor_refused(self):
        for bad in ('no registration',REGISTRATION_ANCHOR+REGISTRATION_ANCHOR):
            with self.assertRaises(ValueError):edit_main(bad)
        with self.assertRaises(ValueError):edit_requests('def create_request():\n    pass\n')
        with self.assertRaises(ValueError):edit_v91_bot('other errors')

    def test_check_apply_backups_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'main.py').write_text(REGISTRATION_ANCHOR+'\n')
            (root/'adult_requests_v91.py').write_text(
                'def create_request(uid, db=None, now=None):\n'+RPC_ANCHOR+'    return 1\n')
            (root/'v91_access_bot.py').write_text(OLD_APPROVAL_ERROR, encoding='utf-8')
            for name in ('v92_admin_bot.py','v93_reliability_bot.py',
                         'SQL_V93_ATOMIC_REQUESTS.sql','TEST_V93_RELIABILITY.py'):
                (root/name).write_text('fixture\n')
            snapshot={name:(root/name).read_bytes() for name in ('main.py','adult_requests_v91.py','v91_access_bot.py')}
            run(root,apply=False)
            self.assertEqual(snapshot,{name:(root/name).read_bytes() for name in snapshot})
            run(root,apply=True)
            self.assertEqual(changes(root),{})
            run(root,apply=True)
            self.assertEqual(len(list(root.glob('V93_BACKUP_*'))),1)
            backup=list(root.glob('V93_BACKUP_*'))[0]
            for name in snapshot:self.assertEqual((backup/name).read_bytes(),snapshot[name])

    def test_sql_grants_service_role_only(self):
        sql=(Path(__file__).resolve().parent/'SQL_V93_ATOMIC_REQUESTS.sql').read_text()
        self.assertIn('pg_catalog.pg_advisory_xact_lock',sql)
        self.assertIn('SECURITY DEFINER',sql)
        self.assertIn('REVOKE ALL ON FUNCTION',sql)
        self.assertIn('TO service_role',sql)
        self.assertNotIn('GRANT EXECUTE ON FUNCTION public.v93_submit_adult_request(BIGINT) TO PUBLIC',sql)


if __name__=='__main__':
    unittest.main()
