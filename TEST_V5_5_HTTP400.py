"""Offline HTTP-400 structured-error tests. No network or actual credentials."""
import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from TEST_V5_5_AI import ai

class ErrorCodesTests(unittest.TestCase):
    def setUp(self):
        self.patcher=patch.dict('os.environ',{'CLOUDFLARE_ACCOUNT_ID':'a'*32,'CLOUDFLARE_API_TOKEN':'secret-test-key'})
        self.patcher.start()
    def tearDown(self):
        self.patcher.stop()
    def test_code_5007_and_model_logged_no_secrets(self):
        response=SimpleNamespace(status_code=400,json=lambda:{'success':False,'errors':[{'code':5007,'message':'No such model with user secret user text'}]})
        buf=io.StringIO()
        with patch.object(ai.requests,'post',return_value=response),contextlib.redirect_stdout(buf):
            with self.assertRaises(ai.AIUnavailable) as cm:
                ai._provider_call(ai.CF_MODEL,[{'role':'user','content':'private prompt text'}],32)
        self.assertEqual(cm.exception.code,'http_400')
        self.assertIn('Cloudflare AI error codes: 5007',buf.getvalue())
        self.assertIn(ai.CF_MODEL,buf.getvalue())
        for s in ['secret-test-key','private prompt text','user secret user text']:
            self.assertNotIn(s,buf.getvalue())
    def test_no_json_response(self):
        response=SimpleNamespace(status_code=400,json=lambda:(_ for _ in ()).throw(ValueError('invalid')))
        buf=io.StringIO()
        with patch.object(ai.requests,'post',return_value=response),contextlib.redirect_stdout(buf):
            with self.assertRaises(ai.AIUnavailable):
                ai._provider_call(ai.GUARD_MODEL,[{'role':'user','content':'test'}],32)
        self.assertIn('Cloudflare AI error codes: not_provided',buf.getvalue())
        self.assertIn(ai.GUARD_MODEL,buf.getvalue())
    def test_nonnumeric_error_message_is_not_logged(self):
        response=SimpleNamespace(status_code=400,json=lambda:{'errors':[{'code':'NONSENSE','message':'very private text'}]})
        buf=io.StringIO()
        with patch.object(ai.requests,'post',return_value=response),contextlib.redirect_stdout(buf):
            with self.assertRaises(ai.AIUnavailable):
                ai._provider_call(ai.GUARD_MODEL,[{'role':'user','content':'test'}],32)
        self.assertIn('not_provided',buf.getvalue())
        self.assertNotIn('very private text',buf.getvalue())
if __name__=='__main__': unittest.main()
