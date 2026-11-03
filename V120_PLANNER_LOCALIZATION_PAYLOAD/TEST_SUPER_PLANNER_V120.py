"""Focused backend contract tests for the V12 read-only academic planner."""
from __future__ import annotations
import os
import sys
import types
import unittest
from unittest.mock import patch
from TEST_SUPER_MINIAPP_V120 import module, FakeApp

class TestPlannerV120(unittest.TestCase):
    def setUp(self):
        self.app=FakeApp()
        module.register_super_miniapp(self.app)
        self.view=self.app.view_functions['v120_super_planner']

    def test_read_only_queries_use_signed_account_not_request_id(self):
        seen=[]
        assignments=types.ModuleType('assignments')
        exams=types.ModuleType('exam_planner')
        def get_a(uid,status,limit):
            seen.append(('assign',uid,status,limit))
            return [{'title':'Due paper','due_at':'2026-11-20T10:30:00+00:00','status':'pending','priority':'high','user_id':999,'private_note':'secret'}]
        def get_e(uid,upcoming_only,limit):
            seen.append(('exam',uid,upcoming_only,limit))
            return [{'title':'Math','exam_at':'2026-11-21T10:00:00+00:00','location':'Hall A','chat_id':123,'notes':'secret'}]
        assignments.get_assignments=get_a
        exams.get_exams=get_e
        with patch.dict(sys.modules,{'assignments':assignments,'exam_planner':exams}):
            data=module.read_planner_overview(44)
        self.assertEqual(seen,[('assign',44,'pending',30),('exam',44,True,30)])
        self.assertEqual(data['assignments'][0],{'title':'Due paper','due_at':'2026-11-20T10:30:00+00:00','status':'pending','priority':'high'})
        self.assertEqual(data['exams'][0],{'title':'Math','exam_at':'2026-11-21T10:00:00+00:00','location':'Hall A'})
        self.assertTrue(data['read_only'])
        self.assertNotIn('user_id',repr(data))
        self.assertNotIn('chat_id',repr(data))

    def call(self,raw,uid=44,permission=False,overview=None):
        request=types.SimpleNamespace(headers={'X-Telegram-Init-Data':raw})
        with patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':'true'}):
            with patch.object(module,'request',request),patch.object(module,'jsonify',side_effect=lambda val:val):
                with patch.object(module,'verify_super_session',side_effect=(PermissionError('age') if permission else ValueError('bad token') if uid is None else None),return_value=uid) as auth:
                    with patch.object(module,'read_planner_overview',return_value=overview or {'assignments':[],'exams':[],'read_only':True}) as db:
                        result=self.view()
        return result,auth,db

    def test_authorized_response(self):
        response,auth,db=self.call('signed',overview={'assignments':[{'title':'A'}],'exams':[],'read_only':True})
        self.assertTrue(response['ok'])
        self.assertEqual(response['assignments'][0]['title'],'A')
        auth.assert_called_once_with('signed')
        db.assert_called_once_with(44)

    def test_invalid_login_rejected_before_database(self):
        result,auth,db=self.call('bad',uid=None)
        self.assertEqual(result[1],401)
        db.assert_not_called()
        self.assertNotIn('bad token',repr(result))

    def test_18_plus_gate_before_database(self):
        result,auth,db=self.call('signed',permission=True)
        self.assertEqual(result[1],403)
        db.assert_not_called()

    def test_disabled_returns_404_without_database(self):
        with patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':'false'}),patch.object(module,'abort',side_effect=RuntimeError('404')) as aborter:
            with self.assertRaisesRegex(RuntimeError,'404'):self.view()
        aborter.assert_called_once_with(404)

    def test_database_failure_returns_generic_503(self):
        request=types.SimpleNamespace(headers={'X-Telegram-Init-Data':'signed'})
        self.app.logger=types.SimpleNamespace(warning=lambda msg:None)
        with patch.dict(os.environ,{'SUPER_MINIAPP_V120_ENABLED':'true'}),patch.object(module,'request',request),patch.object(module,'jsonify',side_effect=lambda val:val),patch.object(module,'verify_super_session',return_value=44),patch.object(module,'read_planner_overview',side_effect=RuntimeError('SUPABASE_SECRET_KEY=secret')):
            result=self.view()
        self.assertEqual(result[1],503)
        self.assertNotIn('secret',repr(result))

    def test_overview_ignores_bad_row_objects(self):
        assignments=types.ModuleType('assignments');exams=types.ModuleType('exam_planner')
        assignments.get_assignments=lambda *a,**k:[None,{}, {'title':'X'*300}]
        exams.get_exams=lambda *a,**k:[42, {'title':'Y'}]
        with patch.dict(sys.modules,{'assignments':assignments,'exam_planner':exams}):data=module.read_planner_overview(44)
        self.assertEqual(len(data['assignments']),2)
        self.assertLessEqual(len(data['assignments'][1]['title']),160)
        self.assertEqual(len(data['exams']),1)

if __name__=='__main__':unittest.main()
