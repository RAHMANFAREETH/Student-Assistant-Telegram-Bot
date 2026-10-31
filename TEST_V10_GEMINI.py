"""Gemini V10 tests: no network calls, no credentials, no persistent user content."""
from __future__ import annotations
import os
import sys
import types
import unittest
from unittest.mock import patch, Mock

import v10_gemini as g


class FakeRPC:
    def __init__(self, result=1, error=None):
        self.data = result
        self.error = error
        self.called = []
    def rpc(self, name, payload):
        self.called.append((name, payload))
        return self
    def execute(self):
        if self.error:
            raise self.error
        return self


class ConfigTests(unittest.TestCase):
    def test_gemini_disabled_by_default(self):
        with patch.dict(os.environ, {'V10_GEMINI_ENABLED':''}):
            self.assertFalse(g.enabled())
    def test_quota_bounds(self):
        for raw, expected in [('5',5), ('99',10), ('0',1),('bad',4),('',4)]:
            with self.subTest(raw=raw), patch.dict(os.environ, {'V10_GEMINI_DAILY_LIMIT':raw}):
                self.assertEqual(g.daily_limit(),expected)
    def test_pilot_cannot_use_gemini(self):
        with patch.dict(os.environ, {'STUDY_ACCESS_MODE':'pilot'}):
            self.assertFalse(g.adult_eligible(123))
    def test_verified_record_required(self):
        fake=types.ModuleType('study_access_v9')
        fake.is_verified_adult=lambda uid:uid==77
        with patch.dict(sys.modules, {'study_access_v9':fake}), patch.dict(os.environ, {'STUDY_ACCESS_MODE':'verified_adults'}):
            self.assertTrue(g.adult_eligible(77))
            self.assertFalse(g.adult_eligible(88))
    def test_db_verification_errors_fail_closed(self):
        fake=types.ModuleType('study_access_v9')
        def broken(uid):raise RuntimeError('db down')
        fake.is_verified_adult=broken
        with patch.dict(sys.modules, {'study_access_v9':fake}), patch.dict(os.environ, {'STUDY_ACCESS_MODE':'verified_adults'}):
            self.assertFalse(g.adult_eligible(77))
    def test_missing_key_rejected(self):
        client=types.ModuleType('gemini_ai_studio_v59')
        client.read_api_key=lambda:''
        with patch.dict(sys.modules,{'gemini_ai_studio_v59':client}), patch.dict(os.environ,{'V10_GEMINI_ENABLED':'true'}), \
             patch.object(g,'adult_eligible',return_value=True):
            with self.assertRaisesRegex(g.GeminiStudyError,'not configured'):
                g.validate(77)
    def test_unverified_blocks_even_with_key(self):
        client=types.ModuleType('gemini_ai_studio_v59')
        client.read_api_key=lambda:'fake-example-key'
        with patch.dict(sys.modules,{'gemini_ai_studio_v59':client}), patch.dict(os.environ,{'V10_GEMINI_ENABLED':'true'}), \
             patch.object(g,'adult_eligible',return_value=False):
            with self.assertRaisesRegex(g.GeminiStudyError,'verified'):
                g.validate(77)
    def test_script_detection(self):
        self.assertEqual(g.detect_language('தமிழ்'), 'tamil')
        self.assertEqual(g.detect_language('සිංහල'), 'sinhala')
        self.assertEqual(g.detect_language('اللغة'), 'arabic')
        self.assertEqual(g.detect_language('English'), 'english')


class QuotaTests(unittest.TestCase):
    def test_atomic_rpc_shape(self):
        db=FakeRPC(result=2)
        with patch.dict(os.environ,{'V10_GEMINI_DAILY_LIMIT':'4'}):
            self.assertEqual(g.claim_quota(123,db),2)
        self.assertEqual(db.called,[('v10_claim_gemini_quota',{'p_user_id':123,'p_daily_limit':4})])
    def test_reached_limit(self):
        with self.assertRaisesRegex(g.GeminiStudyError,'limit'):
            g.claim_quota(123,FakeRPC(result=0))
    def test_fail_closed_on_db_error(self):
        with self.assertRaisesRegex(g.GeminiStudyError,'unavailable'):
            g.claim_quota(123,FakeRPC(error=RuntimeError('Database secret diagnostic')))
    def test_bad_response_type(self):
        with self.assertRaisesRegex(g.GeminiStudyError,'invalid'):
            g.claim_quota(123,FakeRPC(result='2'))
    def test_postgrest_list_unwrapped(self):
        self.assertEqual(g.claim_quota(123,FakeRPC(result=[{'v10_claim_gemini_quota':1}])),1)
    def test_quota_out_of_range(self):
        with self.assertRaisesRegex(g.GeminiStudyError,'invalid'):
            g.claim_quota(123,FakeRPC(result=9))


class PromptTests(unittest.TestCase):
    sources=[{'title':'Science','page_number':5,'body':'Gravity pulls objects toward Earth.'}]
    def test_grounded_sources_cited(self):
        prompt=g.build_prompt('answer','What is gravity?',self.sources)
        self.assertIn('[S1] Science, page 5:',prompt)
        self.assertIn('UNTRUSTED DATA',prompt)
    def test_requires_evidence(self):
        with self.assertRaises(g.GeminiStudyError):g.build_prompt('answer','What is gravity?',[])
    def test_max_four_excerpts(self):
        prompt=g.build_prompt('answer','gravity?',self.sources*10)
        self.assertNotIn('[S5]',prompt)
    def test_prompt_is_bounded(self):
        prompt=g.build_prompt('answer','question'*300,self.sources*20)
        self.assertLessEqual(len(prompt),4700)
    def test_coach_requires_priorities(self):
        with self.assertRaises(g.GeminiStudyError):g.build_prompt('coach',priorities=[])
    def test_coach_uses_only_records(self):
        self.assertIn('Revise algebra',g.build_prompt('coach',priorities=['Revise algebra']))
    def test_viva_question_is_single(self):
        prompt=g.build_prompt('viva','gravity',self.sources)
        self.assertIn('ONE oral-exam question',prompt)
    def test_no_full_document_in_prompt(self):
        huge='Z'*45000
        prompt=g.build_prompt('answer','gravity',[{'title':'File','page_number':1,'body':huge}])
        self.assertLessEqual(prompt.count('Z'),700)
    def test_invalid_mode(self):
        with self.assertRaises(g.GeminiStudyError):g.build_prompt('bad','x',self.sources)


class ProviderTests(unittest.TestCase):
    sources=[{'title':'Science','page_number':5,'body':'Gravity pulls objects toward Earth.'}]
    def setUp(self):
        self.fake=types.ModuleType('gemini_ai_studio_v59')
        self.fake.read_api_key=lambda:'test-secret'
        class Error(RuntimeError):pass
        self.fake.GeminiClientError=Error
        self.fake.responses=[]
        fake=self.fake
        class Client:
            def __init__(self,key,timeout):
                if key!='test-secret':raise AssertionError('wrong key')
            def generate(self,prompt,task,language):
                fake.responses.append((prompt,task,language))
                return 'Gravity acts on objects [S1].'
        self.fake.GeminiClient=Client
        self.modules=patch.dict(sys.modules,{'gemini_ai_studio_v59':self.fake})
        self.modules.start()
        self.access=patch.object(g,'adult_eligible',return_value=True)
        self.access.start()
        self.flags=patch.dict(os.environ,{'V10_GEMINI_ENABLED':'true','STUDY_ACCESS_MODE':'verified_adults'})
        self.flags.start()
    def tearDown(self):
        self.modules.stop();self.access.stop();self.flags.stop()
    def test_verified_consent_api_call_one_quota(self):
        with patch.object(g,'claim_quota',return_value=1) as quota:
            answer=g.generate(77,'answer','What is gravity?',self.sources)
        self.assertIn('Gravity',answer)
        quota.assert_called_once_with(77)
        self.assertEqual(len(self.fake.responses),1)
        self.assertEqual(self.fake.responses[0][1:3],('ask','english'))
    def test_provider_never_called_when_unverified(self):
        with patch.object(g,'adult_eligible',return_value=False),patch.object(g,'claim_quota') as quota:
            with self.assertRaises(g.GeminiStudyError):g.generate(77,'answer','Gravity?',self.sources)
        quota.assert_not_called();self.assertEqual(self.fake.responses,[])
    def test_provider_never_called_when_quota_reached(self):
        with patch.object(g,'claim_quota',side_effect=g.GeminiStudyError('limit')):
            with self.assertRaises(g.GeminiStudyError):g.generate(77,'answer','Gravity?',self.sources)
        self.assertEqual(self.fake.responses,[])
    def test_per_provider_text_cap(self):
        with patch.object(g,'claim_quota',return_value=1):
            g.generate(77,'answer','Gravity?',self.sources)
        self.assertLessEqual(len(self.fake.responses[0][0]),4700)
    def test_ai_not_called_without_evidence(self):
        with patch.object(g,'claim_quota') as quota:
            with self.assertRaises(g.GeminiStudyError):g.generate(77,'answer','Gravity?',[])
        quota.assert_not_called();self.assertEqual(self.fake.responses,[])
    def test_busy_does_not_use_quota(self):
        with patch.object(g._GEMINI_SLOTS,'acquire',return_value=False),patch.object(g,'claim_quota') as quota:
            with self.assertRaisesRegex(g.GeminiStudyError,'busy'):
                g.generate(77,'answer','Gravity?',self.sources)
        quota.assert_not_called()
    def test_cancel_single_use_not_in_provider(self):
        # Bot tests separately prove no provider invocation before /v10confirm_ai.
        self.assertEqual(self.fake.responses,[])


if __name__ == '__main__':unittest.main()
